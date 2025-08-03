#!/usr/bin/env python3
"""
Alternative implementation for daily MLB stats collection.

Since batting_stats_range and pitching_stats_range are broken in pybaseball 2.2.7,
we'll use an alternative approach with statcast data or player game logs.
"""

import sys
import logging
import pandas as pd
import pybaseball as pyb
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DailyStatsCollector:
    """Collect daily MLB stats using alternative pybaseball methods."""
    
    def __init__(self):
        """Initialize the collector."""
        self.cache = {}
        
    def get_all_players_for_date(self, target_date: date) -> pd.DataFrame:
        """
        Get all MLB players who played on a specific date.
        
        This is a workaround since batting_stats_range is broken.
        We'll use team rosters and game logs.
        """
        year = target_date.year
        date_str = target_date.strftime('%Y-%m-%d')
        
        all_players = []
        
        # Get all teams
        teams = ['LAA', 'HOU', 'OAK', 'TOR', 'ATL', 'MIL', 'STL', 
                'CHC', 'ARI', 'LAD', 'SF', 'CLE', 'SEA', 'MIA', 
                'NYM', 'WSH', 'BAL', 'SD', 'PHI', 'PIT', 'TEX', 
                'TB', 'BOS', 'CIN', 'COL', 'KC', 'DET', 'MIN', 
                'CHW', 'NYY']
        
        logger.info(f"Collecting players for {date_str} from {len(teams)} teams")
        
        for team in teams:
            try:
                # Try to get team game logs
                # This would give us who played that day
                # Note: This is a simplified approach
                pass  # Placeholder since team_game_logs also has issues
                
            except Exception as e:
                logger.debug(f"Could not get {team} data: {e}")
        
        return pd.DataFrame(all_players)
    
    def get_player_daily_stats_statcast(self, player_name: str, target_date: date) -> Dict[str, Any]:
        """
        Get daily stats for a player using Statcast data.
        
        This aggregates pitch-level data into daily batting statistics.
        """
        try:
            # Look up player
            parts = player_name.split()
            if len(parts) >= 2:
                first = parts[0]
                last = ' '.join(parts[1:])
                player_lookup = pyb.playerid_lookup(last, first)
                
                if player_lookup is not None and not player_lookup.empty:
                    mlb_id = int(player_lookup.iloc[0]['key_mlbam'])
                    
                    # Get statcast data for that day
                    date_str = target_date.strftime('%Y-%m-%d')
                    data = pyb.statcast_batter(date_str, date_str, player_id=mlb_id)
                    
                    if data is not None and not data.empty:
                        # Aggregate to daily stats
                        stats = self._aggregate_statcast_to_daily(data, player_name, target_date)
                        return stats
        except Exception as e:
            logger.debug(f"Could not get statcast data for {player_name}: {e}")
        
        return {}
    
    def _aggregate_statcast_to_daily(self, statcast_data: pd.DataFrame, 
                                    player_name: str, target_date: date) -> Dict[str, Any]:
        """
        Aggregate pitch-level Statcast data to daily statistics.
        """
        stats = {
            'player_name': player_name,
            'date': target_date.isoformat(),
            'games_played': 1,  # If we have data, they played
            'plate_appearances': 0,
            'at_bats': 0,
            'runs': 0,
            'hits': 0,
            'singles': 0,
            'doubles': 0,
            'triples': 0,
            'home_runs': 0,
            'rbis': 0,
            'walks': 0,
            'strikeouts': 0,
            'stolen_bases': 0
        }
        
        # Count events
        if 'events' in statcast_data.columns:
            events = statcast_data['events'].dropna()
            
            # Plate appearances (any non-null event)
            stats['plate_appearances'] = len(events)
            
            # At-bats (PAs minus walks, HBP, sac flies, etc.)
            walk_events = ['walk', 'intentional_walk', 'hit_by_pitch']
            non_ab_events = walk_events + ['sac_fly', 'sac_bunt']
            stats['at_bats'] = len(events[~events.isin(non_ab_events)])
            
            # Hits
            hit_events = ['single', 'double', 'triple', 'home_run']
            hits = events[events.isin(hit_events)]
            stats['hits'] = len(hits)
            
            # Hit types
            stats['singles'] = len(events[events == 'single'])
            stats['doubles'] = len(events[events == 'double'])
            stats['triples'] = len(events[events == 'triple'])
            stats['home_runs'] = len(events[events == 'home_run'])
            
            # Walks and strikeouts
            stats['walks'] = len(events[events.isin(['walk', 'intentional_walk'])])
            stats['strikeouts'] = len(events[events == 'strikeout'])
        
        # Calculate total bases
        stats['total_bases'] = (stats['singles'] + 
                               2 * stats['doubles'] + 
                               3 * stats['triples'] + 
                               4 * stats['home_runs'])
        
        return stats
    
    def get_season_to_date_stats(self, year: int) -> pd.DataFrame:
        """
        Get season-to-date stats as a fallback.
        
        This uses the working batting_stats function.
        """
        try:
            # This works and gives us season totals
            batting_data = pyb.batting_stats(year, qual=1)
            return batting_data
        except Exception as e:
            logger.error(f"Error getting season stats: {e}")
            return pd.DataFrame()


def main():
    """Test the alternative implementation."""
    collector = DailyStatsCollector()
    
    # Test 1: Get season stats (this works)
    print("1. Testing season stats for 2024...")
    season_stats = collector.get_season_to_date_stats(2024)
    if not season_stats.empty:
        print(f"   Got {len(season_stats)} players with season stats")
        print(f"   Sample player: {season_stats.iloc[0]['Name']} - {season_stats.iloc[0]['H']} hits")
    
    # Test 2: Try statcast approach for a specific player
    print("\n2. Testing Statcast daily stats for Aaron Judge on 2024-07-01...")
    daily_stats = collector.get_player_daily_stats_statcast("Aaron Judge", date(2024, 7, 1))
    if daily_stats:
        print(f"   Daily stats: {daily_stats}")
    else:
        print("   No stats found for that date")
    
    print("\n" + "=" * 60)
    print("SOLUTION:")
    print("1. For now, use season-level stats from batting_stats() and pitching_stats()")
    print("2. Store these as 'cumulative' stats with date stamps")
    print("3. In future, implement daily collection via Statcast aggregation")
    print("4. Or wait for pybaseball fix to batting_stats_range")


if __name__ == "__main__":
    main()