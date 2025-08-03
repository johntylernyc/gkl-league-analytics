#!/usr/bin/env python3
"""
Multi-Season Daily Lineups Backfill Script

This script performs large-scale backfill of daily lineup data across multiple seasons
using parallel processing and comprehensive error handling.

Features:
- Multi-season support (2021-2025)
- Parallel processing with configurable workers
- Automatic token refresh
- Progress tracking and checkpointing
- Resume capability for interrupted jobs
- Rate limiting and error recovery
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from multiprocessing import Process, Queue, current_process

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.season_manager import SeasonManager
from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.job_manager import LineupJobManager
from daily_lineups.config import get_database_path, get_lineup_table_name


class MultiSeasonBackfiller:
    """Manages multi-season backfill operations."""
    
    def __init__(self, environment="production", num_processes=2):
        self.environment = environment
        self.num_processes = num_processes
        self.season_manager = SeasonManager()
        self.job_manager = LineupJobManager(environment)
        self.db_path = get_database_path(environment)
        
    def get_missing_dates_for_season(self, season: int) -> List[str]:
        """Get list of missing dates for a specific season."""
        info = self.season_manager.get_season_info(season)
        if not info:
            return []
        
        # Check what data actually exists in the database
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            table_name = get_lineup_table_name(self.environment)
            
            # Get existing dates for this season (any team key format)
            cursor.execute(f"""
                SELECT DISTINCT date
                FROM {table_name}
                WHERE season = ?
                    AND date BETWEEN ? AND ?
                ORDER BY date
            """, (season, info['start_date'], info['end_date']))
            
            existing_dates = set(row[0] for row in cursor.fetchall())
            
            # Generate all dates in season range
            start = datetime.strptime(info['start_date'], "%Y-%m-%d").date()
            end = datetime.strptime(info['end_date'], "%Y-%m-%d").date()
            
            missing_dates = []
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                if date_str not in existing_dates:
                    missing_dates.append(date_str)
                current += timedelta(days=1)
            
            return missing_dates
            
        finally:
            conn.close()
    
    def analyze_missing_data(self, seasons: List[int]) -> Dict:
        """Analyze what data is missing across seasons."""
        print("Analyzing missing data across seasons...")
        
        analysis = {
            'total_missing_days': 0,
            'seasons': {},
            'priority_seasons': []
        }
        
        for season in seasons:
            missing_dates = self.get_missing_dates_for_season(season)
            season_info = self.season_manager.get_season_info(season)
            
            if season_info:
                total_days = self.season_manager.calculate_season_days(season)
                completion_pct = ((total_days - len(missing_dates)) / total_days) * 100
                
                analysis['seasons'][season] = {
                    'missing_days': len(missing_dates),
                    'total_days': total_days,
                    'completion_pct': completion_pct,
                    'league_key': season_info['league_key'],
                    'date_range': (season_info['start_date'], season_info['end_date'])
                }
                
                analysis['total_missing_days'] += len(missing_dates)
                
                # Prioritize seasons with significant missing data
                if len(missing_dates) > 10:  # More than 10 days missing
                    analysis['priority_seasons'].append(season)
        
        return analysis
    
    def create_collection_plan(self, seasons: List[int], mode: str = "missing") -> List[Dict]:
        """Create a collection plan for multiple seasons."""
        analysis = self.analyze_missing_data(seasons)
        
        print("\nCollection Analysis:")
        print("=" * 50)
        for season, data in analysis['seasons'].items():
            print(f"{season}: {data['missing_days']:3d} missing days "
                  f"({data['completion_pct']:5.1f}% complete)")
        
        print(f"\nTotal missing days: {analysis['total_missing_days']}")
        
        # Create collection jobs
        jobs = []
        
        if mode == "missing":
            # Collect only missing data for each season
            for season in seasons:
                missing_dates = self.get_missing_dates_for_season(season)
                if missing_dates:
                    season_info = self.season_manager.get_season_info(season)
                    
                    # Group consecutive dates for efficient collection
                    date_ranges = self._group_consecutive_dates(missing_dates)
                    
                    for start_date, end_date in date_ranges:
                        jobs.append({
                            'season': season,
                            'league_key': season_info['league_key'],
                            'start_date': start_date,
                            'end_date': end_date,
                            'estimated_days': (
                                datetime.strptime(end_date, "%Y-%m-%d") - 
                                datetime.strptime(start_date, "%Y-%m-%d")
                            ).days + 1
                        })
        
        elif mode == "full":
            # Full season collection for all seasons
            for season in seasons:
                season_info = self.season_manager.get_season_info(season)
                if season_info:
                    jobs.append({
                        'season': season,
                        'league_key': season_info['league_key'],
                        'start_date': season_info['start_date'],
                        'end_date': season_info['end_date'],
                        'estimated_days': self.season_manager.calculate_season_days(season)
                    })
        
        # Sort by estimated work (smaller jobs first for quick wins)
        jobs.sort(key=lambda x: x['estimated_days'])
        
        return jobs
    
    def _group_consecutive_dates(self, dates: List[str]) -> List[Tuple[str, str]]:
        """Group consecutive dates into ranges."""
        if not dates:
            return []
        
        # Sort dates
        sorted_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in dates])
        
        ranges = []
        start = sorted_dates[0]
        end = sorted_dates[0]
        
        for date in sorted_dates[1:]:
            if (date - end).days == 1:
                # Consecutive date, extend range
                end = date
            else:
                # Gap found, save current range and start new one
                ranges.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
                start = date
                end = date
        
        # Add final range
        ranges.append((start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        
        return ranges
    
    def run_collection_job(self, job: Dict, process_id: int, result_queue: Queue):
        """Run a single collection job in a worker process."""
        process_name = f"Worker-{process_id}"
        
        print(f"{process_name}: Starting {job['season']} "
              f"({job['start_date']} to {job['end_date']})")
        
        try:
            # Create collector for this process
            collector = EnhancedLineupsCollector(environment=self.environment)
            
            # Start collection with resume capability
            job_id = collector.collect_date_range_with_resume(
                start_date=job['start_date'],
                end_date=job['end_date'],
                league_key=job['league_key'],
                resume=False
            )
            
            # Get final job status
            manager = LineupJobManager(environment=self.environment)
            status = manager.get_job_status(job_id)
            
            result = {
                "process_id": process_id,
                "job_id": job_id,
                "season": job['season'],
                "start_date": job['start_date'],
                "end_date": job['end_date'],
                "status": status.get("status", "unknown"),
                "records_inserted": status.get("records_inserted", 0),
                "success": status.get("status") == "completed"
            }
            
            print(f"{process_name}: Completed {job['season']} "
                  f"({result['records_inserted']} records)")
            
        except Exception as e:
            print(f"{process_name}: Failed {job['season']}: {e}")
            result = {
                "process_id": process_id,
                "season": job['season'],
                "start_date": job['start_date'],
                "end_date": job['end_date'],
                "error": str(e),
                "success": False
            }
        
        result_queue.put(result)
    
    def run_parallel_backfill(self, jobs: List[Dict]) -> Dict:
        """Run parallel backfill across multiple jobs."""
        print(f"\nStarting parallel backfill with {self.num_processes} processes")
        print(f"Total jobs: {len(jobs)}")
        
        all_results = []
        
        # Process jobs in batches to avoid overwhelming the system
        batch_size = self.num_processes
        
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]
            print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} jobs)")
            
            processes = []
            result_queue = Queue()
            
            # Start processes for this batch
            for j, job in enumerate(batch):
                p = Process(
                    target=self.run_collection_job,
                    args=(job, j + 1, result_queue),
                    name=f"CollectionWorker-{j + 1}"
                )
                processes.append(p)
                p.start()
                
                # Stagger starts to avoid token conflicts
                time.sleep(2)
            
            # Wait for batch to complete
            for p in processes:
                p.join()
            
            # Collect results
            batch_results = []
            while not result_queue.empty():
                batch_results.append(result_queue.get())
            
            all_results.extend(batch_results)
            
            # Show batch summary
            successful = sum(1 for r in batch_results if r.get("success"))
            total_records = sum(r.get("records_inserted", 0) for r in batch_results)
            
            print(f"Batch complete: {successful}/{len(batch)} successful, "
                  f"{total_records:,} records")
            
            # Brief pause between batches
            if i + batch_size < len(jobs):
                print("Pausing 30 seconds between batches...")
                time.sleep(30)
        
        # Final summary
        summary = {
            "total_jobs": len(jobs),
            "successful": sum(1 for r in all_results if r.get("success")),
            "failed": sum(1 for r in all_results if not r.get("success")),
            "total_records": sum(r.get("records_inserted", 0) for r in all_results),
            "results": all_results
        }
        
        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-season daily lineups backfill")
    parser.add_argument("--seasons", default="2025",
                       help="Season range (e.g., '2021-2025') or comma-separated list")
    parser.add_argument("--mode", choices=["missing", "full"], default="missing",
                       help="Collection mode: missing data only or full seasons")
    parser.add_argument("--processes", type=int, default=2,
                       help="Number of parallel processes")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show plan without executing")
    parser.add_argument("--auto-confirm", action="store_true",
                       help="Skip confirmation prompt (auto-proceed)")
    
    args = parser.parse_args()
    
    # Parse seasons
    if '-' in args.seasons:
        start, end = args.seasons.split('-')
        seasons = list(range(int(start), int(end) + 1))
    else:
        seasons = [int(s.strip()) for s in args.seasons.split(',')]
    
    print(f"Multi-Season Daily Lineups Backfill")
    print(f"Seasons: {seasons}")
    print(f"Mode: {args.mode}")
    print(f"Processes: {args.processes}")
    print(f"Environment: {args.env}")
    
    # Initialize backfiller
    backfiller = MultiSeasonBackfiller(
        environment=args.env,
        num_processes=args.processes
    )
    
    # Create collection plan
    jobs = backfiller.create_collection_plan(seasons, args.mode)
    
    if not jobs:
        print("\nNo collection jobs needed - all data already present!")
        return 0
    
    print(f"\nCollection Plan ({len(jobs)} jobs):")
    print("-" * 60)
    for i, job in enumerate(jobs, 1):
        print(f"{i:2d}. {job['season']}: {job['start_date']} to {job['end_date']} "
              f"({job['estimated_days']} days)")
    
    total_days = sum(job['estimated_days'] for job in jobs)
    estimated_hours = (total_days * 12) / (args.processes * 1000)  # Conservative estimate
    
    print(f"\nTotal estimated days: {total_days}")
    print(f"Estimated time: {estimated_hours:.1f} hours")
    
    if args.dry_run:
        print("\nDry run complete - no data collected")
        return 0
    
    # Confirm execution unless auto-confirm is set
    if not args.auto_confirm:
        try:
            response = input(f"\nProceed with backfill? (y/N): ")
            if response.lower() != 'y':
                print("Backfill cancelled")
                return 0
        except EOFError:
            print("\nNon-interactive mode detected - use --auto-confirm to proceed")
            return 1
    else:
        print("\nAuto-confirm enabled - proceeding with backfill...")
    
    # Run backfill
    start_time = time.time()
    summary = backfiller.run_parallel_backfill(jobs)
    elapsed = time.time() - start_time
    
    # Final report
    print("\n" + "=" * 60)
    print("BACKFILL COMPLETE")
    print("=" * 60)
    print(f"Total time: {elapsed / 3600:.1f} hours")
    print(f"Jobs successful: {summary['successful']}/{summary['total_jobs']}")
    print(f"Records inserted: {summary['total_records']:,}")
    
    if summary['failed'] > 0:
        print(f"\nFailed jobs: {summary['failed']}")
        for result in summary['results']:
            if not result.get('success'):
                print(f"  {result['season']}: {result.get('error', 'Unknown error')}")
    
    print("=" * 60)
    
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())