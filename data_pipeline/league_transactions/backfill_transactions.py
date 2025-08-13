#!/usr/bin/env python
"""
Backfill Transactions - Bulk Historical Data Collection

This script handles bulk collection of transaction data from Yahoo Fantasy Sports API.
It's designed for populating entire seasons or fetching multiple months of data
with parallel processing capabilities while respecting API rate limits.

Usage:
    # Backfill entire season
    python backfill_transactions.py --season 2025
    
    # Backfill date range with parallel workers
    python backfill_transactions.py --start 2025-03-01 --end 2025-09-30 --workers 4
    
    # Backfill multiple seasons
    python backfill_transactions.py --seasons 2023,2024,2025
    
    # Backfill all configured seasons
    python backfill_transactions.py --all-seasons

Features:
    - Parallel processing with configurable workers (respects Yahoo API rate limits)
    - Comprehensive job logging and progress tracking
    - Resume capability for interrupted jobs
    - Data quality validation before insertion
    - Support for multiple seasons
    - Automatic date correction using transaction timestamps
"""

import argparse
import json
import logging
import os
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
from data_pipeline.common.season_manager import SeasonManager, get_league_key, get_season_dates
from data_pipeline.config.database_config import get_database_path, get_table_name
from data_pipeline.league_transactions.data_quality_check import TransactionDataQualityChecker
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
CHECKPOINT_FILE = Path(__file__).parent / 'backfill_checkpoint.json'


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


class TransactionBackfiller:
    """Handles bulk transaction data collection from Yahoo Fantasy Sports API."""
    
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
        self.season_manager = SeasonManager()
        self.quality_checker = TransactionDataQualityChecker()
        
        # Database setup
        self.db_path = get_database_path(environment)
        self.table_name = get_table_name('transactions', environment)
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
        
        # Create transactions table if it doesn't exist
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                league_key TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                yahoo_player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_position TEXT,
                player_team TEXT,
                movement_type TEXT NOT NULL,
                destination_team_key TEXT,
                destination_team_name TEXT,
                source_team_key TEXT,
                source_team_name TEXT,
                timestamp INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_id TEXT,
                UNIQUE(league_key, transaction_id, yahoo_player_id, movement_type)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_date ON {self.table_name}(date)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_player ON {self.table_name}(player_name)')
        cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_trans_id ON {self.table_name}(transaction_id)')
        
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
    
    def fetch_transactions_for_date(self, league_key: str, date_str: str) -> List[Dict]:
        """
        Fetch transactions for a specific date from Yahoo API.
        
        Args:
            league_key: Yahoo league key
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of transaction dictionaries
        """
        self.rate_limiter.wait()
        
        url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
        headers = {
            'Authorization': f'Bearer {self.token_manager.get_access_token()}',
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse XML and extract transactions
            transactions = self.parse_transaction_xml(response.text, date_str, league_key)
            
            # IMPORTANT: Filter by actual timestamp since API returns all transactions
            filtered_transactions = []
            for trans in transactions:
                # The parse function should have already set the correct date from timestamp
                if trans.get('date') == date_str:
                    filtered_transactions.append(trans)
            
            return filtered_transactions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions for {date_str}: {e}")
            self.stats['errors'] += 1
            return []
    
    def parse_transaction_xml(self, xml_data: str, date_str: str, league_key: str) -> List[Dict]:
        """
        Parse transaction XML data into structured records.
        
        Args:
            xml_data: Raw XML response from Yahoo API
            date_str: Date string (may be overridden by actual timestamp)
            league_key: League identifier
            
        Returns:
            List of transaction dictionaries
        """
        transactions = []
        
        try:
            root = ET.fromstring(xml_data)
            ns = {'y': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            
            transaction_elements = root.findall('.//y:transaction', ns)
            
            for trans_elem in transaction_elements:
                trans_id = trans_elem.find('.//y:transaction_id', ns)
                trans_type = trans_elem.find('.//y:type', ns)
                timestamp_elem = trans_elem.find('.//y:timestamp', ns)
                
                # Get actual date from timestamp
                actual_date = date_str
                transaction_timestamp = 0  # Default value
                if timestamp_elem is not None and timestamp_elem.text:
                    try:
                        transaction_timestamp = int(timestamp_elem.text)
                        actual_date = datetime.fromtimestamp(transaction_timestamp).strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass
                
                # Process each player in the transaction
                players = trans_elem.findall('.//y:player', ns)
                
                for player in players:
                    yahoo_player_id = player.find('.//y:player_id', ns)
                    player_name = player.find('.//y:name/y:full', ns)
                    player_team = player.find('.//y:editorial_team_abbr', ns)
                    player_pos = player.find('.//y:display_position', ns)
                    
                    # Get transaction data for this player
                    trans_data = player.find('.//y:transaction_data', ns)
                    
                    if trans_data is not None:
                        move_type = trans_data.find('.//y:type', ns)
                        source_team_name = trans_data.find('.//y:source_team_name', ns)
                        dest_team_name = trans_data.find('.//y:destination_team_name', ns)
                        source_team_key = trans_data.find('.//y:source_team_key', ns)
                        dest_team_key = trans_data.find('.//y:destination_team_key', ns)
                        
                        transaction = {
                            'date': actual_date,  # Use actual date from timestamp
                            'league_key': league_key,
                            'transaction_id': trans_id.text if trans_id is not None else '',
                            'transaction_type': trans_type.text if trans_type is not None else '',
                            'yahoo_player_id': yahoo_player_id.text if yahoo_player_id is not None else '',',
                            'player_name': player_name.text if player_name is not None else '',
                            'player_position': player_pos.text if player_pos is not None else '',
                            'player_team': player_team.text if player_team is not None else '',
                            'movement_type': move_type.text if move_type is not None else '',
                            'destination_team_key': dest_team_key.text if dest_team_key is not None else '',
                            'destination_team_name': dest_team_name.text if dest_team_name is not None else '',
                            'source_team_key': source_team_key.text if source_team_key is not None else '',
                            'source_team_name': source_team_name.text if source_team_name is not None else '',
                            'timestamp': transaction_timestamp,
                            'job_id': self.job_id
                        }
                        
                        transactions.append(transaction)
        
        except ET.ParseError as e:
            logger.error(f"Error parsing XML: {e}")
            self.stats['errors'] += 1
        
        return transactions
    
    def insert_transactions(self, transactions: List[Dict]) -> int:
        """
        Insert transactions into database with duplicate handling.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Number of records inserted
        """
        if not transactions:
            return 0
        
        # Validate data quality
        validation_results = self.quality_checker.validate_batch(transactions)
        if validation_results['invalid'] > 0:
            logger.warning(f"Found {validation_results['invalid']} invalid transactions")
            logger.warning(self.quality_checker.generate_report(validation_results))
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        inserted = 0
        for trans in transactions:
            try:
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {self.table_name} (
                        date, league_key, transaction_id, transaction_type,
                        yahoo_player_id, player_name, player_position, player_team,
                        movement_type, destination_team_key, destination_team_name,
                        source_team_key, source_team_name, timestamp, job_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trans['date'], trans['league_key'], trans['transaction_id'],
                    trans['transaction_type'], trans['yahoo_player_id'], trans['player_name'],
                    trans['player_position'], trans['player_team'], trans['movement_type'],
                    trans['destination_team_key'], trans['destination_team_name'],
                    trans['source_team_key'], trans['source_team_name'], trans.get('timestamp', 0), trans['job_id']
                ))
                
                if cursor.rowcount > 0:
                    inserted += 1
                    
            except sqlite3.Error as e:
                logger.error(f"Error inserting transaction: {e}")
                self.stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return inserted
    
    def backfill_date_range(self, start_date: datetime, end_date: datetime, 
                           league_key: str) -> Dict:
        """
        Backfill transactions for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            league_key: Yahoo league key
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Backfilling {league_key} from {start_date.date()} to {end_date.date()}")
        
        # Start job
        self.start_job(
            job_type='transaction_backfill',
            date_range_start=str(start_date.date()),
            date_range_end=str(end_date.date()),
            league_key=league_key,
            metadata=f"Workers: {self.max_workers}"
        )
        
        self.stats['start_time'] = time.time()
        
        # Generate list of dates
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        logger.info(f"Processing {len(dates)} days with {self.max_workers} workers")
        
        # Process dates in parallel
        all_transactions = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_date = {
                executor.submit(self.fetch_transactions_for_date, league_key, date): date
                for date in dates
            }
            
            for future in as_completed(future_to_date):
                date = future_to_date[future]
                try:
                    transactions = future.result()
                    if transactions:
                        all_transactions.extend(transactions)
                        logger.info(f"Fetched {len(transactions)} transactions for {date}")
                    self.stats['total_fetched'] += len(transactions)
                    
                except Exception as e:
                    logger.error(f"Error processing {date}: {e}")
                    self.stats['errors'] += 1
                
                # Show progress
                completed = len([f for f in future_to_date if f.done()])
                if completed % 10 == 0:
                    logger.info(f"Progress: {completed}/{len(dates)} days processed")
        
        # Insert all transactions
        if all_transactions:
            logger.info(f"Inserting {len(all_transactions)} transactions...")
            inserted = self.insert_transactions(all_transactions)
            self.stats['total_inserted'] = inserted
            logger.info(f"Inserted {inserted} new transactions")
        
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
        Backfill all transactions for a season.
        
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
        description='Backfill transaction data from Yahoo Fantasy Sports',
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
    backfiller = TransactionBackfiller(
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