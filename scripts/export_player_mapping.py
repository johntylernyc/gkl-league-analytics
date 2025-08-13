#!/usr/bin/env python3
"""
Export player_mapping table from local database for D1 import
Date: 2025-08-13
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

def export_player_mapping():
    """Export player_mapping table to SQL for D1 import."""
    
    # Database path
    db_path = Path("R:/GitHub/gkl-league-analytics/database/league_analytics.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all player mappings
        cursor.execute("""
            SELECT 
                player_mapping_id,
                mlb_player_id,
                yahoo_player_id,
                baseball_reference_id,
                fangraphs_id,
                player_name,
                first_name,
                last_name,
                team_code,
                active,
                last_verified,
                created_at,
                updated_at
            FROM player_mapping
            ORDER BY player_mapping_id
        """)
        
        mappings = cursor.fetchall()
        print(f"Found {len(mappings)} player mappings to export")
        
        # Create output directory
        output_dir = Path("R:/GitHub/gkl-league-analytics/cloudflare-production/sql/incremental")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"player_mapping_complete_{timestamp}.sql"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"-- Complete Player Mapping Export\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Total Records: {len(mappings)}\n")
            f.write("-- This replaces all existing player_mapping data\n\n")
            
            # First, clear existing data
            f.write("-- Clear existing mappings\n")
            f.write("DELETE FROM player_mapping;\n\n")
            
            # Fix the schema - copy mlb_id to mlb_player_id if needed
            f.write("-- Ensure mlb_player_id column has data\n")
            f.write("UPDATE player_mapping SET mlb_player_id = mlb_id WHERE mlb_player_id IS NULL AND mlb_id IS NOT NULL;\n\n")
            
            # Write insert statements
            f.write("-- Insert all player mappings\n")
            for mapping in mappings:
                # Handle NULL values properly
                values = []
                for val in mapping:
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, str):
                        # Escape single quotes
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, bool):
                        values.append("1" if val else "0")
                    else:
                        values.append(str(val))
                
                f.write(f"INSERT INTO player_mapping (player_mapping_id, mlb_player_id, yahoo_player_id, ")
                f.write(f"baseball_reference_id, fangraphs_id, player_name, first_name, last_name, ")
                f.write(f"team_code, active, last_verified, created_at, updated_at) VALUES (")
                f.write(", ".join(values))
                f.write(");\n")
            
            # Add summary
            f.write(f"\n-- Export complete: {len(mappings)} records\n")
        
        print(f"\n[SUCCESS] Export completed successfully!")
        print(f"   Output file: {output_file}")
        
        # Show statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo,
                COUNT(baseball_reference_id) as with_bbref,
                COUNT(fangraphs_id) as with_fg
            FROM player_mapping
        """)
        stats = cursor.fetchone()
        print(f"\n[STATS] Statistics:")
        print(f"   Total mappings: {stats[0]}")
        print(f"   With Yahoo ID: {stats[1]} ({stats[1]*100//stats[0]}%)")
        print(f"   With Baseball Reference ID: {stats[2]} ({stats[2]*100//stats[0]}%)")
        print(f"   With Fangraphs ID: {stats[3]} ({stats[3]*100//stats[0]}%)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error during export: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    export_player_mapping()