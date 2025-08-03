"""
Enhanced Daily Lineups Collector with Job Management Integration
Includes checkpoint/resume capability and progress tracking.
"""

import requests
import xml.etree.ElementTree as ET
import sqlite3
import json
import logging
import time
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from auth.config import BASE_FANTASY_URL
from daily_lineups.config import (
    API_DELAY_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    REQUEST_TIMEOUT,
    BATCH_SIZE,
    get_lineup_table_name,
    get_database_path,
    get_league_key,
    get_season_dates
)
from daily_lineups.job_manager import LineupJobManager, LineupProgressTracker
from daily_lineups.collector import DailyLineupsCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedLineupsCollector(DailyLineupsCollector):
    """Enhanced collector with job management and checkpoint/resume."""
    
    def __init__(self, token_manager=None, environment="production"):
        """
        Initialize the enhanced collector.
        
        Args:
            token_manager: TokenManager instance for OAuth2 authentication
            environment: 'production' or 'test' for table selection
        """
        super().__init__(token_manager, environment)
        self.job_manager = LineupJobManager(environment)
        self.progress_tracker = None
        self.checkpoint_enabled = True
    
    def collect_date_range_with_resume(self, 
                                       start_date: str, 
                                       end_date: str, 
                                       league_key: str = None,
                                       resume: bool = False) -> str:
        """
        Collect lineup data with checkpoint/resume capability.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            league_key: Yahoo league key
            resume: Whether to resume from checkpoint
            
        Returns:
            job_id: The job identifier
        """
        # Check for existing checkpoint if resuming
        checkpoint = None
        job_id = None
        
        if resume:
            checkpoint = self.job_manager.load_checkpoint()
            if checkpoint:
                logger.info(f"Resuming job {checkpoint['job_id']} from {checkpoint['current_date']}")
                job_id = checkpoint['job_id']
                start_date = checkpoint['current_date']
                league_key = checkpoint['league_key']
                # Restore completed dates
                self.stats['dates_completed'] = checkpoint.get('dates_completed', [])
            else:
                logger.warning("No checkpoint found, starting fresh")
                resume = False
        
        # Start new job if not resuming
        if not resume:
            job_id = self.job_manager.start_job(
                job_type='lineup_collection',
                date_range_start=start_date,
                date_range_end=end_date,
                league_key=league_key or get_league_key(datetime.strptime(start_date, '%Y-%m-%d').year),
                metadata={'resumed': False}
            )
            self.stats['dates_completed'] = []
        
        # Get league key if not provided
        if not league_key:
            season = datetime.strptime(start_date, '%Y-%m-%d').year
            league_key = get_league_key(season)
            if not league_key:
                error_msg = f"No league key configured for season {season}"
                self.job_manager.update_job(job_id, 'failed', error_message=error_msg)
                raise ValueError(error_msg)
        
        try:
            # Execute collection with progress tracking
            self._collect_with_progress(
                job_id=job_id,
                start_date=start_date,
                end_date=end_date,
                league_key=league_key,
                checkpoint=checkpoint
            )
            
            # Mark job as completed
            self.job_manager.update_job(
                job_id,
                status='completed',
                records_processed=self.stats['records_processed'],
                records_inserted=self.stats['records_inserted'],
                progress_pct=100.0
            )
            
            # Clear checkpoint on successful completion
            self.job_manager.clear_checkpoint()
            
            logger.info(f"Job {job_id} completed successfully")
            logger.info(f"Statistics: {self.stats}")
            
            return job_id
            
        except KeyboardInterrupt:
            # Handle graceful shutdown
            logger.info("Collection interrupted by user, saving checkpoint...")
            self.job_manager.update_job(job_id, 'paused')
            raise
            
        except Exception as e:
            # Handle failure
            logger.error(f"Collection failed: {e}")
            self.job_manager.update_job(
                job_id,
                status='failed',
                error_message=str(e),
                records_processed=self.stats.get('records_processed', 0),
                records_inserted=self.stats.get('records_inserted', 0)
            )
            raise
    
    def _collect_with_progress(self,
                               job_id: str,
                               start_date: str,
                               end_date: str,
                               league_key: str,
                               checkpoint: Dict = None):
        """
        Internal method to collect data with progress tracking.
        
        Args:
            job_id: Job identifier
            start_date: Start date
            end_date: End date
            league_key: League key
            checkpoint: Optional checkpoint data
        """
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Calculate total work
        total_days = (end - start).days + 1
        
        # Get teams
        teams = self.fetch_league_teams(league_key)
        total_items = total_days * len(teams)
        
        # Initialize progress tracker
        self.progress_tracker = LineupProgressTracker(job_id, total_items)
        
        # Extract season
        season = start.year
        
        logger.info(f"Starting collection: {total_days} days, {len(teams)} teams = {total_items} total items")
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Track completed dates
        dates_completed = checkpoint.get('dates_completed', []) if checkpoint else []
        
        try:
            # Process each date
            current_date = start
            batch_data = []
            
            while current_date <= end:
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Skip if already completed (from checkpoint)
                if date_str in dates_completed:
                    logger.info(f"Skipping {date_str} (already completed)")
                    # Update progress tracker
                    self.progress_tracker.update(len(teams))
                    current_date += timedelta(days=1)
                    continue
                
                logger.info(f"Processing {date_str}")
                
                # Process each team for this date
                teams_processed = []
                
                for team_key, team_name in teams:
                    try:
                        # Add delay between requests
                        time.sleep(API_DELAY_SECONDS)
                        
                        # Fetch roster
                        players = self.fetch_team_roster(team_key, date_str)
                        
                        # Prepare batch insert data
                        for player in players:
                            batch_data.append((
                                job_id,  # Include job_id for lineage
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
                        
                        teams_processed.append(team_key)
                        
                        # Update progress
                        self.progress_tracker.update(1)
                        
                        # Insert in batches
                        if len(batch_data) >= BATCH_SIZE:
                            self._insert_batch(cursor, batch_data)
                            conn.commit()
                            batch_data = []
                        
                    except Exception as e:
                        logger.error(f"Error processing {team_name} on {date_str}: {e}")
                        continue
                
                # Mark date as completed
                dates_completed.append(date_str)
                
                # Update checkpoint
                if self.checkpoint_enabled:
                    self.job_manager.update_checkpoint(
                        current_date=date_str,
                        teams_processed=teams_processed,
                        dates_completed=dates_completed
                    )
                
                # Update job progress
                progress_pct = self.job_manager.calculate_progress(
                    date_str, start_date, end_date
                )
                self.job_manager.update_job(
                    job_id,
                    progress_pct=progress_pct,
                    records_processed=self.stats['records_processed']
                )
                
                # Move to next date
                current_date += timedelta(days=1)
            
            # Insert remaining data
            if batch_data:
                self._insert_batch(cursor, batch_data)
                conn.commit()
            
        finally:
            conn.close()
    
    def get_missing_dates(self, 
                         start_date: str,
                         end_date: str,
                         league_key: str) -> List[str]:
        """
        Identify dates missing lineup data.
        
        Args:
            start_date: Start date
            end_date: End date
            league_key: League key
            
        Returns:
            List of missing dates (YYYY-MM-DD format)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get existing dates
            cursor.execute(f"""
                SELECT DISTINCT date
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                    AND team_key LIKE ?
                ORDER BY date
            """, (start_date, end_date, f"{league_key}%"))
            
            existing_dates = set(row[0] for row in cursor.fetchall())
            
            # Generate all dates in range
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            all_dates = []
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                if date_str not in existing_dates:
                    all_dates.append(date_str)
                current += timedelta(days=1)
            
            return all_dates
            
        finally:
            conn.close()
    
    def validate_data_completeness(self, 
                                   start_date: str,
                                   end_date: str,
                                   league_key: str) -> Dict:
        """
        Validate data completeness for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            league_key: League key
            
        Returns:
            Dictionary with validation results
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get team count
            teams = self.fetch_league_teams(league_key)
            expected_teams = len(teams)
            
            # Check data completeness
            cursor.execute(f"""
                SELECT 
                    date,
                    COUNT(DISTINCT team_key) as teams_found,
                    COUNT(DISTINCT player_id) as players_found,
                    COUNT(*) as total_records
                FROM {self.table_name}
                WHERE date BETWEEN ? AND ?
                    AND team_key LIKE ?
                GROUP BY date
                ORDER BY date
            """, (start_date, end_date, f"{league_key}%"))
            
            results = cursor.fetchall()
            
            # Analyze completeness
            complete_dates = []
            incomplete_dates = []
            
            for row in results:
                date_str, teams_found, players_found, total_records = row
                
                if teams_found == expected_teams:
                    complete_dates.append(date_str)
                else:
                    incomplete_dates.append({
                        'date': date_str,
                        'teams_found': teams_found,
                        'teams_expected': expected_teams,
                        'missing_teams': expected_teams - teams_found
                    })
            
            # Get missing dates
            missing_dates = self.get_missing_dates(start_date, end_date, league_key)
            
            return {
                'complete_dates': len(complete_dates),
                'incomplete_dates': len(incomplete_dates),
                'missing_dates': len(missing_dates),
                'total_expected_dates': (
                    datetime.strptime(end_date, "%Y-%m-%d").date() -
                    datetime.strptime(start_date, "%Y-%m-%d").date()
                ).days + 1,
                'completeness_pct': round(
                    len(complete_dates) / ((
                        datetime.strptime(end_date, "%Y-%m-%d").date() -
                        datetime.strptime(start_date, "%Y-%m-%d").date()
                    ).days + 1) * 100, 2
                ),
                'incomplete_details': incomplete_dates[:10],  # First 10
                'missing_dates_list': missing_dates[:10]  # First 10
            }
            
        finally:
            conn.close()


def main():
    """Enhanced command line interface with resume capability."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect daily lineup data with job management")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--league", help="League key (optional)")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (production/test)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from checkpoint")
    parser.add_argument("--validate", action="store_true",
                       help="Validate data completeness")
    parser.add_argument("--missing", action="store_true",
                       help="Show missing dates")
    
    args = parser.parse_args()
    
    # Initialize collector
    collector = EnhancedLineupsCollector(environment=args.env)
    
    if args.validate:
        # Validate mode
        if not args.start or not args.end:
            print("Error: --start and --end required for validation")
            return
        
        league_key = args.league or get_league_key(
            datetime.strptime(args.start, '%Y-%m-%d').year
        )
        
        print(f"\nValidating data completeness for {league_key}")
        print(f"Date range: {args.start} to {args.end}")
        print("-" * 60)
        
        validation = collector.validate_data_completeness(
            args.start, args.end, league_key
        )
        
        print(f"Complete dates: {validation['complete_dates']}")
        print(f"Incomplete dates: {validation['incomplete_dates']}")
        print(f"Missing dates: {validation['missing_dates']}")
        print(f"Completeness: {validation['completeness_pct']}%")
        
        if validation['incomplete_details']:
            print("\nIncomplete dates (first 10):")
            for detail in validation['incomplete_details']:
                print(f"  {detail['date']}: {detail['teams_found']}/{detail['teams_expected']} teams")
        
        if validation['missing_dates_list']:
            print("\nMissing dates (first 10):")
            for date_str in validation['missing_dates_list']:
                print(f"  {date_str}")
    
    elif args.missing:
        # Show missing dates
        if not args.start or not args.end:
            print("Error: --start and --end required")
            return
        
        league_key = args.league or get_league_key(
            datetime.strptime(args.start, '%Y-%m-%d').year
        )
        
        missing = collector.get_missing_dates(args.start, args.end, league_key)
        
        print(f"\nMissing dates for {league_key}:")
        print(f"Date range: {args.start} to {args.end}")
        print("-" * 40)
        
        if missing:
            for date_str in missing:
                print(f"  {date_str}")
            print(f"\nTotal: {len(missing)} missing dates")
        else:
            print("No missing dates found!")
    
    else:
        # Collection mode
        if args.resume:
            # Resume from checkpoint
            job_id = collector.collect_date_range_with_resume(
                start_date=args.start or "",
                end_date=args.end or "",
                league_key=args.league,
                resume=True
            )
        else:
            # Fresh collection
            if not args.start or not args.end:
                print("Error: --start and --end required for new collection")
                return
            
            job_id = collector.collect_date_range_with_resume(
                start_date=args.start,
                end_date=args.end,
                league_key=args.league,
                resume=False
            )
        
        print(f"\nCollection complete. Job ID: {job_id}")
        print(f"Use 'python job_manager.py status --job-id {job_id}' to check status")


if __name__ == "__main__":
    main()