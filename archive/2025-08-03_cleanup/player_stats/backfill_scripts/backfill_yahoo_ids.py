#!/usr/bin/env python3
"""
Backfill Yahoo Player IDs

Updates existing daily_gkl_player_stats records with yahoo_player_id values
using the name-based mappings we identified from our analysis.
"""

import sys
import sqlite3
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_mapping_table():
    """Populate the player_id_mapping table with exact matches from our analysis."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    if not candidates_path.exists():
        logger.error(f"Candidates file not found: {candidates_path}")
        return False
    
    logger.info("Populating player_id_mapping table with exact matches")
    
    # Read candidates
    candidates = pd.read_csv(candidates_path)
    exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
    
    logger.info(f"Found {len(exact_matches)} exact matches to insert")
    
    conn = sqlite3.connect(db_path, timeout=120)
    cursor = conn.cursor()
    
    try:
        # Clear existing mappings to avoid conflicts
        cursor.execute('DELETE FROM player_id_mapping')
        logger.info("Cleared existing mappings")
        
        # Insert exact matches in batches
        batch_size = 50
        inserted = 0
        
        for i in range(0, len(exact_matches), batch_size):
            batch = exact_matches.iloc[i:i+batch_size]
            
            records = []
            for _, row in batch.iterrows():
                records.append((
                    row['yahoo_player_id'],
                    row['yahoo_player_name'],
                    str(row['mlb_player_id']),
                    row['standardized_name'],
                    row['team_code'],
                    row['position_codes'],
                    0.95,  # confidence_score
                    'exact',
                    'valid',
                    datetime.now(),
                    datetime.now()
                ))
            
            cursor.executemany('''
                INSERT INTO player_id_mapping (
                    yahoo_player_id, yahoo_player_name, mlb_player_id,
                    standardized_name, team_code, position_codes,
                    confidence_score, mapping_method, validation_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            inserted += len(records)
            conn.commit()
            logger.info(f"Inserted batch: {inserted}/{len(exact_matches)} mappings")
        
        logger.info(f"✓ Successfully populated {inserted} player mappings")
        return True
        
    except Exception as e:
        logger.error(f"Error populating mapping table: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def backfill_yahoo_player_ids():
    """Backfill yahoo_player_id values in existing daily_gkl_player_stats records."""
    db_path = root_dir / "database" / "league_analytics.db"
    
    logger.info("Starting Yahoo Player ID backfill process")
    
    conn = sqlite3.connect(db_path, timeout=120)
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats')
        total_records = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
        with_yahoo = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM player_id_mapping')
        mappings_available = cursor.fetchone()[0]
        
        logger.info(f"Current state:")
        logger.info(f"  Total MLB stats records: {total_records}")
        logger.info(f"  Records with Yahoo ID: {with_yahoo}")
        logger.info(f"  Player mappings available: {mappings_available}")
        
        if mappings_available == 0:
            logger.error("No player mappings available. Run populate_mapping_table() first.")
            return False
        
        # Update records with yahoo_player_id using the mapping table
        logger.info("Updating records with Yahoo Player IDs...")
        
        cursor.execute('''
            UPDATE daily_gkl_player_stats
            SET yahoo_player_id = pm.yahoo_player_id,
                updated_at = CURRENT_TIMESTAMP
            FROM player_id_mapping pm
            WHERE daily_gkl_player_stats.mlb_player_id = pm.mlb_player_id
            AND pm.is_active = 1
            AND daily_gkl_player_stats.yahoo_player_id IS NULL
        ''')
        
        updated_count = cursor.rowcount
        conn.commit()
        
        # Check final state
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
        final_with_yahoo = cursor.fetchone()[0]
        
        logger.info(f"Backfill results:")
        logger.info(f"  Records updated: {updated_count}")
        logger.info(f"  Total with Yahoo ID: {final_with_yahoo}")
        logger.info(f"  Coverage: {(final_with_yahoo/total_records)*100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during backfill: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def validate_backfill_results():
    """Validate the backfill results and provide detailed analysis."""
    db_path = root_dir / "database" / "league_analytics.db"
    
    logger.info("Validating backfill results")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Overall statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_records,
                COUNT(yahoo_player_id) as with_yahoo_id,
                COUNT(DISTINCT mlb_player_id) as unique_mlb_players,
                COUNT(DISTINCT yahoo_player_id) as unique_yahoo_players
            FROM daily_gkl_player_stats
        ''')
        
        total, with_yahoo, unique_mlb, unique_yahoo = cursor.fetchone()
        
        logger.info(f"=== BACKFILL VALIDATION RESULTS ===")
        logger.info(f"Total records: {total:,}")
        logger.info(f"Records with Yahoo ID: {with_yahoo:,} ({(with_yahoo/total)*100:.1f}%)")
        logger.info(f"Unique MLB players: {unique_mlb:,}")
        logger.info(f"Unique Yahoo players: {unique_yahoo:,}")
        
        # Check linkage to daily_lineups
        cursor.execute('''
            SELECT COUNT(DISTINCT s.yahoo_player_id)
            FROM daily_gkl_player_stats s
            INNER JOIN daily_lineups l ON s.yahoo_player_id = l.player_id
            WHERE s.yahoo_player_id IS NOT NULL
        ''')
        
        linked_to_lineups = cursor.fetchone()[0]
        logger.info(f"Yahoo players linked to lineups: {linked_to_lineups:,}")
        
        # Sample some successful links
        cursor.execute('''
            SELECT s.yahoo_player_id, s.player_name, s.team_code, COUNT(*) as record_count
            FROM daily_gkl_player_stats s
            WHERE s.yahoo_player_id IS NOT NULL
            GROUP BY s.yahoo_player_id, s.player_name, s.team_code
            ORDER BY record_count DESC
            LIMIT 10
        ''')
        
        logger.info("Sample successful mappings:")
        for row in cursor.fetchall():
            logger.info(f"  {row[1]} ({row[0]}) - {row[2]} - {row[3]} records")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return False
    finally:
        conn.close()


def main():
    """Run the complete backfill process."""
    logger.info("=== YAHOO PLAYER ID BACKFILL PROCESS ===")
    
    # Step 1: Populate mapping table
    if not populate_mapping_table():
        logger.error("Failed to populate mapping table")
        return
    
    # Step 2: Backfill existing records
    if not backfill_yahoo_player_ids():
        logger.error("Failed to backfill Yahoo Player IDs")
        return
    
    # Step 3: Validate results
    if not validate_backfill_results():
        logger.error("Failed to validate results")
        return
    
    logger.info("✓ Yahoo Player ID backfill process completed successfully!")


if __name__ == "__main__":
    main()