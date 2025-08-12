#!/usr/bin/env python3
"""
Sync Player Mappings to D1

This script syncs player mappings from local SQLite to Cloudflare D1.
It handles both inserts and updates.

Usage:
    python sync_player_mappings_to_d1.py
"""

import sys
import sqlite3
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.common.d1_connection import D1Connection

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_player_mappings():
    """Sync player mappings from local SQLite to D1."""
    
    # Connect to local database
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    local_conn = sqlite3.connect(str(db_path))
    local_cursor = local_conn.cursor()
    
    # Connect to D1
    d1 = D1Connection()
    
    # Get all player mappings from local
    local_cursor.execute("""
        SELECT 
            mlb_id,
            yahoo_player_id,
            baseball_reference_id,
            fangraphs_id,
            player_name,
            first_name,
            last_name,
            team_code,
            active
        FROM player_mapping
        ORDER BY mlb_id
    """)
    
    local_mappings = local_cursor.fetchall()
    logger.info(f"Found {len(local_mappings)} player mappings in local database")
    
    # Check what's in D1
    result = d1.execute("SELECT COUNT(*) as count FROM player_mapping")
    d1_count = result['results'][0]['count'] if result and 'results' in result else 0
    logger.info(f"Current D1 player_mapping count: {d1_count}")
    
    # Process in batches
    batch_size = 100
    inserted = 0
    updated = 0
    errors = 0
    
    for i in range(0, len(local_mappings), batch_size):
        batch = local_mappings[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({i+1}-{min(i+batch_size, len(local_mappings))})")
        
        for mapping in batch:
            mlb_id, yahoo_id, bbref_id, fg_id, name, first, last, team, active = mapping
            
            try:
                # First check if it exists
                check_result = d1.execute(
                    "SELECT mlb_id FROM player_mapping WHERE mlb_id = ?",
                    [mlb_id]
                )
                
                if check_result and 'results' in check_result and check_result['results']:
                    # Update existing
                    d1.execute("""
                        UPDATE player_mapping 
                        SET mlb_player_id = ?,
                            yahoo_player_id = ?,
                            baseball_reference_id = ?,
                            fangraphs_id = ?,
                            player_name = ?,
                            first_name = ?,
                            last_name = ?,
                            team_code = ?,
                            active = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE mlb_id = ?
                    """, [mlb_id, yahoo_id, bbref_id, fg_id, name, first, last, team, active, mlb_id])
                    updated += 1
                else:
                    # Insert new
                    d1.execute("""
                        INSERT INTO player_mapping (
                            mlb_id,
                            mlb_player_id,
                            yahoo_player_id,
                            baseball_reference_id,
                            fangraphs_id,
                            player_name,
                            first_name,
                            last_name,
                            team_code,
                            active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [mlb_id, mlb_id, yahoo_id, bbref_id, fg_id, name, first, last, team, active])
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"Error processing player {name} (MLB ID {mlb_id}): {e}")
                errors += 1
        
        logger.info(f"  Batch complete. Total so far - Inserted: {inserted}, Updated: {updated}, Errors: {errors}")
    
    # Final verification
    final_result = d1.execute("SELECT COUNT(*) as count FROM player_mapping")
    final_count = final_result['results'][0]['count'] if final_result and 'results' in final_result else 0
    
    logger.info("\n" + "="*60)
    logger.info("SYNC COMPLETE")
    logger.info("="*60)
    logger.info(f"Starting D1 count: {d1_count}")
    logger.info(f"Final D1 count: {final_count}")
    logger.info(f"Records inserted: {inserted}")
    logger.info(f"Records updated: {updated}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Net change: +{final_count - d1_count}")
    
    # Check specific player that was missing
    check_result = d1.execute("""
        SELECT mlb_player_id, yahoo_player_id, baseball_reference_id, fangraphs_id
        FROM player_mapping
        WHERE mlb_player_id = 829272
    """)
    
    if check_result and 'results' in check_result and check_result['results']:
        player = check_result['results'][0]
        logger.info(f"\nVerification - Player 829272:")
        logger.info(f"  Yahoo: {player['yahoo_player_id']}")
        logger.info(f"  BBRef: {player['baseball_reference_id']}")
        logger.info(f"  FanGraphs: {player['fangraphs_id']}")
    
    local_conn.close()


if __name__ == '__main__':
    sync_player_mappings()