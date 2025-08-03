#!/usr/bin/env python3
"""
Current-Date Daily Lineups Collection Script

This script implements the correct daily lineup collection behavior:
1. Only processes dates up to today (never future dates)
2. Updates the most recent date to capture roster changes
3. Collects missing dates from last update through today
4. Includes date validation to prevent future date collection

Usage:
    python daily_lineups_current.py [--env production]
    python daily_lineups_current.py --dry-run
    python daily_lineups_current.py --check-status
"""

import sys
import os
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.job_manager import LineupJobManager
from daily_lineups.repository import LineupRepository
from daily_lineups.config import (
    get_database_path,
    get_lineup_table_name,
    get_league_key,
    get_season_dates,
    SEASON_DATES
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CurrentDateLineupCollector:
    """Manages current-date-only lineup data collection."""
    
    def __init__(self, environment="production"):
        """
        Initialize the current-date collector.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.db_path = get_database_path(environment)
        self.table_name = get_lineup_table_name(environment)
        self.job_manager = LineupJobManager(environment)
        self.repository = LineupRepository(environment)
        
        # Initialize collector (will use tokens.json fallback)
        self.collector = EnhancedLineupsCollector(token_manager=None, environment=environment)
        
        # Get today's date - this is our maximum allowed date
        self.today = date.today()
        self.today_str = self.today.strftime("%Y-%m-%d")
        
        logger.info(f"Initialized CurrentDateLineupCollector for {environment}")
        logger.info(f"Today's date (max allowed): {self.today_str}")
    
    def validate_date(self, date_str: str) -> bool:
        """
        Validate that a date is not in the future and within season bounds.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            True if date is valid, False otherwise
        """
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Critical validation: Never allow future dates
            if target_date > self.today:
                logger.error(f"REJECTED: Date {date_str} is in the future (today: {self.today_str})")
                return False
            
            # Check if date is within season bounds
            year = target_date.year
            season_dates = SEASON_DATES.get(year)
            
            if not season_dates:
                logger.warning(f"No season configuration for year {year}")
                return False
            
            season_start = datetime.strptime(season_dates[0], "%Y-%m-%d").date()
            season_end = datetime.strptime(season_dates[1], "%Y-%m-%d").date()
            
            if not (season_start <= target_date <= season_end):
                logger.warning(f"Date {date_str} is outside season bounds ({season_dates[0]} to {season_dates[1]})")
                return False
            
            return True
            
        except ValueError as e:
            logger.error(f"Invalid date format {date_str}: {e}")
            return False
    
    def get_last_update_date(self) -> Optional[str]:
        """
        Get the most recent date in the database.
        
        Returns:
            Last update date in YYYY-MM-DD format or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT MAX(date) as last_date
                FROM {self.table_name}
                WHERE date <= ?
            """, (self.today_str,))
            
            result = cursor.fetchone()
            last_date = result[0] if result and result[0] else None
            
            if last_date:
                logger.info(f"Last update date in database: {last_date}")
            else:
                logger.info("No existing data found in database")
            
            return last_date
            
        finally:
            conn.close()
    
    def get_database_date_range(self) -> Dict:
        """
        Get the current date range in the database.
        
        Returns:
            Dictionary with min_date, max_date, and record count
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT 
                    MIN(date) as min_date,
                    MAX(date) as max_date,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT date) as unique_dates,
                    COUNT(DISTINCT team_key) as unique_teams
                FROM {self.table_name}
                WHERE date <= ?
            """, (self.today_str,))
            
            result = cursor.fetchone()
            
            return {
                "min_date": result[0] if result else None,
                "max_date": result[1] if result else None,
                "total_records": result[2] if result else 0,
                "unique_dates": result[3] if result else 0,
                "unique_teams": result[4] if result else 0
            }
            
        finally:
            conn.close()
    
    def generate_missing_dates(self, last_date: Optional[str] = None) -> List[str]:
        """
        Generate list of dates that need to be collected.
        
        Args:
            last_date: Last date in database (optional)
            
        Returns:
            List of dates to collect (YYYY-MM-DD format)
        """
        missing_dates = []
        
        if last_date:
            # Start from day after last update
            last_dt = datetime.strptime(last_date, "%Y-%m-%d").date()
            start_date = last_dt + timedelta(days=1)
        else:
            # No existing data - start from season beginning
            year = self.today.year
            season_dates = SEASON_DATES.get(year)
            if season_dates:
                start_date = datetime.strptime(season_dates[0], "%Y-%m-%d").date()
            else:
                # Fallback to beginning of current year
                start_date = date(year, 1, 1)
        
        # Generate dates from start_date through today
        current_date = start_date
        while current_date <= self.today:
            date_str = current_date.strftime("%Y-%m-%d")
            if self.validate_date(date_str):
                missing_dates.append(date_str)
            current_date += timedelta(days=1)
        
        return missing_dates
    
    def get_collection_plan(self) -> Dict:
        """
        Create a collection plan for current-date processing.
        
        Returns:
            Dictionary with collection plan details
        """
        logger.info("Creating collection plan...")
        
        # Get current database state
        db_state = self.get_database_date_range()
        last_date = self.get_last_update_date()
        missing_dates = self.generate_missing_dates(last_date)
        
        plan = {
            "today": self.today_str,
            "max_allowed_date": self.today_str,
            "database_state": db_state,
            "last_update_date": last_date,
            "refresh_date": last_date,  # Re-collect to catch changes
            "missing_dates": missing_dates,
            "total_new_dates": len(missing_dates),
            "estimated_records": len(missing_dates) * 18 * 25,  # dates * teams * avg_players
            "will_refresh_last": last_date is not None
        }
        
        logger.info(f"Collection plan created:")
        logger.info(f"  Last update date: {last_date}")
        logger.info(f"  Will refresh last date: {plan['will_refresh_last']}")
        logger.info(f"  Missing dates to collect: {len(missing_dates)}")
        logger.info(f"  Date range: {missing_dates[0] if missing_dates else 'N/A'} to {self.today_str}")
        
        return plan
    
    def collect_single_date(self, date_str: str, job_id: str, is_refresh: bool = False) -> Dict:
        """
        Collect lineup data for a single date.
        
        Args:
            date_str: Date to collect (YYYY-MM-DD format)
            job_id: Job identifier for tracking
            is_refresh: Whether this is a refresh of existing data
            
        Returns:
            Collection results
        """
        if not self.validate_date(date_str):
            raise ValueError(f"Invalid date for collection: {date_str}")
        
        action = "Refreshing" if is_refresh else "Collecting"
        logger.info(f"{action} data for {date_str}")
        
        try:
            # If this is a refresh, remove existing data first
            if is_refresh:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    cursor.execute(f"""
                        DELETE FROM {self.table_name}
                        WHERE date = ?
                    """, (date_str,))
                    removed_count = cursor.rowcount
                    conn.commit()
                    logger.info(f"Removed {removed_count} existing records for {date_str}")
                finally:
                    conn.close()
            
            # Collect fresh data for this date
            year = datetime.strptime(date_str, "%Y-%m-%d").year
            league_key = get_league_key(year)
            
            # Use collector to get fresh data
            collection_job_id = self.collector.collect_date_range_with_resume(
                start_date=date_str,
                end_date=date_str,
                league_key=league_key,
                resume=False
            )
            
            # Brief pause for collection to complete
            import time
            time.sleep(1)
            
            # Verify collection results
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) as records, COUNT(DISTINCT team_key) as teams
                    FROM {self.table_name}
                    WHERE date = ?
                """, (date_str,))
                
                result = cursor.fetchone()
                records = result[0] if result else 0
                teams = result[1] if result else 0
                
            finally:
                conn.close()
            
            return {
                "date": date_str,
                "action": action.lower(),
                "collection_job_id": collection_job_id,
                "records": records,
                "teams": teams,
                "success": records > 0
            }
            
        except Exception as e:
            logger.error(f"Failed to collect {date_str}: {e}")
            return {
                "date": date_str,
                "action": action.lower(),
                "error": str(e),
                "success": False
            }
    
    def execute_current_collection(self, dry_run: bool = False) -> Dict:
        """
        Execute the complete current-date collection process.
        
        Args:
            dry_run: If True, show plan without executing
            
        Returns:
            Execution results
        """
        logger.info("Starting current-date lineup collection")
        
        # Create collection plan
        plan = self.get_collection_plan()
        
        if dry_run:
            logger.info("DRY RUN - Collection plan:")
            logger.info(f"  Database state: {plan['database_state']}")
            logger.info(f"  Would refresh: {plan['refresh_date']}")
            logger.info(f"  Would collect {len(plan['missing_dates'])} new dates")
            return {"status": "dry_run", "plan": plan}
        
        # Start job logging
        year = self.today.year
        league_key = get_league_key(year)
        
        total_dates = len(plan['missing_dates']) + (1 if plan['will_refresh_last'] else 0)
        
        job_id = self.job_manager.start_job(
            job_type="current_date_collection",
            date_range_start=plan['refresh_date'] or plan['missing_dates'][0] if plan['missing_dates'] else self.today_str,
            date_range_end=self.today_str,
            league_key=league_key,
            metadata={
                "total_dates": total_dates,
                "refresh_date": plan['refresh_date'],
                "missing_dates_count": len(plan['missing_dates']),
                "today": self.today_str,
                "purpose": "Current-date-only collection with last-date refresh"
            }
        )
        
        execution_results = {
            "job_id": job_id,
            "started_at": datetime.now().isoformat(),
            "plan": plan,
            "results": [],
            "summary": {
                "successful_dates": 0,
                "failed_dates": 0,
                "total_records": 0
            }
        }
        
        try:
            all_results = []
            
            # Step 1: Refresh the most recent date (if exists)
            if plan['will_refresh_last'] and plan['refresh_date']:
                logger.info("Step 1: Refreshing most recent date for changes")
                refresh_result = self.collect_single_date(
                    plan['refresh_date'], 
                    job_id, 
                    is_refresh=True
                )
                all_results.append(refresh_result)
                
                if refresh_result['success']:
                    execution_results['summary']['successful_dates'] += 1
                    execution_results['summary']['total_records'] += refresh_result['records']
                else:
                    execution_results['summary']['failed_dates'] += 1
            
            # Step 2: Collect missing dates
            if plan['missing_dates']:
                logger.info(f"Step 2: Collecting {len(plan['missing_dates'])} missing dates")
                
                for i, date_str in enumerate(plan['missing_dates'], 1):
                    logger.info(f"Collecting date {i}/{len(plan['missing_dates'])}: {date_str}")
                    
                    collect_result = self.collect_single_date(date_str, job_id, is_refresh=False)
                    all_results.append(collect_result)
                    
                    if collect_result['success']:
                        execution_results['summary']['successful_dates'] += 1
                        execution_results['summary']['total_records'] += collect_result['records']
                    else:
                        execution_results['summary']['failed_dates'] += 1
                        
                    # Brief pause between collections
                    if i < len(plan['missing_dates']):
                        import time
                        time.sleep(0.5)
            else:
                logger.info("No missing dates to collect - database is current")
            
            execution_results['results'] = all_results
            
            # Mark job as completed
            self.job_manager.update_job(
                job_id,
                status='completed',
                records_processed=execution_results['summary']['successful_dates'],
                records_inserted=execution_results['summary']['total_records']
            )
            
            execution_results['status'] = 'completed'
            execution_results['completed_at'] = datetime.now().isoformat()
            
            logger.info("Current-date collection completed successfully")
            logger.info(f"Summary: {execution_results['summary']}")
            
        except Exception as e:
            logger.error(f"Collection execution failed: {e}")
            
            # Mark job as failed
            self.job_manager.update_job(job_id, status='failed', error_message=str(e))
            
            execution_results['status'] = 'failed'
            execution_results['error'] = str(e)
            execution_results['failed_at'] = datetime.now().isoformat()
            
            raise
        
        return execution_results
    
    def check_status(self) -> Dict:
        """
        Check current database status and collection needs.
        
        Returns:
            Status information
        """
        logger.info("Checking current database status...")
        
        db_state = self.get_database_date_range()
        last_date = self.get_last_update_date()
        missing_dates = self.generate_missing_dates(last_date)
        
        # Check for any future dates (should be none)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT COUNT(*) as future_records
                FROM {self.table_name}
                WHERE date > ?
            """, (self.today_str,))
            
            future_count = cursor.fetchone()[0]
            
        finally:
            conn.close()
        
        status = {
            "today": self.today_str,
            "database_state": db_state,
            "last_update_date": last_date,
            "days_behind": len(missing_dates),
            "missing_dates": missing_dates,
            "future_records": future_count,
            "needs_update": len(missing_dates) > 0 or future_count > 0,
            "is_current": len(missing_dates) == 0 and future_count == 0
        }
        
        logger.info(f"Status check results:")
        logger.info(f"  Database range: {db_state['min_date']} to {db_state['max_date']}")
        logger.info(f"  Total records: {db_state['total_records']}")
        logger.info(f"  Days behind: {status['days_behind']}")
        logger.info(f"  Future records: {future_count}")
        logger.info(f"  Needs update: {status['needs_update']}")
        
        return status


def main():
    """Command-line interface for current-date collection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Current-date daily lineup collection")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show collection plan without executing")
    parser.add_argument("--check-status", action="store_true",
                       help="Check current database status")
    
    args = parser.parse_args()
    
    collector = CurrentDateLineupCollector(environment=args.env)
    
    if args.check_status:
        print("Current Database Status")
        print("=" * 60)
        
        status = collector.check_status()
        
        print(f"Today's date: {status['today']}")
        print(f"Database range: {status['database_state']['min_date']} to {status['database_state']['max_date']}")
        print(f"Total records: {status['database_state']['total_records']:,}")
        print(f"Unique dates: {status['database_state']['unique_dates']}")
        print(f"Days behind: {status['days_behind']}")
        
        if status['future_records'] > 0:
            print(f"WARNING: Future records found: {status['future_records']} (should be 0)")
        
        if status['is_current']:
            print("SUCCESS: Database is current")
        else:
            print(f"UPDATE NEEDED: {status['days_behind']} missing dates")
            if status['missing_dates']:
                print(f"   Missing range: {status['missing_dates'][0]} to {status['missing_dates'][-1]}")
        
        return
    
    # Execute collection
    print(f"Current-Date Daily Lineup Collection")
    print(f"Environment: {args.env}")
    print(f"Today: {collector.today_str}")
    print("=" * 60)
    
    try:
        results = collector.execute_current_collection(dry_run=args.dry_run)
        
        if args.dry_run:
            print("DRY RUN COMPLETE")
            plan = results['plan']
            print(f"Would refresh: {plan['refresh_date']}")
            print(f"Would collect: {len(plan['missing_dates'])} dates")
            print(f"Estimated records: {plan['estimated_records']:,}")
        else:
            print(f"\nCollection Results:")
            print(f"Job ID: {results['job_id']}")
            print(f"Status: {results['status']}")
            print(f"Successful dates: {results['summary']['successful_dates']}")
            print(f"Failed dates: {results['summary']['failed_dates']}")
            print(f"Total records: {results['summary']['total_records']:,}")
            
            if results['results']:
                print(f"\nDate Details:")
                for result in results['results']:
                    status = "SUCCESS" if result['success'] else "FAILED"
                    action = result.get('action', 'unknown')
                    records = result.get('records', 0)
                    print(f"  {status}: {result['date']} ({action}): {records} records")
    
    except Exception as e:
        print(f"FAILED: Collection failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())