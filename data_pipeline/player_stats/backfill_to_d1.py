#!/usr/bin/env python3
"""
Backfill Player Stats from Local to D1

This script backfills historical player stats data from the local SQLite database
to Cloudflare D1. It handles the data in batches to avoid timeouts and includes
progress tracking.

Usage:
    python backfill_to_d1.py
    python backfill_to_d1.py --start 2025-03-27 --end 2025-08-08
    python backfill_to_d1.py --days-per-batch 7
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.comprehensive_collector import ComprehensiveStatsCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def backfill_date_range(start_date: str, end_date: str, batch_days: int = 7):
    """
    Backfill player stats for a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        batch_days: Number of days to process in each batch
    """
    logger.info(f"Starting backfill from {start_date} to {end_date}")
    
    # Initialize collector with D1
    collector = ComprehensiveStatsCollector(environment='production', use_d1=True)
    
    # Convert dates
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    total_days = (end - current).days + 1
    processed_days = 0
    successful_days = 0
    failed_days = 0
    total_records = 0
    
    logger.info(f"Processing {total_days} days in batches of {batch_days}")
    
    while current <= end:
        # Calculate batch end date
        batch_end = min(current + timedelta(days=batch_days - 1), end)
        batch_size = (batch_end - current).days + 1
        
        logger.info(f"\n--- Processing batch: {current.date()} to {batch_end.date()} ({batch_size} days) ---")
        
        # Process each day in the batch
        batch_date = current
        while batch_date <= batch_end:
            date_str = batch_date.strftime('%Y-%m-%d')
            processed_days += 1
            
            try:
                logger.info(f"[{processed_days}/{total_days}] Processing {date_str}...")
                
                # Collect stats for this date
                records = collector.collect_daily_stats(date_str)
                
                if records > 0:
                    logger.info(f"  ✓ Successfully processed {records} player records")
                    successful_days += 1
                    total_records += records
                else:
                    logger.warning(f"  ⚠ No records found for {date_str}")
                    
            except Exception as e:
                logger.error(f"  ✗ Failed to process {date_str}: {e}")
                failed_days += 1
            
            batch_date += timedelta(days=1)
        
        # Move to next batch
        current = batch_end + timedelta(days=1)
        
        # Progress summary
        logger.info(f"\nProgress: {processed_days}/{total_days} days completed")
        logger.info(f"  Successful: {successful_days}, Failed: {failed_days}, Total Records: {total_records}")
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("BACKFILL COMPLETE")
    logger.info("="*60)
    logger.info(f"Total days processed: {processed_days}")
    logger.info(f"Successful days: {successful_days}")
    logger.info(f"Failed days: {failed_days}")
    logger.info(f"Total records inserted: {total_records}")
    
    if failed_days > 0:
        logger.warning(f"\n⚠ {failed_days} days failed. You may want to re-run for those specific dates.")
    
    return {
        'processed': processed_days,
        'successful': successful_days,
        'failed': failed_days,
        'total_records': total_records
    }


def verify_d1_data():
    """Verify data in D1 after backfill."""
    try:
        from data_pipeline.common.d1_connection import D1Connection
        
        d1 = D1Connection()
        
        # Check total records
        result = d1.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                COUNT(DISTINCT date) as unique_dates,
                COUNT(DISTINCT mlb_player_id) as unique_players
            FROM daily_gkl_player_stats
        """)
        
        if result and 'results' in result and result['results']:
            stats = result['results'][0]
            logger.info("\n" + "="*60)
            logger.info("D1 DATABASE VERIFICATION")
            logger.info("="*60)
            logger.info(f"Total records: {stats['total_records']}")
            logger.info(f"Date range: {stats['earliest_date']} to {stats['latest_date']}")
            logger.info(f"Unique dates: {stats['unique_dates']}")
            logger.info(f"Unique players: {stats['unique_players']}")
            
            # Check recent dates
            recent_result = d1.execute("""
                SELECT date, COUNT(*) as count
                FROM daily_gkl_player_stats
                GROUP BY date
                ORDER BY date DESC
                LIMIT 5
            """)
            
            if recent_result and 'results' in recent_result:
                logger.info("\nRecent dates:")
                for row in recent_result['results']:
                    logger.info(f"  {row['date']}: {row['count']} records")
                    
    except Exception as e:
        logger.error(f"Failed to verify D1 data: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Backfill player stats from local database to Cloudflare D1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--start', default='2025-03-27',
                       help='Start date (YYYY-MM-DD), default: 2025-03-27')
    parser.add_argument('--end', default='2025-08-08',
                       help='End date (YYYY-MM-DD), default: 2025-08-08')
    parser.add_argument('--days-per-batch', type=int, default=7,
                       help='Number of days to process per batch (default: 7)')
    parser.add_argument('--verify-only', action='store_true',
                       help='Only verify existing D1 data without backfilling')
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_d1_data()
    else:
        # Run backfill
        results = backfill_date_range(
            start_date=args.start,
            end_date=args.end,
            batch_days=args.days_per_batch
        )
        
        # Verify after backfill
        if results['successful'] > 0:
            verify_d1_data()


if __name__ == '__main__':
    main()