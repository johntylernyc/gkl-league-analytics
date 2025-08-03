"""
Incremental Update Script for Daily Lineups
Designed for daily/scheduled updates to keep lineup data current.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
import sqlite3
import json
import logging
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.backfill_lineups import LineupBackfiller
from daily_lineups.job_manager import LineupJobManager
from daily_lineups.config import (
    LEAGUE_KEYS,
    SEASON_DATES,
    get_database_path,
    get_lineup_table_name
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LineupUpdater:
    """Manages incremental updates of lineup data."""
    
    def __init__(self, environment="production"):
        """
        Initialize the updater.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.db_path = get_database_path(environment)
        self.table_name = get_lineup_table_name(environment)
        self.job_manager = LineupJobManager(environment)
        self.collector = EnhancedLineupsCollector(environment)
        self.backfiller = LineupBackfiller(environment)
    
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
                SELECT MAX(date) 
                FROM {self.table_name}
                WHERE date <= date('now')
            """)
            
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
            
        finally:
            conn.close()
    
    def update_recent_days(self, days_back: int = 7) -> str:
        """
        Update lineup data for the most recent N days.
        
        Args:
            days_back: Number of days to update (default: 7)
            
        Returns:
            Job ID
        """
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back - 1)
        
        # Check if we're in season
        current_year = end_date.year
        season_dates = SEASON_DATES.get(current_year)
        
        if not season_dates:
            logger.warning(f"No season configured for {current_year}")
            return None
        
        season_start = datetime.strptime(season_dates[0], "%Y-%m-%d").date()
        season_end = datetime.strptime(season_dates[1], "%Y-%m-%d").date()
        
        # Adjust dates to stay within season
        if start_date < season_start:
            start_date = season_start
        if end_date > season_end:
            end_date = season_end
        
        if start_date > end_date:
            logger.info("Outside of season dates, no update needed")
            return None
        
        logger.info(f"Updating lineups from {start_date} to {end_date}")
        
        # Use the enhanced collector for updates
        job_id = self.collector.collect_date_range_with_resume(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            resume=False
        )
        
        return job_id
    
    def update_missing_recent(self, lookback_days: int = 30) -> str:
        """
        Find and update any missing dates in recent history.
        
        Args:
            lookback_days: How many days back to check
            
        Returns:
            Job ID or None if no missing dates
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days - 1)
        
        # Find missing dates
        missing = self.backfiller.identify_missing_dates(
            season=end_date.year,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if not missing:
            logger.info(f"No missing dates in the last {lookback_days} days")
            return None
        
        logger.info(f"Found {len(missing)} missing dates in the last {lookback_days} days")
        
        # Backfill missing dates
        job_id = self.backfiller.backfill_season(
            season=end_date.year,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            mode="missing"
        )
        
        return job_id
    
    def smart_update(self) -> Dict:
        """
        Perform a smart update based on current data state.
        
        This method:
        1. Checks the last update date
        2. Determines what needs updating
        3. Performs the appropriate update
        
        Returns:
            Dictionary with update results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "actions": []
        }
        
        # Get last update date
        last_update = self.get_last_update_date()
        
        if not last_update:
            logger.info("No data found, need full collection")
            results["actions"].append({
                "type": "no_data",
                "message": "Database is empty, run full collection first"
            })
            return results
        
        last_update_date = datetime.strptime(last_update, "%Y-%m-%d").date()
        today = date.today()
        days_behind = (today - last_update_date).days
        
        logger.info(f"Last update: {last_update}, {days_behind} days behind")
        
        # Determine update strategy
        if days_behind == 0:
            logger.info("Data is current, checking for today's updates")
            
            # Check if today's data is complete
            completeness = self.backfiller.check_date_completeness(
                today.strftime("%Y-%m-%d")
            )
            
            if not completeness["is_complete"]:
                # Update today
                job_id = self.update_recent_days(1)
                results["actions"].append({
                    "type": "update_today",
                    "job_id": job_id,
                    "date": today.strftime("%Y-%m-%d")
                })
            else:
                logger.info("Today's data is complete")
                results["actions"].append({
                    "type": "already_current",
                    "message": "Data is up to date"
                })
        
        elif days_behind <= 7:
            # Update recent days
            logger.info(f"Updating {days_behind} recent days")
            job_id = self.update_recent_days(days_behind)
            results["actions"].append({
                "type": "update_recent",
                "job_id": job_id,
                "days": days_behind
            })
        
        elif days_behind <= 30:
            # Check for missing dates and update
            logger.info(f"Checking for missing dates in last {days_behind} days")
            job_id = self.update_missing_recent(days_behind)
            
            if job_id:
                results["actions"].append({
                    "type": "backfill_missing",
                    "job_id": job_id,
                    "lookback_days": days_behind
                })
            else:
                # Just update recent days
                job_id = self.update_recent_days(min(days_behind, 7))
                results["actions"].append({
                    "type": "update_recent",
                    "job_id": job_id,
                    "days": min(days_behind, 7)
                })
        
        else:
            # Too far behind, need manual intervention
            logger.warning(f"Data is {days_behind} days behind, consider full backfill")
            results["actions"].append({
                "type": "manual_required",
                "message": f"Data is {days_behind} days old, run backfill script",
                "last_update": last_update
            })
        
        return results
    
    def generate_update_report(self) -> Dict:
        """
        Generate a report on the current update status.
        
        Returns:
            Dictionary with update status information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get overall statistics
            cursor.execute(f"""
                SELECT 
                    MAX(date) as last_date,
                    MIN(date) as first_date,
                    COUNT(DISTINCT date) as total_days,
                    COUNT(DISTINCT player_id) as total_players,
                    COUNT(*) as total_records
                FROM {self.table_name}
                WHERE date >= date('now', '-30 days')
            """)
            
            recent_stats = cursor.fetchone()
            
            # Get today's status
            today = date.today().strftime("%Y-%m-%d")
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT team_key) as teams,
                    COUNT(*) as records
                FROM {self.table_name}
                WHERE date = ?
            """, (today,))
            
            today_stats = cursor.fetchone()
            
            # Get recent job history
            cursor.execute("""
                SELECT 
                    job_id,
                    status,
                    date_range_start,
                    date_range_end,
                    records_inserted,
                    start_time
                FROM job_log
                WHERE job_type LIKE 'lineup_%'
                ORDER BY start_time DESC
                LIMIT 5
            """)
            
            recent_jobs = cursor.fetchall()
            
            # Calculate update lag
            last_date = recent_stats[0] if recent_stats[0] else None
            if last_date:
                last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
                lag_days = (date.today() - last_date_obj).days
            else:
                lag_days = None
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "update_status": {
                    "last_data_date": last_date,
                    "lag_days": lag_days,
                    "is_current": lag_days == 0 if lag_days is not None else False
                },
                "recent_statistics": {
                    "date_range": f"{recent_stats[1]} to {recent_stats[0]}" if recent_stats[0] else None,
                    "days_with_data": recent_stats[2],
                    "unique_players": recent_stats[3],
                    "total_records": recent_stats[4]
                },
                "today": {
                    "date": today,
                    "teams": today_stats[0],
                    "records": today_stats[1],
                    "is_complete": today_stats[0] >= 18
                },
                "recent_jobs": [
                    {
                        "job_id": job[0],
                        "status": job[1],
                        "date_range": f"{job[2]} to {job[3]}",
                        "records": job[4],
                        "started": job[5]
                    }
                    for job in recent_jobs
                ]
            }
            
            return report
            
        finally:
            conn.close()


def main():
    """Command-line interface for update operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update lineup data incrementally")
    parser.add_argument("command", 
                       choices=["update", "smart", "status", "missing"],
                       help="Command to execute")
    parser.add_argument("--days", type=int, default=7,
                       help="Number of days to update (default: 7)")
    parser.add_argument("--lookback", type=int, default=30,
                       help="Days to look back for missing data (default: 30)")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment (default: production)")
    
    args = parser.parse_args()
    
    updater = LineupUpdater(environment=args.env)
    
    if args.command == "update":
        print(f"Updating last {args.days} days of lineup data")
        print("-" * 60)
        
        job_id = updater.update_recent_days(args.days)
        
        if job_id:
            print(f"Update started!")
            print(f"Job ID: {job_id}")
            print("\nMonitor progress with:")
            print(f"  python daily_lineups/job_manager.py status --job-id {job_id}")
        else:
            print("No update needed (outside of season)")
    
    elif args.command == "smart":
        print("Performing smart update")
        print("-" * 60)
        
        results = updater.smart_update()
        
        print(f"\nSmart Update Results")
        print(f"Timestamp: {results['timestamp']}")
        print("\nActions taken:")
        
        for action in results["actions"]:
            print(f"\n  Type: {action['type']}")
            for key, value in action.items():
                if key != "type":
                    print(f"    {key}: {value}")
    
    elif args.command == "missing":
        print(f"Updating missing dates from last {args.lookback} days")
        print("-" * 60)
        
        job_id = updater.update_missing_recent(args.lookback)
        
        if job_id:
            print(f"Backfill started for missing dates!")
            print(f"Job ID: {job_id}")
        else:
            print("No missing dates found")
    
    elif args.command == "status":
        print("Lineup Data Update Status")
        print("=" * 60)
        
        report = updater.generate_update_report()
        
        print(f"\nAs of: {report['timestamp']}")
        
        print("\nUpdate Status:")
        for key, value in report["update_status"].items():
            print(f"  {key}: {value}")
        
        print("\nRecent Data (last 30 days):")
        for key, value in report["recent_statistics"].items():
            print(f"  {key}: {value}")
        
        print(f"\nToday ({report['today']['date']}):")
        print(f"  Teams: {report['today']['teams']}/18")
        print(f"  Records: {report['today']['records']}")
        print(f"  Complete: {'Yes' if report['today']['is_complete'] else 'No'}")
        
        if report["recent_jobs"]:
            print("\nRecent Jobs:")
            for job in report["recent_jobs"]:
                print(f"  {job['job_id'][:40]}...")
                print(f"    Status: {job['status']}, Records: {job['records']}")


if __name__ == "__main__":
    main()