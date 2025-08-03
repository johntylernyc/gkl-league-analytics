#!/usr/bin/env python3
"""
Simple Yahoo Player ID Update

A minimal approach to update Yahoo Player IDs using the exact matches.
"""

import sys
import sqlite3
import pandas as pd
from pathlib import Path

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent

def update_yahoo_ids():
    """Update Yahoo Player IDs using exact matches."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    print("Loading mapping candidates...")
    candidates = pd.read_csv(candidates_path)
    exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
    print(f"Found {len(exact_matches)} exact matches")
    
    print("Connecting to database...")
    conn = sqlite3.connect(db_path, timeout=120)
    cursor = conn.cursor()
    
    updated_total = 0
    
    try:
        print("Updating records...")
        for i, (_, match) in enumerate(exact_matches.iterrows()):
            mlb_id = str(match['mlb_player_id'])
            yahoo_id = match['yahoo_player_id']
            
            cursor.execute('''
                UPDATE daily_gkl_player_stats 
                SET yahoo_player_id = ?
                WHERE mlb_player_id = ? AND yahoo_player_id IS NULL
            ''', (yahoo_id, mlb_id))
            
            updated_count = cursor.rowcount
            updated_total += updated_count
            
            if (i + 1) % 50 == 0:
                conn.commit()
                print(f"Processed {i + 1}/{len(exact_matches)}, updated {updated_total} records")
        
        conn.commit()
        
        # Check results
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
        final_count = cursor.fetchone()[0]
        
        print(f"Update complete!")
        print(f"Records updated: {updated_total}")
        print(f"Total with Yahoo ID: {final_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_yahoo_ids()