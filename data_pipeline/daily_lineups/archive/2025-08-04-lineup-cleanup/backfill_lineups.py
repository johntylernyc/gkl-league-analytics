"""
Historical Backfill Script for Daily Lineups
Supports parallel processing, duplicate detection, and incremental updates.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta
import sqlite3
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import time
from uuid import uuid4

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.collector import DailyLineupsCollector
from daily_lineups.job_manager import LineupJobManager, LineupProgressTracker
from daily_lineups.config import (
    LEAGUE_KEYS,
    SEASON_DATES,
    API_DELAY_SECONDS,
    get_database_path,
    get_lineup_table_name
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LineupBackfiller:
    """Manages historical backfill of lineup data with parallel processing."""
    
    def __init__(self, environment="production", max_workers=2):
        """
        Initialize the backfiller.
        
        Args:
            environment: 'production' or 'test'
            max_workers: Maximum concurrent workers (default 2 for API rate limiting)
        """
        self.environment = environment
        self.max_workers = max_workers
        self.db_path = get_database_path(environment)
        self.table_name = get_lineup_table_name(environment)
        self.job_manager = LineupJobManager(environment)
        self.collectors = []
        self.stats = {
            "dates_processed": 0,
            "dates_skipped": 0,
            "records_inserted": 0,
            "duplicates_avoided": 0,
            "errors": 0
        }
    
    def identify_missing_dates(self, 
                              season: int,
                              start_date: str = None,
                              end_date: str = None) -> List[str]:
        """
        Identify dates missing lineup data for a season.
        
        Args:
            season: Season year
            start_date: Optional start date override
            end_date: Optional end date override
            
        Returns:
            List of missing dates in YYYY-MM-DD format
        """
        # Get season dates
        season_start, season_end = SEASON_DATES.get(season, (None, None))
        if not season_start:
            raise ValueError(f"No season dates configured for {season}")
        
        start_date = start_date or season_start
        end_date = end_date or season_end
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get existing dates
            cursor.execute(f"""
                SELECT DISTINCT date
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            """, (start_date, end_date))
            
            existing_dates = set(row[0] for row in cursor.fetchall())
            
            # Generate all dates in range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            missing_dates = []
            current_dt = start_dt
            
            while current_dt <= end_dt:
                date_str = current_dt.strftime("%Y-%m-%d")
                if date_str not in existing_dates:
                    missing_dates.append(date_str)
                current_dt += timedelta(days=1)
            
            logger.info(f"Found {len(missing_dates)} missing dates for season {season}")
            return missing_dates
            
        finally:
            conn.close()
    
    def check_date_completeness(self, date_str: str, expected_teams: int = 18) -> Dict:
        """
        Check if data for a specific date is complete.
        
        Args:
            date_str: Date to check (YYYY-MM-DD)
            expected_teams: Expected number of teams
            
        Returns:
            Dictionary with completeness information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT team_key) as teams,
                    COUNT(DISTINCT player_id) as players,
                    COUNT(*) as records
                FROM {self.table_name}
                WHERE date = ?
            """, (date_str,))
            
            result = cursor.fetchone()
            
            return {
                "date": date_str,
                "is_complete": result[0] >= expected_teams,
                "teams_found": result[0],
                "teams_expected": expected_teams,
                "players": result[1],
                "records": result[2]
            }
            
        finally:
            conn.close()
    
    def process_single_date(self, 
                           collector: DailyLineupsCollector,
                           date_str: str,
                           league_key: str,
                           teams: List[Tuple[str, str]],
                           job_id: str) -> Dict:
        """
        Process lineup data for a single date.
        
        Args:
            collector: Collector instance to use
            date_str: Date to process
            league_key: League key
            teams: List of (team_key, team_name) tuples
            job_id: Job ID for tracking
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        records_inserted = 0
        errors = []
        
        # Check if date already has complete data
        completeness = self.check_date_completeness(date_str, len(teams))
        if completeness["is_complete"]:
            logger.info(f"Skipping {date_str} - already complete")
            return {
                "date": date_str,
                "status": "skipped",
                "reason": "already_complete",
                "time": time.time() - start_time
            }
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            batch_data = []
            season = int(date_str[:4])
            
            # Process each team
            for team_key, team_name in teams:
                try:
                    # Add delay between API calls
                    time.sleep(API_DELAY_SECONDS)
                    
                    # Fetch roster
                    players = collector.fetch_team_roster(team_key, date_str)
                    
                    # Prepare batch data
                    for player in players:
                        batch_data.append((
                            job_id,
                            season,
                            date_str,
                            team_key,
                            team_name,
                            player["player_id"],
                            player["player_name"],
                            player["selected_position"],
                            player["position_type"],
                            player["player_status"],
                            player["eligible_positions"],
                            player.get("player_team")
                        ))
                    
                except Exception as e:
                    error_msg = f"Error processing {team_name} on {date_str}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Insert data with duplicate detection
            if batch_data:
                cursor.executemany(f"""
                    INSERT OR IGNORE INTO {self.table_name} (
                        job_id, season, date, team_key, team_name,
                        player_id, player_name, selected_position, position_type,
                        player_status, eligible_positions, player_team
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch_data)
                
                records_inserted = cursor.rowcount
                conn.commit()
                
                logger.info(f"Inserted {records_inserted} records for {date_str}")
            
            return {
                "date": date_str,
                "status": "success",
                "records_inserted": records_inserted,
                "errors": errors,
                "time": time.time() - start_time
            }
            
        except Exception as e:
            conn.rollback()
            error_msg = f"Failed to process {date_str}: {e}"
            logger.error(error_msg)
            return {
                "date": date_str,
                "status": "error",
                "error": str(e),
                "time": time.time() - start_time
            }
            
        finally:
            conn.close()
    
    def backfill_season(self,
                       season: int,
                       start_date: str = None,
                       end_date: str = None,
                       mode: str = "missing") -> str:
        """
        Backfill lineup data for a season.
        
        Args:
            season: Season year
            start_date: Optional start date
            end_date: Optional end date
            mode: 'missing' (only missing dates), 'all' (all dates), 'incomplete' (incomplete dates)
            
        Returns:
            Job ID
        """
        # Get league key
        league_key = LEAGUE_KEYS.get(season)
        if not league_key:
            raise ValueError(f"No league key configured for season {season}")
        
        # Get dates to process based on mode
        if mode == "missing":
            dates_to_process = self.identify_missing_dates(season, start_date, end_date)
        elif mode == "all":
            # Process all dates in range
            season_start, season_end = SEASON_DATES.get(season)
            start_date = start_date or season_start
            end_date = end_date or season_end
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            dates_to_process = []
            current_dt = start_dt
            while current_dt <= end_dt:
                dates_to_process.append(current_dt.strftime("%Y-%m-%d"))
                current_dt += timedelta(days=1)
        elif mode == "incomplete":
            # Find incomplete dates
            all_dates = self.identify_missing_dates(season, start_date, end_date)
            
            # Add dates that exist but are incomplete
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT date, COUNT(DISTINCT team_key) as team_count
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                HAVING team_count < 18
            """, (start_date or SEASON_DATES[season][0], 
                  end_date or SEASON_DATES[season][1]))
            
            incomplete = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            dates_to_process = list(set(all_dates + incomplete))
            dates_to_process.sort()
        else:
            raise ValueError(f"Invalid mode: {mode}")
        
        if not dates_to_process:
            logger.info(f"No dates to process for season {season}")
            return None
        
        logger.info(f"Starting backfill for season {season}: {len(dates_to_process)} dates")
        
        # Create job
        job_id = self.job_manager.start_job(
            job_type="lineup_backfill",
            date_range_start=dates_to_process[0],
            date_range_end=dates_to_process[-1],
            league_key=league_key,
            metadata={
                "season": season,
                "mode": mode,
                "total_dates": len(dates_to_process),
                "max_workers": self.max_workers
            }
        )
        
        # Initialize collectors for parallel processing
        collectors = [DailyLineupsCollector(environment=self.environment) 
                     for _ in range(self.max_workers)]
        
        # Fetch teams once
        teams = collectors[0].fetch_league_teams(league_key)
        
        # Initialize progress tracker
        progress_tracker = LineupProgressTracker(job_id, len(dates_to_process))
        
        try:
            # Process dates in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit tasks
                future_to_date = {}
                
                for i, date_str in enumerate(dates_to_process):
                    collector = collectors[i % self.max_workers]
                    future = executor.submit(
                        self.process_single_date,
                        collector, date_str, league_key, teams, job_id
                    )
                    future_to_date[future] = date_str
                
                # Process results as they complete
                for future in as_completed(future_to_date):
                    date_str = future_to_date[future]
                    
                    try:
                        result = future.result()
                        
                        # Update stats
                        if result["status"] == "success":
                            self.stats["dates_processed"] += 1
                            self.stats["records_inserted"] += result.get("records_inserted", 0)
                        elif result["status"] == "skipped":
                            self.stats["dates_skipped"] += 1
                        else:
                            self.stats["errors"] += 1
                        
                        # Update progress
                        progress_tracker.update(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing {date_str}: {e}")
                        self.stats["errors"] += 1
                        progress_tracker.update(1)
                
                # Update job with final stats
                self.job_manager.update_job(
                    job_id,
                    status="completed",
                    records_processed=self.stats["dates_processed"] + self.stats["dates_skipped"],
                    records_inserted=self.stats["records_inserted"],
                    progress_pct=100.0
                )
                
                logger.info(f"Backfill completed: {self.stats}")
                
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            self.job_manager.update_job(
                job_id,
                status="failed",
                error_message=str(e)
            )
            raise
        
        return job_id
    
    def generate_validation_report(self, season: int) -> Dict:
        """
        Generate a validation report for a season's data.
        
        Args:
            season: Season year
            
        Returns:
            Dictionary with validation results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            season_start, season_end = SEASON_DATES.get(season)
            
            # Overall statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT date) as days_with_data,
                    COUNT(DISTINCT team_key) as unique_teams,
                    COUNT(DISTINCT player_id) as unique_players,
                    COUNT(*) as total_records,
                    MIN(date) as first_date,
                    MAX(date) as last_date
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
            """, (season_start, season_end))
            
            stats = cursor.fetchone()
            
            # Calculate expected days
            start_dt = datetime.strptime(season_start, "%Y-%m-%d").date()
            end_dt = datetime.strptime(season_end, "%Y-%m-%d").date()
            expected_days = (end_dt - start_dt).days + 1
            
            # Find incomplete dates
            cursor.execute(f"""
                SELECT date, COUNT(DISTINCT team_key) as team_count
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                HAVING team_count < 18
                ORDER BY date
            """, (season_start, season_end))
            
            incomplete_dates = cursor.fetchall()
            
            # Find dates with unusual record counts
            cursor.execute(f"""
                SELECT date, COUNT(*) as record_count
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                HAVING record_count < 400 OR record_count > 500
                ORDER BY date
            """, (season_start, season_end))
            
            unusual_dates = cursor.fetchall()
            
            report = {
                "season": season,
                "date_range": f"{season_start} to {season_end}",
                "statistics": {
                    "days_with_data": stats[0],
                    "expected_days": expected_days,
                    "completeness_pct": round(stats[0] / expected_days * 100, 2),
                    "unique_teams": stats[1],
                    "unique_players": stats[2],
                    "total_records": stats[3],
                    "first_date": stats[4],
                    "last_date": stats[5]
                },
                "issues": {
                    "missing_days": expected_days - stats[0],
                    "incomplete_dates": len(incomplete_dates),
                    "unusual_record_counts": len(unusual_dates)
                },
                "incomplete_dates": incomplete_dates[:10],  # First 10
                "unusual_dates": unusual_dates[:10]  # First 10
            }
            
            return report
            
        finally:
            conn.close()


def main():
    """Command-line interface for backfill operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill historical lineup data")
    parser.add_argument("command", choices=["backfill", "validate", "missing"],
                       help="Command to execute")
    parser.add_argument("--season", type=int, default=2025,
                       help="Season year (default: 2025)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--mode", default="missing",
                       choices=["missing", "all", "incomplete"],
                       help="Backfill mode (default: missing)")
    parser.add_argument("--workers", type=int, default=2,
                       help="Number of parallel workers (default: 2)")
    parser.add_argument("--env", default="production",
                       choices=["production", "test"],
                       help="Environment (default: production)")
    
    args = parser.parse_args()
    
    backfiller = LineupBackfiller(
        environment=args.env,
        max_workers=args.workers
    )
    
    if args.command == "backfill":
        print(f"Starting backfill for season {args.season}")
        print(f"Mode: {args.mode}")
        print(f"Workers: {args.workers}")
        print("-" * 60)
        
        job_id = backfiller.backfill_season(
            season=args.season,
            start_date=args.start,
            end_date=args.end,
            mode=args.mode
        )
        
        if job_id:
            print(f"\nBackfill completed!")
            print(f"Job ID: {job_id}")
            print(f"Statistics: {backfiller.stats}")
    
    elif args.command == "missing":
        print(f"Identifying missing dates for season {args.season}")
        print("-" * 60)
        
        missing = backfiller.identify_missing_dates(
            season=args.season,
            start_date=args.start,
            end_date=args.end
        )
        
        if missing:
            print(f"Found {len(missing)} missing dates:")
            for date_str in missing[:20]:  # First 20
                print(f"  {date_str}")
            if len(missing) > 20:
                print(f"  ... and {len(missing) - 20} more")
        else:
            print("No missing dates found!")
    
    elif args.command == "validate":
        print(f"Generating validation report for season {args.season}")
        print("-" * 60)
        
        report = backfiller.generate_validation_report(args.season)
        
        print(f"\nSeason {report['season']} Validation Report")
        print("=" * 60)
        print(f"Date Range: {report['date_range']}")
        print("\nStatistics:")
        for key, value in report["statistics"].items():
            print(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}")
        
        print("\nIssues:")
        for key, value in report["issues"].items():
            print(f"  {key}: {value}")
        
        if report["incomplete_dates"]:
            print("\nIncomplete Dates (first 10):")
            for date, teams in report["incomplete_dates"]:
                print(f"  {date}: {teams}/18 teams")


if __name__ == "__main__":
    main()