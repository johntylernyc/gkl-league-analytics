#!/usr/bin/env python3
"""
Populate Baseball Reference and Fangraphs IDs

Uses pybaseball to lookup and populate external player IDs
for all players in the daily_gkl_player_stats table.
"""

import sqlite3
import pandas as pd
import pybaseball as pyb
import time
from pathlib import Path

def populate_external_ids():
    """Populate Baseball Reference and Fangraphs IDs using pybaseball."""
    
    root_dir = Path(__file__).parent.parent
    db_path = root_dir / "database" / "league_analytics.db"
    
    conn = sqlite3.connect(db_path, timeout=60)
    cursor = conn.cursor()
    
    # Get unique players from database
    cursor.execute('''
        SELECT DISTINCT mlb_player_id, player_name
        FROM daily_gkl_player_stats
        WHERE mlb_player_id IS NOT NULL
        AND (baseball_reference_id IS NULL OR fangraphs_id IS NULL)
        ORDER BY player_name
    ''')
    
    players = cursor.fetchall()
    print(f"Found {len(players)} unique players needing external IDs")
    
    # Process in batches
    updated_count = 0
    error_count = 0
    
    for i, (mlb_id, full_name) in enumerate(players):
        try:
            # Split name for lookup
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
                
                # Lookup player using pybaseball
                player_data = pyb.playerid_lookup(last_name, first_name)
                
                if not player_data.empty:
                    # Find the row with matching MLB ID
                    matching_row = player_data[player_data['key_mlbam'] == mlb_id]
                    
                    if matching_row.empty:
                        # If no exact match, use first result
                        matching_row = player_data.iloc[0]
                    else:
                        matching_row = matching_row.iloc[0]
                    
                    # Extract IDs
                    bbref_id = matching_row.get('key_bbref', None)
                    fangraphs_id = matching_row.get('key_fangraphs', None)
                    
                    # Convert fangraphs ID to string if it's numeric
                    if pd.notna(fangraphs_id):
                        fangraphs_id = str(int(fangraphs_id))
                    
                    # Update database
                    if bbref_id or fangraphs_id:
                        cursor.execute('''
                            UPDATE daily_gkl_player_stats
                            SET baseball_reference_id = COALESCE(?, baseball_reference_id),
                                fangraphs_id = COALESCE(?, fangraphs_id)
                            WHERE mlb_player_id = ?
                        ''', (bbref_id, fangraphs_id, str(mlb_id)))
                        
                        updated_count += cursor.rowcount
                        
                        if (i + 1) % 10 == 0:
                            conn.commit()
                            print(f"Processed {i + 1}/{len(players)} players, updated {updated_count} records")
                
                # Rate limiting to avoid overwhelming the API
                time.sleep(0.5)
                
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"Error processing {full_name}: {e}")
            
            # Continue with next player
            continue
        
        # Periodic commit
        if (i + 1) % 50 == 0:
            conn.commit()
    
    # Final commit
    conn.commit()
    
    # Check results
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            COUNT(baseball_reference_id) as bbref_count,
            COUNT(fangraphs_id) as fg_count
        FROM daily_gkl_player_stats
    ''')
    
    total, bbref_count, fg_count = cursor.fetchone()
    
    print(f"\n=== RESULTS ===")
    print(f"Total records: {total:,}")
    print(f"Baseball Reference IDs: {bbref_count:,} ({bbref_count/total*100:.1f}%)")
    print(f"Fangraphs IDs: {fg_count:,} ({fg_count/total*100:.1f}%)")
    print(f"Records updated: {updated_count:,}")
    
    if error_count > 0:
        print(f"Errors encountered: {error_count}")
    
    conn.close()

if __name__ == "__main__":
    populate_external_ids()