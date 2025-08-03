#!/usr/bin/env python3
"""
Pre-flight Check and Test Script for Daily Lineups Multi-Season Backfill

This script performs comprehensive validation before running a large-scale backfill
of daily lineup data for seasons 2021-2025.

Checks performed:
1. Token validity and refresh capability
2. Database readiness and space
3. API connectivity for all league keys
4. Small-scale test collection
5. Performance estimation
"""

import sys
import os
import time
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.season_manager import SeasonManager, get_profile_seasons
from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.config import get_database_path, get_lineup_table_name
from daily_lineups.archive.test_scripts.parallel_collection import ParallelCollectionManager


class PreflightChecker:
    """Performs pre-flight checks for multi-season backfill."""
    
    def __init__(self, environment="production"):
        self.environment = environment
        self.season_manager = SeasonManager()
        self.db_path = get_database_path(environment)
        self.results = {}
        self.warnings = []
        self.errors = []
    
    def check_token_availability(self) -> bool:
        """Check if OAuth tokens are available and can be refreshed."""
        print("\n1. TOKEN AVAILABILITY CHECK")
        print("-" * 40)
        
        token_path = Path(__file__).parent.parent / "auth" / "tokens.json"
        
        if not token_path.exists():
            self.errors.append("Tokens file not found - run auth/initialize_tokens.py")
            print("   [ERROR] Tokens file not found")
            return False
        
        try:
            with open(token_path, 'r') as f:
                tokens = json.load(f)
            
            # Check for required fields
            required = ['access_token', 'refresh_token']
            missing = [field for field in required if field not in tokens]
            
            if missing:
                self.errors.append(f"Missing token fields: {missing}")
                print(f"   [ERROR] Missing fields: {missing}")
                return False
            
            # Check expiration if expires_at is present
            if 'expires_at' in tokens:
                expires_at = tokens['expires_at']
                expires_time = datetime.fromtimestamp(expires_at)
                now = datetime.now()
                
                if expires_time <= now:
                    print(f"   [WARNING] Token expired at {expires_time}")
                    print("   [INFO] Will attempt refresh during collection")
                    self.warnings.append("Token expired - will refresh automatically")
                else:
                    time_left = expires_time - now
                    print(f"   [OK] Token valid for {time_left.total_seconds() / 60:.1f} minutes")
            else:
                print("   [INFO] No expiration time found - will check at runtime")
                self.warnings.append("Token expiration unknown - will refresh as needed")
            
            self.results['token_check'] = True
            return True
            
        except Exception as e:
            self.errors.append(f"Token check failed: {e}")
            print(f"   [ERROR] {e}")
            return False
    
    def check_database_status(self) -> bool:
        """Check database connectivity and available space."""
        print("\n2. DATABASE STATUS CHECK")
        print("-" * 40)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables exist
            tables_to_check = ['daily_lineups', 'daily_lineups_test', 'job_log']
            for table in tables_to_check:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if cursor.fetchone():
                    # Get record count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   [OK] Table {table}: {count:,} records")
                else:
                    if table == 'daily_lineups_test' and self.environment == 'production':
                        continue  # Test table not required for production
                    self.errors.append(f"Table {table} does not exist")
                    print(f"   [ERROR] Table {table} not found")
                    return False
            
            # Check database file size
            db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            print(f"   [INFO] Database size: {db_size:.1f} MB")
            
            # Estimate space needed (rough estimate: 100 bytes per record)
            # 12 teams * 180 days * 5 seasons * 30 players/team * 100 bytes
            estimated_mb = (12 * 180 * 5 * 30 * 100) / (1024 * 1024)
            print(f"   [INFO] Estimated space needed: {estimated_mb:.1f} MB")
            
            # Check job_log has progress tracking columns
            cursor.execute("PRAGMA table_info(job_log)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'progress_pct' not in columns:
                self.warnings.append("job_log missing progress_pct column")
                print("   [WARNING] Progress tracking column missing")
            
            conn.close()
            self.results['database_check'] = True
            return True
            
        except Exception as e:
            self.errors.append(f"Database check failed: {e}")
            print(f"   [ERROR] {e}")
            return False
    
    def check_league_keys(self, seasons: List[int]) -> bool:
        """Verify league keys exist for all requested seasons."""
        print("\n3. LEAGUE KEYS VALIDATION")
        print("-" * 40)
        
        all_valid = True
        valid_seasons = []
        
        for season in seasons:
            info = self.season_manager.get_season_info(season)
            if info:
                days = self.season_manager.calculate_season_days(season)
                print(f"   [OK] {season}: {info['league_key']} ({days} days)")
                valid_seasons.append(season)
            else:
                self.errors.append(f"No configuration for season {season}")
                print(f"   [ERROR] {season}: No configuration found")
                all_valid = False
        
        self.results['league_keys_check'] = all_valid
        self.results['valid_seasons'] = valid_seasons
        
        # Calculate total workload
        if valid_seasons:
            total_days = sum(
                self.season_manager.calculate_season_days(s) 
                for s in valid_seasons
            )
            print(f"\n   Total days to collect: {total_days:,}")
            print(f"   Estimated records: {total_days * 12 * 30:,}")  # 12 teams, ~30 players
            
            # Time estimate (assuming 1 second per team-date)
            estimated_hours = (total_days * 12) / 3600
            print(f"   Estimated time: {estimated_hours:.1f} hours")
        
        return all_valid
    
    def test_api_connectivity(self, sample_seasons: List[int] = None) -> bool:
        """Test API connectivity for sample seasons."""
        print("\n4. API CONNECTIVITY TEST")
        print("-" * 40)
        
        if not sample_seasons:
            # Test most recent and oldest requested seasons
            valid_seasons = self.results.get('valid_seasons', [])
            if not valid_seasons:
                print("   [SKIP] No valid seasons to test")
                return True
            sample_seasons = [max(valid_seasons), min(valid_seasons)]
        
        collector = EnhancedLineupsCollector(environment=self.environment)
        all_success = True
        
        for season in sample_seasons:
            info = self.season_manager.get_season_info(season)
            if not info:
                continue
            
            print(f"\n   Testing {season} ({info['league_key']})...")
            
            try:
                # Test fetching teams
                teams = collector.fetch_league_teams(info['league_key'])
                if teams:
                    print(f"     [OK] Found {len(teams)} teams")
                    
                    # Test fetching one day of data for first team
                    test_date = info['start_date']
                    team_key = teams[0][0]
                    
                    players = collector.fetch_team_roster(team_key, test_date)
                    if players:
                        print(f"     [OK] Retrieved {len(players)} players for {test_date}")
                    else:
                        print(f"     [WARNING] No players found for {test_date}")
                else:
                    self.errors.append(f"No teams found for {season}")
                    print(f"     [ERROR] No teams found")
                    all_success = False
                    
            except Exception as e:
                self.errors.append(f"API test failed for {season}: {e}")
                print(f"     [ERROR] {e}")
                all_success = False
        
        self.results['api_connectivity'] = all_success
        return all_success
    
    def run_small_test(self, test_days: int = 3) -> bool:
        """Run a small test collection to verify everything works."""
        print("\n5. SMALL-SCALE TEST COLLECTION")
        print("-" * 40)
        
        # Use most recent season for testing
        test_season = 2025
        info = self.season_manager.get_season_info(test_season)
        
        if not info:
            print("   [SKIP] No 2025 season configuration")
            return True
        
        # Test with a few days in July
        test_start = "2025-07-01"
        test_end = datetime.strptime(test_start, "%Y-%m-%d") + timedelta(days=test_days - 1)
        test_end_str = test_end.strftime("%Y-%m-%d")
        
        print(f"   Testing {test_days} days: {test_start} to {test_end_str}")
        print(f"   Environment: {self.environment}")
        
        try:
            collector = EnhancedLineupsCollector(environment=self.environment)
            
            # Check if data already exists
            existing = collector.get_missing_dates(test_start, test_end_str, info['league_key'])
            
            if not existing:
                print("   [INFO] Test data already collected")
                self.results['test_collection'] = True
                return True
            
            print(f"   [INFO] Collecting {len(existing)} missing dates...")
            
            # Run collection
            start_time = time.time()
            job_id = collector.collect_date_range_with_resume(
                start_date=test_start,
                end_date=test_end_str,
                league_key=info['league_key'],
                resume=False
            )
            
            elapsed = time.time() - start_time
            
            # Check results
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            table_name = get_lineup_table_name(self.environment)
            cursor.execute(f"""
                SELECT COUNT(*), COUNT(DISTINCT date), COUNT(DISTINCT team_key)
                FROM {table_name}
                WHERE job_id = ?
            """, (job_id,))
            
            total_records, days_collected, teams_collected = cursor.fetchone()
            
            print(f"\n   Test Results:")
            print(f"     Job ID: {job_id[:40]}...")
            print(f"     Records inserted: {total_records}")
            print(f"     Days collected: {days_collected}")
            print(f"     Teams collected: {teams_collected}")
            print(f"     Time elapsed: {elapsed:.1f} seconds")
            print(f"     Rate: {total_records / elapsed:.1f} records/second")
            
            conn.close()
            
            self.results['test_collection'] = True
            self.results['test_rate'] = total_records / elapsed if elapsed > 0 else 0
            
            return True
            
        except Exception as e:
            self.errors.append(f"Test collection failed: {e}")
            print(f"   [ERROR] {e}")
            return False
    
    def estimate_backfill_time(self, seasons: List[int]) -> None:
        """Estimate time required for full backfill."""
        print("\n6. BACKFILL TIME ESTIMATION")
        print("-" * 40)
        
        total_days = 0
        for season in seasons:
            days = self.season_manager.calculate_season_days(season)
            if days:
                total_days += days
                print(f"   {season}: {days} days")
        
        print(f"\n   Total days: {total_days}")
        print(f"   Teams per day: 12")
        print(f"   Total API calls: {total_days * 12:,}")
        
        # Use test rate if available, otherwise use conservative estimate
        if 'test_rate' in self.results:
            rate = self.results['test_rate']
            estimated_records = total_days * 12 * 30  # ~30 players per team
            estimated_seconds = estimated_records / rate
        else:
            # Conservative: 1 second per API call + processing
            estimated_seconds = total_days * 12 * 1.5
        
        estimated_hours = estimated_seconds / 3600
        
        print(f"\n   Estimated time (single process): {estimated_hours:.1f} hours")
        print(f"   Estimated time (2 processes): {estimated_hours/2:.1f} hours")
        print(f"   Estimated time (4 processes): {estimated_hours/4:.1f} hours")
        
        self.results['estimated_hours'] = estimated_hours
    
    def generate_report(self) -> bool:
        """Generate final pre-flight report."""
        print("\n" + "=" * 60)
        print("PRE-FLIGHT CHECK REPORT")
        print("=" * 60)
        
        # Check results
        all_passed = all([
            self.results.get('token_check', False),
            self.results.get('database_check', False),
            self.results.get('league_keys_check', False),
            self.results.get('api_connectivity', False)
        ])
        
        print("\nCheck Results:")
        print(f"  Token Availability: {'PASS' if self.results.get('token_check') else 'FAIL'}")
        print(f"  Database Status: {'PASS' if self.results.get('database_check') else 'FAIL'}")
        print(f"  League Keys: {'PASS' if self.results.get('league_keys_check') else 'FAIL'}")
        print(f"  API Connectivity: {'PASS' if self.results.get('api_connectivity') else 'FAIL'}")
        print(f"  Test Collection: {'PASS' if self.results.get('test_collection') else 'N/A'}")
        
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")
        
        print("\n" + "=" * 60)
        
        if all_passed:
            print("RESULT: READY FOR BACKFILL")
            print("\nRecommended next steps:")
            print("1. Run small backfill for one season first:")
            print("   python daily_lineups/backfill_multi_season.py --seasons 2025 --processes 2")
            print("\n2. Monitor job progress:")
            print("   python daily_lineups/monitor_jobs.py")
            print("\n3. If successful, run full backfill:")
            print("   python daily_lineups/backfill_multi_season.py --seasons 2021-2025 --processes 4")
        else:
            print("RESULT: NOT READY - FIX ERRORS ABOVE")
        
        print("=" * 60)
        
        return all_passed


def main():
    """Run pre-flight checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-flight check for daily lineups backfill")
    parser.add_argument("--seasons", default="2021-2025",
                       help="Season range (e.g., '2021-2025') or comma-separated list")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment to use")
    parser.add_argument("--skip-test", action="store_true",
                       help="Skip test collection")
    
    args = parser.parse_args()
    
    # Parse seasons
    if '-' in args.seasons:
        start, end = args.seasons.split('-')
        seasons = list(range(int(start), int(end) + 1))
    else:
        seasons = [int(s.strip()) for s in args.seasons.split(',')]
    
    print(f"Pre-flight check for seasons: {seasons}")
    print(f"Environment: {args.env}")
    
    # Run checks
    checker = PreflightChecker(environment=args.env)
    
    # Core checks
    checker.check_token_availability()
    checker.check_database_status()
    checker.check_league_keys(seasons)
    checker.test_api_connectivity()
    
    # Optional test collection
    if not args.skip_test:
        checker.run_small_test()
    
    # Time estimation
    valid_seasons = checker.results.get('valid_seasons', seasons)
    if valid_seasons:
        checker.estimate_backfill_time(valid_seasons)
    
    # Final report
    ready = checker.generate_report()
    
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())