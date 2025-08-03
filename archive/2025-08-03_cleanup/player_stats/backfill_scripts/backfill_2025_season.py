#!/usr/bin/env python3
"""
Backfill 2025 MLB Season Player Statistics

This script backfills all player statistics for the 2025 MLB season
from the season start date through the current date (or season end).

Features:
- Batch processing by week for efficiency
- Progress tracking and resumption capability
- Error handling and retry logic
- Job logging for audit trail
"""

import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Tuple
import time

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


class SeasonBackfiller:
    """Manages backfilling of an entire MLB season."""
    
    def __init__(self, environment="production"):
        """Initialize the backfiller."""
        self.environment = environment
        self.collector = PlayerStatsCollector(environment)
        self.db_path = self.collector.db_path
        
        # 2025 season dates
        self.season_start = date(2025, 3, 27)
        self.season_end = date(2025, 9, 28)
        
        # Determine collection range
        today = date.today()
        self.collection_end = min(today, self.season_end)
        
        logger.info(f"Initialized SeasonBackfiller for {environment}")
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
    
    def process_date_batch(self, dates: List[date], batch_name: str) -> Tuple[int, int]:
        """
        Process a batch of dates.
        
        Returns:
            Tuple of (successful_days, failed_days)
        """
        successful = 0
        failed = 0
        
        for process_date in dates:
            try:
                logger.info(f"Processing {process_date}...")
                
                # Collect data for this date
                job_id = self.collector.collect_daily_stats(
                    process_date,
                    job_metadata=f"2025 season backfill - {batch_name}"
                )
                
                # Check job status
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT status FROM job_log WHERE job_id = ?",
                    (job_id,)
                )
                status = cursor.fetchone()[0]
                conn.close()
                
                if status == 'completed':
                    successful += 1
                    logger.info(f"  [OK] {process_date} completed")
                else:
                    failed += 1
                    logger.error(f"  [FAIL] {process_date} failed with status: {status}")
                
                # Brief pause between days to be respectful to API
                time.sleep(1)
                
            except Exception as e:
                failed += 1
                logger.error(f"  [ERROR] {process_date}: {e}")
        
        return successful, failed
    
    def run_backfill(self, batch_size: int = 7):
        """
        Run the full season backfill.
        
        Args:
            batch_size: Number of days to process in each batch (default 7 for weekly)
        """
        # Start master job
        master_job_id = start_job_log(
            job_type="season_backfill_2025",
            environment=self.environment,
            date_range_start=self.season_start.isoformat(),
            date_range_end=self.collection_end.isoformat(),
            league_key="mlb",
            metadata=f"Full 2025 season backfill"
        )
        
        try:
            # Get dates to process
            dates_to_process = self.get_dates_to_process()
            total_days = len(dates_to_process)
            
            if total_days == 0:
                logger.info("No dates to process - all data already collected!")
                update_job_log(master_job_id, 'completed', records_processed=0, records_inserted=0)
                return
            
            logger.info(f"Found {total_days} days to process")
            
            # Process in batches
            total_successful = 0
            total_failed = 0
            batch_num = 0
            
            for i in range(0, total_days, batch_size):
                batch_dates = dates_to_process[i:i+batch_size]
                batch_num += 1
                
                batch_start = batch_dates[0]
                batch_end = batch_dates[-1]
                batch_name = f"Batch {batch_num}: {batch_start} to {batch_end}"
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing {batch_name}")
                logger.info(f"Days in batch: {len(batch_dates)}")
                
                successful, failed = self.process_date_batch(batch_dates, batch_name)
                
                total_successful += successful
                total_failed += failed
                
                logger.info(f"Batch complete: {successful} successful, {failed} failed")
                
                # Progress update
                progress_pct = ((i + len(batch_dates)) / total_days) * 100
                logger.info(f"Overall progress: {progress_pct:.1f}% ({total_successful + total_failed}/{total_days} days)")
                
                # Brief pause between batches
                if i + batch_size < total_days:
                    logger.info("Pausing 5 seconds before next batch...")
                    time.sleep(5)
            
            # Final summary
            logger.info(f"\n{'='*60}")
            logger.info("BACKFILL COMPLETE")
            logger.info(f"Total days processed: {total_successful + total_failed}")
            logger.info(f"Successful: {total_successful}")
            logger.info(f"Failed: {total_failed}")
            
            # Get total records count
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
                
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            update_job_log(master_job_id, 'failed', error_message=str(e))
            raise


def main():
    """Run the 2025 season backfill."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill 2025 MLB season statistics")
    parser.add_argument("--env", default="production", choices=["test", "production"],
                       help="Environment (default: production)")
    parser.add_argument("--batch-size", type=int, default=7,
                       help="Days per batch (default: 7)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check what needs to be processed without running")
    
    args = parser.parse_args()
    
    backfiller = SeasonBackfiller(environment=args.env)
    
    if args.check_only:
        dates_to_process = backfiller.get_dates_to_process()
        print(f"\nDates that need processing ({len(dates_to_process)} total):")
        
        if dates_to_process:
            # Show first and last 5 dates
            if len(dates_to_process) <= 10:
                for d in dates_to_process:
                    print(f"  - {d}")
            else:
                print("  First 5 dates:")
                for d in dates_to_process[:5]:
                    print(f"    - {d}")
                print(f"  ... ({len(dates_to_process) - 10} more dates)")
                print("  Last 5 dates:")
                for d in dates_to_process[-5:]:
                    print(f"    - {d}")
        else:
            print("  None - all data already collected!")
    else:
        print(f"\n{'='*60}")
        print("2025 MLB SEASON BACKFILL")
        print(f"{'='*60}")
        print(f"Environment: {args.env}")
        print(f"Season dates: {backfiller.season_start} to {backfiller.season_end}")
        print(f"Collection end: {backfiller.collection_end}")
        print(f"Batch size: {args.batch_size} days")
        
        dates_to_process = backfiller.get_dates_to_process()
        print(f"Days to process: {len(dates_to_process)}")
        
        if len(dates_to_process) > 0:
            estimated_time = len(dates_to_process) * 35 / 60  # ~35 seconds per day based on test
            print(f"Estimated time: {estimated_time:.1f} minutes")
            print(f"\nStarting backfill in 5 seconds...")
            time.sleep(5)
            
            start_time = time.time()
            backfiller.run_backfill(batch_size=args.batch_size)
            
            elapsed = time.time() - start_time
            print(f"\nTotal time: {elapsed/60:.1f} minutes")
        else:
            print("\nNothing to backfill - all dates already have data!")


if __name__ == "__main__":
    main()