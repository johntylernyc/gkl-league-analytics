#!/usr/bin/env python3
"""Fix position codes in daily_gkl_player_stats using data from daily_lineups."""

import sqlite3
from pathlib import Path
from collections import defaultdict

def fix_position_codes():
    """Update position_codes using actual position data from daily_lineups."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # First, get the most common position for each player from daily_lineups
    cursor.execute("""
        SELECT 
            player_id,
            player_name,
            selected_position,
            COUNT(*) as times_played
        FROM daily_lineups
        WHERE player_id IS NOT NULL 
        AND selected_position IS NOT NULL
        AND selected_position NOT IN ('BN', 'IL', 'NA')  -- Exclude bench/injured
        GROUP BY player_id, player_name, selected_position
        ORDER BY player_id, times_played DESC
    """)
    
    # Build a mapping of player_id to their primary position
    player_positions = {}
    player_names = {}
    
    for row in cursor.fetchall():
        player_id = row[0]
        player_name = row[1]
        position = row[2]
        
        if player_id not in player_positions:
            # First position for this player (most common)
            if position in ['SP', 'RP']:
                player_positions[player_id] = 'P'
            elif position == 'Util':
                # Skip Util as it's not a real position
                continue
            else:
                player_positions[player_id] = position
            player_names[player_id] = player_name
    
    print(f"Found {len(player_positions)} players with position data")
    
    # Show position distribution
    position_counts = defaultdict(int)
    for pos in player_positions.values():
        position_counts[pos] += 1
    
    print("\nPosition distribution from lineups:")
    for pos, count in sorted(position_counts.items()):
        print(f"  {pos:4} : {count:4} players")
    
    # Now update daily_gkl_player_stats
    print("\nUpdating daily_gkl_player_stats...")
    
    updated = 0
    for player_id, position in player_positions.items():
        cursor.execute("""
            UPDATE daily_gkl_player_stats
            SET position_codes = ?
            WHERE yahoo_player_id = ?
        """, (position, player_id))
        updated += cursor.rowcount
    
    # For players not in lineups, use simple P/POS logic based on their stats
    cursor.execute("""
        UPDATE daily_gkl_player_stats
        SET position_codes = 'P'
        WHERE (position_codes IS NULL OR position_codes = '')
        AND (pitching_innings_pitched > 0 OR pitching_games_started > 0)
    """)
    updated += cursor.rowcount
    
    cursor.execute("""
        UPDATE daily_gkl_player_stats
        SET position_codes = 'POS'
        WHERE (position_codes IS NULL OR position_codes = '')
        AND batting_at_bats > 0
        AND (pitching_innings_pitched = 0 OR pitching_innings_pitched IS NULL)
    """)
    updated += cursor.rowcount
    
    conn.commit()
    print(f"\nUpdated {updated} records")
    
    # Verify the results
    cursor.execute("""
        SELECT 
            position_codes,
            COUNT(*) as count
        FROM daily_gkl_player_stats
        GROUP BY position_codes
        ORDER BY count DESC
    """)
    
    print("\nFinal position distribution:")
    print("Position | Count")
    print("-" * 20)
    for row in cursor.fetchall():
        pos = row[0] if row[0] else 'NULL'
        print(f"{pos:8} | {row[1]:7}")
    
    # Show some examples
    cursor.execute("""
        SELECT DISTINCT
            player_name,
            position_codes
        FROM daily_gkl_player_stats
        WHERE player_name IN ('Mike Trout', 'Shohei Ohtani', 'Aaron Judge', 
                              'Mookie Betts', 'Gerrit Cole', 'Salvador Perez')
        ORDER BY player_name
    """)
    
    print("\nSample players:")
    for row in cursor.fetchall():
        print(f"  {row[0]:20} : {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    fix_position_codes()