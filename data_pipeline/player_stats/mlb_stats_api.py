#!/usr/bin/env python3
"""
MLB Stats API Integration for Daily Player Statistics.

This module provides direct access to MLB's official stats API for collecting
true daily (game-by-game) statistics, working around the pybaseball bug.
"""

import sys
import logging
import json
import requests
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLBStatsAPI:
    """Direct interface to MLB Stats API for daily statistics."""
    
    BASE_URL = "https://statsapi.mlb.com/api/v1"
    
    def __init__(self):
        """Initialize the MLB Stats API client."""
        self.session = requests.Session()
        self.last_request_time = None
        self.min_request_interval = 0.5  # Be respectful with rate limiting
        
    def _rate_limit(self):
        """Apply rate limiting between API requests."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make a request to the MLB Stats API."""
        self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def get_games_for_date(self, target_date: date) -> List[Dict]:
        """Get all games played on a specific date."""
        date_str = target_date.strftime('%Y-%m-%d')
        
        data = self._make_request(
            "/schedule",
            params={
                "sportId": 1,  # MLB
                "date": date_str,
                "hydrate": "team,probablePitcher,lineups"
            }
        )
        
        if not data or 'dates' not in data or not data['dates']:
            logger.warning(f"No games found for {date_str}")
            return []
        
        games = []
        for date_data in data['dates']:
            if 'games' in date_data:
                games.extend(date_data['games'])
        
        logger.info(f"Found {len(games)} games on {date_str}")
        return games
    
    def get_game_boxscore(self, game_id: int) -> Optional[Dict]:
        """Get detailed boxscore for a specific game."""
        data = self._make_request(f"/game/{game_id}/boxscore")
        return data
    
    def get_player_game_stats(self, game_id: int, player_id: int) -> Dict[str, Any]:
        """Get a specific player's stats from a game."""
        boxscore = self.get_game_boxscore(game_id)
        
        if not boxscore:
            return {}
        
        stats = {
            'batting': {},
            'pitching': {}
        }
        
        # Check both teams
        for team_side in ['away', 'home']:
            team_data = boxscore.get('teams', {}).get(team_side, {})
            
            # Check batters
            batters = team_data.get('batters', [])
            if player_id in batters:
                player_stats = team_data.get('players', {}).get(f"ID{player_id}", {})
                if 'stats' in player_stats and 'batting' in player_stats['stats']:
                    stats['batting'] = player_stats['stats']['batting']
            
            # Check pitchers
            pitchers = team_data.get('pitchers', [])
            if player_id in pitchers:
                player_stats = team_data.get('players', {}).get(f"ID{player_id}", {})
                if 'stats' in player_stats and 'pitching' in player_stats['stats']:
                    stats['pitching'] = player_stats['stats']['pitching']
        
        return stats
    
    def get_daily_stats_for_all_players(self, target_date: date) -> pd.DataFrame:
        """
        Get daily statistics for all players who played on a specific date.
        
        Returns a DataFrame with one row per player per game.
        """
        games = self.get_games_for_date(target_date)
        
        if not games:
            return pd.DataFrame()
        
        all_player_stats = []
        
        for game in games:
            game_id = game['gamePk']
            game_date = game['gameDate']
            
            logger.debug(f"Processing game {game_id}")
            
            boxscore = self.get_game_boxscore(game_id)
            if not boxscore:
                continue
            
            # Process both teams
            for team_side in ['away', 'home']:
                team_data = boxscore.get('teams', {}).get(team_side, {})
                team_info = team_data.get('team', {})
                team_name = team_info.get('name', '')
                team_abbr = team_info.get('abbreviation', '')
                
                # Process all players
                players = team_data.get('players', {})
                
                for player_key, player_data in players.items():
                    player_info = player_data.get('person', {})
                    player_id = player_info.get('id')
                    player_name = player_info.get('fullName', '')
                    
                    # Get batting stats if available
                    if 'batting' in player_data.get('stats', {}):
                        batting = player_data['stats']['batting']
                        
                        stats_row = {
                            'date': target_date.isoformat(),
                            'game_id': game_id,
                            'player_id': player_id,
                            'player_name': player_name,
                            'team': team_abbr,
                            'team_name': team_name,
                            'stat_type': 'batting',
                            
                            # Batting stats (all component stats, no ratios)
                            'games_played': 1,
                            'plate_appearances': batting.get('plateAppearances', 0),
                            'at_bats': batting.get('atBats', 0),
                            'runs': batting.get('runs', 0),
                            'hits': batting.get('hits', 0),
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
                            'left_on_base': batting.get('leftOnBase', 0),
                            
                            # Calculate singles and total bases
                            'singles': batting.get('hits', 0) - batting.get('doubles', 0) - batting.get('triples', 0) - batting.get('homeRuns', 0),
                            'total_bases': (batting.get('hits', 0) - batting.get('doubles', 0) - batting.get('triples', 0) - batting.get('homeRuns', 0) +
                                          2 * batting.get('doubles', 0) + 3 * batting.get('triples', 0) + 4 * batting.get('homeRuns', 0))
                        }
                        
                        all_player_stats.append(stats_row)
                    
                    # Get pitching stats if available
                    if 'pitching' in player_data.get('stats', {}):
                        pitching = player_data['stats']['pitching']
                        
                        stats_row = {
                            'date': target_date.isoformat(),
                            'game_id': game_id,
                            'player_id': player_id,
                            'player_name': player_name,
                            'team': team_abbr,
                            'team_name': team_name,
                            'stat_type': 'pitching',
                            
                            # Pitching stats (all component stats, no ratios)
                            'games_played': 1,
                            'games_started': 1 if player_data.get('gameStatus', {}).get('isCurrentPitcher') else 0,
                            'wins': 1 if pitching.get('wins', 0) > 0 else 0,
                            'losses': 1 if pitching.get('losses', 0) > 0 else 0,
                            'saves': pitching.get('saves', 0),
                            'holds': pitching.get('holds', 0),
                            'blown_saves': pitching.get('blownSaves', 0),
                            'complete_games': pitching.get('completeGames', 0),
                            'shutouts': pitching.get('shutouts', 0),
                            'innings_pitched': pitching.get('inningsPitched', '0'),
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
                            'batters_faced': pitching.get('battersFaced', 0),
                            'pitches_thrown': pitching.get('numberOfPitches', 0),
                            
                            # Quality start determination (6+ IP, 3 or fewer ER)
                            'quality_starts': 1 if (self._innings_to_decimal(pitching.get('inningsPitched', '0')) >= 6.0 and 
                                                   pitching.get('earnedRuns', 0) <= 3) else 0
                        }
                        
                        all_player_stats.append(stats_row)
        
        df = pd.DataFrame(all_player_stats)
        logger.info(f"Collected stats for {len(df)} player-games on {target_date}")
        
        return df
    
    def _innings_to_decimal(self, innings_str: str) -> float:
        """Convert innings pitched format (e.g., '6.2') to decimal."""
        try:
            if '.' in str(innings_str):
                whole, outs = str(innings_str).split('.')
                return float(whole) + float(outs) / 3.0
            return float(innings_str)
        except:
            return 0.0


def main():
    """Test the MLB Stats API integration."""
    api = MLBStatsAPI()
    
    # Test date - use a date from 2024 season
    test_date = date(2024, 7, 1)
    
    print(f"Testing MLB Stats API for {test_date}...")
    print("-" * 60)
    
    # Get games for the date
    games = api.get_games_for_date(test_date)
    print(f"Found {len(games)} games")
    
    if games:
        # Show first game
        game = games[0]
        print(f"\nFirst game: {game.get('teams', {}).get('away', {}).get('team', {}).get('name', 'Unknown')} @ "
              f"{game.get('teams', {}).get('home', {}).get('team', {}).get('name', 'Unknown')}")
        
        # Get all player stats for the date
        print(f"\nCollecting all player stats for {test_date}...")
        stats_df = api.get_daily_stats_for_all_players(test_date)
        
        if not stats_df.empty:
            print(f"\nCollected {len(stats_df)} player-game records")
            
            # Show batting leaders
            batting_df = stats_df[stats_df['stat_type'] == 'batting']
            if not batting_df.empty:
                print("\nTop 5 hitters by hits:")
                top_hitters = batting_df.nlargest(5, 'hits')[['player_name', 'team', 'hits', 'home_runs', 'rbis']]
                for _, row in top_hitters.iterrows():
                    print(f"  {row['player_name']} ({row['team']}): {row['hits']} H, {row['home_runs']} HR, {row['rbis']} RBI")
            
            # Show pitching leaders
            pitching_df = stats_df[stats_df['stat_type'] == 'pitching']
            if not pitching_df.empty:
                print("\nTop 5 pitchers by strikeouts:")
                top_pitchers = pitching_df.nlargest(5, 'strikeouts_pitched')[['player_name', 'team', 'innings_pitched', 'strikeouts_pitched', 'earned_runs']]
                for _, row in top_pitchers.iterrows():
                    print(f"  {row['player_name']} ({row['team']}): {row['innings_pitched']} IP, {row['strikeouts_pitched']} K, {row['earned_runs']} ER")
        
        print("\n" + "=" * 60)
        print("SUCCESS! MLB Stats API provides true daily game statistics")
        print("This is the correct data source for daily player stats")


if __name__ == "__main__":
    main()