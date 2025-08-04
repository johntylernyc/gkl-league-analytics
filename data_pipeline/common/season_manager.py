"""
Season Manager - Centralized season management for Yahoo Fantasy Baseball data collection.

This module provides utilities for managing league keys, season dates, and multi-season
data collection operations. It serves as the single interface for all season-related
operations across the application.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import centralized league configuration
from data_pipeline.metadata.league_keys import LEAGUE_KEYS, SEASON_DATES


class SeasonManager:
    """Manages season-related operations and data access."""
    
    def __init__(self):
        self.league_keys = LEAGUE_KEYS
        self.season_dates = SEASON_DATES
        self.current_year = datetime.now().year
    
    def get_available_seasons(self) -> List[int]:
        """Get list of all configured seasons.
        
        Returns:
            List of season years in ascending order
        """
        return sorted(self.league_keys.keys())
    
    def validate_season(self, year: int) -> bool:
        """Check if season data exists for the given year.
        
        Args:
            year: Season year to validate
            
        Returns:
            True if season data exists, False otherwise
        """
        return year in self.league_keys and year in self.season_dates
    
    def get_season_info(self, year: int) -> Optional[Dict[str, any]]:
        """Get league key and dates for a specific season.
        
        Args:
            year: Season year
            
        Returns:
            Dictionary with league_key, start_date, and end_date,
            or None if season doesn't exist
        """
        if not self.validate_season(year):
            return None
        
        start_date, end_date = self.season_dates[year]
        return {
            'year': year,
            'league_key': self.league_keys[year],
            'start_date': start_date,
            'end_date': end_date
        }
    
    def get_league_key(self, year: int) -> Optional[str]:
        """Get league key for a specific season.
        
        Args:
            year: Season year
            
        Returns:
            League key string or None if season doesn't exist
        """
        return self.league_keys.get(year)
    
    def get_season_dates(self, year: int) -> Optional[Tuple[str, str]]:
        """Get start and end dates for a specific season.
        
        Args:
            year: Season year
            
        Returns:
            Tuple of (start_date, end_date) or None if season doesn't exist
        """
        return self.season_dates.get(year)
    
    def calculate_season_days(self, year: int) -> Optional[int]:
        """Calculate total days in a season.
        
        Args:
            year: Season year
            
        Returns:
            Number of days in the season or None if season doesn't exist
        """
        dates = self.get_season_dates(year)
        if not dates:
            return None
        
        start_date = datetime.strptime(dates[0], "%Y-%m-%d")
        end_date = datetime.strptime(dates[1], "%Y-%m-%d")
        return (end_date - start_date).days + 1
    
    def get_seasons_in_range(self, start_year: int, end_year: int) -> List[int]:
        """Get list of seasons within a year range.
        
        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
            
        Returns:
            List of available seasons within the range
        """
        available = self.get_available_seasons()
        return [year for year in available if start_year <= year <= end_year]
    
    def get_recent_seasons(self, count: int = 3) -> List[int]:
        """Get the most recent N seasons.
        
        Args:
            count: Number of recent seasons to return
            
        Returns:
            List of recent season years in descending order
        """
        available = self.get_available_seasons()
        return sorted(available[-count:], reverse=True)
    
    def get_current_season(self) -> Optional[int]:
        """Get the current season year if available.
        
        Returns:
            Current year if it's a configured season, None otherwise
        """
        return self.current_year if self.validate_season(self.current_year) else None
    
    def get_date_range_for_seasons(self, seasons: List[int]) -> Optional[Tuple[str, str]]:
        """Get the overall date range for multiple seasons.
        
        Args:
            seasons: List of season years
            
        Returns:
            Tuple of (earliest_start_date, latest_end_date) or None if no valid seasons
        """
        valid_seasons = [s for s in seasons if self.validate_season(s)]
        if not valid_seasons:
            return None
        
        all_dates = []
        for season in valid_seasons:
            start_date, end_date = self.season_dates[season]
            all_dates.extend([start_date, end_date])
        
        return (min(all_dates), max(all_dates))
    
    def generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of dates between start and end (inclusive).
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of date strings in YYYY-MM-DD format
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def get_season_for_date(self, date_str: str) -> Optional[int]:
        """Determine which season a date belongs to.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Season year or None if date doesn't fall within any season
        """
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        for year, (start_str, end_str) in self.season_dates.items():
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start_date <= target_date <= end_date:
                return year
        
        return None


# Collection profiles for convenient multi-season operations
COLLECTION_PROFILES = {
    "recent": "Last 3 seasons",
    "historical": "All seasons before current",
    "full": "All available seasons",
    "current": "Current season only"
}


def get_profile_seasons(profile: str, manager: Optional[SeasonManager] = None) -> List[int]:
    """Get seasons for a named collection profile.
    
    Args:
        profile: Profile name from COLLECTION_PROFILES
        manager: SeasonManager instance (creates new if not provided)
        
    Returns:
        List of season years for the profile
    """
    if manager is None:
        manager = SeasonManager()
    
    if profile == "recent":
        return manager.get_recent_seasons(3)
    elif profile == "current":
        current = manager.get_current_season()
        return [current] if current else []
    elif profile == "historical":
        current = manager.get_current_season()
        if current:
            all_seasons = manager.get_available_seasons()
            return [s for s in all_seasons if s < current]
        return []
    elif profile == "full":
        return manager.get_available_seasons()
    else:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(COLLECTION_PROFILES.keys())}")


# Create a default instance for convenience
default_manager = SeasonManager()

# Export commonly used functions at module level
get_available_seasons = default_manager.get_available_seasons
validate_season = default_manager.validate_season
get_season_info = default_manager.get_season_info
get_league_key = default_manager.get_league_key
get_season_dates = default_manager.get_season_dates
calculate_season_days = default_manager.calculate_season_days
get_seasons_in_range = default_manager.get_seasons_in_range
get_recent_seasons = default_manager.get_recent_seasons
get_current_season = default_manager.get_current_season