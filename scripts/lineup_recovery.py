#!/usr/bin/env python3
"""Recovery script for lineup collection - skip errors and continue."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'data_pipeline'))

from daily_lineups.update_lineups import LineupUpdater
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_lineups_with_recovery():
    """Collect lineups with aggressive error recovery."""
    
    updater = LineupUpdater(use_d1=True, environment='production')
    league_key = '458.l.6966'
    
    # Get team keys
    team_keys = updater.get_all_team_keys(league_key)
    if not team_keys:
        logger.error("Could not fetch team keys")
        return
    
    logger.info(f"Found {len(team_keys)} teams")
    
    # Process recent dates only (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    logger.info(f"Collecting lineups from {start_date.date()} to {end_date.date()}")
    
    # Start job
    updater.start_job(
        job_type='lineup_recovery',
        date_range_start=str(start_date.date()),
        date_range_end=str(end_date.date()),
        league_key=league_key,
        metadata="Recovery collection with error handling"
    )
    
    success_count = 0
    error_count = 0
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        logger.info(f"Processing {date_str}")
        
        for team_key in team_keys:
            try:
                # Add delay to avoid rate limiting
                time.sleep(0.5)
                
                lineups = updater.fetch_and_parse_lineups(league_key, team_key, date_str)
                
                if lineups:
                    # Insert immediately to avoid losing data
                    new_count, dup_count = updater.insert_new_lineups(lineups)
                    if new_count > 0:
                        logger.info(f"  {team_key}: Added {new_count} players")
                        success_count += new_count
                    
            except Exception as e:
                logger.warning(f"  {team_key}: Error - {str(e)[:100]}")
                error_count += 1
                # Continue to next team
                continue
        
        current_date += timedelta(days=1)
    
    # Complete job
    updater.complete_job(
        records_processed=success_count + error_count,
        records_inserted=success_count,
        metadata=f"Success: {success_count}, Errors: {error_count}"
    )
    
    logger.info(f"Recovery complete: {success_count} records added, {error_count} errors")

if __name__ == "__main__":
    collect_lineups_with_recovery()