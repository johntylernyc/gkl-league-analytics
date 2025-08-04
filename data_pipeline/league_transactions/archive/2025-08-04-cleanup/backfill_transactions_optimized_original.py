import requests
import xml.etree.ElementTree as ET
import json
import datetime
import re
import base64
import logging
import os
import sys
import time
import sqlite3
import threading
import queue
import platform
import signal
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from auth import config
from data_pipeline.config.database_config import get_database_path, get_table_name, get_environment

# Import centralized league configuration
from data_pipeline.metadata.league_keys import LEAGUE_KEYS, SEASON_DATES
from data_pipeline.common.season_manager import SeasonManager, get_league_key, get_season_dates

# === CONFIG ===
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI
TOKEN_URL = config.TOKEN_URL
BASE_FANTASY_URL = config.BASE_FANTASY_URL

script_dir = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_FILE = os.path.join(script_dir, "resume_transactions.json")
log_file_path = os.path.join(script_dir, 'fetch_transactions.log')
# DB_FILE now determined by environment
DB_FILE = None  # Will be set dynamically based on environment

logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === PERFORMANCE SETTINGS ===
DEFAULT_SLEEP_TIME = 1.0  # Reduced from 3 seconds
BATCH_SIZE = 10  # Process multiple dates before committing to DB
MAX_WORKERS = 2  # Conservative concurrent requests
DB_BATCH_SIZE = 100  # Batch database operations

# Test date ranges for benchmarking
TEST_SCENARIOS = {
    "small": ("2025-04-01", "2025-04-07"),    # 1 week
    "medium": ("2025-04-01", "2025-04-21"),   # 3 weeks
    "large": ("2025-04-01", "2025-05-01"),    # 1 month
}

# League keys and season dates now imported from centralized metadata module
# Initialize season manager for multi-season support
season_manager = SeasonManager()

# === RATE LIMITING ===
class RateLimiter:
    def __init__(self, requests_per_second=1.0):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait(self):
        with self.lock:
            now = time.time()
            time_since_last = now - self.last_request_time
            min_interval = 1.0 / self.requests_per_second
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

# Global rate limiter
rate_limiter = RateLimiter(requests_per_second=1.0)

# === TOKEN MANAGEMENT ===
class TokenManager:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.token_acquired_at = 0
        self.lock = threading.Lock()
    
    def get_access_token(self):
        with self.lock:
            if time.time() - self.token_acquired_at > 3600:  # Token expires in 1 hour
                self._refresh_tokens()
            return self.access_token
    
    def _refresh_tokens(self):
        credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'redirect_uri': REDIRECT_URI,
            'refresh_token': self.refresh_token
        }
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        tokens = response.json()
        
        self.access_token = tokens['access_token']
        self.refresh_token = tokens['refresh_token']
        self.token_acquired_at = time.time()
        
        # Save tokens to file
        tokens_path = os.path.abspath(os.path.join(script_dir, '..', 'auth', 'tokens.json'))
        with open(tokens_path, 'w') as f:
            json.dump(tokens, f, indent=4)
    
    def initialize(self):
        tokens_path = os.path.abspath(os.path.join(script_dir, '..', 'auth', 'tokens.json'))
        with open(tokens_path) as f:
            tokens = json.load(f)
            self.refresh_token = tokens['refresh_token']
        self._refresh_tokens()

# === COMPATIBILITY CHECKS ===
def check_sqlite_version():
    """Verify SQLite version meets requirements."""
    version = sqlite3.sqlite_version
    major, minor, patch = map(int, version.split('.'))
    
    if (major, minor, patch) < (3, 8, 2):
        logging.warning(f"SQLite version {version} is below recommended 3.8.2")
        return False
    return True

def check_wal_compatibility(db_path):
    """Check if database location supports WAL mode."""
    # Check if database is on network filesystem (not recommended for WAL)
    if platform.system() == 'Windows':
        # Check for network path
        if db_path.startswith(r'\\'):
            logging.warning("Database on network path - WAL mode may have issues")
            return False
    
    # Check write permissions for WAL files
    db_dir = os.path.dirname(db_path)
    test_wal = os.path.join(db_dir, '.wal_test')
    try:
        with open(test_wal, 'w') as f:
            f.write('test')
        os.remove(test_wal)
        return True
    except Exception as e:
        logging.error(f"Cannot write WAL files to {db_dir}: {e}")
        return False

# === DATABASE OPERATIONS ===
def init_database(environment=None, validate_only=False):
    """
    Initialize database with optional optimizations based on feature flags.
    
    Args:
        environment: Database environment (test/production)
        validate_only: If True, only validate without applying changes
    """
    global DB_FILE
    env = get_environment(environment)
    DB_FILE = str(get_database_path(env))
    
    # Import feature flags
    try:
        from database.feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
    except ImportError:
        logging.info("Feature flags module not found, using default settings")
        feature_flags = None
    
    # Validation phase
    if not check_sqlite_version():
        logging.warning("SQLite version check failed")
    
    if validate_only:
        print("Validation mode - checking compatibility...")
        wal_compatible = check_wal_compatibility(DB_FILE)
        print(f"WAL compatibility: {'✅' if wal_compatible else '❌'}")
        print(f"SQLite version: {sqlite3.sqlite_version}")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Apply optimizations based on feature flags
    optimizations_applied = []
    
    if feature_flags and feature_flags.is_enabled('pragma_optimizations'):
        # Start with conservative settings
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA synchronous = NORMAL")
        optimizations_applied.append("busy_timeout=5000")
        optimizations_applied.append("synchronous=NORMAL")
        
        if feature_flags.is_enabled('aggressive_caching'):
            cursor.execute("PRAGMA cache_size = -64000")  # 64MB
            cursor.execute("PRAGMA temp_store = MEMORY")
            cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
            optimizations_applied.extend(["cache=64MB", "temp_store=MEMORY", "mmap=256MB"])
        else:
            # Conservative caching
            cursor.execute("PRAGMA cache_size = -16000")  # 16MB
            optimizations_applied.append("cache=16MB")
    
    if feature_flags and feature_flags.is_enabled('wal_mode'):
        # Only enable WAL if compatibility check passes
        if check_wal_compatibility(DB_FILE):
            result = cursor.execute("PRAGMA journal_mode = WAL").fetchone()
            if result and result[0].upper() == 'WAL':
                optimizations_applied.append("WAL mode")
                logging.info("WAL mode enabled successfully")
            else:
                logging.error(f"Failed to enable WAL mode, got: {result}")
                if feature_flags:
                    feature_flags.disable('wal_mode')  # Auto-disable on failure
        else:
            logging.warning("WAL mode skipped due to compatibility issues")
    
    # Log applied optimizations
    if optimizations_applied:
        logging.info(f"SQLite optimizations applied: {', '.join(optimizations_applied)}")
        print(f"Database optimizations: {', '.join(optimizations_applied)}")
    else:
        logging.info("Running with default SQLite settings")
        print("Running with default SQLite settings (optimizations disabled)")
    
    # Verify settings
    for pragma in ['busy_timeout', 'journal_mode', 'synchronous', 'cache_size']:
        try:
            result = cursor.execute(f"PRAGMA {pragma}").fetchone()
            logging.debug(f"PRAGMA {pragma} = {result}")
        except Exception as e:
            logging.error(f"Error reading PRAGMA {pragma}: {e}")
    
    print(f"Initializing database for environment: {env}")
    print(f"Database path: {DB_FILE}")
    
    # Create job logging table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_log (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            environment TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP NULL,
            duration_seconds REAL NULL,
            records_processed INTEGER DEFAULT 0,
            records_inserted INTEGER DEFAULT 0,
            date_range_start TEXT NULL,
            date_range_end TEXT NULL,
            league_key TEXT NULL,
            error_message TEXT NULL,
            metadata TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Note: fantasy_teams lookup table removed in favor of direct team storage in transactions
    
    # Get the appropriate table name based on environment
    table_name = get_table_name('transactions', env)
    
    # Check existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # Create transactions table with new schema
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
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
            job_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(transaction_id, player_id, movement_type)
        )
    ''')
    
    # Add required columns to existing table if they don't exist
    required_columns = [
        ('player_position', 'TEXT'),
        ('destination_team_key', 'TEXT'),
        ('destination_team_name', 'TEXT'), 
        ('source_team_key', 'TEXT'),
        ('source_team_name', 'TEXT'),
        ('job_id', 'TEXT')
    ]
    
    for col_name, col_type in required_columns:
        if col_name not in existing_columns:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}')
            print(f"Added column {col_name} to {table_name}")
    
    # Create indexes for job log
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_type ON job_log(job_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_environment ON job_log(environment)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_status ON job_log(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_start_time ON job_log(start_time)')
    
    # Note: fantasy_teams indexes removed - no longer using lookup table
    
    # Create indexes for transactions table
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON {table_name}(date)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_league ON {table_name}(league_key)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_player ON {table_name}(player_id)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_dest_team ON {table_name}(destination_team_key)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_source_team ON {table_name}(source_team_key)')
    cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_job ON {table_name}(job_id)')
    
    conn.commit()
    conn.close()

# === INCREMENTAL UPDATE FUNCTIONS ===
def get_latest_transaction_date(environment=None, league_key=None):
    """
    Get the most recent transaction date from the database.
    
    Args:
        environment: Database environment (test/production)
        league_key: League key to filter by (optional)
    
    Returns:
        str: Latest transaction date in YYYY-MM-DD format, or None if no transactions
    """
    env = get_environment(environment)
    db_path = get_database_path(env)
    table_name = get_table_name('transactions', env)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        if league_key:
            query = f"""
                SELECT MAX(date) 
                FROM {table_name} 
                WHERE league_key = ?
            """
            cursor.execute(query, (league_key,))
        else:
            query = f"SELECT MAX(date) FROM {table_name}"
            cursor.execute(query)
        
        result = cursor.fetchone()
        latest_date = result[0] if result and result[0] else None
        
        conn.close()
        
        if latest_date:
            logging.info(f"Latest transaction date in {env}: {latest_date}")
        else:
            logging.info(f"No transactions found in {env} database")
            
        return latest_date
        
    except Exception as e:
        logging.error(f"Error getting latest transaction date: {e}")
        return None

def get_date_range_for_update(environment=None, league_key=None, max_days_back=30):
    """
    Determine the date range for incremental updates.
    
    Args:
        environment: Database environment (test/production)
        league_key: League key to check
        max_days_back: Maximum days to look back from today
    
    Returns:
        tuple: (start_date, end_date) in YYYY-MM-DD format
    """
    # Get latest transaction date from database
    latest_date = get_latest_transaction_date(environment, league_key)
    
    # Calculate date range
    today = datetime.datetime.now().date()
    
    if latest_date:
        # Start from the day after latest transaction
        latest = datetime.datetime.strptime(latest_date, '%Y-%m-%d').date()
        start_date = latest + timedelta(days=1)
        
        # Don't go too far back to avoid excessive API calls
        earliest_allowed = today - timedelta(days=max_days_back)
        if start_date < earliest_allowed:
            start_date = earliest_allowed
            logging.warning(f"Limiting update range to {max_days_back} days back")
    else:
        # No existing data, start from recent period
        start_date = today - timedelta(days=max_days_back)
        logging.info("No existing transactions, starting incremental update from recent period")
    
    # End date is today
    end_date = today
    
    # Don't update if start date is after end date
    if start_date > end_date:
        logging.info("Database is already up to date")
        return None, None
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    logging.info(f"Incremental update range: {start_str} to {end_str}")
    return start_str, end_str

def run_incremental_update(environment=None, league_key=None, max_days_back=30):
    """
    Run an incremental update to collect new transactions since the last update.
    
    Args:
        environment: Database environment (test/production) 
        league_key: League key to update
        max_days_back: Maximum days to look back
    
    Returns:
        dict: Update results with counts and status
    """
    # Initialize database
    init_database(environment)
    
    # Get league key if not provided
    if not league_key:
        current_year = datetime.datetime.now().year
        league_key = get_league_key(current_year)
    
    # Determine date range for update
    start_date, end_date = get_date_range_for_update(environment, league_key, max_days_back)
    
    if not start_date or not end_date:
        return {
            'status': 'up_to_date',
            'message': 'Database is already current',
            'transactions_added': 0
        }
    
    # Start job logging
    job_id = start_job_log(
        job_type="transaction_update_incremental",
        environment=get_environment(environment),
        date_range_start=start_date,
        date_range_end=end_date,
        league_key=league_key,
        metadata=f"Incremental update, max_days_back={max_days_back}"
    )
    
    try:
        # Initialize token manager
        token_manager = TokenManager()
        
        # Collect transactions for date range
        all_transactions = []
        current_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')
            logging.info(f"Fetching incremental data for {date_str}")
            
            try:
                xml_data = fetch_transactions_for_date(token_manager, league_key, date_str, job_id)
                
                if xml_data:
                    # Parse transactions for this date
                    date_transactions = parse_transaction_xml(xml_data, date_str, league_key, job_id)
                    all_transactions.extend(date_transactions)
                    logging.info(f"Found {len(date_transactions)} transactions for {date_str}")
                
                # Rate limiting
                sleep(DEFAULT_SLEEP_TIME)
                
            except Exception as e:
                logging.error(f"Error fetching data for {date_str}: {e}")
                # Continue with next date
            
            current_date += timedelta(days=1)
        
        # Insert all transactions
        if all_transactions:
            inserted_count = batch_insert_transactions(all_transactions, environment)
            logging.info(f"Incremental update inserted {inserted_count} new transactions")
            
            update_job_log(job_id, 'completed', 
                         records_processed=len(all_transactions),
                         records_inserted=inserted_count)
            
            return {
                'status': 'success',
                'message': f'Added {inserted_count} new transactions',
                'transactions_added': inserted_count,
                'date_range': f'{start_date} to {end_date}'
            }
        else:
            logging.info("No new transactions found in incremental update")
            update_job_log(job_id, 'completed', records_processed=0, records_inserted=0)
            
            return {
                'status': 'no_new_data',
                'message': 'No new transactions found',
                'transactions_added': 0,
                'date_range': f'{start_date} to {end_date}'
            }
            
    except Exception as e:
        error_msg = f"Incremental update failed: {e}"
        logging.error(error_msg)
        update_job_log(job_id, 'failed', error_message=error_msg)
        
        return {
            'status': 'error',
            'message': error_msg,
            'transactions_added': 0
        }

def parse_transaction_xml(xml_data, date_str, league_key, job_id):
    """
    Parse transaction XML data into structured records.
    
    Args:
        xml_data: Raw XML response from Yahoo API
        date_str: Date string in YYYY-MM-DD format
        league_key: League identifier
        job_id: Job ID for tracking
    
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    try:
        root = ET.fromstring(xml_data)
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        transaction_elements = root.findall('.//fantasy:transaction', ns)
        
        for trans_elem in transaction_elements:
            trans_id = trans_elem.find('.//fantasy:transaction_id', ns)
            trans_type = trans_elem.find('.//fantasy:type', ns)
            timestamp_elem = trans_elem.find('.//fantasy:timestamp', ns)
            
            # Get timestamp
            timestamp = None
            if timestamp_elem is not None:
                try:
                    timestamp = datetime.datetime.fromtimestamp(int(timestamp_elem.text))
                except:
                    timestamp = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            else:
                timestamp = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            
            # Process players
            players = trans_elem.findall('.//fantasy:player', ns)
            
            for player in players:
                player_id_elem = player.find('.//fantasy:player_id', ns)
                player_name_elem = player.find('.//fantasy:full', ns)
                player_team_elem = player.find('.//fantasy:editorial_team_abbr', ns)
                player_pos_elem = player.find('.//fantasy:display_position', ns)
                
                # Get transaction data
                trans_data = player.find('.//fantasy:transaction_data', ns)
                
                if trans_data is not None:
                    move_type_elem = trans_data.find('.//fantasy:type', ns)
                    source_team_elem = trans_data.find('.//fantasy:source_team_name', ns)
                    dest_team_elem = trans_data.find('.//fantasy:destination_team_name', ns)
                    source_team_key_elem = trans_data.find('.//fantasy:source_team_key', ns)
                    dest_team_key_elem = trans_data.find('.//fantasy:destination_team_key', ns)
                    
                    transaction = {
                        'date': date_str,
                        'league_key': league_key,
                        'transaction_id': trans_id.text if trans_id is not None else '',
                        'transaction_type': trans_type.text if trans_type is not None else '',
                        'player_id': player_id_elem.text if player_id_elem is not None else '',
                        'player_name': player_name_elem.text if player_name_elem is not None else '',
                        'player_position': player_pos_elem.text if player_pos_elem is not None else '',
                        'player_team': player_team_elem.text if player_team_elem is not None else '',
                        'movement_type': move_type_elem.text if move_type_elem is not None else '',
                        'destination_team_key': dest_team_key_elem.text if dest_team_key_elem is not None else '',
                        'destination_team_name': dest_team_elem.text if dest_team_elem is not None else '',
                        'source_team_key': source_team_key_elem.text if source_team_key_elem is not None else '',
                        'source_team_name': source_team_elem.text if source_team_elem is not None else '',
                        'job_id': job_id
                    }
                    
                    transactions.append(transaction)
    
    except Exception as e:
        logging.error(f"Error parsing transaction XML: {e}")
        raise
    
    return transactions

# === JOB LOGGING FUNCTIONS ===
def start_job_log(job_type, environment, date_range_start, date_range_end, league_key, metadata=None):
    """Start a new job log entry and return job_id"""
    import uuid
    
    # Ensure DB_FILE is set for the environment
    global DB_FILE
    if DB_FILE is None:
        DB_FILE = str(get_database_path(environment))
    
    job_id = f"{job_type}_{environment}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO job_log 
        (job_id, job_type, environment, status, date_range_start, date_range_end, league_key, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, job_type, environment, 'running', date_range_start, date_range_end, league_key, metadata))
    
    conn.commit()
    conn.close()
    
    logging.info(f"Started job: {job_id}")
    return job_id

def update_job_log(job_id, status, records_processed=None, records_inserted=None, error_message=None):
    """Update job log with progress or completion"""
    # Ensure DB_FILE is set
    if DB_FILE is None:
        raise RuntimeError("DB_FILE not initialized. Call init_database() first.")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Build update query dynamically based on provided parameters
    updates = ["status = ?"]
    params = [status]
    
    if status in ['completed', 'failed']:
        updates.append("end_time = CURRENT_TIMESTAMP")
        updates.append("duration_seconds = (julianday(CURRENT_TIMESTAMP) - julianday(start_time)) * 86400")
    
    if records_processed is not None:
        updates.append("records_processed = ?")
        params.append(records_processed)
    
    if records_inserted is not None:
        updates.append("records_inserted = ?")
        params.append(records_inserted)
    
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    
    params.append(job_id)
    
    cursor.execute(f'''
        UPDATE job_log 
        SET {", ".join(updates)}
        WHERE job_id = ?
    ''', params)
    
    conn.commit()
    conn.close()
    
    logging.info(f"Updated job {job_id}: {status}")

def get_job_summary():
    """Get summary of recent jobs for reporting"""
    # Ensure DB_FILE is set
    if DB_FILE is None:
        raise RuntimeError("DB_FILE not initialized. Call init_database() first.")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT job_id, job_type, environment, status, start_time, duration_seconds, 
               records_processed, records_inserted, date_range_start, date_range_end
        FROM job_log 
        ORDER BY start_time DESC 
        LIMIT 10
    ''')
    
    jobs = cursor.fetchall()
    conn.close()
    
    return jobs

    # Note: batch_insert_fantasy_teams function removed - no longer using lookup table approach

def batch_insert_transactions(transaction_list, environment=None, use_new_system=None):
    """
    Insert transactions in batch with optional new transaction management.
    
    Args:
        transaction_list: List of transactions to insert
        environment: Database environment
        use_new_system: Override feature flag (for testing)
    """
    if not transaction_list:
        return 0
    
    # Get environment and table name
    env = get_environment(environment)
    table_name = get_table_name('transactions', env)
    
    # Import feature flags and db_utils if available
    try:
        from database.feature_flags import get_feature_flags
        from database.db_utils import DatabaseConnection, transaction, retry_on_lock
        feature_flags = get_feature_flags()
        has_new_features = True
    except ImportError:
        has_new_features = False
        feature_flags = None
    
    # Determine which system to use
    use_new = use_new_system if use_new_system is not None else \
              (has_new_features and feature_flags and \
               (feature_flags.is_enabled('explicit_transactions') or \
                feature_flags.is_enabled('retry_logic')))
    
    # Prepare batch insert data
    data_tuples = []
    for trans in transaction_list:
        data_tuples.append((
            trans["date"],
            trans["league_key"],
            trans["transaction_id"],
            trans["transaction_type"],
            trans["player_id"],
            trans["player_name"],
            trans["player_position"],
            trans["player_team"],
            trans["movement_type"],
            trans["destination_team_key"],
            trans["destination_team_name"],
            trans["source_team_key"],
            trans["source_team_name"],
            trans["job_id"]
        ))
    
    if use_new and has_new_features:
        # New system with enhanced features
        @retry_on_lock(max_attempts=5, initial_delay=0.1, operation_name=f"batch_insert_{table_name}")
        def insert_with_new_system():
            with DatabaseConnection(DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Use explicit transaction for batch insert
                with transaction(conn, timeout_override=10.0):  # Longer timeout for batch
                    cursor.executemany(f'''
                        INSERT OR IGNORE INTO {table_name} 
                        (date, league_key, transaction_id, transaction_type, player_id, 
                         player_name, player_position, player_team, movement_type,
                         destination_team_key, destination_team_name, source_team_key, 
                         source_team_name, job_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data_tuples)
                    
                    inserted_count = cursor.rowcount
                    logging.info(f"Batch inserted {inserted_count} transactions (new system)")
                    return inserted_count
        
        try:
            return insert_with_new_system()
        except Exception as e:
            logging.error(f"New system failed: {e}, falling back to legacy system")
            # Fall through to old system
    
    # Legacy system (current implementation) - kept for compatibility
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.executemany(f'''
            INSERT OR IGNORE INTO {table_name} 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, source_team_name, job_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_tuples)
        
        inserted_count = cursor.rowcount
        conn.commit()
        logging.info(f"Batch inserted {inserted_count} transactions (legacy system)")
        return inserted_count
    except sqlite3.Error as e:
        logging.error(f"Error batch inserting transactions to {table_name}: {e}")
        return 0
    finally:
        conn.close()

# === API OPERATIONS ===
def fetch_transactions_for_date(token_manager, league_key, date_str, job_id=None):
    rate_limiter.wait()  # Rate limiting
    
    access_token = token_manager.get_access_token()
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/xml"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 404:
            return date_str, []
        response.raise_for_status()
        
        xml_text = re.sub(' xmlns=\"[^\"]+\"', '', response.text, count=1)
        root = ET.fromstring(xml_text)
        transactions = []
        
        for txn in root.findall(".//transaction"):
            txn_id = txn.findtext("transaction_id")
            txn_type = txn.findtext("type")
            
            # Extract transaction timestamp and convert to date
            timestamp_str = txn.findtext("timestamp")
            if timestamp_str:
                # Convert Unix timestamp to date string (YYYY-MM-DD)
                timestamp = int(timestamp_str)
                transaction_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            else:
                # Fallback to requested date if timestamp not available
                transaction_date = date_str
            
            players = txn.findall("players/player")
            
            for player in players:
                name = player.findtext("name/full")
                player_id = player.findtext("player_id")
                player_position = player.findtext("display_position")
                player_team = player.findtext("editorial_team_abbr")
                transaction_data = player.find("transaction_data")
                movement_type = transaction_data.findtext("type")
                
                # Extract team information directly
                destination_team_key = None
                destination_team_name = None
                source_team_key = None
                source_team_name = None
                
                if transaction_data is not None:
                    destination_team_key = transaction_data.findtext("destination_team_key")
                    destination_team_name = transaction_data.findtext("destination_team_name")
                    source_team_key = transaction_data.findtext("source_team_key")
                    source_team_name = transaction_data.findtext("source_team_name")
                
                transactions.append({
                    "date": transaction_date,
                    "league_key": league_key,
                    "transaction_id": txn_id,
                    "transaction_type": txn_type,
                    "player_id": player_id,
                    "player_name": name,
                    "player_position": player_position,
                    "player_team": player_team,
                    "movement_type": movement_type,
                    "destination_team_key": destination_team_key,
                    "destination_team_name": destination_team_name,
                    "source_team_key": source_team_key,
                    "source_team_name": source_team_name,
                    "job_id": job_id
                })
        
        return date_str, transactions
    
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for {date_str}: {e}")
        return date_str, []

# === BENCHMARKING ===
def benchmark_scenario(scenario_name, start_date_str, end_date_str, league_key, token_manager, use_concurrency=False, environment='production'):
    print(f"\nBenchmarking {scenario_name} scenario ({start_date_str} to {end_date_str})")
    
    # Start job logging
    metadata = f"scenario={scenario_name}, concurrency={use_concurrency}, workers={MAX_WORKERS if use_concurrency else 1}"
    job_id = start_job_log("transaction_collection", environment, start_date_str, end_date_str, league_key, metadata)
    
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date.isoformat())
            current_date += datetime.timedelta(days=1)
        
        start_time = time.time()
        all_transactions = []
        
        if use_concurrency:
            print(f"  Using {MAX_WORKERS} concurrent workers")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_date = {
                    executor.submit(fetch_transactions_for_date, token_manager, league_key, date_str, job_id): date_str 
                    for date_str in dates
                }
                
                for future in as_completed(future_to_date):
                    date_str, transactions = future.result()
                    if transactions:
                        all_transactions.extend(transactions)
                        print(f"  + {date_str}: {len(transactions)} transactions")
                    else:
                        print(f"  - {date_str}: no transactions")
        else:
            print("  Using sequential processing")
            for date_str in dates:
                date_str, transactions = fetch_transactions_for_date(token_manager, league_key, date_str, job_id)
                if transactions:
                    all_transactions.extend(transactions)
                    print(f"  + {date_str}: {len(transactions)} transactions")
                else:
                    print(f"  - {date_str}: no transactions")
    
        # Batch insert all transactions
        inserted_count = 0
        if all_transactions:
            inserted_count = batch_insert_transactions(all_transactions, environment)
            print(f"  Inserted {inserted_count} transactions to database ({environment} environment)")
            
            # Count unique teams for reporting
            unique_dest_teams = set()
            unique_source_teams = set()
            for txn in all_transactions:
                if txn.get("destination_team_key"):
                    unique_dest_teams.add(txn["destination_team_key"])
                if txn.get("source_team_key"):
                    unique_source_teams.add(txn["source_team_key"])
            
            all_unique_teams = unique_dest_teams | unique_source_teams
            if all_unique_teams:
                print(f"  Found {len(all_unique_teams)} unique fantasy teams")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Total transactions: {len(all_transactions)}")
        print(f"  Rate: {len(dates)/duration:.2f} dates/second")
        
        # Update job log with success
        update_job_log(job_id, 'completed', records_processed=len(all_transactions), records_inserted=inserted_count)
        
        return {
            'scenario': scenario_name,
            'duration': duration,
            'transactions': len(all_transactions),
            'dates_processed': len(dates),
            'rate': len(dates)/duration,
            'use_concurrency': use_concurrency,
            'job_id': job_id
        }
    
    except Exception as e:
        # Update job log with failure
        error_msg = f"Error in benchmark_scenario: {str(e)}"
        update_job_log(job_id, 'failed', error_message=error_msg)
        logging.error(error_msg)
        raise

# === CONFIGURATION ===
# Environment determined by DATA_ENV environment variable or command line
# Date configurations
TEST_DATE_RANGE = ("2025-07-25", "2025-08-01")  # 1 week for validation
PRODUCTION_DATE_RANGE = ("2025-03-27", "2025-08-02")  # Full 2025 season YTD

# === CONNECTION CLEANUP ===
def cleanup_database_connections():
    """Cleanup function to ensure all database connections are closed safely."""
    global DB_FILE
    if not DB_FILE:
        return
    
    try:
        from database.feature_flags import get_feature_flags
        feature_flags = get_feature_flags()
    except ImportError:
        feature_flags = None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Only checkpoint if WAL mode is enabled
        if feature_flags and feature_flags.is_enabled('wal_mode'):
            # Check if actually in WAL mode
            mode = conn.execute("PRAGMA journal_mode").fetchone()
            if mode and mode[0].upper() == 'WAL':
                # Checkpoint but don't truncate (safer)
                result = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                logging.info(f"WAL checkpoint completed: {result}")
        
        # Close any remaining connections
        conn.close()
        logging.info("Database connections cleaned up")
        
    except Exception as e:
        # Don't let cleanup errors crash the program
        logging.error(f"Non-critical error during database cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, cleaning up...")
    cleanup_database_connections()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_database_connections)
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

# === MAIN EXECUTION ===
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill transaction data with multi-season support')
    parser.add_argument('--environment', choices=['test', 'production'], 
                       help='Environment to use (overrides DATA_ENV)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate database compatibility without making changes')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    # Multi-season support arguments
    parser.add_argument('--season', type=int, help='Specific season year (e.g., 2023)')
    parser.add_argument('--seasons', help='Season range (e.g., "2020-2023")')
    parser.add_argument('--all-seasons', action='store_true', help='Process all available seasons')
    parser.add_argument('--profile', choices=['recent', 'historical', 'full', 'current'],
                       help='Use a predefined collection profile')
    args = parser.parse_args()
    
    # Check for validation mode
    if args.validate:
        print("Running database validation...")
        init_database(validate_only=True)
        return
    
    # Determine environment
    environment = args.environment or get_environment()
    
    # Determine which seasons to process
    if args.all_seasons:
        seasons_to_process = season_manager.get_available_seasons()
        print(f"Processing ALL available seasons: {seasons_to_process}")
    elif args.seasons:
        # Parse season range (e.g., "2020-2023")
        if '-' in args.seasons:
            start_year, end_year = map(int, args.seasons.split('-'))
            seasons_to_process = season_manager.get_seasons_in_range(start_year, end_year)
        else:
            # Single season as string
            seasons_to_process = [int(args.seasons)]
        print(f"Processing seasons: {seasons_to_process}")
    elif args.season:
        seasons_to_process = [args.season]
        print(f"Processing season: {args.season}")
    elif args.profile:
        from common.season_manager import get_profile_seasons
        seasons_to_process = get_profile_seasons(args.profile, season_manager)
        print(f"Processing {args.profile} profile seasons: {seasons_to_process}")
    else:
        # Default to current season or 2025
        current = season_manager.get_current_season()
        seasons_to_process = [current if current else 2025]
        print(f"Processing default season: {seasons_to_process[0]}")
    
    # Validate seasons
    for season in seasons_to_process:
        if not season_manager.validate_season(season):
            print(f"ERROR: No configuration found for season {season}")
            return
    
    print(f"Initializing optimized transaction fetcher ({environment} mode)...")
    init_database(environment)
    
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Process each season
    total_transactions = 0
    all_results = []
    
    for season in seasons_to_process:
        league_key = get_league_key(season)
        season_dates = get_season_dates(season)
        
        # Select date range based on environment or args
        if args.start_date and args.end_date:
            # Custom date range overrides season dates
            start_date_str = args.start_date
            end_date_str = args.end_date
            scenario_name = f"custom_range_{season}"
        else:
            # Use season dates
            start_date_str, end_date_str = season_dates
            if environment == 'test':
                # For test mode, limit to first week of season
                from datetime import datetime, timedelta
                start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_dt = start_dt + timedelta(days=7)
                end_date_str = min(end_dt.strftime("%Y-%m-%d"), season_dates[1])
                scenario_name = f"test_week_{season}"
                print(f"TEST mode: Limiting {season} to first week")
            else:
                scenario_name = f"full_season_{season}"
    
        print("\n" + "="*60)
        print(f"COLLECTING TRANSACTION DATA: {season} SEASON ({environment.upper()})")
        print("="*60)
        print(f"Date range: {start_date_str} to {end_date_str}")
        print(f"League: {league_key}")
        print(f"Environment: {environment}")
        print(f"Target table: {get_table_name('transactions', environment)}")
        
        # Run the collection with concurrent processing for better performance
        result = benchmark_scenario(scenario_name, start_date_str, end_date_str, league_key, token_manager, use_concurrency=True, environment=environment)
        
        # Store result for summary
        all_results.append({
            'season': season,
            'result': result,
            'start_date': start_date_str,
            'end_date': end_date_str,
            'league_key': league_key
        })
        
        # Display results summary for this season
        print("\n" + "="*60)
        print(f"SEASON {season} RESULTS")
        print("="*60)
        print(f"Duration: {result['duration']:.2f} seconds ({result['duration']/60:.1f} minutes)")
        print(f"Total transactions collected: {result['transactions']:,}")
        print(f"Dates processed: {result['dates_processed']}")
        print(f"Processing rate: {result['rate']:.2f} dates/second")
        
        total_transactions += result['transactions']
    
    # Display overall summary if multiple seasons
    if len(seasons_to_process) > 1:
        print("\n" + "="*60)
        print("MULTI-SEASON COLLECTION SUMMARY")
        print("="*60)
        print(f"Seasons processed: {seasons_to_process}")
        print(f"Total transactions collected: {total_transactions:,}")
        
        total_duration = sum(r['result']['duration'] for r in all_results)
        print(f"Total duration: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
        
        for season_data in all_results:
            print(f"\n{season_data['season']}:")
            print(f"   League: {season_data['league_key']}")
            print(f"   Dates: {season_data['start_date']} to {season_data['end_date']}")
            print(f"   Transactions: {season_data['result']['transactions']:,}")
            print(f"   Job ID: {season_data['result']['job_id']}")
    
    # Get final database stats
    table_name = get_table_name('transactions', environment)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get overall database statistics
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_db_transactions = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT MIN(date), MAX(date) FROM {table_name}")
    overall_date_range = cursor.fetchone()
    
    # Get per-season counts if applicable
    if 'season' in [col[1] for col in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()]:
        cursor.execute(f"SELECT season, COUNT(*) FROM {table_name} GROUP BY season ORDER BY season")
        season_counts = cursor.fetchall()
    else:
        season_counts = []
    
    conn.close()
    
    print(f"\n" + "="*60)
    print("DATABASE STATISTICS")
    print("="*60)
    print(f"Environment: {environment}")
    print(f"Table: {table_name}")
    print(f"Total transactions in database: {total_db_transactions:,}")
    if overall_date_range[0] and overall_date_range[1]:
        print(f"Date range in database: {overall_date_range[0]} to {overall_date_range[1]}")
    print(f"Database file: {DB_FILE}")
    
    if season_counts:
        print(f"\nTransactions by season:")
        for season, count in season_counts:
            print(f"   {season}: {count:,}")
    
    if environment == 'test':
        print(f"\nTEST VALIDATION COMPLETE!")
        print(f"Next steps:")
        print(f"1. Review test data quality and completeness")
        print(f"2. Set DATA_ENV=production or use --environment production for full season collection")
    else:
        print(f"\nPRODUCTION DATA COLLECTION COMPLETE!")
    
    # Show recent job history
    print(f"\n" + "="*60)
    print("RECENT JOB HISTORY")
    print("="*60)
    
    recent_jobs = get_job_summary()
    if recent_jobs:
        print(f"{'Job Type':<20} {'Environment':<12} {'Status':<10} {'Start Time':<20} {'Duration':<10} {'Records':<10}")
        print("-" * 90)
        for job in recent_jobs:
            job_id, job_type, env, status, start_time, duration, processed, inserted, date_start, date_end = job
            duration_str = f"{duration:.1f}s" if duration else "N/A"
            print(f"{job_type:<20} {env:<12} {status:<10} {start_time:<20} {duration_str:<10} {inserted or 0:<10}")
    
    print("\nData collection complete!")