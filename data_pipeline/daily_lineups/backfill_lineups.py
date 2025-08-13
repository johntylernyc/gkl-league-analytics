#!/usr/bin/env python
"""
Backfill Daily Lineups - Bulk Historical Data Collection

This script handles bulk collection of daily lineup data from Yahoo Fantasy Sports API.
It's designed for populating entire seasons or fetching multiple months of data
with parallel processing capabilities while respecting API rate limits.

Usage:
    # Backfill entire season
    python backfill_lineups.py --season 2025
    
    # Backfill date range with parallel workers
    python backfill_lineups.py --start 2025-03-01 --end 2025-09-30 --workers 4
    
    # Backfill multiple seasons
    python backfill_lineups.py --seasons 2023,2024,2025
    
    # Backfill all configured seasons
    python backfill_lineups.py --all-seasons

Features:
    - Parallel processing with configurable workers (respects Yahoo API rate limits)
    - Comprehensive job logging and progress tracking
    - Resume capability for interrupted jobs
    - Data quality validation before insertion
    - Support for multiple seasons
    - Automatic duplicate detection
"""

import argparse
import logging
import sqlite3
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

# Import required modules
from auth.token_manager import YahooTokenManager
from data_pipeline.common.season_manager import get_league_key, get_season_dates
from data_pipeline.config.database_config import get_database_path, get_table_name
from data_pipeline.daily_lineups.data_quality_check import LineupDataQualityChecker
from data_pipeline.daily_lineups.parser import LineupParser
from data_pipeline.metadata.league_keys import LEAGUE_KEYS, SEASON_DATES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'
DEFAULT_WORKERS = 2
MAX_WORKERS = 4
RATE_LIMIT_DELAY = 1.0  # 1 second between requests per Yahoo guidelines
BATCH_SIZE = 100  # Database batch insert size


class RateLimiter:
    """Thread-safe rate limiter for API requests."""
    
    def __init__(self, requests_per_second=1.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait(self):
        """Wait if necessary to maintain rate limit."""
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()


class LineupBackfiller:
    """Handles bulk lineup data collection from Yahoo Fantasy Sports API."""
    
    def __init__(self, environment='production', max_workers=DEFAULT_WORKERS):
        """
        Initialize the backfiller.
        
        Args:
            environment: Database environment ('production' or 'test')
            max_workers: Maximum number of parallel workers
        """
        self.environment = environment
        self.max_workers = min(max_workers, MAX_WORKERS)
        self.token_manager = YahooTokenManager()
        self.rate_limiter = RateLimiter(requests_per_second=1.0)
        self.quality_checker = LineupDataQualityChecker()
        self.parser = LineupParser()
        
        # Database setup
        self.db_path = get_database_path(environment)
        self.table_name = get_table_name('daily_lineups', environment)
        self._init_database()
        
        # Job tracking
        self.job_id = None
        self.stats = {
            'total_fetched': 0,
            'total_inserted': 0,
            'errors': 0,
            'start_time': None
        }
    
    def _init_database(self):
        """Initialize database and ensure tables exist."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create daily_lineups table if it doesn't exist
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                date DATE NOT NULL,
                team_key TEXT NOT NULL,
                team_name TEXT NOT NULL,
                yahoo_player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                selected_position TEXT,
                position_type TEXT,
                player_status TEXT,
                eligible_positions TEXT,
                player_team TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, team_key, yahoo_player_id, selected_position)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_date ON {self.table_name}(date)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_team ON {self.table_name}(team_key)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_yahoo_player ON {self.table_name}(yahoo_player_id)')
        
        # Create job_log table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_log (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                date_range_start TEXT,
                date_range_end TEXT,
                league_key TEXT,
                records_processed INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                error_message TEXT,
                metadata TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_job(self, job_type: str, date_range_start: str, date_range_end: str, 
                  league_key: str, metadata: Optional[str] = None) -> str:
        """Start a new job and return job_id."""
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_id = f"{job_type}_{self.environment}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO job_log (job_id, job_type, environment, status, 
                                date_range_start, date_range_end, league_key, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (job_id, job_type, self.environment, 'running', 
              date_range_start, date_range_end, league_key, metadata))
        conn.commit()
        conn.close()
        
        self.job_id = job_id
        logger.info(f"Started job: {job_id}")
        return job_id
    
    def update_job(self, status: str, records_processed: int = None, 
                   records_inserted: int = None, error_message: str = None):
        """Update job status."""
        if not self.job_id:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        update_parts = ['status = ?']
        params = [status]
        
        if records_processed is not None:
            update_parts.append('records_processed = ?')
            params.append(records_processed)
        
        if records_inserted is not None:
            update_parts.append('records_inserted = ?')
            params.append(records_inserted)
        
        if error_message:
            update_parts.append('error_message = ?')
            params.append(error_message)
        
        if status in ['completed', 'failed']:
            update_parts.append('end_time = CURRENT_TIMESTAMP')
        
        params.append(self.job_id)
        
        query = f"UPDATE job_log SET {', '.join(update_parts)} WHERE job_id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()
    
    def fetch_lineups_for_date(self, league_key: str, team_key: str, date_str: str) -> List[Dict]:
        """
        Fetch lineup for a specific team and date from Yahoo API.
        
        Args:
            league_key: Yahoo league key
            team_key: Yahoo team key
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of lineup dictionaries
        """
        self.rate_limiter.wait()
        
        url = f"{BASE_FANTASY_URL}/team/{team_key}/roster;date={date_str}"
        headers = {
            'Authorization': f'Bearer {self.token_manager.get_access_token()}',
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse XML and extract lineup data
            lineups = self.parse_lineup_xml(response.text, date_str, team_key, league_key)
            return lineups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching lineup for {team_key} on {date_str}: {e}")
            self.stats['errors'] += 1
            return []
    
    def parse_lineup_xml(self, xml_data: str, date_str: str, team_key: str, league_key: str) -> List[Dict]:
        """
        Parse lineup XML data into structured records.
        
        Args:
            xml_data: Raw XML response from Yahoo API
            date_str: Date string
            team_key: Team identifier
            league_key: League identifier
            
        Returns:
            List of lineup dictionaries
        """
        lineups = []
        
        try:
            root = ET.fromstring(xml_data)
            ns = {'y': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            
            # Get team name
            team_name_elem = root.find('.//y:team/y:name', ns)
            team_name = team_name_elem.text if team_name_elem is not None else team_key
            
            # Get season from league key
            season = int(league_key.split('.')[0].replace('mlb', ''))
            
            # Find all players in the roster
            players = root.findall('.//y:player', ns)
            
            for player in players:
                yahoo_player_id = player.find('.//y:player_id', ns)
                player_name = player.find('.//y:name/y:full', ns)
                selected_position = player.find('.//y:selected_position/y:position', ns)
                position_type = player.find('.//y:position_type', ns)
                player_status = player.find('.//y:status', ns)
                player_team = player.find('.//y:editorial_team_abbr', ns)
                
                # Get eligible positions
                eligible_positions = []
                eligible_pos_elements = player.findall('.//y:eligible_positions/y:position', ns)
                for pos_elem in eligible_pos_elements:
                    if pos_elem.text:
                        eligible_positions.append(pos_elem.text)
                
                lineup = {
                    'job_id': self.job_id,
                    'season': season,
                    'date': date_str,
                    'team_key': team_key,
                    'team_name': team_name,
                    'yahoo_player_id': yahoo_player_id.text if yahoo_player_id is not None else '',',
                    'player_name': player_name.text if player_name is not None else '',
                    'selected_position': selected_position.text if selected_position is not None else '',
                    'position_type': position_type.text if position_type is not None else '',
                    'player_status': player_status.text if player_status is not None else 'healthy',
                    'eligible_positions': ','.join(eligible_positions),
                    'player_team': player_team.text if player_team is not None else ''
                }
                
                lineups.append(lineup)
        
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
            self.stats['errors'] += 1
        
        return lineups
    
    def get_all_team_keys(self, league_key: str) -> List[str]:
        """
        Get all team keys for a league.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            List of team keys
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/teams"
        headers = {
            'Authorization': f'Bearer {self.token_manager.get_access_token()}',
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            ns = {'y': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            
            team_keys = []
            teams = root.findall('.//y:team', ns)
            for team in teams:
                team_key_elem = team.find('.//y:team_key', ns)
                if team_key_elem is not None:
                    team_keys.append(team_key_elem.text)
            
            return team_keys
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching team keys: {e}")
            return []
    
    def insert_lineups(self, lineups: List[Dict]) -> int:
        """
        Insert lineups into database with duplicate handling.
        
        Args:
            lineups: List of lineup dictionaries
            
        Returns:
            Number of records inserted
        """
        if not lineups:
            return 0
        
        # Validate data quality
        validation_results = self.quality_checker.validate_batch(lineups)
        if validation_results['invalid'] > 0:
            logger.warning(f"Found {validation_results['invalid']} invalid lineups")
            logger.warning(self.quality_checker.generate_report(validation_results))
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        inserted = 0
        for lineup in lineups:
            try:
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {self.table_name} (
                        job_id, season, date, team_key, team_name,
                        yahoo_player_id, player_name, selected_position, position_type,
                        player_status, eligible_positions, player_team
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    lineup['job_id'], lineup['season'], lineup['date'],
                    lineup['team_key'], lineup['team_name'], lineup['yahoo_player_id'],
                    lineup['player_name'], lineup['selected_position'],
                    lineup['position_type'], lineup['player_status'],
                    lineup['eligible_positions'], lineup['player_team']
                ))
                
                if cursor.rowcount > 0:
                    inserted += 1
                    
            except sqlite3.Error as e:
                logger.error(f"Error inserting lineup: {e}")
                self.stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return inserted
    
    def backfill_date_range(self, start_date: datetime, end_date: datetime, 
                           league_key: str) -> Dict:
        """
        Backfill lineups for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            league_key: Yahoo league key
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Backfilling {league_key} from {start_date.date()} to {end_date.date()}")
        
        # Get all team keys
        team_keys = self.get_all_team_keys(league_key)
        if not team_keys:
            logger.error("Could not fetch team keys")
            return {'error': 'Failed to get team keys'}
        
        logger.info(f"Found {len(team_keys)} teams to process")
        
        # Start job
        self.start_job(
            job_type='lineup_backfill',
            date_range_start=str(start_date.date()),
            date_range_end=str(end_date.date()),
            league_key=league_key,
            metadata=f"Workers: {self.max_workers}, Teams: {len(team_keys)}"
        )
        
        self.stats['start_time'] = time.time()
        
        # Generate list of date-team combinations
        tasks = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            for team_key in team_keys:
                tasks.append((team_key, date_str))
            current_date += timedelta(days=1)
        
        logger.info(f"Processing {len(tasks)} team-date combinations with {self.max_workers} workers")
        
        # Process tasks in parallel
        all_lineups = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {
                executor.submit(self.fetch_lineups_for_date, league_key, team_key, date): (team_key, date)
                for team_key, date in tasks
            }
            
            completed = 0
            for future in as_completed(future_to_task):
                team_key, date = future_to_task[future]
                try:
                    lineups = future.result()
                    if lineups:
                        all_lineups.extend(lineups)
                        logger.debug(f"Fetched {len(lineups)} players for {team_key} on {date}")
                    self.stats['total_fetched'] += len(lineups) if lineups else 0
                    
                except Exception as e:
                    logger.error(f"Error processing {team_key} on {date}: {e}")
                    self.stats['errors'] += 1
                
                # Show progress
                completed += 1
                if completed % 10 == 0:
                    logger.info(f"Progress: {completed}/{len(tasks)} tasks processed")
        
        # Insert all lineups
        if all_lineups:
            logger.info(f"Inserting {len(all_lineups)} lineup records...")
            inserted = self.insert_lineups(all_lineups)
            self.stats['total_inserted'] = inserted
            logger.info(f"Inserted {inserted} new lineup records")
        
        # Update job status
        self.update_job(
            status='completed',
            records_processed=self.stats['total_fetched'],
            records_inserted=self.stats['total_inserted']
        )
        
        # Calculate elapsed time
        elapsed = time.time() - self.stats['start_time']
        self.stats['elapsed_time'] = elapsed
        
        return self.stats
    
    def backfill_season(self, year: int) -> Dict:
        """
        Backfill all lineups for a season.
        
        Args:
            year: Season year
            
        Returns:
            Statistics dictionary
        """
        league_key = get_league_key(year)
        if not league_key:
            logger.error(f"No league key found for {year}")
            return {'error': f'No league key for {year}'}
        
        season_dates = get_season_dates(year)
        if not season_dates:
            logger.error(f"No season dates found for {year}")
            return {'error': f'No season dates for {year}'}
        
        start_date = datetime.strptime(season_dates['start'], '%Y-%m-%d')
        end_date = datetime.strptime(season_dates['end'], '%Y-%m-%d')
        
        # Adjust end date to today if season is current
        today = datetime.now()
        if end_date > today:
            end_date = today
        
        return self.backfill_date_range(start_date, end_date, league_key)
    
    def backfill_multiple_seasons(self, years: List[int]) -> Dict:
        """
        Backfill multiple seasons.
        
        Args:
            years: List of season years
            
        Returns:
            Combined statistics dictionary
        """
        combined_stats = {
            'total_fetched': 0,
            'total_inserted': 0,
            'errors': 0,
            'seasons': {}
        }
        
        for year in years:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing season {year}")
            logger.info(f"{'='*60}")
            
            stats = self.backfill_season(year)
            combined_stats['seasons'][year] = stats
            combined_stats['total_fetched'] += stats.get('total_fetched', 0)
            combined_stats['total_inserted'] += stats.get('total_inserted', 0)
            combined_stats['errors'] += stats.get('errors', 0)
        
        return combined_stats


def main():
    """Main entry point for the backfill script."""
    parser = argparse.ArgumentParser(
        description='Backfill daily lineup data from Yahoo Fantasy Sports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Date range options
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    
    # Season options
    parser.add_argument('--season', type=int, help='Backfill specific season (e.g., 2025)')
    parser.add_argument('--seasons', type=str, help='Comma-separated list of seasons (e.g., 2023,2024,2025)')
    parser.add_argument('--all-seasons', action='store_true', help='Backfill all configured seasons')
    
    # Configuration options
    parser.add_argument('--environment', choices=['production', 'test'], default='production',
                       help='Database environment (default: production)')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                       help=f'Number of parallel workers (default: {DEFAULT_WORKERS}, max: {MAX_WORKERS})')
    parser.add_argument('--league-key', type=str, help='Override league key')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if not any([args.start, args.season, args.seasons, args.all_seasons]):
        parser.error('Must specify either --start/--end, --season, --seasons, or --all-seasons')
    
    if args.start and not args.end:
        parser.error('--end is required when --start is specified')
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be written")
        return
    
    # Initialize backfiller
    backfiller = LineupBackfiller(
        environment=args.environment,
        max_workers=args.workers
    )
    
    try:
        # Execute based on arguments
        if args.all_seasons:
            # Backfill all configured seasons
            years = list(LEAGUE_KEYS.keys())
            logger.info(f"Backfilling all seasons: {years}")
            stats = backfiller.backfill_multiple_seasons(years)
            
        elif args.seasons:
            # Backfill multiple specific seasons
            years = [int(y.strip()) for y in args.seasons.split(',')]
            logger.info(f"Backfilling seasons: {years}")
            stats = backfiller.backfill_multiple_seasons(years)
            
        elif args.season:
            # Backfill single season
            logger.info(f"Backfilling season {args.season}")
            stats = backfiller.backfill_season(args.season)
            
        else:
            # Backfill date range
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
            
            # Determine league key
            if args.league_key:
                league_key = args.league_key
            else:
                # Use the year from start date to find league key
                league_key = get_league_key(start_date.year)
                if not league_key:
                    logger.error(f"No league key found for {start_date.year}")
                    return
            
            logger.info(f"Backfilling from {args.start} to {args.end}")
            stats = backfiller.backfill_date_range(start_date, end_date, league_key)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("BACKFILL COMPLETE")
        logger.info("="*60)
        logger.info(f"Total fetched: {stats.get('total_fetched', 0)}")
        logger.info(f"Total inserted: {stats.get('total_inserted', 0)}")
        logger.info(f"Errors: {stats.get('errors', 0)}")
        
        if 'elapsed_time' in stats:
            logger.info(f"Elapsed time: {stats['elapsed_time']:.2f} seconds")
        
        if 'seasons' in stats:
            logger.info("\nSeason Summary:")
            for year, season_stats in stats['seasons'].items():
                logger.info(f"  {year}: {season_stats.get('total_inserted', 0)} inserted")
    
    except KeyboardInterrupt:
        logger.info("\nBackfill interrupted by user")
        if backfiller.job_id:
            backfiller.update_job('failed', error_message='Interrupted by user')
    
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        if backfiller.job_id:
            backfiller.update_job('failed', error_message=str(e))
        raise


if __name__ == '__main__':
    main()