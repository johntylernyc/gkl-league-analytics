#!/usr/bin/env python3
"""Clean D1 player stats - remove .0 duplicates and bad data."""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'data_pipeline'))

from common.d1_connection import D1Connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_d1_duplicates():
    """Remove duplicate player records with .0 suffix and bad position codes."""
    
    # Initialize D1 connection
    d1 = D1Connection()
    
    try:
        # Step 1: Count problematic records
        logger.info("Analyzing D1 data quality issues...")
        
        # Records with .0
        result = d1.execute_query(
            "SELECT COUNT(*) as count FROM daily_gkl_player_stats WHERE yahoo_player_id LIKE '%.0'"
        )
        decimal_count = result[0].get('count', 0) if result and result[0] else 0
        logger.info(f"Records with .0 suffix: {decimal_count:,}")
        
        # Records with bad positions
        result = d1.execute_query(
            "SELECT COUNT(*) as count FROM daily_gkl_player_stats WHERE position_codes = 'POS'"
        )
        bad_pos_count = result[0].get('count', 0) if result and result[0] else 0
        logger.info(f"Records with generic 'POS': {bad_pos_count:,}")
        
        if decimal_count == 0 and bad_pos_count == 0:
            logger.info("No data quality issues found!")
            return
        
        # User confirmation
        print("\n" + "="*60)
        print("This will remove the following from D1:")
        print(f"- {decimal_count:,} records with .0 Yahoo IDs")
        print(f"- {bad_pos_count:,} records with generic 'POS' position")
        print("="*60)
        response = input("\nProceed with cleanup? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("Cleanup cancelled by user")
            return
        
        # Step 2: Remove records with .0 suffix
        if decimal_count > 0:
            logger.info("Removing records with .0 suffix...")
            d1.execute_query(
                "DELETE FROM daily_gkl_player_stats WHERE yahoo_player_id LIKE '%.0'"
            )
            logger.info(f"Removed {decimal_count:,} records with .0 suffix")
        
        # Step 3: Remove records with bad position codes
        if bad_pos_count > 0:
            logger.info("Removing records with generic 'POS'...")
            d1.execute_query(
                "DELETE FROM daily_gkl_player_stats WHERE position_codes = 'POS'"
            )
            logger.info(f"Removed {bad_pos_count:,} records with 'POS'")
        
        # Step 4: Verify cleanup
        logger.info("\nVerifying cleanup...")
        
        result = d1.execute_query(
            "SELECT COUNT(*) as total, COUNT(DISTINCT yahoo_player_id) as players FROM daily_gkl_player_stats"
        )
        if result and result[0]:
            logger.info(f"Remaining records: {result[0].get('total', 0):,}")
            logger.info(f"Unique players: {result[0].get('players', 0):,}")
        
        print("\n✅ Cleanup complete!")
        print("\nNote: This only removed duplicates and bad data.")
        print("You still need to run GitHub Actions to:")
        print("1. Fill in missing dates")
        print("2. Update position codes with correct eligible positions")
        
    except Exception as e:
        logger.error(f"Error cleaning D1: {e}")
        raise

if __name__ == "__main__":
    clean_d1_duplicates()