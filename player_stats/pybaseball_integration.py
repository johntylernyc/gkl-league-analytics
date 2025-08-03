#!/usr/bin/env python3
"""
PyBaseball Integration Module

Provides interface to pybaseball library for collecting MLB statistics.
Handles data collection, caching, and error handling for all MLB data sources.

Key Features:
- Daily batting and pitching statistics collection via MLB Stats API
- Player lookup and identification services via pybaseball
- Data caching and rate limiting
- Error handling and retry logic
- Multiple data source support (MLB Stats API, Fangraphs, Baseball Reference, Statcast)

Note: Due to a bug in pybaseball 2.2.7's batting_stats_range and pitching_stats_range,
we use the MLB Stats API directly for daily statistics.
"""

import sys
import logging
import json
import time
import requests
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PyBaseballIntegration:
    """
    Manages all interactions with the pybaseball library and MLB Stats API.
    
    Provides centralized access to MLB data with proper error handling,
    caching, and rate limiting to ensure reliable data collection.
    
    Note: Due to bugs in pybaseball's batting_stats_range and pitching_stats_range,
    we use the MLB Stats API directly for daily statistics.
    """
    
    MLB_STATS_API_BASE = "https://statsapi.mlb.com/api/v1"
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the pybaseball integration.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        
        # Rate limiting settings
        self.last_request_time = None
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        
        # Data validation thresholds
        self.validation_config = self.config['data_validation']
        
        # Session for MLB Stats API
        self.session = requests.Session()
        
        logger.info(f"Initialized PyBaseballIntegration for {environment} environment")
        
        # Lazy import pybaseball to avoid immediate dependency
        self._pybaseball = None
        
    @property
    def pybaseball(self):
        """Lazy import of pybaseball to handle dependency gracefully."""
        if self._pybaseball is None:
            try:
                import pybaseball as pyb
                self._pybaseball = pyb
                logger.info("Successfully imported pybaseball")
            except ImportError as e:
                logger.error(f"Failed to import pybaseball: {e}")
                logger.error("Install with: pip install pybaseball")
                raise ImportError("pybaseball library is required. Install with: pip install pybaseball")
        
        return self._pybaseball
    
    def _rate_limit(self):
        """Apply rate limiting between API requests."""
        if self.last_request_time is not None:
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _mlb_api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make a request to the MLB Stats API."""
        self._rate_limit()
        
        url = f"{self.MLB_STATS_API_BASE}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MLB API request failed for {endpoint}: {e}")
            return None
    
    def _get_games_for_date(self, target_date: date) -> List[Dict]:
        """Get all games played on a specific date."""
        date_str = target_date.strftime('%Y-%m-%d')
        
        data = self._mlb_api_request(
            "/schedule",
            params={
                "sportId": 1,  # MLB
                "date": date_str,
                "hydrate": "team,probablePitcher,lineups"
            }
        )
        
        if not data or 'dates' not in data or not data['dates']:
            return []
        
        games = []
        for date_data in data['dates']:
            if 'games' in date_data:
                games.extend(date_data['games'])
        
        return games
    
    def _get_game_boxscore(self, game_id: int) -> Optional[Dict]:
        """Get detailed boxscore for a specific game."""
        return self._mlb_api_request(f"/game/{game_id}/boxscore")
    
    def _calculate_total_bases(self, batting: Dict) -> int:
        """Calculate total bases from batting stats."""
        singles = batting.get('hits', 0) - batting.get('doubles', 0) - batting.get('triples', 0) - batting.get('homeRuns', 0)
        return (singles + 
                2 * batting.get('doubles', 0) + 
                3 * batting.get('triples', 0) + 
                4 * batting.get('homeRuns', 0))
    
    def _innings_to_decimal(self, innings_str: str) -> float:
        """Convert innings pitched format (e.g., '6.2') to decimal."""
        try:
            if '.' in str(innings_str):
                whole, outs = str(innings_str).split('.')
                return float(whole) + float(outs) / 3.0
            return float(innings_str)
        except:
            return 0.0
    
    def lookup_player_ids(self, last_name: str, first_name: str = None) -> List[Dict[str, Any]]:
        """
        Look up player IDs across different data sources.
        
        Args:
            last_name: Player's last name
            first_name: Player's first name (optional)
            
        Returns:
            List of player records with various IDs
        """
        self._rate_limit()
        
        try:
            logger.debug(f"Looking up player IDs for: {first_name} {last_name}")
            
            # Use pybaseball's playerid_lookup function
            results = self.pybaseball.playerid_lookup(last_name, first_name)
            
            if results is None or results.empty:
                logger.warning(f"No player found for: {first_name} {last_name}")
                return []
            
            # Convert DataFrame to list of dictionaries
            players = []
            for _, row in results.iterrows():
                player = {
                    'name': f"{row.get('name_first', '')} {row.get('name_last', '')}".strip(),
                    'mlb_id': str(row.get('key_mlbam', '')) if pd.notna(row.get('key_mlbam')) else None,
                    'fangraphs_id': str(row.get('key_fangraphs', '')) if pd.notna(row.get('key_fangraphs')) else None,
                    'bbref_id': str(row.get('key_bbref', '')) if pd.notna(row.get('key_bbref')) else None,
                    'birth_year': int(row.get('birth_year', 0)) if pd.notna(row.get('birth_year')) else None,
                    'positions': None,  # Will be populated from other sources if needed
                    'team': None,       # Will be populated from stats if needed
                    'active_years': {
                        'start': int(row.get('mlb_played_first', 0)) if pd.notna(row.get('mlb_played_first')) else None,
                        'end': int(row.get('mlb_played_last', 0)) if pd.notna(row.get('mlb_played_last')) else None
                    }
                }
                players.append(player)
            
            logger.debug(f"Found {len(players)} player(s) for: {first_name} {last_name}")
            return players
            
        except Exception as e:
            logger.error(f"Error looking up player IDs for {first_name} {last_name}: {e}")
            return []
    
    def get_daily_batting_stats(self, target_date: date) -> Optional[pd.DataFrame]:
        """
        Get daily batting statistics for a specific date using MLB Stats API.
        
        Args:
            target_date: Date to collect stats for
            
        Returns:
            DataFrame with batting stats or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Collecting daily batting stats for {target_date} via MLB Stats API")
            
            # Get all games for the date
            games = self._get_games_for_date(target_date)
            if not games:
                logger.warning(f"No games found for {target_date}")
                return None
            
            all_batting_stats = []
            
            for game in games:
                game_id = game['gamePk']
                
                # Get boxscore for the game
                boxscore = self._get_game_boxscore(game_id)
                if not boxscore:
                    continue
                
                # Process both teams
                for team_side in ['away', 'home']:
                    team_data = boxscore.get('teams', {}).get(team_side, {})
                    team_info = team_data.get('team', {})
                    team_abbr = team_info.get('abbreviation', '')
                    
                    # Process all players
                    players = team_data.get('players', {})
                    
                    for player_key, player_data in players.items():
                        if 'batting' not in player_data.get('stats', {}):
                            continue
                        
                        player_info = player_data.get('person', {})
                        batting = player_data['stats']['batting']
                        
                        # Create row with component stats (no ratios)
                        stats_row = {
                            'player_id': player_info.get('id'),
                            'player_name': player_info.get('fullName', ''),
                            'team': team_abbr,
                            'games_played': 1,
                            'plate_appearances': batting.get('plateAppearances', 0),
                            'at_bats': batting.get('atBats', 0),
                            'runs': batting.get('runs', 0),
                            'hits': batting.get('hits', 0),
                            'singles': (batting.get('hits', 0) - batting.get('doubles', 0) - 
                                       batting.get('triples', 0) - batting.get('homeRuns', 0)),
                            'doubles': batting.get('doubles', 0),
                            'triples': batting.get('triples', 0),
                            'home_runs': batting.get('homeRuns', 0),
                            'rbis': batting.get('rbi', 0),
                            'walks': batting.get('baseOnBalls', 0),
                            'intentional_walks': batting.get('intentionalWalks', 0),
                            'strikeouts': batting.get('strikeOuts', 0),
                            'stolen_bases': batting.get('stolenBases', 0),
                            'caught_stealing': batting.get('caughtStealing', 0),
                            'hit_by_pitch': batting.get('hitByPitch', 0),
                            'sacrifice_flies': batting.get('sacFlies', 0),
                            'sacrifice_hits': batting.get('sacBunts', 0),
                            'ground_into_double_play': batting.get('groundIntoDoublePlay', 0),
                            'total_bases': self._calculate_total_bases(batting),
                            'data_date': target_date.isoformat(),
                            'collection_date': date.today().isoformat()
                        }
                        
                        all_batting_stats.append(stats_row)
            
            if not all_batting_stats:
                logger.warning(f"No batting data collected for {target_date}")
                return None
            
            batting_data = pd.DataFrame(all_batting_stats)
            
            # Aggregate by player (in case they played multiple games)
            numeric_cols = [col for col in batting_data.columns 
                          if col not in ['player_id', 'player_name', 'team', 'data_date', 'collection_date']]
            
            batting_data = batting_data.groupby(['player_id', 'player_name', 'team', 'data_date', 'collection_date'])[numeric_cols].sum().reset_index()
            
            logger.info(f"Collected daily batting stats for {len(batting_data)} players on {target_date}")
            return batting_data
            
        except Exception as e:
            logger.error(f"Error collecting batting stats for {target_date}: {e}")
            return None
    
    def get_daily_pitching_stats(self, target_date: date) -> Optional[pd.DataFrame]:
        """
        Get daily pitching statistics for a specific date using MLB Stats API.
        
        Args:
            target_date: Date to collect stats for
            
        Returns:
            DataFrame with pitching stats or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Collecting daily pitching stats for {target_date} via MLB Stats API")
            
            # Get all games for the date
            games = self._get_games_for_date(target_date)
            if not games:
                logger.warning(f"No games found for {target_date}")
                return None
            
            all_pitching_stats = []
            
            for game in games:
                game_id = game['gamePk']
                
                # Get boxscore for the game
                boxscore = self._get_game_boxscore(game_id)
                if not boxscore:
                    continue
                
                # Process both teams
                for team_side in ['away', 'home']:
                    team_data = boxscore.get('teams', {}).get(team_side, {})
                    team_info = team_data.get('team', {})
                    team_abbr = team_info.get('abbreviation', '')
                    
                    # Process all players
                    players = team_data.get('players', {})
                    
                    for player_key, player_data in players.items():
                        if 'pitching' not in player_data.get('stats', {}):
                            continue
                        
                        player_info = player_data.get('person', {})
                        pitching = player_data['stats']['pitching']
                        
                        # Determine if this was a quality start
                        ip_decimal = self._innings_to_decimal(pitching.get('inningsPitched', '0'))
                        quality_start = (ip_decimal >= 6.0 and pitching.get('earnedRuns', 0) <= 3)
                        
                        # Create row with component stats (no ratios)
                        stats_row = {
                            'player_id': player_info.get('id'),
                            'player_name': player_info.get('fullName', ''),
                            'team': team_abbr,
                            'games_played': 1,
                            'games_started': 1 if player_data.get('gameStatus', {}).get('isStartingPitcher') else 0,
                            'complete_games': pitching.get('completeGames', 0),
                            'shutouts': pitching.get('shutouts', 0),
                            'wins': 1 if pitching.get('wins', 0) > 0 else 0,
                            'losses': 1 if pitching.get('losses', 0) > 0 else 0,
                            'saves': pitching.get('saves', 0),
                            'blown_saves': pitching.get('blownSaves', 0),
                            'holds': pitching.get('holds', 0),
                            'innings_pitched': ip_decimal,  # Store as decimal
                            'batters_faced': pitching.get('battersFaced', 0),
                            'hits_allowed': pitching.get('hits', 0),
                            'runs_allowed': pitching.get('runs', 0),
                            'earned_runs': pitching.get('earnedRuns', 0),
                            'home_runs_allowed': pitching.get('homeRuns', 0),
                            'walks_allowed': pitching.get('baseOnBalls', 0),
                            'intentional_walks_allowed': pitching.get('intentionalWalks', 0),
                            'strikeouts_pitched': pitching.get('strikeOuts', 0),
                            'hit_batters': pitching.get('hitBatsmen', 0),
                            'wild_pitches': pitching.get('wildPitches', 0),
                            'balks': pitching.get('balks', 0),
                            'quality_starts': 1 if quality_start else 0,
                            'data_date': target_date.isoformat(),
                            'collection_date': date.today().isoformat()
                        }
                        
                        all_pitching_stats.append(stats_row)
            
            if not all_pitching_stats:
                logger.warning(f"No pitching data collected for {target_date}")
                return None
            
            pitching_data = pd.DataFrame(all_pitching_stats)
            
            # Aggregate by player (in case they played multiple games)
            numeric_cols = [col for col in pitching_data.columns 
                          if col not in ['player_id', 'player_name', 'team', 'data_date', 'collection_date']]
            
            pitching_data = pitching_data.groupby(['player_id', 'player_name', 'team', 'data_date', 'collection_date'])[numeric_cols].sum().reset_index()
            
            logger.info(f"Collected daily pitching stats for {len(pitching_data)} players on {target_date}")
            return pitching_data
            
        except Exception as e:
            logger.error(f"Error collecting pitching stats for {target_date}: {e}")
            return None
    
    def get_game_logs(self, player_id: str, year: int, id_type: str = "fangraphs") -> Optional[pd.DataFrame]:
        """
        Get game logs for a specific player.
        
        Args:
            player_id: Player ID
            year: Year to get logs for
            id_type: Type of ID ('fangraphs', 'bbref', 'mlb')
            
        Returns:
            DataFrame with game logs or None if error
        """
        self._rate_limit()
        
        try:
            logger.debug(f"Getting game logs for player {player_id} ({id_type}) in {year}")
            
            if id_type == "fangraphs":
                # Get batting game logs from Fangraphs
                batting_logs = self.pybaseball.batting_stats_range(
                    f"{year}-01-01", f"{year}-12-31",
                    playerid=int(player_id)
                )
                
                # Get pitching game logs from Fangraphs
                pitching_logs = self.pybaseball.pitching_stats_range(
                    f"{year}-01-01", f"{year}-12-31", 
                    playerid=int(player_id)
                )
                
                # Combine if both exist
                if batting_logs is not None and not batting_logs.empty:
                    return batting_logs
                elif pitching_logs is not None and not pitching_logs.empty:
                    return pitching_logs
                else:
                    return None
            
            elif id_type == "bbref":
                # Use Baseball Reference game logs if available
                # This would require bbref-specific pybaseball functions
                logger.warning("Baseball Reference game logs not yet implemented")
                return None
            
            else:
                logger.warning(f"Unsupported ID type: {id_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting game logs for player {player_id}: {e}")
            return None
    
    def validate_batting_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate batting data quality.
        
        Args:
            data: DataFrame with batting stats
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'stats': {}
        }
        
        if data is None or data.empty:
            validation['is_valid'] = False
            validation['errors'].append("No data provided")
            return validation
        
        # Basic data quality checks
        validation['stats']['total_rows'] = len(data)
        validation['stats']['total_columns'] = len(data.columns)
        
        # Check for required columns
        required_batting_cols = ['Name', 'Team', 'G', 'AB', 'R', 'H', 'HR', 'RBI']
        missing_cols = [col for col in required_batting_cols if col not in data.columns]
        
        if missing_cols:
            validation['errors'].append(f"Missing required columns: {missing_cols}")
            validation['is_valid'] = False
        
        # Check for reasonable value ranges
        if 'AVG' in data.columns:
            invalid_avg = data[(data['AVG'] < 0) | (data['AVG'] > 1.0)]['AVG'].count()
            if invalid_avg > 0:
                validation['warnings'].append(f"{invalid_avg} players with invalid batting averages")
        
        if 'HR' in data.columns:
            max_hr = data['HR'].max()
            if max_hr > self.validation_config['max_home_runs_per_game']:
                validation['warnings'].append(f"Maximum HR ({max_hr}) exceeds expected range")
        
        validation['stats']['validation_score'] = 1.0 if validation['is_valid'] else 0.0
        
        return validation
    
    def validate_pitching_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate pitching data quality.
        
        Args:
            data: DataFrame with pitching stats
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'stats': {}
        }
        
        if data is None or data.empty:
            validation['is_valid'] = False
            validation['errors'].append("No data provided")
            return validation
        
        # Basic data quality checks
        validation['stats']['total_rows'] = len(data)
        validation['stats']['total_columns'] = len(data.columns)
        
        # Check for required columns
        required_pitching_cols = ['Name', 'Team', 'G', 'GS', 'IP', 'H', 'ER', 'BB', 'SO']
        missing_cols = [col for col in required_pitching_cols if col not in data.columns]
        
        if missing_cols:
            validation['errors'].append(f"Missing required columns: {missing_cols}")
            validation['is_valid'] = False
        
        # Check for reasonable value ranges
        if 'ERA' in data.columns:
            max_era = data['ERA'].max()
            if max_era > self.validation_config['max_era']:
                validation['warnings'].append(f"Maximum ERA ({max_era:.2f}) exceeds expected range")
        
        if 'WHIP' in data.columns:
            max_whip = data['WHIP'].max()
            if max_whip > self.validation_config['max_whip']:
                validation['warnings'].append(f"Maximum WHIP ({max_whip:.2f}) exceeds expected range")
        
        validation['stats']['validation_score'] = 1.0 if validation['is_valid'] else 0.0
        
        return validation
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the pybaseball connection and functionality.
        
        Returns:
            Dictionary with test results
        """
        test_results = {
            'pybaseball_available': False,
            'player_lookup_working': False,
            'batting_stats_working': False,
            'pitching_stats_working': False,
            'errors': []
        }
        
        try:
            # Test pybaseball import
            _ = self.pybaseball
            test_results['pybaseball_available'] = True
            
            # Test player lookup
            try:
                players = self.lookup_player_ids("Trout", "Mike")
                if players:
                    test_results['player_lookup_working'] = True
                else:
                    test_results['errors'].append("Player lookup returned no results")
            except Exception as e:
                test_results['errors'].append(f"Player lookup failed: {e}")
            
            # Test batting stats (try to get a small sample)
            try:
                # Get yesterday's batting stats as a test
                from datetime import timedelta
                test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                batting_data = self.pybaseball.batting_stats_range(test_date, test_date)
                if batting_data is not None and not batting_data.empty:
                    test_results['batting_stats_working'] = True
                else:
                    test_results['errors'].append("Batting stats returned no data")
            except Exception as e:
                test_results['errors'].append(f"Batting stats failed: {e}")
            
            # Test pitching stats
            try:
                from datetime import timedelta
                test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                pitching_data = self.pybaseball.pitching_stats_range(test_date, test_date)
                if pitching_data is not None and not pitching_data.empty:
                    test_results['pitching_stats_working'] = True
                else:
                    test_results['errors'].append("Pitching stats returned no data")
            except Exception as e:
                test_results['errors'].append(f"Pitching stats failed: {e}")
                
        except Exception as e:
            test_results['errors'].append(f"PyBaseball not available: {e}")
        
        return test_results


def main():
    """Command-line interface for pybaseball integration testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyBaseball Integration Testing")
    parser.add_argument("action", choices=["test", "lookup", "batting", "pitching"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--last-name", help="Player last name for lookup")
    parser.add_argument("--first-name", help="Player first name for lookup")
    parser.add_argument("--date", help="Date for stats collection (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    integration = PyBaseballIntegration(environment=args.env)
    
    if args.action == "test":
        print(f"Testing pybaseball integration...")
        print("-" * 60)
        
        results = integration.test_connection()
        
        print(f"PyBaseball available: {'[SUCCESS]' if results['pybaseball_available'] else '[FAILED]'}")
        print(f"Player lookup working: {'[SUCCESS]' if results['player_lookup_working'] else '[FAILED]'}")
        print(f"Batting stats working: {'[SUCCESS]' if results['batting_stats_working'] else '[FAILED]'}")
        print(f"Pitching stats working: {'[SUCCESS]' if results['pitching_stats_working'] else '[FAILED]'}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
    
    elif args.action == "lookup":
        if not args.last_name:
            print("ERROR: --last-name is required for lookup")
            return
        
        print(f"Looking up player: {args.first_name} {args.last_name}")
        print("-" * 60)
        
        players = integration.lookup_player_ids(args.last_name, args.first_name)
        
        if players:
            for i, player in enumerate(players, 1):
                print(f"{i}. {player['name']}")
                print(f"   MLB ID: {player['mlb_id']}")
                print(f"   Fangraphs ID: {player['fangraphs_id']}")
                print(f"   BBRef ID: {player['bbref_id']}")
                print(f"   Birth Year: {player['birth_year']}")
                print()
        else:
            print("No players found")
    
    elif args.action in ["batting", "pitching"]:
        if not args.date:
            print("ERROR: --date is required for stats collection")
            return
        
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Collecting {args.action} stats for {target_date}")
        print("-" * 60)
        
        if args.action == "batting":
            data = integration.get_daily_batting_stats(target_date)
            if data is not None:
                print(f"Collected {len(data)} batting records")
                validation = integration.validate_batting_data(data)
                print(f"Validation: {'[SUCCESS]' if validation['is_valid'] else '[FAILED]'}")
                if validation['warnings']:
                    print("Warnings:", validation['warnings'])
                if validation['errors']:
                    print("Errors:", validation['errors'])
            else:
                print("No batting data collected")
        
        elif args.action == "pitching":
            data = integration.get_daily_pitching_stats(target_date)
            if data is not None:
                print(f"Collected {len(data)} pitching records")
                validation = integration.validate_pitching_data(data)
                print(f"Validation: {'[SUCCESS]' if validation['is_valid'] else '[FAILED]'}")
                if validation['warnings']:
                    print("Warnings:", validation['warnings'])
                if validation['errors']:
                    print("Errors:", validation['errors'])
            else:
                print("No pitching data collected")


if __name__ == "__main__":
    main()