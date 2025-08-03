#!/usr/bin/env python3
"""
Continue 2025 season backfill with automatic resumption.
Processes remaining dates in small batches to avoid timeouts.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from player_stats.backfill_2025_season import SeasonBackfiller
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def run_partial_backfill(max_days=10):
    """Run backfill for a limited number of days."""
    backfiller = SeasonBackfiller(environment="production")
    
    # Get remaining dates
    dates_to_process = backfiller.get_dates_to_process()
    
    if not dates_to_process:
        logger.info("Backfill complete - no more dates to process!")
        return 0
    
    # Process only max_days at a time
    dates_batch = dates_to_process[:max_days]
    
    logger.info(f"Processing {len(dates_batch)} days out of {len(dates_to_process)} remaining")
    logger.info(f"First date: {dates_batch[0]}")
    logger.info(f"Last date: {dates_batch[-1]}")
    
    successful, failed = backfiller.process_date_batch(dates_batch, f"Batch {dates_batch[0]} to {dates_batch[-1]}")
    
    logger.info(f"Batch complete: {successful} successful, {failed} failed")
    logger.info(f"Remaining dates: {len(dates_to_process) - len(dates_batch)}")
    
    return len(dates_to_process) - len(dates_batch)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Continue 2025 backfill")
    parser.add_argument("--days", type=int, default=10, help="Days to process (default: 10)")
    parser.add_argument("--loop", action="store_true", help="Continue until complete")
    
    args = parser.parse_args()
    
    if args.loop:
        remaining = 1
        batch_num = 0
        while remaining > 0:
            batch_num += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH {batch_num}")
            logger.info(f"{'='*60}")
            
            remaining = run_partial_backfill(args.days)
            
            if remaining > 0:
                logger.info(f"Pausing 5 seconds before next batch...")
                time.sleep(5)
        
        logger.info("\n" + "="*60)
        logger.info("BACKFILL COMPLETE!")
    else:
        run_partial_backfill(args.days)