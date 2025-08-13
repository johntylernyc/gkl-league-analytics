#!/usr/bin/env python3
"""
Comprehensive MLB Player Stats Collector

Collects daily statistics for ALL MLB players using PyBaseball and MLB Stats API.
Includes multi-platform player ID mapping (MLB, Yahoo, Baseball Reference, FanGraphs).
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
import numpy as np

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment
from data_pipeline.player_stats.job_manager import PlayerStatsJobManager
from data_pipeline.player_stats.pybaseball_integration import PyBaseballIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveStatsCollector:
    """Collects stats for all MLB players with multi-platform ID mapping"""
    
    def __init__(self, environment='test', use_d1=False):
        self.environment = environment
        self.use_d1 = use_d1
        self.config = get_config_for_environment(environment)
        
        # Database connection
        if use_d1:
            from data_pipeline.common.d1_connection import D1Connection
            self.d1_conn = D1Connection()
            self.conn = None
            logger.info("Using Cloudflare D1 database")
        else:
            self.conn = sqlite3.connect(self.config['database_path'])
            self.d1_conn = None
            logger.info(f"Using SQLite database: {self.config['database_path']}")
        
        self.job_manager = PlayerStatsJobManager(environment=environment, use_d1=use_d1)
        self.pybaseball_integration = PyBaseballIntegration(environment)
        
        # Initialize pybaseball
        self.pybaseball = self.pybaseball_integration.pybaseball
        
        # Tables
        self.player_mapping_table = 'player_mapping'
        self.stats_table = 'daily_gkl_player_stats'
        
        logger.info(f"Initialized ComprehensiveStatsCollector for {environment}")
    
    def _get_cursor(self):
        """Get appropriate cursor for database operations"""
        if self.use_d1:
            return self.d1_conn  # D1Connection acts as cursor
        else:
            return self.conn.cursor()
    
    def _execute_query(self, query: str, params: tuple = ()) -> Any:
        """Execute query on appropriate database"""
        if self.use_d1:
            return self.d1_conn.execute(query, params)
        else:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
    
    def _fetchone(self, cursor_or_result) -> tuple:
        """Fetch one result"""
        if self.use_d1:
            # D1 returns a dict with 'results' key
            results = cursor_or_result.get('results', [])
            return tuple(results[0]) if results else None
        else:
            return cursor_or_result.fetchone()
    
    def _fetchall(self, cursor_or_result) -> List[tuple]:
        """Fetch all results"""
        if self.use_d1:
            # D1 returns a dict with 'results' key
            results = cursor_or_result.get('results', [])
            return [tuple(row) for row in results]
        else:
            return cursor_or_result.fetchall()
    
    def _commit(self):
        """Commit transaction"""
        if not self.use_d1:  # D1 auto-commits
            self.conn.commit()
        
    def initialize_player_mappings(self):
        """Initialize player mapping table with comprehensive player registry"""
        logger.info("Initializing player mappings from Chadwick Bureau registry...")
        
        try:
            # Get comprehensive player registry
            # This includes MLB ID, Baseball Reference ID, FanGraphs ID, etc.
            players = self.pybaseball.playerid_lookup('', '')  # Empty strings to get all
            
            if players is None or players.empty:
                # Alternative: use chadwick_register
                logger.info("Using chadwick_register for comprehensive player list...")
                players = self.pybaseball.chadwick_register()
            
            # Filter to recent players (active since 2020)
            if 'mlb_played_last' in players.columns:
                recent_players = players[players['mlb_played_last'] >= 2020].copy()
            else:
                recent_players = players.copy()
            
            logger.info(f"Found {len(recent_players)} recent players")
            
            cursor = self._get_cursor()
            
            # Insert players into mapping table
            inserted = 0
            for _, player in recent_players.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO player_mapping (
                            mlb_id, baseball_reference_id, fangraphs_id,
                            player_name, first_name, last_name, active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        player.get('key_mlbam'),  # MLB ID
                        player.get('key_bbref'),  # Baseball Reference ID
                        player.get('key_fangraphs'),  # FanGraphs ID
                        f"{player.get('name_first', '')} {player.get('name_last', '')}".strip(),
                        player.get('name_first'),
                        player.get('name_last'),
                        1 if player.get('mlb_played_last', 0) >= 2023 else 0
                    ))
                    inserted += 1
                except Exception as e:
                    logger.error(f"Error inserting player {player.get('name_last')}: {e}")
            
            self._commit()
            logger.info(f"Inserted {inserted} players into mapping table")
            
            # Show sample
            cursor.execute("SELECT COUNT(*) FROM player_mapping WHERE active = 1")
            active_count = cursor.fetchone()[0]
            logger.info(f"Active players: {active_count}")
            
        except Exception as e:
            logger.error(f"Error initializing player mappings: {e}")
            raise
    
    def collect_daily_stats(self, target_date: str):
        """Collect stats for all MLB players on a given date"""
        logger.info(f"Collecting comprehensive stats for {target_date}")
        
        # Start job
        job_id = self.job_manager.start_job(
            job_type='stats_comprehensive_daily',
            date_range_start=target_date,
            date_range_end=target_date,
            metadata={'source': 'pybaseball', 'scope': 'all_mlb_players'}
        )
        
        try:
            # Get games for the date to know which teams played
            games = self._get_games_for_date(target_date)
            logger.info(f"Found {len(games)} games on {target_date}")
            
            # Collect batting stats
            batting_stats = self._collect_batting_stats(target_date, games)
            logger.info(f"Collected batting stats for {len(batting_stats)} players")
            
            # Collect pitching stats
            pitching_stats = self._collect_pitching_stats(target_date, games)
            logger.info(f"Collected pitching stats for {len(pitching_stats)} players")
            
            # Merge and enrich with player IDs
            all_stats = self._merge_and_enrich_stats(batting_stats, pitching_stats, target_date)
            
            # Calculate rate stats
            all_stats = self._calculate_rate_stats(all_stats)
            
            # Save to database
            records_saved = self._save_stats(all_stats, job_id, target_date)
            
            # Update job
            self.job_manager.update_job(
                job_id, 'completed',
                records_processed=len(all_stats),
                records_inserted=records_saved
            )
            
            return records_saved
            
        except Exception as e:
            logger.error(f"Error collecting stats: {e}")
            self.job_manager.update_job(job_id, 'failed', metadata={'error': str(e)})
            raise
    
    def _get_games_for_date(self, target_date: str) -> List[Dict]:
        """Get all MLB games for a given date"""
        # Convert string date to date object
        from datetime import datetime
        date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        # Use MLB Stats API via pybaseball integration
        games_data = self.pybaseball_integration._get_games_for_date(date_obj)
        
        games = []
        for game in games_data:
            if game.get('status', {}).get('codedGameState') in ['F', 'C']:  # Final or Completed
                games.append({
                    'game_id': game['gamePk'],
                    'home_team': game['teams']['home']['team']['abbreviation'],
                    'away_team': game['teams']['away']['team']['abbreviation']
                })
        
        return games
    
    def _collect_batting_stats(self, target_date: str, games: List[Dict]) -> pd.DataFrame:
        """Collect batting stats for all players who played on the given date"""
        all_batting_stats = []
        
        for game in games:
            game_id = game['game_id']
            
            # Get box score for the game
            boxscore_data = self.pybaseball_integration._get_game_boxscore(game_id)
            
            if not boxscore_data:
                continue
            
            # Process home and away batters
            for team_type in ['home', 'away']:
                team_code = game[f'{team_type}_team']
                batters = boxscore_data.get('teams', {}).get(team_type, {}).get('batters', [])
                
                for batter_id in batters:
                    player_data = boxscore_data.get('teams', {}).get(team_type, {}).get('players', {}).get(f'ID{batter_id}', {})
                    
                    if player_data and 'stats' in player_data and 'batting' in player_data['stats']:
                        batting = player_data['stats']['batting']
                        
                        stats_dict = {
                            'mlb_id': batter_id,
                            'player_name': player_data.get('person', {}).get('fullName', ''),
                            'team_code': team_code,
                            'games_played': 1,
                            'batting_plate_appearances': batting.get('plateAppearances', 0),
                            'batting_at_bats': batting.get('atBats', 0),
                            'batting_hits': batting.get('hits', 0),
                            'batting_doubles': batting.get('doubles', 0),
                            'batting_triples': batting.get('triples', 0),
                            'batting_home_runs': batting.get('homeRuns', 0),
                            'batting_runs': batting.get('runs', 0),
                            'batting_rbis': batting.get('rbi', 0),
                            'batting_walks': batting.get('baseOnBalls', 0),
                            'batting_intentional_walks': batting.get('intentionalWalks', 0),
                            'batting_strikeouts': batting.get('strikeOuts', 0),
                            'batting_hit_by_pitch': batting.get('hitByPitch', 0),
                            'batting_sacrifice_hits': batting.get('sacBunts', 0),
                            'batting_sacrifice_flies': batting.get('sacFlies', 0),
                            'batting_stolen_bases': batting.get('stolenBases', 0),
                            'batting_caught_stealing': batting.get('caughtStealing', 0),
                            'batting_grounded_into_double_plays': batting.get('groundIntoDoublePlay', 0),
                            'has_batting_data': 1
                        }
                        
                        # Calculate singles
                        stats_dict['batting_singles'] = (
                            stats_dict['batting_hits'] - 
                            stats_dict['batting_doubles'] - 
                            stats_dict['batting_triples'] - 
                            stats_dict['batting_home_runs']
                        )
                        
                        all_batting_stats.append(stats_dict)
        
        return pd.DataFrame(all_batting_stats)
    
    def _collect_pitching_stats(self, target_date: str, games: List[Dict]) -> pd.DataFrame:
        """Collect pitching stats for all players who pitched on the given date"""
        all_pitching_stats = []
        
        for game in games:
            game_id = game['game_id']
            
            # Get box score for the game
            boxscore_data = self.pybaseball_integration._get_game_boxscore(game_id)
            
            if not boxscore_data:
                continue
            
            # Process home and away pitchers
            for team_type in ['home', 'away']:
                team_code = game[f'{team_type}_team']
                pitchers = boxscore_data.get('teams', {}).get(team_type, {}).get('pitchers', [])
                
                for pitcher_id in pitchers:
                    player_data = boxscore_data.get('teams', {}).get(team_type, {}).get('players', {}).get(f'ID{pitcher_id}', {})
                    
                    if player_data and 'stats' in player_data and 'pitching' in player_data['stats']:
                        pitching = player_data['stats']['pitching']
                        
                        # Convert innings pitched from "5.2" format to decimal
                        ip_str = str(pitching.get('inningsPitched', '0.0'))
                        innings_pitched = self._convert_innings_pitched(ip_str)
                        
                        stats_dict = {
                            'mlb_id': pitcher_id,
                            'player_name': player_data.get('person', {}).get('fullName', ''),
                            'team_code': team_code,
                            'games_played': 1,
                            'pitching_games': 1,
                            'pitching_games_started': 1 if pitching.get('gamesStarted', 0) > 0 else 0,
                            'pitching_complete_games': pitching.get('completeGames', 0),
                            'pitching_shutouts': pitching.get('shutouts', 0),
                            'pitching_wins': pitching.get('wins', 0),
                            'pitching_losses': pitching.get('losses', 0),
                            'pitching_saves': pitching.get('saves', 0),
                            'pitching_holds': pitching.get('holds', 0),
                            'pitching_blown_saves': pitching.get('blownSaves', 0),
                            'pitching_innings_pitched': innings_pitched,
                            'pitching_hits_allowed': pitching.get('hits', 0),
                            'pitching_runs_allowed': pitching.get('runs', 0),
                            'pitching_earned_runs': pitching.get('earnedRuns', 0),
                            'pitching_home_runs_allowed': pitching.get('homeRuns', 0),
                            'pitching_walks_allowed': pitching.get('baseOnBalls', 0),
                            'pitching_intentional_walks_allowed': pitching.get('intentionalWalks', 0),
                            'pitching_strikeouts': pitching.get('strikeOuts', 0),
                            'pitching_hit_batters': pitching.get('hitBatsmen', 0),
                            'pitching_wild_pitches': pitching.get('wildPitches', 0),
                            'pitching_balks': pitching.get('balks', 0),
                            'has_pitching_data': 1
                        }
                        
                        all_pitching_stats.append(stats_dict)
        
        return pd.DataFrame(all_pitching_stats)
    
    def _convert_innings_pitched(self, ip_str: str) -> float:
        """Convert innings pitched from '5.2' format to 5.67 decimal"""
        if '.' in ip_str:
            innings, outs = ip_str.split('.')
            return float(innings) + float(outs) / 3.0
        return float(ip_str)
    
    def _merge_and_enrich_stats(self, batting_df: pd.DataFrame, pitching_df: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """Merge batting and pitching stats and enrich with player IDs"""
        # Merge on mlb_id
        if not batting_df.empty and not pitching_df.empty:
            all_stats = pd.merge(
                batting_df, pitching_df,
                on=['mlb_id', 'player_name', 'team_code', 'games_played'],
                how='outer'
            )
        elif not batting_df.empty:
            all_stats = batting_df.copy()
        elif not pitching_df.empty:
            all_stats = pitching_df.copy()
        else:
            all_stats = pd.DataFrame()
        
        if all_stats.empty:
            return all_stats
        
        # Fill NaN values with 0 for numeric columns
        numeric_columns = [col for col in all_stats.columns if col.startswith(('batting_', 'pitching_'))]
        all_stats[numeric_columns] = all_stats[numeric_columns].fillna(0)
        
        # Add date
        all_stats['date'] = target_date
        
        # Initialize position_codes column
        all_stats['position_codes'] = ''
        
        # Enrich with player IDs from mapping table
        for idx, row in all_stats.iterrows():
            # Both local and D1 now use mlb_player_id after migration
            result = self._execute_query(f"""
                SELECT yahoo_player_id, baseball_reference_id, fangraphs_id
                FROM player_mapping
                WHERE mlb_player_id = ?
            """, (row['mlb_id'],))
            
            mapping = self._fetchone(result)
            if mapping:
                # Handle Yahoo ID - it's already a string in the database
                yahoo_id = mapping[0]
                if yahoo_id is not None and str(yahoo_id).strip() and str(yahoo_id) != 'None':
                    # Yahoo IDs are already strings like "10794", just use them as is
                    yahoo_id = str(yahoo_id).strip()
                else:
                    yahoo_id = None
                all_stats.at[idx, 'yahoo_player_id'] = yahoo_id
                all_stats.at[idx, 'baseball_reference_id'] = mapping[1]
                all_stats.at[idx, 'fangraphs_id'] = mapping[2]
            else:
                # Player not found in mapping - set to None instead of leaving undefined
                all_stats.at[idx, 'yahoo_player_id'] = None
                all_stats.at[idx, 'baseball_reference_id'] = None
                all_stats.at[idx, 'fangraphs_id'] = None
            
            # Try to infer position from player's role in the game
            # Pitchers will have pitching stats, others are position players
            if row.get('pitching_games_started', 0) > 0 or row.get('pitching_innings_pitched', 0) > 0:
                all_stats.at[idx, 'position_codes'] = 'P'
            elif row.get('batting_at_bats', 0) > 0:
                # For now, mark as generic position player
                # Can be refined later with roster data
                all_stats.at[idx, 'position_codes'] = 'POS'
        
        return all_stats
    
    def _calculate_rate_stats(self, stats_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all rate statistics"""
        if stats_df.empty:
            return stats_df
        
        # Batting rate stats
        # AVG = H / AB
        stats_df['batting_avg'] = np.where(
            stats_df['batting_at_bats'] > 0,
            stats_df['batting_hits'] / stats_df['batting_at_bats'],
            0
        )
        
        # OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
        obp_numerator = (
            stats_df['batting_hits'] + 
            stats_df['batting_walks'] + 
            stats_df['batting_hit_by_pitch']
        )
        obp_denominator = (
            stats_df['batting_at_bats'] + 
            stats_df['batting_walks'] + 
            stats_df['batting_hit_by_pitch'] + 
            stats_df['batting_sacrifice_flies']
        )
        stats_df['batting_obp'] = np.where(
            obp_denominator > 0,
            obp_numerator / obp_denominator,
            0
        )
        
        # SLG = Total Bases / AB
        total_bases = (
            stats_df['batting_singles'] + 
            2 * stats_df['batting_doubles'] + 
            3 * stats_df['batting_triples'] + 
            4 * stats_df['batting_home_runs']
        )
        stats_df['batting_slg'] = np.where(
            stats_df['batting_at_bats'] > 0,
            total_bases / stats_df['batting_at_bats'],
            0
        )
        
        # OPS = OBP + SLG
        stats_df['batting_ops'] = stats_df['batting_obp'] + stats_df['batting_slg']
        
        # ISO = SLG - AVG
        stats_df['batting_iso'] = stats_df['batting_slg'] - stats_df['batting_avg']
        
        # BABIP = (H - HR) / (AB - K - HR + SF)
        babip_numerator = stats_df['batting_hits'] - stats_df['batting_home_runs']
        babip_denominator = (
            stats_df['batting_at_bats'] - 
            stats_df['batting_strikeouts'] - 
            stats_df['batting_home_runs'] + 
            stats_df['batting_sacrifice_flies']
        )
        stats_df['batting_babip'] = np.where(
            babip_denominator > 0,
            babip_numerator / babip_denominator,
            0
        )
        
        # Pitching rate stats
        # ERA = 9 * ER / IP
        stats_df['pitching_era'] = np.where(
            stats_df['pitching_innings_pitched'] > 0,
            9 * stats_df['pitching_earned_runs'] / stats_df['pitching_innings_pitched'],
            0
        )
        
        # WHIP = (H + BB) / IP
        stats_df['pitching_whip'] = np.where(
            stats_df['pitching_innings_pitched'] > 0,
            (stats_df['pitching_hits_allowed'] + stats_df['pitching_walks_allowed']) / stats_df['pitching_innings_pitched'],
            0
        )
        
        # K/9 = 9 * K / IP
        stats_df['pitching_k_per_9'] = np.where(
            stats_df['pitching_innings_pitched'] > 0,
            9 * stats_df['pitching_strikeouts'] / stats_df['pitching_innings_pitched'],
            0
        )
        
        # BB/9 = 9 * BB / IP
        stats_df['pitching_bb_per_9'] = np.where(
            stats_df['pitching_innings_pitched'] > 0,
            9 * stats_df['pitching_walks_allowed'] / stats_df['pitching_innings_pitched'],
            0
        )
        
        # HR/9 = 9 * HR / IP
        stats_df['pitching_hr_per_9'] = np.where(
            stats_df['pitching_innings_pitched'] > 0,
            9 * stats_df['pitching_home_runs_allowed'] / stats_df['pitching_innings_pitched'],
            0
        )
        
        # K/BB = K / BB
        stats_df['pitching_k_bb_ratio'] = np.where(
            stats_df['pitching_walks_allowed'] > 0,
            stats_df['pitching_strikeouts'] / stats_df['pitching_walks_allowed'],
            stats_df['pitching_strikeouts']  # If no walks, ratio is just K
        )
        
        # Round rate stats to reasonable precision
        rate_stat_columns = [
            'batting_avg', 'batting_obp', 'batting_slg', 'batting_ops', 'batting_iso', 'batting_babip',
            'pitching_era', 'pitching_whip', 'pitching_k_per_9', 'pitching_bb_per_9', 
            'pitching_hr_per_9', 'pitching_k_bb_ratio'
        ]
        
        for col in rate_stat_columns:
            if col in stats_df.columns:
                stats_df[col] = stats_df[col].round(3)
        
        return stats_df
    
    def _save_stats(self, stats_df: pd.DataFrame, job_id: str, target_date: str) -> int:
        """Save stats to database"""
        if stats_df.empty:
            return 0
        
        cursor = self._get_cursor() if self.use_d1 else self.conn.cursor()
        records_saved = 0
        
        # Define columns based on environment schema
        # Note: D1 production now uses mlb_player_id consistently
        if self.environment == 'production' or self.use_d1:
            # Production/D1 database schema
            columns = [
                'job_id', 'date', 'mlb_player_id', 'yahoo_player_id', 'baseball_reference_id', 'fangraphs_id',
                'player_name', 'team_code', 'position_codes', 'games_played',
                # Batting stats (only those that exist in production)
                'batting_plate_appearances', 'batting_at_bats', 'batting_runs', 'batting_hits', 
                'batting_singles', 'batting_doubles', 'batting_triples', 'batting_home_runs', 
                'batting_rbis', 'batting_stolen_bases', 'batting_caught_stealing', 'batting_walks',
                'batting_intentional_walks', 'batting_strikeouts', 'batting_hit_by_pitch',
                'batting_sacrifice_hits', 'batting_sacrifice_flies', 'batting_ground_into_double_play',
                # Pitching stats (only those that exist in production)
                'pitching_games_started', 'pitching_complete_games', 'pitching_shutouts',
                'pitching_wins', 'pitching_losses', 'pitching_saves', 'pitching_blown_saves', 
                'pitching_holds', 'pitching_innings_pitched', 'pitching_hits_allowed', 
                'pitching_runs_allowed', 'pitching_earned_runs', 'pitching_home_runs_allowed', 
                'pitching_walks_allowed', 'pitching_intentional_walks_allowed', 'pitching_strikeouts', 
                'pitching_hit_batters', 'pitching_wild_pitches', 'pitching_balks',
                # Metadata
                'data_source', 'has_batting_data', 'has_pitching_data'
            ]
        else:
            # Test/D1 database schema (comprehensive)
            columns = [
                'job_id', 'date', 'mlb_id', 'yahoo_player_id', 'baseball_reference_id', 'fangraphs_id',
                'player_name', 'team_code', 'position_codes', 'games_played',
                # Batting counting
                'batting_plate_appearances', 'batting_at_bats', 'batting_hits', 'batting_singles',
                'batting_doubles', 'batting_triples', 'batting_home_runs', 'batting_runs', 'batting_rbis',
                'batting_walks', 'batting_intentional_walks', 'batting_strikeouts', 'batting_hit_by_pitch',
                'batting_sacrifice_hits', 'batting_sacrifice_flies', 'batting_stolen_bases',
                'batting_caught_stealing', 'batting_grounded_into_double_plays',
                # Batting calculated
                'batting_avg', 'batting_obp', 'batting_slg', 'batting_ops', 'batting_babip', 'batting_iso',
                # Pitching counting
                'pitching_games', 'pitching_games_started', 'pitching_complete_games', 'pitching_shutouts',
                'pitching_wins', 'pitching_losses', 'pitching_saves', 'pitching_holds', 'pitching_blown_saves',
                'pitching_innings_pitched', 'pitching_hits_allowed', 'pitching_runs_allowed',
                'pitching_earned_runs', 'pitching_home_runs_allowed', 'pitching_walks_allowed',
                'pitching_intentional_walks_allowed', 'pitching_strikeouts', 'pitching_hit_batters',
                'pitching_wild_pitches', 'pitching_balks',
                # Pitching calculated
                'pitching_era', 'pitching_whip', 'pitching_k_per_9', 'pitching_bb_per_9',
                'pitching_hr_per_9', 'pitching_k_bb_ratio',
                # Metadata
                'has_batting_data', 'has_pitching_data', 'data_source'
            ]
        
        # Build INSERT query
        placeholders = ','.join(['?' for _ in columns])
        insert_query = f"""
            INSERT OR REPLACE INTO {self.stats_table} 
            ({','.join(columns)}, created_at, updated_at)
            VALUES ({placeholders}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        
        for _, row in stats_df.iterrows():
            try:
                # Build values list matching the column order
                values = []
                
                for col in columns:
                    if col == 'job_id':
                        values.append(job_id)
                    elif col == 'date':
                        values.append(target_date)
                    elif col in ['mlb_id', 'mlb_player_id']:
                        values.append(row.get('mlb_id'))
                    elif col == 'batting_ground_into_double_play':
                        # Handle production column name difference
                        values.append(row.get('batting_grounded_into_double_plays', 0))
                    elif col == 'data_source':
                        values.append('mlb_stats_api')
                    elif col == 'position_codes':
                        values.append(row.get(col, ''))
                    elif col == 'games_played':
                        values.append(row.get(col, 1))
                    else:
                        # Handle NaN values for D1 compatibility
                        value = row.get(col, 0)
                        if pd.isna(value) or (isinstance(value, float) and np.isnan(value)):
                            # Replace NaN with None for NULL in database
                            value = None
                        values.append(value)
                
                if self.use_d1:
                    try:
                        result = self.d1_conn.execute(insert_query, values)
                        if result and result.get('success', False):
                            records_saved += 1
                        else:
                            logger.error(f"D1 insert failed for {row.get('player_name')}: {result}")
                    except Exception as d1_error:
                        logger.error(f"D1 error for {row.get('player_name')}: {d1_error}")
                        logger.debug(f"Query: {insert_query[:100]}...")
                        logger.debug(f"Values count: {len(values)}, Columns count: {len(columns)}")
                        raise
                else:
                    cursor.execute(insert_query, values)
                    records_saved += 1
                
            except Exception as e:
                logger.error(f"Error saving stats for {row.get('player_name')}: {e}")
                logger.debug(f"Row data: mlb_id={row.get('mlb_id')}, player={row.get('player_name')}")
        
        self._commit()
        return records_saved
    
    def show_sample_results(self, target_date: str):
        """Show sample of collected stats"""
        mlb_id_column = 'mlb_player_id' if self.environment == 'production' else 'mlb_id'
        
        # Show summary
        result = self._execute_query(f"""
            SELECT 
                COUNT(DISTINCT {mlb_id_column}) as total_players,
                COUNT(DISTINCT CASE WHEN has_batting_data = 1 THEN {mlb_id_column} END) as batters,
                COUNT(DISTINCT CASE WHEN has_pitching_data = 1 THEN {mlb_id_column} END) as pitchers,
                COUNT(DISTINCT team_code) as teams
            FROM {self.stats_table}
            WHERE date = ?
        """, (target_date,))
        
        summary = self._fetchone(result)
        print(f"\n{'='*80}")
        print(f"STATS SUMMARY FOR {target_date}")
        print(f"{'='*80}")
        print(f"Total players: {summary[0]}")
        print(f"Batters: {summary[1]}")
        print(f"Pitchers: {summary[2]}")
        print(f"Teams: {summary[3]}")
        
        # Show top batters
        print(f"\n{'='*80}")
        print("TOP BATTING PERFORMANCES")
        print(f"{'='*80}")
        print(f"{'Player':<25} {'Team':<5} {'AB':<4} {'H':<3} {'R':<3} {'RBI':<4} {'HR':<3} {'AVG':<6} {'OPS':<6}")
        print("-" * 80)
        
        result = self._execute_query(f"""
            SELECT player_name, team_code, batting_at_bats, batting_hits, batting_runs,
                   batting_rbis, batting_home_runs, batting_avg, batting_ops
            FROM {self.stats_table}
            WHERE date = ? AND has_batting_data = 1 AND batting_at_bats > 0
            ORDER BY batting_ops DESC, batting_hits DESC
            LIMIT 10
        """, (target_date,))
        
        for row in self._fetchall(result):
            name = row[0][:25].ljust(25)
            team = (row[1] or 'N/A').ljust(5)
            ab = str(row[2]).rjust(4)
            h = str(row[3]).rjust(3)
            r = str(row[4]).rjust(3)
            rbi = str(row[5]).rjust(4)
            hr = str(row[6]).rjust(3)
            avg = f"{row[7]:.3f}".ljust(6)
            ops = f"{row[8]:.3f}".ljust(6)
            print(f"{name} {team} {ab} {h} {r} {rbi} {hr} {avg} {ops}")
        
        # Show ID mapping status
        result = self._execute_query(f"""
            SELECT 
                COUNT(DISTINCT {mlb_id_column}) as total,
                COUNT(DISTINCT CASE WHEN yahoo_player_id IS NOT NULL THEN {mlb_id_column} END) as yahoo_mapped,
                COUNT(DISTINCT CASE WHEN baseball_reference_id IS NOT NULL THEN {mlb_id_column} END) as bbref_mapped,
                COUNT(DISTINCT CASE WHEN fangraphs_id IS NOT NULL THEN {mlb_id_column} END) as fg_mapped
            FROM {self.stats_table}
            WHERE date = ?
        """, (target_date,))
        
        mapping = self._fetchone(result)
        print(f"\n{'='*80}")
        print("PLAYER ID MAPPING STATUS")
        print(f"{'='*80}")
        print(f"Total players: {mapping[0]}")
        print(f"Yahoo ID mapped: {mapping[1]} ({mapping[1]/mapping[0]*100:.1f}%)")
        print(f"Baseball Reference ID mapped: {mapping[2]} ({mapping[2]/mapping[0]*100:.1f}%)")
        print(f"FanGraphs ID mapped: {mapping[3]} ({mapping[3]/mapping[0]*100:.1f}%)")


def main():
    """Main function for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect comprehensive MLB player stats')
    parser.add_argument('--date', default='2024-08-05', help='Date to collect (YYYY-MM-DD)')
    parser.add_argument('--environment', default='test', choices=['test', 'production'])
    parser.add_argument('--init-mappings', action='store_true', help='Initialize player mappings')
    parser.add_argument('--use-d1', action='store_true', help='Use Cloudflare D1 database')
    
    args = parser.parse_args()
    
    collector = ComprehensiveStatsCollector(environment=args.environment, use_d1=args.use_d1)
    
    if args.init_mappings:
        collector.initialize_player_mappings()
        return
    
    # Collect stats
    records = collector.collect_daily_stats(args.date)
    print(f"\nCollected {records} player records for {args.date}")
    
    # Show results
    collector.show_sample_results(args.date)


if __name__ == '__main__':
    main()