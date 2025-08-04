"""
Parallel Collection Manager for Daily Lineups
Splits date ranges across multiple processes for faster collection.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
import sqlite3
import json
import logging
from multiprocessing import Process, Queue, current_process
from typing import List, Dict, Tuple, Optional
import time
import argparse

sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.job_manager import LineupJobManager
from daily_lineups.config import (
    LEAGUE_KEYS,
    SEASON_DATES,
    get_database_path
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ParallelCollectionManager:
    """Manages multiple collection processes running in parallel."""
    
    def __init__(self, environment="production", num_processes=2):
        """
        Initialize the parallel collection manager.
        
        Args:
            environment: 'production' or 'test'
            num_processes: Number of parallel processes to run
        """
        self.environment = environment
        self.num_processes = num_processes
        self.db_path = get_database_path(environment)
    
    def split_date_range(self, start_date: str, end_date: str, num_chunks: int) -> List[Tuple[str, str]]:
        """
        Split a date range into roughly equal chunks.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            num_chunks: Number of chunks to create
            
        Returns:
            List of (start, end) date tuples
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        total_days = (end_dt - start_dt).days + 1
        days_per_chunk = total_days // num_chunks
        extra_days = total_days % num_chunks
        
        chunks = []
        current_start = start_dt
        
        for i in range(num_chunks):
            # Add an extra day to earlier chunks if there's a remainder
            chunk_days = days_per_chunk + (1 if i < extra_days else 0)
            
            if chunk_days > 0:
                current_end = current_start + timedelta(days=chunk_days - 1)
                
                # Make sure we don't go past the end date
                if current_end > end_dt:
                    current_end = end_dt
                
                chunks.append((
                    current_start.strftime("%Y-%m-%d"),
                    current_end.strftime("%Y-%m-%d")
                ))
                
                current_start = current_end + timedelta(days=1)
        
        return chunks
    
    def find_uncollected_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Find dates that haven't been collected yet.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of uncollected dates
        """
        from daily_lineups.config import get_lineup_table_name
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get existing dates - use environment-specific table name
            table_name = get_lineup_table_name(self.environment)
            cursor.execute(f"""
                SELECT DISTINCT date
                FROM {table_name}
                WHERE date BETWEEN ? AND ?
            """, (start_date, end_date))
            
            existing = set(row[0] for row in cursor.fetchall())
            
            # Generate all dates in range
            uncollected = []
            current = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                if date_str not in existing:
                    uncollected.append(date_str)
                current += timedelta(days=1)
            
            return uncollected
            
        finally:
            conn.close()
    
    def collect_worker(self, process_id: int, start_date: str, end_date: str, 
                      league_key: str, result_queue: Queue):
        """
        Worker function for a collection process.
        
        Args:
            process_id: Process identifier
            start_date: Start date for this worker
            end_date: End date for this worker
            league_key: League key
            result_queue: Queue for reporting results
        """
        process_name = f"Worker-{process_id}"
        logger.info(f"{process_name} starting: {start_date} to {end_date}")
        
        try:
            # Create collector for this process
            collector = EnhancedLineupsCollector(environment=self.environment)
            
            # Start collection
            job_id = collector.collect_date_range_with_resume(
                start_date=start_date,
                end_date=end_date,
                league_key=league_key,
                resume=False
            )
            
            # Get job results
            manager = LineupJobManager(environment=self.environment)
            status = manager.get_job_status(job_id)
            
            result = {
                "process_id": process_id,
                "job_id": job_id,
                "start_date": start_date,
                "end_date": end_date,
                "status": status.get("status", "unknown"),
                "records_inserted": status.get("records_inserted", 0),
                "success": True
            }
            
            logger.info(f"{process_name} completed successfully")
            
        except Exception as e:
            logger.error(f"{process_name} failed: {e}")
            result = {
                "process_id": process_id,
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
                "success": False
            }
        
        result_queue.put(result)
    
    def run_parallel_collection(self, start_date: str, end_date: str, 
                               season: int = None, mode: str = "split"):
        """
        Run parallel collection across multiple processes.
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            season: Season year (for league key)
            mode: 'split' (divide range) or 'missing' (distribute uncollected dates)
            
        Returns:
            Summary of collection results
        """
        # Get league key
        if not season:
            season = int(start_date[:4])
        
        league_key = LEAGUE_KEYS.get(season)
        if not league_key:
            raise ValueError(f"No league key configured for season {season}")
        
        logger.info(f"Starting parallel collection with {self.num_processes} processes")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Mode: {mode}")
        
        processes = []
        result_queue = Queue()
        
        if mode == "split":
            # Split date range evenly across processes
            chunks = self.split_date_range(start_date, end_date, self.num_processes)
            
            for i, (chunk_start, chunk_end) in enumerate(chunks):
                p = Process(
                    target=self.collect_worker,
                    args=(i + 1, chunk_start, chunk_end, league_key, result_queue),
                    name=f"CollectionWorker-{i + 1}"
                )
                processes.append(p)
                p.start()
                logger.info(f"Started process {i + 1}: {chunk_start} to {chunk_end}")
                
                # Stagger process starts slightly to avoid token conflicts
                time.sleep(2)
        
        elif mode == "missing":
            # Find uncollected dates and distribute them
            uncollected = self.find_uncollected_dates(start_date, end_date)
            
            if not uncollected:
                logger.info("No uncollected dates found")
                return {"message": "No dates to collect", "total_dates": 0}
            
            logger.info(f"Found {len(uncollected)} uncollected dates")
            
            # Distribute dates across processes
            dates_per_process = len(uncollected) // self.num_processes
            extra = len(uncollected) % self.num_processes
            
            start_idx = 0
            for i in range(self.num_processes):
                # Calculate dates for this process
                num_dates = dates_per_process + (1 if i < extra else 0)
                if num_dates == 0:
                    break
                
                process_dates = uncollected[start_idx:start_idx + num_dates]
                start_idx += num_dates
                
                # Use first and last date as range
                chunk_start = process_dates[0]
                chunk_end = process_dates[-1]
                
                p = Process(
                    target=self.collect_worker,
                    args=(i + 1, chunk_start, chunk_end, league_key, result_queue),
                    name=f"CollectionWorker-{i + 1}"
                )
                processes.append(p)
                p.start()
                logger.info(f"Started process {i + 1}: {num_dates} dates")
                
                time.sleep(2)
        
        # Wait for all processes to complete
        logger.info("Waiting for all processes to complete...")
        for p in processes:
            p.join()
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # Summarize results
        summary = {
            "total_processes": len(processes),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "total_records": sum(r.get("records_inserted", 0) for r in results),
            "results": results
        }
        
        logger.info(f"Parallel collection completed: {summary['successful']}/{summary['total_processes']} successful")
        logger.info(f"Total records inserted: {summary['total_records']}")
        
        return summary


def monitor_parallel_jobs(environment="production"):
    """Monitor all running collection jobs."""
    from daily_lineups.config import get_lineup_table_name
    
    conn = sqlite3.connect('database/league_analytics.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT job_id, status, date_range_start, date_range_end,
               start_time, records_processed, records_inserted, progress_pct
        FROM job_log
        WHERE job_type = 'lineup_collection'
        AND status = 'running'
        ORDER BY start_time DESC
    """)
    
    jobs = cursor.fetchall()
    
    print(f"\nRunning Collection Jobs: {len(jobs)}")
    print("=" * 80)
    
    table_name = get_lineup_table_name(environment)
    
    for job in jobs:
        job_id = job[0]
        progress = job[7] if len(job) > 7 and job[7] is not None else 0.0
        print(f"Job: {job_id[:40]}...")
        print(f"  Range: {job[2]} to {job[3]}")
        print(f"  Started: {job[4]}")
        print(f"  Records: {job[6]}")
        print(f"  Progress: {progress:.1f}%")
        
        # Check progress
        cursor.execute(f"""
            SELECT COUNT(DISTINCT date) 
            FROM {table_name}
            WHERE job_id = ?
        """, (job_id,))
        
        days_done = cursor.fetchone()[0]
        print(f"  Days completed: {days_done}")
        print("-" * 40)
    
    conn.close()


def main():
    """Command-line interface for parallel collection."""
    
    parser = argparse.ArgumentParser(description="Run parallel lineup collection")
    parser.add_argument("command", choices=["collect", "monitor", "test"],
                       help="Command to execute")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--season", type=int, default=2025,
                       help="Season year (default: 2025)")
    parser.add_argument("--processes", type=int, default=2,
                       help="Number of parallel processes (default: 2)")
    parser.add_argument("--mode", choices=["split", "missing"], default="split",
                       help="Collection mode (default: split)")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment (default: production)")
    
    args = parser.parse_args()
    
    if args.command == "collect":
        if not args.start or not args.end:
            print("Error: --start and --end dates are required for collection")
            return 1
        
        manager = ParallelCollectionManager(
            environment=args.env,
            num_processes=args.processes
        )
        
        print(f"Starting parallel collection with {args.processes} processes")
        print(f"Date range: {args.start} to {args.end}")
        print(f"Mode: {args.mode}")
        print("-" * 60)
        
        summary = manager.run_parallel_collection(
            start_date=args.start,
            end_date=args.end,
            season=args.season,
            mode=args.mode
        )
        
        print("\nCollection Summary:")
        print(f"  Successful processes: {summary['successful']}/{summary['total_processes']}")
        print(f"  Total records inserted: {summary['total_records']}")
        
        if summary.get('results'):
            print("\nProcess Details:")
            for r in summary['results']:
                if r.get('success'):
                    print(f"  Process {r['process_id']}: SUCCESS ({r['records_inserted']} records)")
                else:
                    print(f"  Process {r['process_id']}: FAILED - {r.get('error', 'Unknown error')}")
    
    elif args.command == "monitor":
        monitor_parallel_jobs()
    
    elif args.command == "test":
        # Test date splitting
        manager = ParallelCollectionManager(num_processes=args.processes)
        
        if not args.start or not args.end:
            args.start = "2025-04-01"
            args.end = "2025-04-10"
        
        print(f"Testing date split for {args.processes} processes")
        print(f"Date range: {args.start} to {args.end}")
        print("-" * 40)
        
        chunks = manager.split_date_range(args.start, args.end, args.processes)
        
        for i, (start, end) in enumerate(chunks, 1):
            start_dt = datetime.strptime(start, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end, "%Y-%m-%d").date()
            days = (end_dt - start_dt).days + 1
            
            print(f"Process {i}: {start} to {end} ({days} days)")
        
        # Check for missing dates
        print("\nChecking for uncollected dates...")
        uncollected = manager.find_uncollected_dates(args.start, args.end)
        print(f"Found {len(uncollected)} uncollected dates")
        if uncollected and len(uncollected) <= 10:
            for date in uncollected:
                print(f"  - {date}")


if __name__ == "__main__":
    main()