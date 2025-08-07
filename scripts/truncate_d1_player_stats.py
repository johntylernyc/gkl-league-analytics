#!/usr/bin/env python3
"""Truncate D1 player stats tables to prepare for clean data load."""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'data_pipeline'))

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try data_pipeline/.env
    env_path = Path(__file__).parent.parent / 'data_pipeline' / '.env'
    if env_path.exists():
        load_dotenv(env_path)

from common.d1_connection import D1Connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def truncate_d1_stats():
    """Truncate player stats tables in D1 to prepare for reload."""
    
    # Initialize D1 connection
    d1 = D1Connection()
    
    try:
        # First, check current state
        logger.info("Checking current D1 state...")
        
        # Count records
        result = d1.execute_query(
            "SELECT COUNT(*) as count FROM daily_gkl_player_stats"
        )
        if result and result[0]:
            current_count = result[0].get('count', 0)
            logger.info(f"Current records in D1: {current_count:,}")
        
        # Check for .0 decimals
        result = d1.execute_query(
            "SELECT COUNT(*) as count FROM daily_gkl_player_stats WHERE yahoo_player_id LIKE '%.0'"
        )
        if result and result[0]:
            decimal_count = result[0].get('count', 0)
            logger.info(f"Records with .0 decimal: {decimal_count:,}")
        
        # User confirmation
        print("\n" + "="*60)
        print("WARNING: This will DELETE all player stats data from D1!")
        print("="*60)
        response = input("\nProceed with truncation? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Truncation cancelled by user")
            return
        
        # Truncate the table
        logger.info("Truncating daily_gkl_player_stats table...")
        d1.execute_query("DELETE FROM daily_gkl_player_stats")
        logger.info("Table truncated successfully!")
        
        # Verify truncation
        result = d1.execute_query(
            "SELECT COUNT(*) as count FROM daily_gkl_player_stats"
        )
        if result and result[0]:
            new_count = result[0].get('count', 0)
            logger.info(f"Records after truncation: {new_count}")
            
            if new_count == 0:
                print("\n✅ SUCCESS: D1 player stats table is now empty and ready for clean data!")
                print("\nNext steps:")
                print("1. Merge the feature/player-stats-fixes branch to main")
                print("2. Trigger GitHub Actions with full date range (2025-03-27,2025-08-07)")
                print("3. Monitor the workflow to ensure successful data load")
            else:
                logger.error(f"Truncation may have failed - still {new_count} records")
        
    except Exception as e:
        logger.error(f"Error truncating D1: {e}")
        raise

if __name__ == "__main__":
    truncate_d1_stats()