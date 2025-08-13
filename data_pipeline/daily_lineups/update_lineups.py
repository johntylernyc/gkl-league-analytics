#!/usr/bin/env python
"""
Update Daily Lineups - Incremental Daily Updates

This script handles incremental updates to keep the lineup database current.
It's designed for regular automated runs (daily/hourly) with minimal user interaction.

Usage:
    # Default 7-day lookback update
    python update_lineups.py
    
    # Custom lookback period
    python update_lineups.py --days 14
    
    # Update from last lineup date
    python update_lineups.py --since-last
    
    # Update specific date
    python update_lineups.py --date 2025-08-04
    
    # Test environment
    python update_lineups.py --environment test

Features:
    - Automatic duplicate detection
    - 7-day default lookback window (configurable)
    - Data quality validation
    - Minimal output for automation
    - Job logging for audit trail
"""

import argparse
import logging
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

# Import required modules
from auth.token_manager import YahooTokenManager
from data_pipeline.common.season_manager import get_league_key
from data_pipeline.config.database_config import get_database_path, get_table_name
from data_pipeline.daily_lineups.data_quality_check import LineupDataQualityChecker
from data_pipeline.daily_lineups.parser import LineupParser

# Import D1 connection module
try:
    from data_pipeline.common.d1_connection import D1Connection, is_d1_available
    D1_AVAILABLE = True
except ImportError:
    D1_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'
DEFAULT_LOOKBACK_DAYS = 7
MAX_LOOKBACK_DAYS = 30
MAX_RETRIES = 3
RATES_PER_MINUTE = 20  # Yahoo rate limit


class LineupUpdater:
    """Handles incremental lineup updates from Yahoo Fantasy Sports API."""
    
    def __init__(self, environment='production', use_d1=None):
        """
        Initialize the updater.
        
        Args:
            environment: Database environment ('production' or 'test')
            use_d1: Force D1 usage (True/False). If None, auto-detect from environment
        """
        self.environment = environment
        self.token_manager = YahooTokenManager()
        self.quality_checker = LineupDataQualityChecker()
        self.parser = LineupParser()
        self.last_request_time = 0
        self.request_count = 0
        
        # Determine database type
        if use_d1 is None:
            # Auto-detect: use D1 if credentials are available, otherwise SQLite
            self.use_d1 = D1_AVAILABLE and is_d1_available()
        else:
            self.use_d1 = use_d1
        
        if self.use_d1:
            if not D1_AVAILABLE:
                raise RuntimeError("D1 connection module not available")
            self.d1_conn = D1Connection()
            self.db_path = None
            self.table_name = 'daily_lineups'
            logger.info("Using Cloudflare D1 database")
        else:
            # SQLite setup
            self.d1_conn = None
            self.db_path = get_database_path(environment)
            self.table_name = get_table_name('daily_lineups', environment)
            self._ensure_database()
            logger.info(f"Using SQLite database: {self.db_path}")
        
        # Job tracking
        self.job_id = None
        self.stats = {
            'checked': 0,
            'new': 0,
            'duplicates': 0,
            'errors': 0
        }
    
    def _ensure_database(self):
        """Ensure database and tables exist (SQLite only)."""
        if self.use_d1:
            # D1 tables are assumed to exist in production
            return
            
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
    
    def get_latest_lineup_date(self, league_key: str) -> Optional[datetime]:
        """
        Get the date of the most recent lineup in the database.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            Latest lineup date or None if no lineups
        """
        # Extract season from league key to filter by team_key prefix
        # League key format: 422.l.6966 -> team keys: 422.l.6966.t.1, etc.
        team_key_prefix = league_key + '.t.'
        
        if self.use_d1:
            result = self.d1_conn.execute(f'''
                SELECT MAX(date) FROM {self.table_name}
                WHERE team_key LIKE ?
            ''', [team_key_prefix + '%'])
            
            rows = result.get('results', [])
            if rows and rows[0] and rows[0][0]:
                return datetime.strptime(rows[0][0], '%Y-%m-%d')
            return None
        else:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT MAX(date) FROM {self.table_name}
                WHERE team_key LIKE ?
            ''', (team_key_prefix + '%',))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return datetime.strptime(result[0], '%Y-%m-%d')
            return None
    
    def _rate_limit(self):
        """Implement rate limiting to avoid Yahoo API throttling."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Reset counter if it's been more than a minute
        if time_since_last > 60:
            self.request_count = 0
        
        # If we've hit the rate limit, wait
        if self.request_count >= RATES_PER_MINUTE:
            sleep_time = 60 - time_since_last
            if sleep_time > 0:
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request_with_retry(self, url: str, max_retries: int = MAX_RETRIES) -> requests.Response:
        """Make HTTP request with retry logic and token refresh."""
        for attempt in range(max_retries):
            self._rate_limit()
            
            # Get fresh token (will refresh if needed)
            force_refresh = attempt > 0  # Force refresh on retry
            headers = {
                'Authorization': f'Bearer {self.token_manager.get_access_token(force_refresh=force_refresh)}',
                'Accept': 'application/xml'
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 401:
                    logger.warning(f"401 Unauthorized on attempt {attempt + 1}, will retry with fresh token")
                    if attempt < max_retries - 1:
                        continue
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} of {max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def get_all_team_keys(self, league_key: str) -> List[str]:
        """
        Get all team keys for a league.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            List of team keys
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/teams"
        
        try:
            response = self._make_request_with_retry(url)
            
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
    
    def start_job(self, job_type: str, date_range_start: str, date_range_end: str,
                  league_key: str, metadata: Optional[str] = None) -> str:
        """Start a new job and return job_id."""
        import uuid
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_id = f"{job_type}_{self.environment}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        if self.use_d1:
            # Use D1 connection method
            self.d1_conn.ensure_job_exists(
                job_id=job_id,
                job_type=job_type,
                environment=self.environment,
                league_key=league_key,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                metadata=metadata
            )
        else:
            # Use SQLite
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
        
        if self.use_d1:
            # Use D1 connection method
            self.d1_conn.update_job_status(
                job_id=self.job_id,
                status=status,
                records_processed=records_processed,
                records_inserted=records_inserted,
                error_message=error_message
            )
        else:
            # Use SQLite
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
    
    def fetch_and_parse_lineups(self, league_key: str, team_key: str, date_str: str) -> List[Dict]:
        """
        Fetch and parse lineups for a specific team and date.
        
        Args:
            league_key: Yahoo league key
            team_key: Yahoo team key
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of lineup dictionaries
        """
        url = f"{BASE_FANTASY_URL}/team/{team_key}/roster;date={date_str}"
        
        try:
            response = self._make_request_with_retry(url)
            
            # Parse XML
            lineups = []
            
            # Check if response is empty or not XML
            if not response.text or response.text.strip() == '':
                logger.warning(f"Empty response for {team_key} on {date_str}")
                return lineups
            
            # Check if response starts with HTML (error page)
            if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<html'):
                logger.error(f"Received HTML error page instead of XML for {team_key} on {date_str}")
                logger.debug(f"Response preview: {response.text[:500]}")
                return lineups
            
            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as e:
                logger.error(f"XML parse error for {team_key} on {date_str}: {e}")
                logger.debug(f"Response preview: {response.text[:500]}")
                return lineups
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
                    'yahoo_player_id': yahoo_player_id.text if yahoo_player_id is not None else '',
                    'player_name': player_name.text if player_name is not None else '',
                    'selected_position': selected_position.text if selected_position is not None else '',
                    'position_type': position_type.text if position_type is not None else '',
                    'player_status': player_status.text if player_status is not None else 'healthy',
                    'eligible_positions': ','.join(eligible_positions),
                    'player_team': player_team.text if player_team is not None else ''
                }
                
                lineups.append(lineup)
            
            return lineups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching lineups for {team_key} on {date_str}: {e}")
            self.stats['errors'] += 1
            return []
    
    def insert_new_lineups(self, lineups: List[Dict]) -> Tuple[int, int]:
        """
        Insert new lineups, skipping duplicates.
        
        Args:
            lineups: List of lineup dictionaries
            
        Returns:
            Tuple of (new_count, duplicate_count)
        """
        if not lineups:
            return 0, 0
        
        # Validate data quality
        validation_results = self.quality_checker.validate_batch(lineups)
        if validation_results['invalid'] > 0:
            logger.warning(f"Found {validation_results['invalid']} invalid lineups")
            # Log details but continue with valid lineups
        
        if self.use_d1:
            # Use D1 batch insert method
            inserted_count, error_count = self.d1_conn.insert_lineups(lineups, self.job_id)
            
            # D1 uses REPLACE so we can't distinguish duplicates, return as new
            self.stats['errors'] += error_count
            return inserted_count, 0
        else:
            # Use SQLite
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            new_count = 0
            duplicate_count = 0
            
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
                        new_count += 1
                    else:
                        duplicate_count += 1
                        
                except sqlite3.Error as e:
                    logger.error(f"Error inserting lineup: {e}")
                    self.stats['errors'] += 1
            
            conn.commit()
            conn.close()
            
            return new_count, duplicate_count
    
    def update_recent(self, days_back: int = DEFAULT_LOOKBACK_DAYS,
                     league_key: Optional[str] = None) -> Dict:
        """
        Update lineups for the last N days.
        
        Args:
            days_back: Number of days to look back
            league_key: Override league key (otherwise uses current year)
            
        Returns:
            Statistics dictionary
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        return self.update_date_range(start_date, end_date, league_key)
    
    def update_date_range(self, start_date: datetime, end_date: datetime,
                         league_key: Optional[str] = None) -> Dict:
        """
        Update lineups for a specific date range.
        
        Args:
            start_date: Start date
            end_date: End date
            league_key: Override league key
            
        Returns:
            Statistics dictionary
        """
        # Determine league key
        if not league_key:
            # Use year from start date
            league_key = get_league_key(start_date.year)
            if not league_key:
                logger.error(f"No league key found for {start_date.year}")
                return {'error': f'No league key for {start_date.year}'}
        
        # Get all team keys
        team_keys = self.get_all_team_keys(league_key)
        if not team_keys:
            logger.error("Could not fetch team keys")
            return {'error': 'Failed to get team keys'}
        
        logger.info(f"Updating lineups from {start_date.date()} to {end_date.date()}")
        logger.info(f"Processing {len(team_keys)} teams")
        
        # Start job
        self.start_job(
            job_type='lineup_update',
            date_range_start=str(start_date.date()),
            date_range_end=str(end_date.date()),
            league_key=league_key,
            metadata=f"Lookback: {days_back} days, Teams: {len(team_keys)}"
        )
        
        # Process each day and team
        all_lineups = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            for team_key in team_keys:
                # Fetch lineups for this team and date
                try:
                    lineups = self.fetch_and_parse_lineups(league_key, team_key, date_str)
                    
                    if lineups:
                        all_lineups.extend(lineups)
                        logger.debug(f"Found {len(lineups)} players for {team_key} on {date_str}")
                except requests.exceptions.Timeout as e:
                    logger.error(f"Timeout fetching lineups for {team_key} on {date_str}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error fetching lineups for {team_key} on {date_str}: {e}")
                    continue
            
            self.stats['checked'] += 1
            current_date += timedelta(days=1)
        
        # Insert new lineups
        if all_lineups:
            new_count, duplicate_count = self.insert_new_lineups(all_lineups)
            self.stats['new'] = new_count
            self.stats['duplicates'] = duplicate_count
            
            if new_count > 0:
                logger.info(f"Added {new_count} new lineup records")
            logger.debug(f"Skipped {duplicate_count} duplicates")
        else:
            logger.info("No lineups found in date range")
        
        # Update job
        self.update_job(
            status='completed',
            records_processed=len(all_lineups),
            records_inserted=self.stats['new']
        )
        
        return self.stats
    
    def update_since_last(self, league_key: Optional[str] = None) -> Dict:
        """
        Update lineups since the last lineup date in the database.
        
        Args:
            league_key: Override league key
            
        Returns:
            Statistics dictionary
        """
        # Determine league key
        if not league_key:
            current_year = datetime.now().year
            league_key = get_league_key(current_year)
            if not league_key:
                logger.error(f"No league key found for {current_year}")
                return {'error': f'No league key for {current_year}'}
        
        # Get last lineup date
        last_date = self.get_latest_lineup_date(league_key)
        
        if last_date:
            # Calculate days since last lineup
            days_since = (datetime.now() - last_date).days
            
            if days_since <= 0:
                logger.info("Database is up to date")
                return {'message': 'Already up to date', 'new': 0}
            
            # Limit lookback to MAX_LOOKBACK_DAYS
            days_back = min(days_since + 1, MAX_LOOKBACK_DAYS)
            
            logger.info(f"Last lineup: {last_date.date()}, updating {days_back} days")
            return self.update_recent(days_back, league_key)
        else:
            logger.warning("No lineups in database, use backfill_lineups.py for initial load")
            return {'error': 'No existing lineups, use backfill instead'}
    
    def update_specific_date(self, date: datetime, league_key: Optional[str] = None) -> Dict:
        """
        Update lineups for a specific date.
        
        Args:
            date: Date to update
            league_key: Override league key
            
        Returns:
            Statistics dictionary
        """
        # Determine league key
        if not league_key:
            league_key = get_league_key(date.year)
            if not league_key:
                logger.error(f"No league key found for {date.year}")
                return {'error': f'No league key for {date.year}'}
        
        # Get all team keys
        team_keys = self.get_all_team_keys(league_key)
        if not team_keys:
            logger.error("Could not fetch team keys")
            return {'error': 'Failed to get team keys'}
        
        date_str = date.strftime('%Y-%m-%d')
        logger.info(f"Updating lineups for {date_str}")
        logger.info(f"Processing {len(team_keys)} teams")
        
        # Start job
        self.start_job(
            job_type='lineup_update_single',
            date_range_start=date_str,
            date_range_end=date_str,
            league_key=league_key,
            metadata=f"Single date update, Teams: {len(team_keys)}"
        )
        
        # Fetch lineups for all teams
        all_lineups = []
        for team_key in team_keys:
            lineups = self.fetch_and_parse_lineups(league_key, team_key, date_str)
            if lineups:
                all_lineups.extend(lineups)
        
        # Insert new lineups
        if all_lineups:
            new_count, duplicate_count = self.insert_new_lineups(all_lineups)
            self.stats['new'] = new_count
            self.stats['duplicates'] = duplicate_count
            self.stats['checked'] = 1
            
            if new_count > 0:
                logger.info(f"Added {new_count} new lineup records for {date_str}")
            else:
                logger.info(f"No new lineups for {date_str}")
        else:
            logger.info(f"No lineups found for {date_str}")
        
        # Update job
        self.update_job(
            status='completed',
            records_processed=len(all_lineups) if all_lineups else 0,
            records_inserted=self.stats['new']
        )
        
        return self.stats


def main():
    """Main entry point for the update script."""
    parser = argparse.ArgumentParser(
        description='Update lineup database with recent data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Update options
    parser.add_argument('--days', type=int, default=DEFAULT_LOOKBACK_DAYS,
                       help=f'Number of days to look back (default: {DEFAULT_LOOKBACK_DAYS})')
    parser.add_argument('--since-last', action='store_true',
                       help='Update from last lineup date in database')
    parser.add_argument('--date', type=str,
                       help='Update specific date (YYYY-MM-DD)')
    parser.add_argument('--start', type=str,
                       help='Start date for range update (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                       help='End date for range update (YYYY-MM-DD)')
    
    # Configuration options
    parser.add_argument('--environment', choices=['production', 'test'], default='production',
                       help='Database environment (default: production)')
    parser.add_argument('--league-key', type=str,
                       help='Override league key')
    parser.add_argument('--use-d1', action='store_true',
                       help='Force use of Cloudflare D1 database (auto-detected if not specified)')
    parser.add_argument('--use-sqlite', action='store_true',
                       help='Force use of SQLite database (auto-detected if not specified)')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress non-error output')
    
    args = parser.parse_args()
    
    # Validate database selection
    if args.use_d1 and args.use_sqlite:
        parser.error("Cannot specify both --use-d1 and --use-sqlite")
    
    # Determine database type
    use_d1 = None
    if args.use_d1:
        use_d1 = True
    elif args.use_sqlite:
        use_d1 = False
    # Otherwise auto-detect (use_d1 = None)
    
    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Initialize updater
    updater = LineupUpdater(environment=args.environment, use_d1=use_d1)
    
    try:
        # Execute based on arguments
        if args.start and args.end:
            # Update specific date range
            start_date = datetime.strptime(args.start, '%Y-%m-%d')
            end_date = datetime.strptime(args.end, '%Y-%m-%d')
            stats = updater.update_date_range(start_date, end_date, args.league_key)
            
        elif args.since_last:
            # Update from last lineup date
            stats = updater.update_since_last(args.league_key)
            
        elif args.date:
            # Update specific date
            date = datetime.strptime(args.date, '%Y-%m-%d')
            stats = updater.update_specific_date(date, args.league_key)
            
        else:
            # Default: update recent days
            stats = updater.update_recent(args.days, args.league_key)
        
        # Print summary (unless quiet mode)
        if not args.quiet:
            if 'error' in stats:
                logger.error(f"Update failed: {stats['error']}")
                sys.exit(1)
            elif 'message' in stats:
                logger.info(stats['message'])
            else:
                logger.info(f"Update complete: {stats.get('new', 0)} new, "
                          f"{stats.get('duplicates', 0)} duplicates, "
                          f"{stats.get('errors', 0)} errors")
    
    except KeyboardInterrupt:
        logger.info("Update interrupted by user")
        if updater.job_id:
            updater.update_job('failed', error_message='Interrupted by user')
    
    except Exception as e:
        logger.error(f"Update failed: {e}")
        if updater.job_id:
            updater.update_job('failed', error_message=str(e))
        raise


if __name__ == '__main__':
    main()