#!/usr/bin/env python3
"""Update position_codes to use Yahoo Fantasy eligible positions."""

import sqlite3
from pathlib import Path

def fix_eligible_positions():
    """Update position_codes with Yahoo Fantasy eligible positions."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get the most recent eligible_positions for each player
    # (positions can change during season, so we take the most recent)
    cursor.execute("""
        WITH recent_positions AS (
            SELECT 
                player_id,
                player_name,
                eligible_positions,
                MAX(date) as latest_date
            FROM daily_lineups
            WHERE player_id IS NOT NULL 
            AND eligible_positions IS NOT NULL
            GROUP BY player_id, eligible_positions
        ),
        ranked_positions AS (
            SELECT 
                player_id,
                player_name,
                eligible_positions,
                ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY latest_date DESC) as rn
            FROM recent_positions
        )
        SELECT 
            player_id,
            player_name,
            eligible_positions
        FROM ranked_positions
        WHERE rn = 1
    """)
    
    position_mapping = {}
    for row in cursor.fetchall():
        player_id = row[0]
        eligible = row[2]
        
        # Clean up the eligible positions
        # Remove IL, NA, BN (Injured List, Not Active, Bench)
        # Remove Util (utility is not a real position)
        positions = [p.strip() for p in eligible.split(',')]
        positions = [p for p in positions if p not in ['IL', 'NA', 'BN', 'Util']]
        
        if positions:
            # Join the cleaned positions
            position_mapping[player_id] = ','.join(positions)
    
    print(f"Found {len(position_mapping)} players with eligible positions")
    
    # Show some examples
    examples = list(position_mapping.items())[:10]
    print("\nSample position mappings:")
    for player_id, positions in examples:
        cursor.execute("SELECT player_name FROM daily_lineups WHERE player_id = ? LIMIT 1", (player_id,))
        name = cursor.fetchone()[0]
        print(f"  {name:20} ({player_id}): {positions}")
    
    # Update daily_gkl_player_stats
    print("\nUpdating daily_gkl_player_stats...")
    updated = 0
    
    for player_id, positions in position_mapping.items():
        cursor.execute("""
            UPDATE daily_gkl_player_stats
            SET position_codes = ?
            WHERE yahoo_player_id = ?
        """, (positions, player_id))
        updated += cursor.rowcount
    
    # For players not in our mapping, check if they're pitchers or position players
    # based on their stats (but only as a fallback)
    cursor.execute("""
        UPDATE daily_gkl_player_stats
        SET position_codes = 'P'
        WHERE (position_codes IS NULL OR position_codes = '' OR position_codes = 'POS')
        AND yahoo_player_id NOT IN (SELECT player_id FROM daily_lineups WHERE player_id IS NOT NULL)
        AND (pitching_innings_pitched > 0 OR pitching_games_started > 0)
    """)
    fallback_pitchers = cursor.rowcount
    
    # Leave the rest as NULL - we don't have their Yahoo eligibility
    cursor.execute("""
        UPDATE daily_gkl_player_stats
        SET position_codes = NULL
        WHERE position_codes = 'POS'
    """)
    removed_pos = cursor.rowcount
    
    conn.commit()
    
    print(f"\nUpdated {updated} records with eligible positions")
    print(f"Set {fallback_pitchers} as P (pitchers without lineup data)")
    print(f"Removed {removed_pos} generic 'POS' placeholders")
    
    # Show final distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN position_codes IS NULL THEN 'NULL'
                WHEN position_codes = '' THEN 'BLANK'
                ELSE position_codes
            END as positions,
            COUNT(*) as count
        FROM daily_gkl_player_stats
        GROUP BY positions
        ORDER BY count DESC
        LIMIT 20
    """)
    
    print("\nTop 20 position combinations:")
    print("Positions                    | Count")
    print("-" * 45)
    for row in cursor.fetchall():
        print(f"{row[0]:28} | {row[1]:7}")
    
    # Check specific players
    cursor.execute("""
        SELECT DISTINCT
            player_name,
            position_codes
        FROM daily_gkl_player_stats
        WHERE player_name IN ('Shohei Ohtani', 'Mookie Betts', 'Fernando Tatis Jr.', 
                              'Mike Trout', 'Aaron Judge', 'Jose Ramirez')
        ORDER BY player_name
    """)
    
    print("\nSpecific players:")
    for row in cursor.fetchall():
        pos = row[1] if row[1] else 'NULL'
        print(f"  {row[0]:20} : {pos}")
    
    conn.close()

if __name__ == "__main__":
    fix_eligible_positions()