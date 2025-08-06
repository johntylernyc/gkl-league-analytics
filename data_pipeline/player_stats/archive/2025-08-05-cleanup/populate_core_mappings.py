#!/usr/bin/env python3
"""
Core Player ID Mapping Population

Populates the essential player ID mappings focusing on exact matches
between Yahoo Fantasy players and MLB stats players.
"""

import sys
import sqlite3
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_exact_matches():
    """Populate high-confidence exact name matches."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    # Load candidates
    candidates = pd.read_csv(candidates_path)
    exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
    
    logger.info(f"Processing {len(exact_matches)} exact matches")
    
    conn = sqlite3.connect(db_path, timeout=30)
    
    # Insert one by one to avoid issues
    inserted = 0
    for _, row in exact_matches.iterrows():
        try:
            conn.execute('''
                INSERT INTO player_id_mapping (
                    yahoo_player_id, yahoo_player_name, mlb_player_id, 
                    standardized_name, team_code, position_codes, 
                    confidence_score, mapping_method, validation_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['yahoo_player_id'],
                row['yahoo_player_name'],
                str(row['mlb_player_id']) if pd.notna(row['mlb_player_id']) else None,
                row['standardized_name'],
                row['team_code'],
                row['position_codes'],
                row['confidence_score'],
                'exact_name_match',
                'validated',
                datetime.now(),
                datetime.now()
            ))
            inserted += 1
            
            if inserted % 100 == 0:
                conn.commit()
                logger.info(f"Inserted {inserted}/{len(exact_matches)} exact matches")
                
        except Exception as e:
            logger.error(f"Error inserting {row['yahoo_player_name']}: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    logger.info(f"Successfully inserted {inserted} exact match mappings")
    return inserted


def main():
    """Run the core mapping population."""
    logger.info("Starting core player mapping population")
    
    inserted = populate_exact_matches()
    
    # Verify results
    db_path = root_dir / "database" / "league_analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM player_id_mapping')
    total = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM player_id_mapping 
        WHERE yahoo_player_id IS NOT NULL AND mlb_player_id IS NOT NULL
    ''')
    linked = cursor.fetchone()[0]
    
    conn.close()
    
    logger.info(f"=== RESULTS ===")
    logger.info(f"Total mappings: {total}")
    logger.info(f"Yahoo-MLB linked: {linked}")
    logger.info("Core mapping population complete!")


if __name__ == "__main__":
    main()