"""
Incremental update for league transactions with change detection.
Handles new transactions and detects modifications to existing ones.
"""

import sys
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Import change tracking utilities
sys.path.append(str(parent_dir / 'scripts'))
from change_tracking import ChangeTracker, RefreshStrategy

# Import auth config
from auth.config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, LEAGUE_KEYS, SEASON_DATES

# Constants
TRANSACTION_REFRESH_WINDOW = 2  # Check recent transactions for updates
DB_PATH = Path(__file__).parent.parent / 'database' / 'league_analytics.db'


class TransactionIncrementalUpdater:
    """Incremental updater for league transactions with change detection."""
    
    def __init__(self, league_key='mlb.l.6966', environment='production'):
        """
        Initialize the updater.
        
        Args:
            league_key: Yahoo league key
            environment: 'test' or 'production'
        """
        self.league_key = league_key
        self.environment = environment
        self.conn = sqlite3.connect(str(DB_PATH))
        self.tracker = ChangeTracker()
        self.strategy = RefreshStrategy()
        self.oauth = self._initialize_oauth()
        self.job_id = None
        self.stats = {
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'checked': 0,
            'errors': 0,
            'duplicates': 0
        }
        
    def _initialize_oauth(self):
        """Initialize Yahoo OAuth session."""
        # Simple OAuth placeholder - in production would use proper OAuth library
        class SimpleOAuth:
            def __init__(self):
                self.access_token = None
                self.refresh_token = None
                self.token_expiry = datetime.now()
                
            def is_token_expired(self):
                return datetime.now() >= self.token_expiry
                
            def refresh_access_token(self):
                # Placeholder for token refresh
                pass
        
        oauth = SimpleOAuth()
        
        # Load tokens if they exist
        token_file = Path(__file__).parent.parent / 'auth' / 'tokens.json'
        if token_file.exists():
            with open(token_file, 'r') as f:
                tokens = json.load(f)
                oauth.access_token = tokens.get('access_token')
                oauth.refresh_token = tokens.get('refresh_token')
                if tokens.get('token_expiry'):
                    try:
                        oauth.token_expiry = datetime.fromisoformat(tokens.get('token_expiry'))
                    except:
                        oauth.token_expiry = datetime.now()
        
        return oauth
    
    def start_job_log(self, date_range_start: str, date_range_end: str) -> str:
        """Start a job log entry."""
        cursor = self.conn.cursor()
        job_id = f"transaction_incremental_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                date_range_start, date_range_end, league_key,
                start_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            job_id, 'transaction_incremental', self.environment, 'running',
            date_range_start, date_range_end, self.league_key,
            json.dumps({'refresh_window': TRANSACTION_REFRESH_WINDOW})
        ))
        self.conn.commit()
        
        self.job_id = job_id
        return job_id
    
    def update_job_log(self, status: str, error_message: str = None):
        """Update job log with final status."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE job_log
            SET status = ?,
                end_time = datetime('now'),
                records_processed = ?,
                records_inserted = ?,
                error_message = ?,
                metadata = ?
            WHERE job_id = ?
        """, (
            status,
            self.stats['checked'],
            self.stats['new'] + self.stats['updated'],
            error_message,
            json.dumps(self.stats),
            self.job_id
        ))
        self.conn.commit()
    
    def get_existing_transactions(self, start_date: str, end_date: str) -> Dict[str, Dict]:
        """Get existing transactions for date range."""
        cursor = self.conn.cursor()
        
        # Get transactions with their content hashes
        cursor.execute("""
            SELECT transaction_id, transaction_date, transaction_type, 
                   team_key, player_id, content_hash
            FROM transactions
            WHERE transaction_date BETWEEN ? AND ?
              AND league_key = ?
            ORDER BY transaction_date, transaction_id
        """, (start_date, end_date, self.league_key))
        
        transactions = {}
        for row in cursor.fetchall():
            txn_id, txn_date, txn_type, team_key, player_id, content_hash = row
            
            # Create unique key for transaction
            txn_key = f"{txn_date}_{txn_id}"
            
            transactions[txn_key] = {
                'transaction_id': txn_id,
                'date': txn_date,
                'type': txn_type,
                'team_key': team_key,
                'player_id': player_id,
                'content_hash': content_hash
            }
        
        return transactions
    
    def fetch_transactions_for_date(self, date: str) -> List[Dict]:
        """
        Fetch transactions for a specific date from Yahoo API.
        """
        # Import the fetch function from backfill script
        from league_transactions.backfill_transactions_optimized import fetch_transactions_for_date
        
        try:
            # Use token manager to get access token and fetch data
            from auth.token_manager import YahooTokenManager
            token_manager = YahooTokenManager()
            
            date_str, transactions = fetch_transactions_for_date(
                token_manager, self.league_key, date, self.job_id
            )
            
            # Convert to expected format
            formatted_transactions = []
            for txn in transactions:
                formatted_transactions.append({
                    'transaction_id': txn.get('transaction_id'),
                    'date': txn.get('transaction_date', date),
                    'type': txn.get('transaction_type'),
                    'team_key': txn.get('team_key'),
                    'player_id': txn.get('player_id'),
                    'player_name': txn.get('player_name'),
                    'timestamp': txn.get('timestamp', f"{date}T12:00:00")
                })
            
            return formatted_transactions
            
        except Exception as e:
            print(f"  Error fetching transactions for {date}: {e}")
            return []
    
    def simulate_transactions_for_date(self, date: str) -> List[Dict]:
        """
        Simulate fetching transactions for a date.
        In production, this would fetch from Yahoo API.
        """
        cursor = self.conn.cursor()
        
        # Get some existing transactions to simulate
        cursor.execute("""
            SELECT transaction_id, transaction_type, team_key, 
                   player_id, player_name
            FROM transactions
            WHERE transaction_date = ?
              AND league_key = ?
            LIMIT 10
        """, (date, self.league_key))
        
        transactions = []
        for row in cursor.fetchall():
            txn_id, txn_type, team_key, player_id, player_name = row
            transactions.append({
                'transaction_id': txn_id,
                'date': date,
                'type': txn_type,
                'team_key': team_key,
                'player_id': player_id,
                'player_name': player_name,
                'timestamp': f"{date}T12:00:00"
            })
        
        # Simulate a modification (10% chance)
        import random
        if transactions and random.random() < 0.1:
            # Simulate a transaction update (e.g., timestamp correction)
            transactions[0]['timestamp'] = f"{date}T14:30:00"
            print(f"  [SIMULATED] Transaction update for {transactions[0]['transaction_id']}")
        
        return transactions
    
    def generate_transaction_hash(self, transaction: Dict) -> str:
        """Generate hash for transaction data."""
        # Normalize transaction data for hashing
        normalized = {
            'transaction_id': transaction.get('transaction_id'),
            'date': transaction.get('date'),
            'type': transaction.get('type'),
            'team_key': transaction.get('team_key'),
            'player_id': transaction.get('player_id'),
            'timestamp': transaction.get('timestamp', '')
        }
        
        return self.tracker.generate_hash(normalized)
    
    def detect_transaction_changes(
        self, new_txn: Dict, existing_txn: Dict
    ) -> Tuple[bool, List[str]]:
        """Detect changes in transaction data."""
        changes = []
        
        # Check timestamp changes
        new_timestamp = new_txn.get('timestamp', '')
        old_timestamp = existing_txn.get('timestamp', '')
        if new_timestamp != old_timestamp:
            changes.append(f"timestamp: {old_timestamp} -> {new_timestamp}")
        
        # Check other fields
        for field in ['type', 'team_key', 'player_id']:
            if new_txn.get(field) != existing_txn.get(field):
                changes.append(f"{field}: {existing_txn.get(field)} -> {new_txn.get(field)}")
        
        return len(changes) > 0, changes
    
    def process_transaction(
        self, transaction: Dict, existing_transactions: Dict
    ) -> Dict[str, int]:
        """Process a single transaction."""
        result = {'new': 0, 'updated': 0, 'unchanged': 0, 'duplicate': 0}
        
        txn_date = transaction['date']
        txn_id = transaction['transaction_id']
        txn_key = f"{txn_date}_{txn_id}"
        
        # Generate hash for new transaction
        new_hash = self.generate_transaction_hash(transaction)
        
        cursor = self.conn.cursor()
        
        if txn_key not in existing_transactions:
            # New transaction
            result['new'] += 1
            
            # Extract season from date
            season = int(txn_date.split('-')[0])
            
            # Insert new transaction
            cursor.execute("""
                INSERT OR REPLACE INTO transactions (
                    job_id, league_key, season, transaction_id,
                    transaction_date, transaction_type,
                    team_key, player_id, player_name,
                    content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.job_id, self.league_key, season, txn_id,
                txn_date, transaction['type'],
                transaction['team_key'], transaction['player_id'],
                transaction.get('player_name', f"Player_{transaction['player_id']}"),
                new_hash
            ))
            
        else:
            # Check for changes
            existing = existing_transactions[txn_key]
            old_hash = existing.get('content_hash')
            
            if old_hash and old_hash != new_hash:
                # Transaction has changed
                result['updated'] += 1
                
                has_changes, change_details = self.detect_transaction_changes(
                    transaction, existing
                )
                
                if has_changes:
                    print(f"    [CHANGE] Transaction {txn_id}: {', '.join(change_details)}")
                    
                    # Update transaction
                    cursor.execute("""
                        UPDATE transactions
                        SET content_hash = ?,
                            job_id = ?
                        WHERE transaction_id = ? 
                          AND transaction_date = ?
                          AND league_key = ?
                    """, (new_hash, self.job_id, txn_id, txn_date, self.league_key))
                    
            elif not old_hash:
                # No hash stored yet, update it
                result['updated'] += 1
                cursor.execute("""
                    UPDATE transactions
                    SET content_hash = ?
                    WHERE transaction_id = ? 
                      AND transaction_date = ?
                      AND league_key = ?
                """, (new_hash, txn_id, txn_date, self.league_key))
            else:
                # No changes
                result['unchanged'] += 1
        
        return result
    
    def process_date(self, date: str, existing_transactions: Dict) -> int:
        """Process transactions for a specific date."""
        # Determine if we should check for updates
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_old = (datetime.now() - date_obj).days
        check_updates = days_old <= TRANSACTION_REFRESH_WINDOW
        
        if check_updates:
            print(f"\nProcessing transactions for {date} (checking for updates)...")
        else:
            print(f"\nProcessing transactions for {date} (archive data, skipping)...")
            return 0
        
        # Fetch current transactions from Yahoo API
        current_transactions = self.fetch_transactions_for_date(date)
        
        if not current_transactions:
            print(f"  No transactions found for {date}")
            return 0
        
        processed = 0
        for transaction in current_transactions:
            result = self.process_transaction(transaction, existing_transactions)
            
            self.stats['new'] += result['new']
            self.stats['updated'] += result['updated']
            self.stats['unchanged'] += result['unchanged']
            self.stats['duplicates'] += result['duplicate']
            self.stats['checked'] += 1
            processed += 1
        
        self.conn.commit()
        return processed
    
    def run(self, start_date: str = None, end_date: str = None):
        """
        Run incremental update for transactions.
        
        Args:
            start_date: Start date (default: 2 days ago)
            end_date: End date (default: today)
        """
        # Default date range
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            # Go back to refresh window
            start_date = (datetime.now() - timedelta(days=TRANSACTION_REFRESH_WINDOW)).strftime('%Y-%m-%d')
        
        print("\n" + "="*60)
        print("TRANSACTION INCREMENTAL UPDATE")
        print("="*60)
        print(f"Date range: {start_date} to {end_date}")
        print(f"League: {self.league_key}")
        print(f"Environment: {self.environment}")
        print(f"Refresh window: {TRANSACTION_REFRESH_WINDOW} days")
        
        # Start job logging
        self.start_job_log(start_date, end_date)
        print(f"Job ID: {self.job_id}")
        
        try:
            # Get existing transactions
            print("\nLoading existing transactions...")
            existing_transactions = self.get_existing_transactions(start_date, end_date)
            print(f"Found {len(existing_transactions)} existing transactions")
            
            # Process each date
            current = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                self.process_date(date_str, existing_transactions)
                current += timedelta(days=1)
                
                # Rate limiting
                time.sleep(0.1)
            
            # Update job status
            self.update_job_log('completed')
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            print(f"Transactions checked: {self.stats['checked']}")
            print(f"New transactions: {self.stats['new']}")
            print(f"Updated transactions: {self.stats['updated']}")
            print(f"Unchanged transactions: {self.stats['unchanged']}")
            print(f"Duplicate transactions: {self.stats['duplicates']}")
            print(f"Errors: {self.stats['errors']}")
            print("="*60)
            
        except Exception as e:
            print(f"\n[ERROR] Update failed: {e}")
            import traceback
            traceback.print_exc()
            self.update_job_log('failed', str(e))
            raise
        finally:
            self.conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Incremental update for transactions")
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--league-key', default='mlb.l.6966',
                       help='Yahoo league key')
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'],
                       help='Environment to run in')
    
    args = parser.parse_args()
    
    # Run the updater
    updater = TransactionIncrementalUpdater(
        league_key=args.league_key,
        environment=args.environment
    )
    updater.run(args.start_date, args.end_date)


if __name__ == "__main__":
    main()