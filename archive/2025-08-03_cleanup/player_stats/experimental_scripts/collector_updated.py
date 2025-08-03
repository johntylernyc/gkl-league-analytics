#!/usr/bin/env python3
"""
Player Stats Data Collector (Updated for MLB Stats API)

Core orchestrator for daily MLB player statistics data collection using
the MLB Stats API. Manages the complete workflow from API data retrieval
through staging table population and final data processing.

Key Features:
- Daily batting and pitching statistics collection via MLB Stats API
- Stores all component statistics (no pre-calculated ratios)
- Integration with player ID mapping system
- Job tracking and progress monitoring
- Data quality validation and error handling
"""

import sys
import sqlite3
import logging
import json
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from dataclasses import dataclass
import uuid

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.config import get_config_for_environment
from player_stats.pybaseball_integration import PyBaseballIntegration
from player_stats.player_id_mapper import PlayerIdMapper

# Import job logging from existing system
from league_transactions.backfill_transactions_optimized import start_job_log, update_job_log

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CollectionStats:
    """Statistics for a data collection run."""
    total_players_batting: int = 0
    total_players_pitching: int = 0
    successful_batting_records: int = 0
    successful_pitching_records: int = 0
    failed_records: int = 0
    quality_issues: int = 0
    processing_time_seconds: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class PlayerStatsCollector:
    """
    Orchestrates daily MLB player statistics collection using MLB Stats API.
    
    Manages the complete workflow from MLB Stats API calls through
    staging table population and final data processing with proper
    job tracking and error handling.
    """
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the player stats collector.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.db_path = self.config['database_path']
        
        # Initialize integrations
        self.pybaseball = PyBaseballIntegration(environment)
        self.player_mapper = PlayerIdMapper(environment)
        
        # Table names for this environment
        self.batting_staging_table = self.config['batting_staging_table']
        self.pitching_staging_table = self.config['pitching_staging_table']
        self.final_stats_table = self.config['gkl_player_stats_table']
        self.player_mapping_table = self.config['player_mapping_table']
        
        logger.info(f"Initialized PlayerStatsCollector for {environment} environment")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Using MLB Stats API for daily data collection")
    
    def get_yahoo_player_id(self, mlb_player_id: str) -> Optional[str]:
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
            logger.debug(f"Error looking up Yahoo ID for MLB ID {mlb_player_id}: {e}")
            return None
        finally:
            conn.close()
    
    def collect_daily_stats(self, target_date: date, job_metadata: str = None) -> str:
        """
        Collect MLB statistics for a specific date using MLB Stats API.
        
        Args:
            target_date: Date to collect stats for
            job_metadata: Optional metadata for job tracking
            
        Returns:
            job_id for tracking the collection job
        """
        logger.info(f"Starting daily stats collection for {target_date}")
        
        # Start job logging
        job_id = start_job_log(
            job_type="player_stats_collection",
            environment=self.environment,
            date_range_start=target_date.isoformat(),
            date_range_end=target_date.isoformat(),
            league_key="mlb",
            metadata=job_metadata or f"Daily MLB Stats API collection for {target_date}"
        )
        
        stats = CollectionStats()
        stats.start_time = datetime.now()
        
        try:
            # Step 1: Collect batting statistics via MLB Stats API
            logger.info("Collecting batting statistics from MLB Stats API...")
            batting_success = self._collect_batting_stats(target_date, job_id, stats)
            
            # Step 2: Collect pitching statistics via MLB Stats API
            logger.info("Collecting pitching statistics from MLB Stats API...")
            pitching_success = self._collect_pitching_stats(target_date, job_id, stats)
            
            # Step 3: Process staging data into final table
            logger.info("Processing staging data into final stats...")
            processing_success = self._process_staging_to_final(target_date, job_id, stats)
            
            stats.end_time = datetime.now()
            stats.processing_time_seconds = (stats.end_time - stats.start_time).total_seconds()
            
            # Determine overall success
            overall_success = batting_success and pitching_success and processing_success
            total_records = stats.successful_batting_records + stats.successful_pitching_records
            
            if overall_success:
                logger.info(f"Daily stats collection completed successfully for {target_date}")
                logger.info(f"Processed {total_records} total records in {stats.processing_time_seconds:.1f}s")
                
                update_job_log(
                    job_id, 
                    'completed',
                    records_processed=stats.total_players_batting + stats.total_players_pitching,
                    records_inserted=total_records
                )
            else:
                logger.error(f"Daily stats collection failed for {target_date}")
                update_job_log(
                    job_id,
                    'failed', 
                    error_message=f"Collection failed - batting: {batting_success}, pitching: {pitching_success}, processing: {processing_success}"
                )
            
            return job_id
            
        except Exception as e:
            stats.end_time = datetime.now()
            logger.error(f"Daily stats collection failed with exception: {e}")
            update_job_log(job_id, 'failed', error_message=str(e))
            raise
    
    def _collect_batting_stats(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Collect and store batting statistics for the target date."""
        try:
            # Get batting data from MLB Stats API via pybaseball integration
            batting_data = self.pybaseball.get_daily_batting_stats(target_date)
            
            if batting_data is None or batting_data.empty:
                logger.warning(f"No batting data available for {target_date}")
                return True  # Not a failure - just no games that day
            
            stats.total_players_batting = len(batting_data)
            logger.info(f"Retrieved batting stats for {stats.total_players_batting} players")
            
            # Store in staging table with all component stats
            success_count = self._store_batting_staging(batting_data, target_date, job_id)
            stats.successful_batting_records = success_count
            
            logger.info(f"Successfully stored {success_count} batting records in staging")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting batting stats: {e}")
            return False
    
    def _collect_pitching_stats(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Collect and store pitching statistics for the target date."""
        try:
            # Get pitching data from MLB Stats API via pybaseball integration
            pitching_data = self.pybaseball.get_daily_pitching_stats(target_date)
            
            if pitching_data is None or pitching_data.empty:
                logger.warning(f"No pitching data available for {target_date}")
                return True  # Not a failure - just no games that day
            
            stats.total_players_pitching = len(pitching_data)
            logger.info(f"Retrieved pitching stats for {stats.total_players_pitching} players")
            
            # Store in staging table with all component stats
            success_count = self._store_pitching_staging(pitching_data, target_date, job_id)
            stats.successful_pitching_records = success_count
            
            logger.info(f"Successfully stored {success_count} pitching records in staging")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting pitching stats: {e}")
            return False
    
    def _store_batting_staging(self, batting_data: pd.DataFrame, target_date: date, job_id: str) -> int:
        """Store batting data in staging table with all component statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            success_count = 0
            
            for _, row in batting_data.iterrows():
                try:
                    # Insert into staging table with all component stats
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.batting_staging_table} (
                            job_id, collection_date, data_date, 
                            player_id, player_name, team,
                            games_played, plate_appearances, at_bats, 
                            runs, hits, singles, doubles, triples, home_runs,
                            rbis, stolen_bases, caught_stealing,
                            walks, intentional_walks, hit_by_pitch,
                            strikeouts, sacrifice_hits, sacrifice_flies,
                            ground_into_double_play, total_bases,
                            raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        date.today().isoformat(),
                        target_date.isoformat(),
                        row.get('player_id'),  # MLB Stats API player ID
                        row.get('player_name', ''),
                        row.get('team', ''),
                        row.get('games_played', 0),
                        row.get('plate_appearances', 0),
                        row.get('at_bats', 0),
                        row.get('runs', 0),
                        row.get('hits', 0),
                        row.get('singles', 0),
                        row.get('doubles', 0),
                        row.get('triples', 0),
                        row.get('home_runs', 0),
                        row.get('rbis', 0),
                        row.get('stolen_bases', 0),
                        row.get('caught_stealing', 0),
                        row.get('walks', 0),
                        row.get('intentional_walks', 0),
                        row.get('hit_by_pitch', 0),
                        row.get('strikeouts', 0),
                        row.get('sacrifice_hits', 0),
                        row.get('sacrifice_flies', 0),
                        row.get('ground_into_double_play', 0),
                        row.get('total_bases', 0),
                        json.dumps(row.to_dict() if hasattr(row, 'to_dict') else dict(row), default=str)
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to store batting record for {row.get('player_name', 'unknown')}: {e}")
            
            conn.commit()
            return success_count
            
        finally:
            conn.close()
    
    def _store_pitching_staging(self, pitching_data: pd.DataFrame, target_date: date, job_id: str) -> int:
        """Store pitching data in staging table with all component statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            success_count = 0
            
            for _, row in pitching_data.iterrows():
                try:
                    # Insert into staging table with all component stats
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.pitching_staging_table} (
                            job_id, collection_date, data_date,
                            player_id, player_name, team,
                            games_played, games_started,
                            complete_games, shutouts, 
                            wins, losses, saves, blown_saves, holds,
                            innings_pitched, batters_faced,
                            hits_allowed, runs_allowed, earned_runs, home_runs_allowed,
                            walks_allowed, intentional_walks_allowed, hit_batters,
                            strikeouts_pitched, wild_pitches, balks,
                            ground_into_double_play, quality_starts,
                            raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        date.today().isoformat(),
                        target_date.isoformat(),
                        row.get('player_id'),  # MLB Stats API player ID
                        row.get('player_name', ''),
                        row.get('team', ''),
                        row.get('games_played', 0),
                        row.get('games_started', 0),
                        row.get('complete_games', 0),
                        row.get('shutouts', 0),
                        row.get('wins', 0),
                        row.get('losses', 0),
                        row.get('saves', 0),
                        row.get('blown_saves', 0),
                        row.get('holds', 0),
                        row.get('innings_pitched', 0.0),
                        row.get('batters_faced', 0),
                        row.get('hits_allowed', 0),
                        row.get('runs_allowed', 0),
                        row.get('earned_runs', 0),
                        row.get('home_runs_allowed', 0),
                        row.get('walks_allowed', 0),
                        row.get('intentional_walks_allowed', 0),
                        row.get('hit_batters', 0),
                        row.get('strikeouts_pitched', 0),
                        row.get('wild_pitches', 0),
                        row.get('balks', 0),
                        row.get('ground_into_double_play', 0),
                        row.get('quality_starts', 0),
                        json.dumps(row.to_dict() if hasattr(row, 'to_dict') else dict(row), default=str)
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to store pitching record for {row.get('player_name', 'unknown')}: {e}")
            
            conn.commit()
            return success_count
            
        finally:
            conn.close()
    
    def _process_staging_to_final(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Process staging data into final player stats table."""
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
    
    def calculate_ratios_for_date_range(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Calculate ratio statistics from component stats for a date range.
        
        This method calculates AVG, OBP, SLG, OPS, ERA, WHIP, K/BB on the fly
        from the stored component statistics.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            DataFrame with calculated ratio statistics
        """
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT 
            mlb_player_id,
            player_name,
            team_code,
            
            -- Aggregate batting components
            SUM(batting_at_bats) as total_ab,
            SUM(batting_hits) as total_h,
            SUM(batting_walks) as total_bb,
            SUM(batting_hit_by_pitch) as total_hbp,
            SUM(batting_sacrifice_flies) as total_sf,
            SUM(batting_total_bases) as total_tb,
            
            -- Calculate batting ratios
            CASE WHEN SUM(batting_at_bats) > 0 
                THEN CAST(SUM(batting_hits) AS FLOAT) / SUM(batting_at_bats) 
                ELSE NULL END as batting_avg,
            
            CASE WHEN (SUM(batting_at_bats) + SUM(batting_walks) + SUM(batting_hit_by_pitch) + SUM(batting_sacrifice_flies)) > 0
                THEN CAST(SUM(batting_hits) + SUM(batting_walks) + SUM(batting_hit_by_pitch) AS FLOAT) / 
                     (SUM(batting_at_bats) + SUM(batting_walks) + SUM(batting_hit_by_pitch) + SUM(batting_sacrifice_flies))
                ELSE NULL END as on_base_pct,
            
            CASE WHEN SUM(batting_at_bats) > 0
                THEN CAST(SUM(batting_total_bases) AS FLOAT) / SUM(batting_at_bats)
                ELSE NULL END as slugging_pct,
            
            -- Aggregate pitching components
            SUM(pitching_innings_pitched) as total_ip,
            SUM(pitching_earned_runs) as total_er,
            SUM(pitching_hits_allowed) as total_h_allowed,
            SUM(pitching_walks_allowed) as total_bb_allowed,
            SUM(pitching_strikeouts) as total_k,
            
            -- Calculate pitching ratios
            CASE WHEN SUM(pitching_innings_pitched) > 0
                THEN (CAST(SUM(pitching_earned_runs) AS FLOAT) * 9) / SUM(pitching_innings_pitched)
                ELSE NULL END as era,
            
            CASE WHEN SUM(pitching_innings_pitched) > 0
                THEN CAST(SUM(pitching_hits_allowed) + SUM(pitching_walks_allowed) AS FLOAT) / SUM(pitching_innings_pitched)
                ELSE NULL END as whip,
            
            CASE WHEN SUM(pitching_walks_allowed) > 0
                THEN CAST(SUM(pitching_strikeouts) AS FLOAT) / SUM(pitching_walks_allowed)
                ELSE NULL END as k_bb_ratio
            
        FROM {self.final_stats_table}
        WHERE date >= ? AND date <= ?
        GROUP BY mlb_player_id, player_name, team_code
        """
        
        df = pd.read_sql_query(query, conn, params=(start_date.isoformat(), end_date.isoformat()))
        
        # Calculate OPS (OBP + SLG)
        df['ops'] = df['on_base_pct'] + df['slugging_pct']
        
        conn.close()
        
        return df


def main():
    """Test the updated collector."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect MLB player statistics")
    parser.add_argument("--date", required=True, help="Date to collect (YYYY-MM-DD)")
    parser.add_argument("--env", default="test", choices=["test", "production"],
                       help="Environment (default: test)")
    
    args = parser.parse_args()
    
    target_date = date.fromisoformat(args.date)
    
    collector = PlayerStatsCollector(environment=args.env)
    
    print(f"Collecting MLB stats for {target_date} in {args.env} environment...")
    print("-" * 60)
    
    job_id = collector.collect_daily_stats(target_date)
    
    print(f"\nCollection complete! Job ID: {job_id}")
    print("\nTo calculate ratios for a date range, use:")
    print(f"  ratios = collector.calculate_ratios_for_date_range(start_date, end_date)")


if __name__ == "__main__":
    main()