#!/usr/bin/env python3
"""Fix Yahoo player IDs to remove .0 decimal suffix."""

import sqlite3
from pathlib import Path

def fix_yahoo_ids():
    """Remove .0 from Yahoo player IDs."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # First check how many need fixing
    cursor.execute("""
        SELECT COUNT(DISTINCT yahoo_player_id) 
        FROM daily_gkl_player_stats 
        WHERE yahoo_player_id LIKE '%.0'
    """)
    to_fix = cursor.fetchone()[0]
    print(f"Yahoo IDs ending in .0: {to_fix}")
    
    if to_fix > 0:
        # Fix them by removing the .0
        cursor.execute("""
            UPDATE daily_gkl_player_stats
            SET yahoo_player_id = REPLACE(yahoo_player_id, '.0', '')
            WHERE yahoo_player_id LIKE '%.0'
        """)
        
        updated = cursor.rowcount
        conn.commit()
        print(f"Fixed {updated} records")
        
        # Verify the fix
        cursor.execute("""
            SELECT COUNT(*) 
            FROM daily_gkl_player_stats 
            WHERE yahoo_player_id LIKE '%.0'
        """)
        remaining = cursor.fetchone()[0]
        print(f"Remaining IDs with .0: {remaining}")
        
        # Show some examples of fixed IDs
        cursor.execute("""
            SELECT DISTINCT yahoo_player_id, player_name
            FROM daily_gkl_player_stats
            WHERE yahoo_player_id IN ('10031', '10036', '10047', '10056', '10068')
            LIMIT 5
        """)
        print("\nFixed examples:")
        for row in cursor.fetchall():
            print(f"  {row[0]} - {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    fix_yahoo_ids()