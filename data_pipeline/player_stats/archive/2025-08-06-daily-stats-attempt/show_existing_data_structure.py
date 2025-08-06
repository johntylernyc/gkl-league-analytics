#!/usr/bin/env python3
"""
Show existing data structure from production database to understand what we need to collect
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment


def show_production_data_structure():
    """Show the structure of existing production data"""
    
    # Use production config
    config = get_config_for_environment('production')
    db_path = config['database_path']
    
    print(f"Examining production database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if we have the daily_lineups table with player data
    print("\n" + "="*80)
    print("CHECKING AVAILABLE TABLES")
    print("="*80)
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    print("Available tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check daily_lineups structure
    print("\n" + "="*80)
    print("DAILY_LINEUPS TABLE STRUCTURE")
    print("="*80)
    
    cursor.execute("PRAGMA table_info(daily_lineups)")
    columns = cursor.fetchall()
    
    print("Columns in daily_lineups:")
    for col in columns:
        print(f"  {col[1]:<25} {col[2]:<15} {'NOT NULL' if col[3] else 'NULL':<10} {f'DEFAULT {col[4]}' if col[4] else ''}")
    
    # Show sample daily lineup data
    print("\n" + "="*80)
    print("SAMPLE DAILY LINEUP DATA (Latest Date)")
    print("="*80)
    
    cursor.execute("""
        SELECT date, COUNT(DISTINCT team_key) as teams, COUNT(*) as total_players
        FROM daily_lineups
        WHERE date = (SELECT MAX(date) FROM daily_lineups)
        GROUP BY date
    """)
    
    result = cursor.fetchone()
    if result:
        latest_date, team_count, player_count = result
        print(f"Latest date: {latest_date}")
        print(f"Teams: {team_count}")
        print(f"Total player records: {player_count}")
        
        # Show sample player data
        print("\nSample player records:")
        cursor.execute("""
            SELECT 
                yahoo_player_id,
                player_name,
                team_name,
                position,
                is_starting
            FROM daily_lineups
            WHERE date = ?
            LIMIT 10
        """, (latest_date,))
        
        for row in cursor.fetchall():
            print(f"  {row[0]:<10} {row[1]:<20} {row[2]:<20} {row[3]:<10} {'Starting' if row[4] else 'Bench'}")
    
    # Check if we have any existing player stats table
    print("\n" + "="*80)
    print("CHECKING FOR PLAYER STATS TABLES")
    print("="*80)
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%player_stats%'
        ORDER BY name
    """)
    
    stats_tables = cursor.fetchall()
    if stats_tables:
        print("Found player stats tables:")
        for table in stats_tables:
            print(f"  - {table[0]}")
            
            # Show structure
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print(f"    Columns: {', '.join([col[1] for col in columns[:5]])}...")
    else:
        print("No player stats tables found in production")
    
    # Check transactions for player IDs
    print("\n" + "="*80)
    print("SAMPLE TRANSACTION DATA")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            transaction_type,
            COUNT(*) as count
        FROM transactions
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY transaction_type
        ORDER BY count DESC
    """)
    
    print("Recent transaction types:")
    for row in cursor.fetchall():
        print(f"  {row[0]:<15} {row[1]:>5}")
    
    # Show sample add/drop with player IDs
    cursor.execute("""
        SELECT 
            timestamp,
            transaction_type,
            team_name,
            player_name,
            player_key
        FROM transactions
        WHERE transaction_type IN ('add', 'drop')
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    print("\nSample add/drop transactions:")
    for row in cursor.fetchall():
        print(f"  {row[0]} {row[1]:<4} {row[2]:<15} {row[3]:<20} {row[4]}")
    
    conn.close()
    
    print("\n" + "="*80)
    print("DATA STRUCTURE ANALYSIS COMPLETE")
    print("="*80)
    print("\nKey findings:")
    print("1. Player IDs are available in daily_lineups and transactions tables")
    print("2. We have player names, teams, and positions")
    print("3. The yahoo_player_id format appears to be numeric (e.g., '15640')")
    print("4. Player keys in transactions use format '458.p.XXXXX'")
    print("\nNext steps:")
    print("1. Create a collector that fetches player stats from Yahoo API")
    print("2. Use existing player IDs from daily_lineups as the base")
    print("3. Map Yahoo stat IDs to our schema columns")


def main():
    """Main function"""
    show_production_data_structure()


if __name__ == "__main__":
    main()