#!/usr/bin/env python
"""
Update Transactions - Incremental Daily Updates

This script handles incremental updates to keep the transaction database current.
It's designed for regular automated runs (daily/hourly) with minimal user interaction.

Usage:
    # Default 7-day lookback update
    python update_transactions.py
    
    # Custom lookback period
    python update_transactions.py --days 14
    
    # Update from last transaction date
    python update_transactions.py --since-last
    
    # Update specific date
    python update_transactions.py --date 2025-08-04
    
    # Test environment
    python update_transactions.py --environment test

Features:
    - Automatic duplicate detection
    - 7-day default lookback window (configurable)
    - Timestamp-based date correction
    - Data quality validation
    - Minimal output for automation
    - Job logging for audit trail
"""

import argparse
import logging
import sqlite3
import sys
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
from data_pipeline.league_transactions.data_quality_check import TransactionDataQualityChecker

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


class TransactionUpdater:
    """Handles incremental transaction updates from Yahoo Fantasy Sports API."""
    
    def __init__(self, environment='production'):
        """
        Initialize the updater.
        
        Args:
            environment: Database environment ('production' or 'test')
        """
        self.environment = environment
        self.token_manager = YahooTokenManager()
        self.quality_checker = TransactionDataQualityChecker()
        
        # Database setup
        self.db_path = get_database_path(environment)
        self.table_name = get_table_name('transactions', environment)
        self._ensure_database()
        
        # Job tracking
        self.job_id = None
        self.stats = {
            'checked': 0,
            'new': 0,
            'duplicates': 0,
            'errors': 0
        }
    
    def _ensure_database(self):
        """Ensure database and tables exist."""
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
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_position TEXT,
                player_team TEXT,
                movement_type TEXT NOT NULL,
                destination_team_key TEXT,
                destination_team_name TEXT,
                source_team_key TEXT,
                source_team_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                job_id TEXT,
                UNIQUE(league_key, transaction_id, player_id, movement_type)
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
    
    def get_latest_transaction_date(self, league_key: str) -> Optional[datetime]:
        """
        Get the date of the most recent transaction in the database.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            Latest transaction date or None if no transactions
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT MAX(date) FROM {self.table_name}
            WHERE league_key = ?
        ''', (league_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return datetime.strptime(result[0], '%Y-%m-%d')
        return None
    
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
    
    def fetch_and_parse_transactions(self, league_key: str, date_str: str) -> List[Dict]:
        """
        Fetch and parse transactions for a specific date.
        
        Args:
            league_key: Yahoo league key
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of transaction dictionaries
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
        headers = {
            'Authorization': f'Bearer {self.token_manager.get_access_token()}',
            'Accept': 'application/xml'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            transactions = []
            root = ET.fromstring(response.text)
            ns = {'y': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            
            transaction_elements = root.findall('.//y:transaction', ns)
            
            for trans_elem in transaction_elements:
                trans_id = trans_elem.find('.//y:transaction_id', ns)
                trans_type = trans_elem.find('.//y:type', ns)
                timestamp_elem = trans_elem.find('.//y:timestamp', ns)
                
                # Get actual date from timestamp
                actual_date = date_str
                if timestamp_elem is not None and timestamp_elem.text:
                    try:
                        timestamp = int(timestamp_elem.text)
                        actual_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass
                
                # Only process if within our date range
                if actual_date != date_str:
                    continue
                
                # Process each player
                players = trans_elem.findall('.//y:player', ns)
                
                for player in players:
                    player_id = player.find('.//y:player_id', ns)
                    player_name = player.find('.//y:name/y:full', ns)
                    player_team = player.find('.//y:editorial_team_abbr', ns)
                    player_pos = player.find('.//y:display_position', ns)
                    
                    # Get transaction data
                    trans_data = player.find('.//y:transaction_data', ns)
                    
                    if trans_data is not None:
                        move_type = trans_data.find('.//y:type', ns)
                        source_team_name = trans_data.find('.//y:source_team_name', ns)
                        dest_team_name = trans_data.find('.//y:destination_team_name', ns)
                        source_team_key = trans_data.find('.//y:source_team_key', ns)
                        dest_team_key = trans_data.find('.//y:destination_team_key', ns)
                        
                        transaction = {
                            'date': actual_date,
                            'league_key': league_key,
                            'transaction_id': trans_id.text if trans_id is not None else '',
                            'transaction_type': trans_type.text if trans_type is not None else '',
                            'player_id': player_id.text if player_id is not None else '',
                            'player_name': player_name.text if player_name is not None else '',
                            'player_position': player_pos.text if player_pos is not None else '',
                            'player_team': player_team.text if player_team is not None else '',
                            'movement_type': move_type.text if move_type is not None else '',
                            'destination_team_key': dest_team_key.text if dest_team_key is not None else '',
                            'destination_team_name': dest_team_name.text if dest_team_name is not None else '',
                            'source_team_key': source_team_key.text if source_team_key is not None else '',
                            'source_team_name': source_team_name.text if source_team_name is not None else '',
                            'job_id': self.job_id
                        }
                        
                        transactions.append(transaction)
            
            return transactions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions for {date_str}: {e}")
            self.stats['errors'] += 1
            return []
    
    def insert_new_transactions(self, transactions: List[Dict]) -> Tuple[int, int]:
        """
        Insert new transactions, skipping duplicates.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Tuple of (new_count, duplicate_count)
        """
        if not transactions:
            return 0, 0
        
        # Validate data quality
        validation_results = self.quality_checker.validate_batch(transactions)
        if validation_results['invalid'] > 0:
            logger.warning(f"Found {validation_results['invalid']} invalid transactions")
            # Log details but continue with valid transactions
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        new_count = 0
        duplicate_count = 0
        
        for trans in transactions:
            try:
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {self.table_name} (
                        date, league_key, transaction_id, transaction_type,
                        player_id, player_name, player_position, player_team,
                        movement_type, destination_team_key, destination_team_name,
                        source_team_key, source_team_name, job_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trans['date'], trans['league_key'], trans['transaction_id'],
                    trans['transaction_type'], trans['player_id'], trans['player_name'],
                    trans['player_position'], trans['player_team'], trans['movement_type'],
                    trans['destination_team_key'], trans['destination_team_name'],
                    trans['source_team_key'], trans['source_team_name'], trans['job_id']
                ))
                
                if cursor.rowcount > 0:
                    new_count += 1
                else:
                    duplicate_count += 1
                    
            except sqlite3.Error as e:
                logger.error(f"Error inserting transaction: {e}")
                self.stats['errors'] += 1
        
        conn.commit()
        conn.close()
        
        return new_count, duplicate_count
    
    def update_recent(self, days_back: int = DEFAULT_LOOKBACK_DAYS,
                     league_key: Optional[str] = None) -> Dict:
        """
        Update transactions for the last N days.
        
        Args:
            days_back: Number of days to look back
            league_key: Override league key (otherwise uses current year)
            
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
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Updating transactions from {start_date.date()} to {end_date.date()}")
        
        # Start job
        self.start_job(
            job_type='transaction_update',
            date_range_start=str(start_date.date()),
            date_range_end=str(end_date.date()),
            league_key=league_key,
            metadata=f"Lookback: {days_back} days"
        )
        
        # Process each day
        all_transactions = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Fetch transactions for this date
            transactions = self.fetch_and_parse_transactions(league_key, date_str)
            
            if transactions:
                all_transactions.extend(transactions)
                logger.debug(f"Found {len(transactions)} transactions for {date_str}")
            
            self.stats['checked'] += 1
            current_date += timedelta(days=1)
        
        # Insert new transactions
        if all_transactions:
            new_count, duplicate_count = self.insert_new_transactions(all_transactions)
            self.stats['new'] = new_count
            self.stats['duplicates'] = duplicate_count
            
            if new_count > 0:
                logger.info(f"Added {new_count} new transactions")
            logger.debug(f"Skipped {duplicate_count} duplicates")
        else:
            logger.info("No transactions found in date range")
        
        # Update job
        self.update_job(
            status='completed',
            records_processed=len(all_transactions),
            records_inserted=self.stats['new']
        )
        
        return self.stats
    
    def update_since_last(self, league_key: Optional[str] = None) -> Dict:
        """
        Update transactions since the last transaction date in the database.
        
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
        
        # Get last transaction date
        last_date = self.get_latest_transaction_date(league_key)
        
        if last_date:
            # Calculate days since last transaction
            days_since = (datetime.now() - last_date).days
            
            if days_since <= 0:
                logger.info("Database is up to date")
                return {'message': 'Already up to date', 'new': 0}
            
            # Limit lookback to MAX_LOOKBACK_DAYS
            days_back = min(days_since + 1, MAX_LOOKBACK_DAYS)
            
            logger.info(f"Last transaction: {last_date.date()}, updating {days_back} days")
            return self.update_recent(days_back, league_key)
        else:
            logger.warning("No transactions in database, use backfill_transactions.py for initial load")
            return {'error': 'No existing transactions, use backfill instead'}
    
    def update_specific_date(self, date: datetime, league_key: Optional[str] = None) -> Dict:
        """
        Update transactions for a specific date.
        
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
        
        date_str = date.strftime('%Y-%m-%d')
        logger.info(f"Updating transactions for {date_str}")
        
        # Start job
        self.start_job(
            job_type='transaction_update_single',
            date_range_start=date_str,
            date_range_end=date_str,
            league_key=league_key,
            metadata=f"Single date update"
        )
        
        # Fetch transactions
        transactions = self.fetch_and_parse_transactions(league_key, date_str)
        
        # Insert new transactions
        if transactions:
            new_count, duplicate_count = self.insert_new_transactions(transactions)
            self.stats['new'] = new_count
            self.stats['duplicates'] = duplicate_count
            self.stats['checked'] = 1
            
            if new_count > 0:
                logger.info(f"Added {new_count} new transactions for {date_str}")
            else:
                logger.info(f"No new transactions for {date_str}")
        else:
            logger.info(f"No transactions found for {date_str}")
        
        # Update job
        self.update_job(
            status='completed',
            records_processed=len(transactions) if transactions else 0,
            records_inserted=self.stats['new']
        )
        
        return self.stats


def main():
    """Main entry point for the update script."""
    parser = argparse.ArgumentParser(
        description='Update transaction database with recent data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Update options
    parser.add_argument('--days', type=int, default=DEFAULT_LOOKBACK_DAYS,
                       help=f'Number of days to look back (default: {DEFAULT_LOOKBACK_DAYS})')
    parser.add_argument('--since-last', action='store_true',
                       help='Update from last transaction date in database')
    parser.add_argument('--date', type=str,
                       help='Update specific date (YYYY-MM-DD)')
    
    # Configuration options
    parser.add_argument('--environment', choices=['production', 'test'], default='production',
                       help='Database environment (default: production)')
    parser.add_argument('--league-key', type=str,
                       help='Override league key')
    
    # Other options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress non-error output')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Initialize updater
    updater = TransactionUpdater(environment=args.environment)
    
    try:
        # Execute based on arguments
        if args.since_last:
            # Update from last transaction date
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