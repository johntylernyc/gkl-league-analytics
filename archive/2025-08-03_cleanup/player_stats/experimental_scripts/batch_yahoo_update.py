#!/usr/bin/env python3
"""
Batch Yahoo Player ID Update

Updates Yahoo Player IDs in daily_gkl_player_stats using exact matches
in smaller batches to avoid database locks.
"""

import sqlite3
import pandas as pd
import time
from pathlib import Path

def batch_update_yahoo_ids():
    """Update Yahoo Player IDs in small batches."""
    root_dir = Path(__file__).parent.parent
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    print("Loading mapping candidates...")
    candidates = pd.read_csv(candidates_path)
    
    # Remove duplicates and get exact matches
    exact_matches = candidates[
        candidates['mapping_method'] == 'exact_name_match'
    ].drop_duplicates(subset=['mlb_player_id']).copy()
    
    print(f"Found {len(exact_matches)} unique exact matches")
    
    updated_total = 0
    batch_size = 10
    
    for i in range(0, len(exact_matches), batch_size):
        batch = exact_matches.iloc[i:i+batch_size]
        
        print(f"Processing batch {i//batch_size + 1}: {len(batch)} records")
        
        # Use shorter timeout and new connection for each batch
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        try:
            batch_updated = 0
            for _, match in batch.iterrows():
                mlb_id = str(int(match['mlb_player_id']))  # Ensure integer conversion
                yahoo_id = match['yahoo_player_id']
                
                cursor.execute('''
                    UPDATE daily_gkl_player_stats 
                    SET yahoo_player_id = ?
                    WHERE mlb_player_id = ? AND yahoo_player_id IS NULL
                ''', (yahoo_id, mlb_id))
                
                batch_updated += cursor.rowcount
            
            conn.commit()
            updated_total += batch_updated
            
            print(f"  Updated {batch_updated} records (total: {updated_total})")
            
        except Exception as e:
            print(f"  Error in batch: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        # Small delay between batches
        time.sleep(0.5)
    
    # Final check
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
    final_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n=== UPDATE COMPLETE ===")
    print(f"Records updated: {updated_total:,}")
    print(f"Total with Yahoo ID: {final_count:,}")
    print(f"Fill rate: {final_count/total_count*100:.1f}%")

if __name__ == "__main__":
    batch_update_yahoo_ids()