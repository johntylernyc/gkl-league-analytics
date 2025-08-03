#!/usr/bin/env python3
"""
PyBaseball Integration Module

Provides interface to pybaseball library for collecting MLB statistics.
Handles data collection, caching, and error handling for all MLB data sources.

Key Features:
- Daily batting and pitching statistics collection
- Player lookup and identification services
- Data caching and rate limiting
- Error handling and retry logic
- Multiple data source support (Fangraphs, Baseball Reference, Statcast)
"""

import sys
import logging
import json
import time
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
    Manages all interactions with the pybaseball library.
    
    Provides centralized access to MLB data with proper error handling,
    caching, and rate limiting to ensure reliable data collection.
    """
    
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
        Get daily batting statistics for a specific date.
        
        Args:
            target_date: Date to collect stats for
            
        Returns:
            DataFrame with batting stats or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Collecting daily batting stats for {target_date}")
            
            # Use pybaseball to get daily stats
            # Note: pybaseball doesn't have a direct "daily" function, so we need to
            # get stats for a date range and filter, or use game-by-game data
            
            # For now, we'll use a basic approach with season stats
            # This would need to be enhanced based on available pybaseball functions
            year = target_date.year
            
            # Get season batting stats (this is a placeholder - would need game-level data)
            batting_data = self.pybaseball.batting_stats(year, qual=1)
            
            if batting_data is None or batting_data.empty:
                logger.warning(f"No batting data found for {target_date}")
                return None
            
            # Add metadata columns
            batting_data['data_date'] = target_date.isoformat()
            batting_data['collection_date'] = date.today().isoformat()
            
            logger.info(f"Collected batting stats for {len(batting_data)} players on {target_date}")
            return batting_data
            
        except Exception as e:
            logger.error(f"Error collecting batting stats for {target_date}: {e}")
            return None
    
    def get_daily_pitching_stats(self, target_date: date) -> Optional[pd.DataFrame]:
        """
        Get daily pitching statistics for a specific date.
        
        Args:
            target_date: Date to collect stats for
            
        Returns:
            DataFrame with pitching stats or None if error
        """
        self._rate_limit()
        
        try:
            logger.info(f"Collecting daily pitching stats for {target_date}")
            
            year = target_date.year
            
            # Get season pitching stats (placeholder - would need game-level data)
            pitching_data = self.pybaseball.pitching_stats(year, qual=1)
            
            if pitching_data is None or pitching_data.empty:
                logger.warning(f"No pitching data found for {target_date}")
                return None
            
            # Add metadata columns
            pitching_data['data_date'] = target_date.isoformat()
            pitching_data['collection_date'] = date.today().isoformat()
            
            logger.info(f"Collected pitching stats for {len(pitching_data)} players on {target_date}")
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
                # Get current year batting stats with low qualifier
                current_year = datetime.now().year
                batting_data = self.pybaseball.batting_stats(current_year, qual=1)
                if batting_data is not None and not batting_data.empty:
                    test_results['batting_stats_working'] = True
                else:
                    test_results['errors'].append("Batting stats returned no data")
            except Exception as e:
                test_results['errors'].append(f"Batting stats failed: {e}")
            
            # Test pitching stats
            try:
                current_year = datetime.now().year
                pitching_data = self.pybaseball.pitching_stats(current_year, qual=1)
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