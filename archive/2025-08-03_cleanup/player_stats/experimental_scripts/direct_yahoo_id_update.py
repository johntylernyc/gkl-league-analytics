#!/usr/bin/env python3
"""
Direct Yahoo Player ID Update

Directly updates existing daily_gkl_player_stats records with yahoo_player_id 
values using the exact matches from our analysis, bypassing the mapping table.
"""

import sys
import sqlite3
import logging
import pandas as pd
from pathlib import Path

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def direct_update_yahoo_ids():
    """Directly update yahoo_player_id values using exact matches."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    if not candidates_path.exists():
        logger.error(f"Candidates file not found: {candidates_path}")
        return False
    
    logger.info("Starting direct Yahoo Player ID update")
    
    # Read exact matches
    candidates = pd.read_csv(candidates_path)
    exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
    
    logger.info(f"Found {len(exact_matches)} exact matches for update")
    
    # Wait for database to be available
    import time
    for attempt in range(5):
        try:
            conn = sqlite3.connect(db_path, timeout=60)
            break
        except sqlite3.OperationalError as e:
            if 'locked' in str(e):
                logger.info(f"Database locked, waiting... (attempt {attempt + 1}/5)")
                time.sleep(10)
                continue
            else:
                raise
    else:
        logger.error("Could not acquire database lock after 5 attempts")
        return False
    
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats')
        total_records = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
        current_with_yahoo = cursor.fetchone()[0]
        
        logger.info(f"Current state: {current_with_yahoo:,} of {total_records:,} records have Yahoo ID")
        
        # Update records in batches
        updated_total = 0
        batch_size = 100
        
        for i in range(0, len(exact_matches), batch_size):
            batch = exact_matches.iloc[i:i+batch_size]
            
            for _, match in batch.iterrows():
                mlb_id = str(match['mlb_player_id'])
                yahoo_id = match['yahoo_player_id']
                
                # Update all records for this MLB player
                cursor.execute('''
                    UPDATE daily_gkl_player_stats 
                    SET yahoo_player_id = ?
                    WHERE mlb_player_id = ? AND yahoo_player_id IS NULL
                ''', (yahoo_id, mlb_id))
                
                updated_count = cursor.rowcount
                if updated_count > 0:
                    updated_total += updated_count
                    logger.debug(f"Updated {updated_count} records for {match['yahoo_player_name']} ({yahoo_id})")
            
            # Commit batch
            conn.commit()
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(exact_matches)-1)//batch_size + 1}, total updated: {updated_total:,}")
        
        # Final verification
        cursor.execute('SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id IS NOT NULL')
        final_with_yahoo = cursor.fetchone()[0]
        
        logger.info(f"=== UPDATE RESULTS ===")
        logger.info(f"Records updated in this run: {updated_total:,}")
        logger.info(f"Total records with Yahoo ID: {final_with_yahoo:,}")
        logger.info(f"Coverage: {(final_with_yahoo/total_records)*100:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during update: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def validate_update_results():
    """Validate the update results."""
    db_path = root_dir / "database" / "league_analytics.db"
    
    logger.info("Validating update results")
    
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()
    
    try:
        # Check linkage to daily_lineups
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT s.yahoo_player_id) as unique_yahoo_in_stats,
                COUNT(DISTINCT l.player_id) as unique_yahoo_in_lineups,
                COUNT(DISTINCT s.yahoo_player_id) FILTER (
                    WHERE s.yahoo_player_id IN (SELECT DISTINCT player_id FROM daily_lineups)
                ) as linked_players
            FROM daily_gkl_player_stats s
            CROSS JOIN (SELECT DISTINCT player_id FROM daily_lineups) l
            WHERE s.yahoo_player_id IS NOT NULL
        ''')
        
        result = cursor.fetchone()
        unique_in_stats, unique_in_lineups, linked = result
        
        logger.info(f"=== VALIDATION RESULTS ===")
        logger.info(f"Unique Yahoo players in stats: {unique_in_stats}")
        logger.info(f"Unique Yahoo players in lineups: {unique_in_lineups}")
        logger.info(f"Successfully linked players: {linked}")
        logger.info(f"Link success rate: {(linked/unique_in_lineups)*100:.1f}%")
        
        # Sample successful mappings
        cursor.execute('''
            SELECT s.yahoo_player_id, s.player_name, s.team_code, 
                   COUNT(*) as stats_records,
                   MAX(s.date) as latest_date
            FROM daily_gkl_player_stats s
            WHERE s.yahoo_player_id IS NOT NULL
            GROUP BY s.yahoo_player_id, s.player_name, s.team_code
            ORDER BY stats_records DESC
            LIMIT 10
        ''')
        
        logger.info("Sample successful mappings (top 10 by record count):")
        for row in cursor.fetchall():
            logger.info(f"  {row[1]} ({row[0]}) - {row[2]} - {row[3]} records (latest: {row[4]})")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return False
    finally:
        conn.close()


def main():
    """Run the direct update process."""
    logger.info("=== DIRECT YAHOO PLAYER ID UPDATE PROCESS ===")
    
    # Step 1: Direct update
    if not direct_update_yahoo_ids():
        logger.error("Failed to update Yahoo Player IDs")
        return
    
    # Step 2: Validate results
    if not validate_update_results():
        logger.error("Failed to validate results")
        return
    
    logger.info("✓ Direct Yahoo Player ID update completed successfully!")


if __name__ == "__main__":
    main()