#!/usr/bin/env python3
"""
Fix Yahoo Player ID Integration

Updates the collector system to properly integrate Yahoo Player IDs
using the player ID mapping table during stats collection.
"""

import sys
import sqlite3
import logging
from pathlib import Path

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_simple_mapping_table():
    """Create a simple mapping table with the exact matches we have."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    logger.info("Creating simple player ID mapping table")
    
    conn = sqlite3.connect(db_path, timeout=60)
    cursor = conn.cursor()
    
    try:
        # Clear existing mappings
        cursor.execute('DELETE FROM player_id_mapping')
        
        # Load candidates and insert exact matches only
        import pandas as pd
        candidates = pd.read_csv(candidates_path)
        exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
        
        logger.info(f"Inserting {len(exact_matches)} exact matches")
        
        for _, row in exact_matches.iterrows():
            cursor.execute('''
                INSERT INTO player_id_mapping (
                    yahoo_player_id, yahoo_player_name, mlb_player_id,
                    standardized_name, team_code, position_codes,
                    confidence_score, mapping_method, validation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['yahoo_player_id'],
                row['yahoo_player_name'], 
                str(row['mlb_player_id']),
                row['standardized_name'],
                row['team_code'],
                row['position_codes'],
                0.95,
                'exact_name_match',
                'validated'
            ))
        
        conn.commit()
        
        # Verify
        cursor.execute('SELECT COUNT(*) FROM player_id_mapping')
        count = cursor.fetchone()[0]
        logger.info(f"Successfully inserted {count} player mappings")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating mapping table: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def create_yahoo_id_lookup_function():
    """Create a SQL function to lookup Yahoo Player IDs from MLB Player IDs."""
    
    # Since SQLite doesn't support user-defined functions in the same way,
    # we'll create a helper method in the collector instead
    
    helper_code = '''def get_yahoo_player_id(self, mlb_player_id: str) -> Optional[str]:
    """
    Get Yahoo Player ID for an MLB Player ID using the mapping table.
    
    Args:
        mlb_player_id: MLB Stats API player ID
        
    Returns:
        Yahoo Player ID if found, None otherwise
    """
    if not mlb_player_id:
        return None
        
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT yahoo_player_id 
            FROM player_id_mapping 
            WHERE mlb_player_id = ? AND is_active = 1
            LIMIT 1
        """, (str(mlb_player_id),))
        
        result = cursor.fetchone()
        return result[0] if result else None
        
    except Exception as e:
        logger.warning(f"Error looking up Yahoo ID for MLB ID {mlb_player_id}: {e}")
        return None
    finally:
        conn.close()'''
    
    logger.info("Created helper function code for Yahoo ID lookup")
    return helper_code


def update_processing_to_include_yahoo_ids():
    """Update the _process_staging_to_final method to include Yahoo Player IDs."""
    
    updated_method = '''
    def _process_staging_to_final(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Process staging data into final player stats table with Yahoo Player IDs."""
        try:
            logger.info("Processing staging data into final stats table...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Process batting stats with Yahoo Player ID lookup
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {self.final_stats_table} (
                        job_id, date, mlb_player_id, yahoo_player_id, player_name, team_code,
                        games_played, has_batting_data, has_pitching_data,
                        
                        -- All batting component stats
                        batting_plate_appearances, batting_at_bats,
                        batting_runs, batting_hits, batting_singles,
                        batting_doubles, batting_triples, batting_home_runs,
                        batting_rbis, batting_stolen_bases, batting_caught_stealing,
                        batting_walks, batting_intentional_walks, batting_strikeouts,
                        batting_hit_by_pitch, batting_sacrifice_hits, batting_sacrifice_flies,
                        batting_ground_into_double_play, batting_total_bases,
                        
                        data_source, confidence_score, validation_status
                    )
                    SELECT 
                        b.job_id, b.data_date, b.player_id, 
                        COALESCE(pm.yahoo_player_id, NULL) as yahoo_player_id,
                        b.player_name, b.team,
                        b.games_played, 1, 0,  -- has_batting_data=1, has_pitching_data=0
                        
                        b.plate_appearances, b.at_bats,
                        b.runs, b.hits, b.singles,
                        b.doubles, b.triples, b.home_runs,
                        b.rbis, b.stolen_bases, b.caught_stealing,
                        b.walks, b.intentional_walks, b.strikeouts,
                        b.hit_by_pitch, b.sacrifice_hits, b.sacrifice_flies,
                        b.ground_into_double_play, b.total_bases,
                        
                        'mlb_stats_api', 1.0, 'valid'
                    FROM {self.batting_staging_table} b
                    LEFT JOIN player_id_mapping pm ON b.player_id = pm.mlb_player_id 
                        AND pm.is_active = 1
                    WHERE b.data_date = ?
                """, (target_date.isoformat(),))
                
                batting_count = cursor.rowcount
                logger.info(f"Processed {batting_count} batting records")
                
                # Process pitching stats - update existing or insert new
                cursor.execute(f"""
                    INSERT INTO {self.final_stats_table} (
                        job_id, date, mlb_player_id, yahoo_player_id, player_name, team_code,
                        games_played, has_batting_data, has_pitching_data,
                        
                        -- All pitching component stats
                        pitching_games_started, pitching_complete_games, pitching_shutouts,
                        pitching_wins, pitching_losses, pitching_saves,
                        pitching_blown_saves, pitching_holds, pitching_innings_pitched,
                        pitching_batters_faced, pitching_hits_allowed, pitching_runs_allowed,
                        pitching_earned_runs, pitching_home_runs_allowed,
                        pitching_walks_allowed, pitching_intentional_walks_allowed,
                        pitching_strikeouts, pitching_hit_batters,
                        pitching_wild_pitches, pitching_balks, pitching_quality_starts,
                        
                        data_source, confidence_score, validation_status
                    )
                    SELECT 
                        p.job_id, p.data_date, p.player_id,
                        COALESCE(pm.yahoo_player_id, NULL) as yahoo_player_id,
                        p.player_name, p.team,
                        p.games_played, 0, 1,  -- has_batting_data=0, has_pitching_data=1
                        
                        p.games_started, p.complete_games, p.shutouts,
                        p.wins, p.losses, p.saves,
                        p.blown_saves, p.holds, p.innings_pitched,
                        p.batters_faced, p.hits_allowed, p.runs_allowed,
                        p.earned_runs, p.home_runs_allowed,
                        p.walks_allowed, p.intentional_walks_allowed,
                        p.strikeouts_pitched, p.hit_batters,
                        p.wild_pitches, p.balks, p.quality_starts,
                        
                        'mlb_stats_api', 1.0, 'valid'
                    FROM {self.pitching_staging_table} p
                    LEFT JOIN player_id_mapping pm ON p.player_id = pm.mlb_player_id 
                        AND pm.is_active = 1
                    WHERE p.data_date = ?
                    AND p.player_id NOT IN (
                        SELECT mlb_player_id FROM {self.final_stats_table}
                        WHERE date = ?
                    )
                """, (target_date.isoformat(), target_date.isoformat()))
                
                pitching_new = cursor.rowcount
                
                # Update existing records with pitching data and Yahoo IDs
                cursor.execute(f"""
                    UPDATE {self.final_stats_table}
                    SET 
                        has_pitching_data = 1,
                        yahoo_player_id = COALESCE(pm.yahoo_player_id, {self.final_stats_table}.yahoo_player_id),
                        pitching_games_started = p.games_started,
                        pitching_complete_games = p.complete_games,
                        pitching_shutouts = p.shutouts,
                        pitching_wins = p.wins,
                        pitching_losses = p.losses,
                        pitching_saves = p.saves,
                        pitching_blown_saves = p.blown_saves,
                        pitching_holds = p.holds,
                        pitching_innings_pitched = p.innings_pitched,
                        pitching_batters_faced = p.batters_faced,
                        pitching_hits_allowed = p.hits_allowed,
                        pitching_runs_allowed = p.runs_allowed,
                        pitching_earned_runs = p.earned_runs,
                        pitching_home_runs_allowed = p.home_runs_allowed,
                        pitching_walks_allowed = p.walks_allowed,
                        pitching_intentional_walks_allowed = p.intentional_walks_allowed,
                        pitching_strikeouts = p.strikeouts_pitched,
                        pitching_hit_batters = p.hit_batters,
                        pitching_wild_pitches = p.wild_pitches,
                        pitching_balks = p.balks,
                        pitching_quality_starts = p.quality_starts
                    FROM {self.pitching_staging_table} p
                    LEFT JOIN player_id_mapping pm ON p.player_id = pm.mlb_player_id 
                        AND pm.is_active = 1
                    WHERE {self.final_stats_table}.mlb_player_id = p.player_id
                    AND {self.final_stats_table}.date = p.data_date
                    AND p.data_date = ?
                """, (target_date.isoformat(),))
                
                pitching_updated = cursor.rowcount
                
                logger.info(f"Processed {pitching_new + pitching_updated} pitching records ({pitching_new} new, {pitching_updated} updated)")
                
                conn.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error processing staging to final: {e}")
                conn.rollback()
                return False
                
        finally:
            conn.close()
    '''
    
    logger.info("Generated updated processing method with Yahoo Player ID integration")
    return updated_method


def main():
    """Run the Yahoo Player ID integration fix."""
    logger.info("Starting Yahoo Player ID integration fix")
    
    # Step 1: Create the mapping table with exact matches
    if create_simple_mapping_table():
        logger.info("✓ Player ID mapping table populated")
    else:
        logger.error("✗ Failed to populate mapping table")
        return
    
    # Step 2: Generate the updated code
    helper_code = create_yahoo_id_lookup_function()
    updated_method = update_processing_to_include_yahoo_ids()
    
    # Save the updated code to a file for manual integration
    fix_path = root_dir / "player_stats" / "yahoo_id_integration_fix.txt"
    with open(fix_path, 'w') as f:
        f.write("=== YAHOO PLAYER ID INTEGRATION FIX ===\\n\\n")
        f.write("1. Add this helper method to PlayerStatsCollector class:\\n\\n")
        f.write(helper_code)
        f.write("\\n\\n2. Replace the _process_staging_to_final method with:\\n\\n")
        f.write(updated_method)
    
    logger.info(f"✓ Integration fix code saved to: {fix_path}")
    logger.info("Manual integration required - see the generated fix file")


if __name__ == "__main__":
    main()