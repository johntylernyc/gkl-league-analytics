#!/usr/bin/env python3
"""
Fix Yahoo ID mappings for star players

Corrects mapping issues for high-profile players where the mapping
candidates file has incomplete data.
"""

import sqlite3
import pandas as pd
from pathlib import Path

def fix_star_player_mappings():
    """Manually fix mappings for known star players."""
    
    root_dir = Path(__file__).parent.parent
    db_path = root_dir / "database" / "league_analytics.db"
    
    # Known star player mappings that need fixing
    # Format: (mlb_id, yahoo_id, player_name)
    star_player_fixes = [
        (660271, '11130', 'Shohei Ohtani'),  # Ohtani's Yahoo ID for batter
        (457705, '7382', 'Andrew McCutchen'),
        (518595, '8144', "Travis d'Arnaud"),
        (543877, '8650', 'Christian Vazquez'),
        (553869, '8897', 'Elias Diaz'),
        (572191, '9105', 'Michael A. Taylor'),
        (578428, '8424', 'Jose Iglesias'),
        (641598, '10029', 'Mitch Garver'),
        (641680, '10699', 'Jonah Heim'),
        (608701, '9589', 'Rob Refsnyder'),
        (624431, '9719', 'Jose Trevino'),
        (670764, '11473', 'Taylor Walls'),
        (456781, '7039', 'Donovan Solano'),
        (592773, '9230', 'Ryne Stanek'),
        (593974, '9304', 'Wandy Peralta'),
        (664702, '10970', 'Myles Straw'),
        (669397, '11413', 'Nick Allen'),
        (680474, '13524', 'Max Schuemann'),
    ]
    
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()
    
    print("Fixing star player Yahoo ID mappings...")
    
    total_updated = 0
    for mlb_id, yahoo_id, player_name in star_player_fixes:
        try:
            cursor.execute('''
                UPDATE daily_gkl_player_stats 
                SET yahoo_player_id = ?
                WHERE mlb_player_id = ? AND yahoo_player_id IS NULL
            ''', (yahoo_id, str(mlb_id)))
            
            updated = cursor.rowcount
            total_updated += updated
            
            if updated > 0:
                print(f"  + {player_name}: {updated} records updated")
            else:
                # Check if already has a Yahoo ID
                cursor.execute('''
                    SELECT DISTINCT yahoo_player_id 
                    FROM daily_gkl_player_stats 
                    WHERE mlb_player_id = ?
                ''', (str(mlb_id),))
                
                existing = cursor.fetchone()
                if existing and existing[0]:
                    print(f"  - {player_name}: Already has Yahoo ID {existing[0]}")
                else:
                    print(f"  ? {player_name}: No records found")
                    
        except Exception as e:
            print(f"  x {player_name}: Error - {e}")
    
    conn.commit()
    
    # Check final statistics
    cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
    filled = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats')
    total = cursor.fetchone()[0]
    
    print(f"\n=== RESULTS ===")
    print(f"Total records updated: {total_updated:,}")
    print(f"New fill rate: {filled:,}/{total:,} ({filled/total*100:.1f}%)")
    
    conn.close()

if __name__ == "__main__":
    fix_star_player_mappings()