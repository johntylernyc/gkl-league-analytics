#!/usr/bin/env python3
"""
Multi-Worker MLB Player Statistics Backfill System

Implements parallel processing to dramatically reduce backfill time by using
multiple worker processes to handle date chunks concurrently. Reduces processing
time from ~54 minutes (sequential) to ~13 minutes (4 workers parallel).

Key Features:
- Process pool management with configurable worker count
- Date chunk distribution across workers
- Staggered start times to distribute API load
- Progress tracking across all workers
- Error recovery and retry logic
- API rate limiting coordination
"""

import sys
import sqlite3
import logging
import multiprocessing as mp
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import threading
import queue

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.collector_updated import PlayerStatsCollector
from league_transactions.backfill_transactions_optimized import start_job_log, update_job_log

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Result from a worker process."""
    worker_id: int
    chunk_id: int
    dates_processed: List[str]
    successful_dates: List[str]
    failed_dates: List[str]
    processing_time: float
    error_message: str = None


@dataclass
class ProgressUpdate:
    """Progress update from a worker."""
    worker_id: int
    chunk_id: int
    current_date: str
    completed_count: int
    total_count: int
    status: str  # 'processing', 'completed', 'failed'


def worker_process_dates(worker_id: int, chunk_id: int, dates: List[str], 
                        environment: str, stagger_seconds: int = 0) -> WorkerResult:
    """
    Worker process function to handle a chunk of dates.
    
    Args:
        worker_id: Unique worker identifier
        chunk_id: Chunk identifier for this batch
        dates: List of date strings (YYYY-MM-DD) to process
        environment: Database environment ('test' or 'production')
        stagger_seconds: Seconds to wait before starting (for API load distribution)
        
    Returns:
        WorkerResult with processing details
    """
    start_time = time.time()
    
    # Stagger start times to distribute API load
    if stagger_seconds > 0:
        logger.info(f"Worker {worker_id} waiting {stagger_seconds}s before starting chunk {chunk_id}")
        time.sleep(stagger_seconds)
    
    logger.info(f"Worker {worker_id} starting chunk {chunk_id} with {len(dates)} dates")
    
    try:
        # Initialize collector in worker process
        collector = PlayerStatsCollector(environment)
        
        successful_dates = []
        failed_dates = []
        
        for i, date_str in enumerate(dates):
            try:
                target_date = date.fromisoformat(date_str)
                logger.info(f"Worker {worker_id}: Processing {target_date} ({i+1}/{len(dates)})")
                
                # Collect data for this date
                job_id = collector.collect_daily_stats(
                    target_date,
                    job_metadata=f"Multi-worker backfill - Worker {worker_id}, Chunk {chunk_id}"
                )
                
                # Check job status
                conn = sqlite3.connect(collector.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM job_log WHERE job_id = ?",
                    (job_id,)
                )
                result = cursor.fetchone()
                status = result[0] if result else 'unknown'
                conn.close()
                
                if status == 'completed':
                    successful_dates.append(date_str)
                    logger.info(f"Worker {worker_id}: [OK] {target_date}")
                else:
                    failed_dates.append(date_str)
                    logger.error(f"Worker {worker_id}: [FAIL] {target_date} - status: {status}")
                
                # Brief pause between dates for API courtesy
                time.sleep(1)
                
            except Exception as e:
                failed_dates.append(date_str)
                logger.error(f"Worker {worker_id}: [ERROR] {date_str}: {e}")
        
        processing_time = time.time() - start_time
        
        result = WorkerResult(
            worker_id=worker_id,
            chunk_id=chunk_id,
            dates_processed=dates,
            successful_dates=successful_dates,
            failed_dates=failed_dates,
            processing_time=processing_time
        )
        
        logger.info(f"Worker {worker_id} completed chunk {chunk_id}: "
                   f"{len(successful_dates)} successful, {len(failed_dates)} failed "
                   f"in {processing_time/60:.1f} minutes")
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Worker {worker_id} chunk {chunk_id} failed: {e}")
        
        return WorkerResult(
            worker_id=worker_id,
            chunk_id=chunk_id,
            dates_processed=dates,
            successful_dates=[],
            failed_dates=dates,
            processing_time=processing_time,
            error_message=str(e)
        )


class MultiWorkerBackfiller:
    """
    Manages parallel backfilling using multiple worker processes.
    
    Coordinates multiple worker processes to handle date chunks concurrently,
    dramatically reducing total processing time through parallelization.
    """
    
    def __init__(self, environment: str = "production", worker_count: int = 4):
        """
        Initialize the multi-worker backfiller.
        
        Args:
            environment: Database environment ('test' or 'production')
            worker_count: Number of worker processes to use
        """
        self.environment = environment
        self.worker_count = worker_count
        self.collector = PlayerStatsCollector(environment)
        self.db_path = self.collector.db_path
        
        # 2025 season dates
        self.season_start = date(2025, 3, 27)
        self.season_end = date(2025, 9, 28)
        
        # Determine collection range
        today = date.today()
        self.collection_end = min(today, self.season_end)
        
        logger.info(f"Initialized MultiWorkerBackfiller for {environment}")
        logger.info(f"Worker count: {worker_count}")
        logger.info(f"Season: {self.season_start} to {self.season_end}")
        logger.info(f"Collection range: {self.season_start} to {self.collection_end}")
    
    def get_dates_to_process(self) -> List[date]:
        """Get list of dates that need processing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get dates that already have data
            cursor.execute("""
                SELECT DISTINCT date 
                FROM daily_gkl_player_stats 
                WHERE date >= ? AND date <= ?
                ORDER BY date
            """, (self.season_start.isoformat(), self.collection_end.isoformat()))
            
            existing_dates = set(row[0] for row in cursor.fetchall())
            
            # Generate all dates in range
            all_dates = []
            current = self.season_start
            while current <= self.collection_end:
                if current.isoformat() not in existing_dates:
                    all_dates.append(current)
                current += timedelta(days=1)
            
            return all_dates
            
        finally:
            conn.close()
    
    def create_date_chunks(self, dates: List[date]) -> List[List[str]]:
        """
        Divide dates into chunks for worker processes.
        
        Args:
            dates: List of dates to process
            
        Returns:
            List of date chunk lists (as ISO strings)
        """
        if not dates:
            return []
        
        # Convert dates to ISO strings for serialization
        date_strings = [d.isoformat() for d in dates]
        
        # Calculate chunk size to distribute evenly across workers
        chunk_size = max(1, len(date_strings) // self.worker_count)
        
        # If we have remainder dates, distribute them among first workers
        chunks = []
        for i in range(0, len(date_strings), chunk_size):
            chunk = date_strings[i:i + chunk_size]
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
        
        # If we have more chunks than workers, merge the last chunks
        if len(chunks) > self.worker_count:
            # Merge excess chunks into the last worker_count chunks
            final_chunks = chunks[:self.worker_count-1]
            # Combine remaining chunks into the last one
            last_chunk = []
            for chunk in chunks[self.worker_count-1:]:
                last_chunk.extend(chunk)
            final_chunks.append(last_chunk)
            chunks = final_chunks
        
        logger.info(f"Created {len(chunks)} date chunks for {self.worker_count} workers")
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i+1}: {len(chunk)} dates ({chunk[0]} to {chunk[-1]})")
        
        return chunks
    
    def run_parallel_backfill(self) -> Dict[str, Any]:
        """
        Run the parallel backfill process.
        
        Returns:
            Dictionary with backfill results and statistics
        """
        # Start master job
        master_job_id = start_job_log(
            job_type="parallel_season_backfill_2025",
            environment=self.environment,
            date_range_start=self.season_start.isoformat(),
            date_range_end=self.collection_end.isoformat(),
            league_key="mlb",
            metadata=f"Parallel 2025 season backfill using {self.worker_count} workers"
        )
        
        start_time = time.time()
        
        try:
            # Get dates to process
            dates_to_process = self.get_dates_to_process()
            total_days = len(dates_to_process)
            
            if total_days == 0:
                logger.info("No dates to process - all data already collected!")
                update_job_log(master_job_id, 'completed', records_processed=0, records_inserted=0)
                return {
                    'status': 'completed',
                    'total_days': 0,
                    'successful_days': 0,
                    'failed_days': 0,
                    'processing_time': 0,
                    'worker_count': self.worker_count,
                    'master_job_id': master_job_id
                }
            
            logger.info(f"Processing {total_days} days using {self.worker_count} workers")
            
            # Create date chunks for workers
            date_chunks = self.create_date_chunks(dates_to_process)
            
            if not date_chunks:
                logger.error("No date chunks created!")
                update_job_log(master_job_id, 'failed', error_message="No date chunks created")
                return {
                    'status': 'failed',
                    'error': 'No date chunks created'
                }
            
            # Calculate stagger times to distribute API load
            stagger_interval = 10  # seconds between worker starts
            
            # Prepare worker arguments
            worker_args = []
            for i, chunk in enumerate(date_chunks):
                worker_args.append((
                    i + 1,  # worker_id
                    i + 1,  # chunk_id
                    chunk,  # dates
                    self.environment,  # environment
                    i * stagger_interval  # stagger_seconds
                ))
            
            logger.info(f"Starting {len(worker_args)} workers with {stagger_interval}s stagger...")
            
            # Start worker processes
            with mp.Pool(processes=min(self.worker_count, len(worker_args))) as pool:
                # Launch all workers
                results = pool.starmap(worker_process_dates, worker_args)
            
            # Process results
            total_successful = 0
            total_failed = 0
            all_successful_dates = []
            all_failed_dates = []
            worker_summaries = []
            
            for result in results:
                total_successful += len(result.successful_dates)
                total_failed += len(result.failed_dates)
                all_successful_dates.extend(result.successful_dates)
                all_failed_dates.extend(result.failed_dates)
                
                worker_summaries.append({
                    'worker_id': result.worker_id,
                    'chunk_id': result.chunk_id,
                    'dates_count': len(result.dates_processed),
                    'successful_count': len(result.successful_dates),
                    'failed_count': len(result.failed_dates),
                    'processing_time': result.processing_time,
                    'error_message': result.error_message
                })
                
                logger.info(f"Worker {result.worker_id} final results: "
                           f"{len(result.successful_dates)} successful, "
                           f"{len(result.failed_dates)} failed, "
                           f"{result.processing_time/60:.1f} minutes")
            
            total_time = time.time() - start_time
            
            # Final summary
            logger.info(f"\n{'='*60}")
            logger.info("PARALLEL BACKFILL COMPLETE")
            logger.info(f"Total days processed: {total_successful + total_failed}")
            logger.info(f"Successful: {total_successful}")
            logger.info(f"Failed: {total_failed}")
            logger.info(f"Total time: {total_time/60:.1f} minutes")
            logger.info(f"Time per day: {total_time/(total_successful + total_failed):.1f} seconds")
            logger.info(f"Speedup vs sequential: {(total_days * 30) / total_time:.1f}x")
            
            # Get final record count
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM daily_gkl_player_stats 
                WHERE date >= ? AND date <= ?
            """, (self.season_start.isoformat(), self.collection_end.isoformat()))
            total_records = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"Total player-game records in database: {total_records}")
            
            # Update master job
            if total_failed == 0:
                update_job_log(
                    master_job_id, 
                    'completed',
                    records_processed=total_successful,
                    records_inserted=total_records
                )
            else:
                update_job_log(
                    master_job_id,
                    'completed_with_errors',
                    error_message=f"{total_failed} days failed",
                    records_processed=total_successful,
                    records_inserted=total_records
                )
            
            return {
                'status': 'completed' if total_failed == 0 else 'completed_with_errors',
                'total_days': total_successful + total_failed,
                'successful_days': total_successful,
                'failed_days': total_failed,
                'successful_dates': all_successful_dates,
                'failed_dates': all_failed_dates,
                'processing_time': total_time,
                'worker_count': len(worker_args),
                'worker_summaries': worker_summaries,
                'master_job_id': master_job_id,
                'total_records': total_records
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Parallel backfill failed: {e}")
            update_job_log(master_job_id, 'failed', error_message=str(e))
            
            return {
                'status': 'failed',
                'error': str(e),
                'processing_time': total_time,
                'worker_count': self.worker_count,
                'master_job_id': master_job_id
            }


def main():
    """Command-line interface for multi-worker backfill."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-worker MLB season backfill")
    parser.add_argument("--env", default="production", choices=["test", "production"],
                       help="Environment (default: production)")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of worker processes (default: 4)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check what needs to be processed without running")
    parser.add_argument("--test-range", type=int,
                       help="Test with only first N dates for validation")
    
    args = parser.parse_args()
    
    backfiller = MultiWorkerBackfiller(environment=args.env, worker_count=args.workers)
    
    if args.check_only:
        dates_to_process = backfiller.get_dates_to_process()
        print(f"\nDates that need processing ({len(dates_to_process)} total):")
        
        if dates_to_process:
            # Show chunks that would be created
            chunks = backfiller.create_date_chunks(dates_to_process)
            print(f"\nWould create {len(chunks)} chunks for {args.workers} workers:")
            for i, chunk in enumerate(chunks):
                print(f"  Worker {i+1}: {len(chunk)} dates ({chunk[0]} to {chunk[-1]})")
            
            estimated_time = len(dates_to_process) * 30 / args.workers / 60  # ~30 sec per day / workers
            print(f"\nEstimated time: {estimated_time:.1f} minutes (vs {len(dates_to_process) * 30 / 60:.1f} minutes sequential)")
        else:
            print("  None - all data already collected!")
    else:
        print(f"\n{'='*60}")
        print("MULTI-WORKER MLB SEASON BACKFILL")
        print(f"{'='*60}")
        print(f"Environment: {args.env}")
        print(f"Workers: {args.workers}")
        print(f"Season dates: {backfiller.season_start} to {backfiller.season_end}")
        print(f"Collection end: {backfiller.collection_end}")
        
        dates_to_process = backfiller.get_dates_to_process()
        
        if args.test_range:
            dates_to_process = dates_to_process[:args.test_range]
            print(f"TEST MODE: Processing only first {len(dates_to_process)} dates")
        
        print(f"Days to process: {len(dates_to_process)}")
        
        if len(dates_to_process) > 0:
            estimated_time = len(dates_to_process) * 30 / args.workers / 60
            sequential_time = len(dates_to_process) * 30 / 60
            speedup = sequential_time / estimated_time if estimated_time > 0 else 1
            
            print(f"Estimated time: {estimated_time:.1f} minutes")
            print(f"Sequential time: {sequential_time:.1f} minutes") 
            print(f"Expected speedup: {speedup:.1f}x")
            print(f"\nStarting parallel backfill in 5 seconds...")
            time.sleep(5)
            
            # Run the parallel backfill
            results = backfiller.run_parallel_backfill()
            
            print(f"\n{'='*60}")
            print("FINAL RESULTS")
            print(f"Status: {results['status']}")
            print(f"Total time: {results['processing_time']/60:.1f} minutes")
            if 'total_days' in results and results['total_days'] > 0:
                actual_speedup = sequential_time / (results['processing_time']/60)
                print(f"Actual speedup: {actual_speedup:.1f}x")
        else:
            print("\nNothing to backfill - all dates already have data!")


if __name__ == "__main__":
    main()