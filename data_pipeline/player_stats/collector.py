#!/usr/bin/env python3
"""
Player Stats Data Collector

Core orchestrator for daily MLB player statistics data collection.
Manages the complete workflow from pybaseball data retrieval through
staging table population and final data processing.

Key Features:
- Daily batting and pitching statistics collection
- Integration with player ID mapping system
- Job tracking and progress monitoring
- Data quality validation and error handling
- Performance optimization for large datasets
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent.parent
sys.path.insert(0, str(root_dir))

from data_pipeline.player_stats.config import get_config_for_environment
from data_pipeline.player_stats.pybaseball_integration import PyBaseballIntegration
from data_pipeline.player_stats.player_id_mapper import PlayerIdMapper
from data_pipeline.player_stats.job_manager import PlayerStatsJobManager

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
    Orchestrates daily MLB player statistics collection.
    
    Manages the complete workflow from pybaseball API calls through
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
        self.job_manager = PlayerStatsJobManager(environment)
        
        # Table names for this environment
        self.batting_staging_table = self.config['batting_staging_table']
        self.pitching_staging_table = self.config['pitching_staging_table']
        self.final_stats_table = self.config['gkl_player_stats_table']
        self.player_mapping_table = self.config['player_mapping_table']
        
        logger.info(f"Initialized PlayerStatsCollector for {environment} environment")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Batting staging: {self.batting_staging_table}")
        logger.info(f"Pitching staging: {self.pitching_staging_table}")
        logger.info(f"Final stats: {self.final_stats_table}")
    
    def collect_daily_stats(self, target_date: date, job_metadata: str = None) -> str:
        """
        Collect MLB statistics for a specific date.
        
        Args:
            target_date: Date to collect stats for
            job_metadata: Optional metadata for job tracking
            
        Returns:
            job_id for tracking the collection job
        """
        logger.info(f"Starting daily stats collection for {target_date}")
        
        # Start job logging
        job_id = self.job_manager.start_job(
            job_type="player_stats_collection",
            date_range_start=target_date.isoformat(),
            date_range_end=target_date.isoformat(),
            league_key="mlb",  # General MLB data collection
            metadata={"description": job_metadata or f"Daily stats collection for {target_date}"}
        )
        
        stats = CollectionStats()
        stats.start_time = datetime.now()
        
        try:
            # Step 1: Collect batting statistics
            logger.info("Collecting batting statistics...")
            batting_success = self._collect_batting_stats(target_date, job_id, stats)
            
            # Step 2: Collect pitching statistics  
            logger.info("Collecting pitching statistics...")
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
                
                self.job_manager.update_job(
                    job_id, 
                    'completed',
                    records_processed=stats.total_players_batting + stats.total_players_pitching,
                    records_inserted=total_records
                )
            else:
                logger.error(f"Daily stats collection failed for {target_date}")
                self.job_manager.update_job(
                    job_id,
                    'failed', 
                    error_msg=f"Collection failed - batting: {batting_success}, pitching: {pitching_success}, processing: {processing_success}"
                )
            
            return job_id
            
        except Exception as e:
            stats.end_time = datetime.now()
            logger.error(f"Daily stats collection failed with exception: {e}")
            self.job_manager.update_job(job_id, 'failed', error_msg=str(e))
            raise
    
    def _collect_batting_stats(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Collect and store batting statistics for the target date."""
        try:
            # Get batting data from pybaseball
            batting_data = self.pybaseball.get_daily_batting_stats(target_date)
            
            if batting_data is None or batting_data.empty:
                logger.warning(f"No batting data available for {target_date}")
                return True  # Not a failure - just no data available
            
            stats.total_players_batting = len(batting_data)
            logger.info(f"Retrieved batting stats for {stats.total_players_batting} players")
            
            # Validate data quality
            validation = self.pybaseball.validate_batting_data(batting_data)
            if validation['warnings']:
                logger.warning(f"Batting data quality warnings: {validation['warnings']}")
                stats.quality_issues += len(validation['warnings'])
            
            if not validation['is_valid']:
                logger.error(f"Batting data validation failed: {validation['errors']}")
                return False
            
            # Store in staging table
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
            # Get pitching data from pybaseball
            pitching_data = self.pybaseball.get_daily_pitching_stats(target_date)
            
            if pitching_data is None or pitching_data.empty:
                logger.warning(f"No pitching data available for {target_date}")
                return True  # Not a failure - just no data available
            
            stats.total_players_pitching = len(pitching_data)
            logger.info(f"Retrieved pitching stats for {stats.total_players_pitching} players")
            
            # Validate data quality
            validation = self.pybaseball.validate_pitching_data(pitching_data)
            if validation['warnings']:
                logger.warning(f"Pitching data quality warnings: {validation['warnings']}")
                stats.quality_issues += len(validation['warnings'])
            
            if not validation['is_valid']:
                logger.error(f"Pitching data validation failed: {validation['errors']}")
                return False
            
            # Store in staging table
            success_count = self._store_pitching_staging(pitching_data, target_date, job_id)
            stats.successful_pitching_records = success_count
            
            logger.info(f"Successfully stored {success_count} pitching records in staging")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting pitching stats: {e}")
            return False
    
    def _store_batting_staging(self, batting_data: pd.DataFrame, target_date: date, job_id: str) -> int:
        """Store batting data in staging table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            success_count = 0
            field_mapping = self.config['field_mappings']['batting']
            
            for _, row in batting_data.iterrows():
                try:
                    # Map pybaseball fields to our schema
                    mapped_data = {}
                    for pyb_field, our_field in field_mapping.items():
                        if pyb_field in row and pd.notna(row[pyb_field]):
                            mapped_data[our_field] = row[pyb_field]
                    
                    # Insert into staging table
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.batting_staging_table} (
                            job_id, collection_date, data_date, player_name, team,
                            games_played, at_bats, runs, hits, doubles, triples, home_runs,
                            rbis, stolen_bases, walks, strikeouts, batting_avg, on_base_pct,
                            slugging_pct, ops, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        date.today().isoformat(),
                        target_date.isoformat(),
                        mapped_data.get('player_name', ''),
                        mapped_data.get('team', ''),
                        mapped_data.get('games_played', 0),
                        mapped_data.get('at_bats', 0),
                        mapped_data.get('runs', 0),
                        mapped_data.get('hits', 0),
                        mapped_data.get('doubles', 0),
                        mapped_data.get('triples', 0),
                        mapped_data.get('home_runs', 0),
                        mapped_data.get('rbis', 0),
                        mapped_data.get('stolen_bases', 0),
                        mapped_data.get('walks', 0),
                        mapped_data.get('strikeouts', 0),
                        mapped_data.get('batting_avg'),
                        mapped_data.get('on_base_pct'),
                        mapped_data.get('slugging_pct'),
                        mapped_data.get('ops'),
                        json.dumps(row.to_dict(), default=str)  # Store raw data as JSON
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to store batting record for {mapped_data.get('player_name', 'unknown')}: {e}")
            
            conn.commit()
            return success_count
            
        finally:
            conn.close()
    
    def _store_pitching_staging(self, pitching_data: pd.DataFrame, target_date: date, job_id: str) -> int:
        """Store pitching data in staging table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            success_count = 0
            field_mapping = self.config['field_mappings']['pitching']
            
            for _, row in pitching_data.iterrows():
                try:
                    # Map pybaseball fields to our schema
                    mapped_data = {}
                    for pyb_field, our_field in field_mapping.items():
                        if pyb_field in row and pd.notna(row[pyb_field]):
                            mapped_data[our_field] = row[pyb_field]
                    
                    # Insert into staging table
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {self.pitching_staging_table} (
                            job_id, collection_date, data_date, player_name, team,
                            games_played, games_started, wins, losses, saves, holds,
                            innings_pitched, hits_allowed, runs_allowed, earned_runs,
                            walks_allowed, strikeouts_pitched, home_runs_allowed,
                            era, whip, quality_starts, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job_id,
                        date.today().isoformat(),
                        target_date.isoformat(),
                        mapped_data.get('player_name', ''),
                        mapped_data.get('team', ''),
                        mapped_data.get('games_played', 0),
                        mapped_data.get('games_started', 0),
                        mapped_data.get('wins', 0),
                        mapped_data.get('losses', 0),
                        mapped_data.get('saves', 0),
                        mapped_data.get('holds', 0),
                        mapped_data.get('innings_pitched', 0.0),
                        mapped_data.get('hits_allowed', 0),
                        mapped_data.get('runs_allowed', 0),
                        mapped_data.get('earned_runs', 0),
                        mapped_data.get('walks_allowed', 0),
                        mapped_data.get('strikeouts_pitched', 0),
                        mapped_data.get('home_runs_allowed', 0),
                        mapped_data.get('era'),
                        mapped_data.get('whip'),
                        mapped_data.get('quality_starts', 0),
                        json.dumps(row.to_dict(), default=str)  # Store raw data as JSON
                    ))
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to store pitching record for {mapped_data.get('player_name', 'unknown')}: {e}")
            
            conn.commit()
            return success_count
            
        finally:
            conn.close()
    
    def _process_staging_to_final(self, target_date: date, job_id: str, stats: CollectionStats) -> bool:
        """Process staging data into final player stats table with player mapping."""
        try:
            logger.info("Processing staging data with player ID mapping...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Get all unique players from staging tables for this date
                players_to_map = set()
                
                # Get batting players
                cursor.execute(f"""
                    SELECT DISTINCT player_name, team 
                    FROM {self.batting_staging_table} 
                    WHERE data_date = ?
                """, (target_date.isoformat(),))
                batting_players = cursor.fetchall()
                
                # Get pitching players
                cursor.execute(f"""
                    SELECT DISTINCT player_name, team 
                    FROM {self.pitching_staging_table} 
                    WHERE data_date = ?
                """, (target_date.isoformat(),))
                pitching_players = cursor.fetchall()
                
                # Combine all players
                all_players = set(batting_players + pitching_players)
                logger.info(f"Found {len(all_players)} unique players to process")
                
                # Process each player's stats
                processed_count = 0
                for player_name, team in all_players:
                    try:
                        # Try to get existing player mapping
                        mapping = self._find_player_mapping(player_name, team)
                        
                        if not mapping:
                            # Create new mapping if needed
                            logger.debug(f"Creating new mapping for {player_name} ({team})")
                            # We don't have Yahoo ID yet, so we'll create placeholder mappings
                            # This will be resolved when we integrate with existing player data
                            yahoo_player_id = f"pending_{uuid.uuid4().hex[:8]}"
                            mapping = self.player_mapper.create_automatic_mapping(
                                yahoo_player_id, player_name, team
                            )
                        
                        if mapping:
                            # Convert PlayerMapping object to dictionary if needed
                            if hasattr(mapping, 'yahoo_player_id'):
                                # It's a PlayerMapping object, convert to dict
                                mapping_dict = {
                                    'yahoo_player_id': mapping.yahoo_player_id,
                                    'yahoo_player_name': mapping.yahoo_player_name,
                                    'confidence_score': mapping.confidence_score
                                }
                            else:
                                # It's already a dict
                                mapping_dict = mapping
                            
                            # Create final stats record
                            success = self._create_final_stats_record(
                                target_date, job_id, mapping_dict, player_name, team
                            )
                            if success:
                                processed_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to process player {player_name}: {e}")
                        stats.failed_records += 1
                
                logger.info(f"Successfully processed {processed_count} players into final stats")
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error processing staging to final: {e}")
            return False
    
    def _find_player_mapping(self, player_name: str, team: str) -> Optional[Dict[str, Any]]:
        """Find existing player mapping by name and team."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Look for existing mapping by standardized name
            standardized_name = self.player_mapper.standardize_name(player_name)
            
            cursor.execute(f"""
                SELECT yahoo_player_id, yahoo_player_name, confidence_score
                FROM {self.player_mapping_table}
                WHERE standardized_name = ? AND team_code = ? AND is_active = TRUE
                ORDER BY confidence_score DESC
                LIMIT 1
            """, (standardized_name, team))
            
            row = cursor.fetchone()
            if row:
                return {
                    'yahoo_player_id': row[0],
                    'yahoo_player_name': row[1],
                    'confidence_score': row[2]
                }
            
            return None
            
        finally:
            conn.close()
    
    def _create_final_stats_record(self, target_date: date, job_id: str, 
                                 mapping: Dict[str, Any], player_name: str, team: str) -> bool:
        """Create a final stats record combining batting and pitching data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get batting stats for this player/date
            cursor.execute(f"""
                SELECT games_played, at_bats, runs, hits, doubles, triples, home_runs,
                       rbis, stolen_bases, walks, strikeouts, batting_avg, on_base_pct,
                       slugging_pct, ops
                FROM {self.batting_staging_table}
                WHERE data_date = ? AND player_name = ? AND team = ?
                LIMIT 1
            """, (target_date.isoformat(), player_name, team))
            
            batting_stats = cursor.fetchone()
            
            # Get pitching stats for this player/date
            cursor.execute(f"""
                SELECT games_played, games_started, wins, losses, saves, holds,
                       innings_pitched, hits_allowed, runs_allowed, earned_runs,
                       walks_allowed, strikeouts_pitched, home_runs_allowed,
                       era, whip, quality_starts
                FROM {self.pitching_staging_table}
                WHERE data_date = ? AND player_name = ? AND team = ?
                LIMIT 1
            """, (target_date.isoformat(), player_name, team))
            
            pitching_stats = cursor.fetchone()
            
            # Determine primary games played (use max of batting/pitching)
            games_played = 0
            if batting_stats and batting_stats[0]:
                games_played = max(games_played, batting_stats[0])
            if pitching_stats and pitching_stats[0]:
                games_played = max(games_played, pitching_stats[0])
            
            # Insert into final stats table
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self.final_stats_table} (
                    job_id, date, yahoo_player_id, player_name, team_code,
                    games_played, has_batting_data, has_pitching_data,
                    batting_at_bats, batting_runs, batting_hits, batting_doubles, batting_triples,
                    batting_home_runs, batting_rbis, batting_stolen_bases, batting_walks,
                    batting_strikeouts, batting_avg, batting_obp, batting_slg, batting_ops,
                    pitching_games_started, pitching_wins, pitching_losses, pitching_saves,
                    pitching_holds, pitching_innings_pitched, pitching_hits_allowed,
                    pitching_runs_allowed, pitching_earned_runs, pitching_walks_allowed,
                    pitching_strikeouts, pitching_home_runs_allowed, pitching_era,
                    pitching_whip, pitching_quality_starts, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                target_date.isoformat(),
                mapping['yahoo_player_id'],
                player_name,
                team,
                games_played,
                batting_stats is not None,
                pitching_stats is not None,
                # Batting stats
                batting_stats[1] if batting_stats else None,  # at_bats
                batting_stats[2] if batting_stats else None,  # runs
                batting_stats[3] if batting_stats else None,  # hits
                batting_stats[4] if batting_stats else None,  # doubles
                batting_stats[5] if batting_stats else None,  # triples
                batting_stats[6] if batting_stats else None,  # home_runs
                batting_stats[7] if batting_stats else None,  # rbis
                batting_stats[8] if batting_stats else None,  # stolen_bases
                batting_stats[9] if batting_stats else None,  # walks
                batting_stats[10] if batting_stats else None,  # strikeouts
                batting_stats[11] if batting_stats else None,  # batting_avg
                batting_stats[12] if batting_stats else None,  # on_base_pct
                batting_stats[13] if batting_stats else None,  # slugging_pct
                batting_stats[14] if batting_stats else None,  # ops
                # Pitching stats
                pitching_stats[1] if pitching_stats else None,  # games_started
                pitching_stats[2] if pitching_stats else None,  # wins
                pitching_stats[3] if pitching_stats else None,  # losses
                pitching_stats[4] if pitching_stats else None,  # saves
                pitching_stats[5] if pitching_stats else None,  # holds
                pitching_stats[6] if pitching_stats else None,  # innings_pitched
                pitching_stats[7] if pitching_stats else None,  # hits_allowed
                pitching_stats[8] if pitching_stats else None,  # runs_allowed
                pitching_stats[9] if pitching_stats else None,  # earned_runs
                pitching_stats[10] if pitching_stats else None,  # walks_allowed
                pitching_stats[11] if pitching_stats else None,  # strikeouts_pitched
                pitching_stats[12] if pitching_stats else None,  # home_runs_allowed
                pitching_stats[13] if pitching_stats else None,  # era
                pitching_stats[14] if pitching_stats else None,  # whip
                pitching_stats[15] if pitching_stats else None,  # quality_starts
                mapping.get('confidence_score', 0.0)
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create final stats record for {player_name}: {e}")
            return False
            
        finally:
            conn.close()
    
    def collect_date_range(self, start_date: date, end_date: date, 
                          max_workers: int = 2) -> Dict[str, Any]:
        """
        Collect statistics for a range of dates.
        
        Args:
            start_date: Start date for collection
            end_date: End date for collection
            max_workers: Maximum concurrent collection jobs
            
        Returns:
            Dictionary with collection results
        """
        logger.info(f"Starting date range collection: {start_date} to {end_date}")
        
        results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_dates': 0,
            'successful_dates': 0,
            'failed_dates': 0,
            'job_ids': [],
            'errors': []
        }
        
        # Generate list of dates
        current_date = start_date
        dates = []
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        results['total_dates'] = len(dates)
        logger.info(f"Collecting stats for {len(dates)} dates")
        
        # Process dates with controlled concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_date = {
                executor.submit(self.collect_daily_stats, date_obj): date_obj 
                for date_obj in dates
            }
            
            # Process completed jobs
            for future in as_completed(future_to_date):
                target_date = future_to_date[future]
                try:
                    job_id = future.result()
                    results['job_ids'].append(job_id)
                    results['successful_dates'] += 1
                    logger.info(f"Completed collection for {target_date} (job: {job_id})")
                    
                except Exception as e:
                    results['failed_dates'] += 1
                    error_msg = f"Failed collection for {target_date}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        logger.info(f"Date range collection completed: {results['successful_dates']}/{results['total_dates']} successful")
        return results


def main():
    """Command-line interface for player stats collection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MLB Player Stats Data Collection")
    parser.add_argument("action", choices=["collect", "range"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--date", help="Date for single collection (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start date for range collection (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for range collection (YYYY-MM-DD)")
    parser.add_argument("--workers", type=int, default=2,
                       help="Max concurrent workers for range collection")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    collector = PlayerStatsCollector(environment=args.env)
    
    if args.action == "collect":
        if not args.date:
            print("ERROR: --date is required for single collection")
            return
        
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Collecting MLB player stats for {target_date}...")
        print("-" * 60)
        
        try:
            job_id = collector.collect_daily_stats(target_date)
            print(f"[SUCCESS] Collection completed successfully!")
            print(f"Job ID: {job_id}")
        except Exception as e:
            print(f"[FAILED] Collection failed: {e}")
    
    elif args.action == "range":
        if not args.start_date or not args.end_date:
            print("ERROR: --start-date and --end-date are required for range collection")
            return
        
        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        if start_date > end_date:
            print("ERROR: Start date must be before or equal to end date")
            return
        
        print(f"Collecting MLB player stats from {start_date} to {end_date}...")
        print(f"Using {args.workers} concurrent workers")
        print("-" * 60)
        
        try:
            results = collector.collect_date_range(start_date, end_date, args.workers)
            
            print(f"[COMPLETED] Range collection finished!")
            print(f"Successful: {results['successful_dates']}/{results['total_dates']}")
            print(f"Job IDs: {len(results['job_ids'])}")
            
            if results['errors']:
                print("\nErrors:")
                for error in results['errors']:
                    print(f"  - {error}")
                    
        except Exception as e:
            print(f"[FAILED] Range collection failed: {e}")


if __name__ == "__main__":
    main()