#!/usr/bin/env python3
"""Clean up player stats data - remove duplicates and optimize."""

import sqlite3
from pathlib import Path

def cleanup_stats():
    """Remove duplicate records and optimize the stats table."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # First, identify duplicates (keeping the one with the highest stat_id)
    cursor.execute("""
        DELETE FROM daily_gkl_player_stats
        WHERE stat_id NOT IN (
            SELECT MAX(stat_id)
            FROM daily_gkl_player_stats
            GROUP BY date, yahoo_player_id
        )
    """)
    
    deleted = cursor.rowcount
    print(f"Removed {deleted} duplicate records")
    
    # Commit changes
    conn.commit()
    
    # Check final state
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT date) as days,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM daily_gkl_player_stats
    """)
    
    result = cursor.fetchone()
    print(f"\nFinal state:")
    print(f"  Total records: {result[0]}")
    print(f"  Days covered: {result[1]}")
    print(f"  Date range: {result[2]} to {result[3]}")
    
    conn.close()

if __name__ == "__main__":
    cleanup_stats()