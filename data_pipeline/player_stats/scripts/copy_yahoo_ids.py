#!/usr/bin/env python3
"""
Copy Yahoo player IDs from test database to production database

This script transfers the Yahoo ID mappings that were successfully collected
in the test environment to the production database.
"""

import sys
import sqlite3
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment


def copy_yahoo_ids():
    """Copy Yahoo IDs from test to production database"""
    
    # Get database paths
    test_config = get_config_for_environment('test')
    prod_config = get_config_for_environment('production')
    
    test_db = test_config['database_path']
    prod_db = prod_config['database_path']
    
    print(f"Source (test): {test_db}")
    print(f"Target (production): {prod_db}")
    
    # Connect to both databases
    test_conn = sqlite3.connect(test_db)
    prod_conn = sqlite3.connect(prod_db)
    
    try:
        # Get Yahoo ID mappings from test
        test_cursor = test_conn.cursor()
        test_cursor.execute("""
            SELECT mlb_id, yahoo_player_id, player_name
            FROM player_mapping
            WHERE yahoo_player_id IS NOT NULL
            ORDER BY player_name
        """)
        
        yahoo_mappings = test_cursor.fetchall()
        print(f"\nFound {len(yahoo_mappings)} Yahoo ID mappings in test database")
        
        # Update production database
        prod_cursor = prod_conn.cursor()
        updated = 0
        
        for mlb_id, yahoo_id, player_name in yahoo_mappings:
            # Update production mapping
            prod_cursor.execute("""
                UPDATE player_mapping
                SET yahoo_player_id = ?
                WHERE mlb_id = ?
                AND yahoo_player_id IS NULL
            """, (yahoo_id, mlb_id))
            
            if prod_cursor.rowcount > 0:
                updated += 1
                print(f"  Updated: {player_name} -> Yahoo ID {yahoo_id}")
        
        prod_conn.commit()
        
        # Verify results
        prod_cursor.execute("""
            SELECT COUNT(*) FROM player_mapping WHERE yahoo_player_id IS NOT NULL
        """)
        total_yahoo_ids = prod_cursor.fetchone()[0]
        
        print(f"\nCopy completed:")
        print(f"  Updated: {updated} player mappings")
        print(f"  Total Yahoo IDs in production: {total_yahoo_ids}")
        
        # Show coverage stats
        prod_cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo,
                COUNT(CASE WHEN active = 1 THEN 1 END) as active_total,
                COUNT(CASE WHEN active = 1 AND yahoo_player_id IS NOT NULL THEN 1 END) as active_with_yahoo
            FROM player_mapping
        """)
        
        stats = prod_cursor.fetchone()
        total, with_yahoo, active_total, active_with_yahoo = stats
        
        print(f"\nCoverage Statistics:")
        print(f"  All players: {with_yahoo}/{total} ({with_yahoo/total*100:.1f}%)")
        print(f"  Active players: {active_with_yahoo}/{active_total} ({active_with_yahoo/active_total*100:.1f}%)")
        
    except Exception as e:
        print(f"Error copying Yahoo IDs: {e}")
        prod_conn.rollback()
        raise
    finally:
        test_conn.close()
        prod_conn.close()


if __name__ == '__main__':
    copy_yahoo_ids()