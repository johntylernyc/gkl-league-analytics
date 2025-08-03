#!/usr/bin/env python3
"""Test script to validate the centralized season configuration."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.season_manager import SeasonManager
from auth.config import LEAGUE_KEYS, SEASON_DATES
from daily_lineups.config import get_season_dates, get_league_key
from datetime import datetime


def test_season_manager():
    """Test the SeasonManager functionality."""
    print("Testing SeasonManager...")
    
    # Create an instance of SeasonManager
    manager = SeasonManager()
    
    # Test getting current season
    current = manager.get_current_season()
    print(f"Current season: {current}")
    
    # Test getting season for specific dates
    test_dates = [
        "2024-04-15",
        "2024-10-01",
        "2025-05-01",
        "2025-09-30",
    ]
    
    for date in test_dates:
        season = manager.get_season_for_date(date)
        print(f"Season for {date}: {season}")
    
    # Test league key retrieval
    for year in [2024, 2025]:
        key = manager.get_league_key(year)
        print(f"League key for {year}: {key}")
    
    # Test season dates
    for year in [2024, 2025]:
        dates = manager.get_season_dates(year)
        if dates:
            print(f"Season {year} dates: {dates[0]} to {dates[1]}")
    
    print()


def test_auth_config():
    """Test that auth config imports correctly."""
    print("Testing auth/config.py imports...")
    print(f"LEAGUE_KEYS: {LEAGUE_KEYS}")
    print(f"SEASON_DATES: {SEASON_DATES}")
    print()


def test_daily_lineups_config():
    """Test daily_lineups config functions."""
    print("Testing daily_lineups/config.py functions...")
    
    # Test for different seasons
    for year in [2024, 2025]:
        dates = get_season_dates(year)
        key = get_league_key(year)
        print(f"Year {year}:")
        print(f"  Dates: {dates}")
        print(f"  League key: {key}")
    
    print()


def test_backfill_import():
    """Test that backfill script can import the configs."""
    print("Testing backfill script imports...")
    try:
        from league_transactions.backfill_transactions_optimized import LEAGUE_KEYS as BF_KEYS
        from league_transactions.backfill_transactions_optimized import SEASON_DATES as BF_DATES
        print(f"Backfill LEAGUE_KEYS: {BF_KEYS}")
        print(f"Backfill SEASON_DATES: {BF_DATES}")
        print("[SUCCESS] Backfill script imports successful")
    except ImportError as e:
        print(f"[FAILED] Failed to import from backfill script: {e}")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("CENTRALIZED SEASON CONFIGURATION TEST")
    print("=" * 60)
    print()
    
    test_season_manager()
    test_auth_config()
    test_daily_lineups_config()
    test_backfill_import()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()