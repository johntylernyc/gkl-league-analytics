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
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import config

# === CONFIG ===
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI
TOKEN_URL = config.TOKEN_URL
BASE_FANTASY_URL = config.BASE_FANTASY_URL

script_dir = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_FILE = os.path.join(script_dir, "resume_transactions.json")
log_file_path = os.path.join(script_dir, 'fetch_transactions.log')
DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')

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

SEASON_DATES = {
    2025: ("2025-03-27", "2025-09-28")
   #  2024: "431.l.41728",
   #  2023: "422.l.54537",
   #  2022: "412.l.34665",
   #  2021: "404.l.54012",
   #  2020: "398.l.35682",
   #  2019: "388.l.34240",
   #  2018: "378.l.19344",
   #  2017: "370.l.36931",
   #  2016: "357.l.62816",
   #  2015: "346.l.48624",
   #  2014: "328.l.36901",
   #  2013: "308.l.43210",
   #  2012: "268.l.24275",
   #  2011: "253.l.58530",
   #  2010: "238.l.174722",
   #  2009: "215.l.75484",
   #  2008: "195.l.181050",
}

LEAGUE_KEYS = {
    2025: "mlb.l.6966"
}

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

# === DATABASE OPERATIONS ===
def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
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
    
    # Check existing columns in test table
    cursor.execute("PRAGMA table_info(transactions_test)")
    test_columns = [column[1] for column in cursor.fetchall()]
    
    # Create test transactions table with new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions_test (
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
    
    # Add required columns to existing test table if they don't exist
    required_columns = [
        ('player_position', 'TEXT'),
        ('destination_team_key', 'TEXT'),
        ('destination_team_name', 'TEXT'), 
        ('source_team_key', 'TEXT'),
        ('source_team_name', 'TEXT'),
        ('job_id', 'TEXT')
    ]
    
    for col_name, col_type in required_columns:
        if col_name not in test_columns:
            cursor.execute(f'ALTER TABLE transactions_test ADD COLUMN {col_name} {col_type}')
            print(f"Added column {col_name} to transactions_test")
    
    # Check existing columns in production table
    cursor.execute("PRAGMA table_info(transactions_production)")
    prod_columns = [column[1] for column in cursor.fetchall()]
    
    # Create production transactions table with new schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions_production (
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
    
    # Add required columns to existing production table if they don't exist
    for col_name, col_type in required_columns:
        if col_name not in prod_columns:
            cursor.execute(f'ALTER TABLE transactions_production ADD COLUMN {col_name} {col_type}')
            print(f"Added column {col_name} to transactions_production")
    
    # Create indexes for job log
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_type ON job_log(job_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_environment ON job_log(environment)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_status ON job_log(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_log_start_time ON job_log(start_time)')
    
    # Note: fantasy_teams indexes removed - no longer using lookup table
    
    # Create indexes for test table
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_date ON transactions_test(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_league ON transactions_test(league_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_player ON transactions_test(player_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_dest_team ON transactions_test(destination_team_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_source_team ON transactions_test(source_team_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_job ON transactions_test(job_id)')
    
    # Create indexes for production table
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_date ON transactions_production(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_league ON transactions_production(league_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_player ON transactions_production(player_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_dest_team ON transactions_production(destination_team_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_source_team ON transactions_production(source_team_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_job ON transactions_production(job_id)')
    
    conn.commit()
    conn.close()

# === JOB LOGGING FUNCTIONS ===
def start_job_log(job_type, environment, date_range_start, date_range_end, league_key, metadata=None):
    """Start a new job log entry and return job_id"""
    import uuid
    
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

def batch_insert_transactions(transaction_list, environment='production'):
    if not transaction_list:
        return 0
    
    # Select table based on environment
    table_name = f"transactions_{environment}"
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Prepare batch insert with new simplified schema
    data_tuples = []
    for transaction in transaction_list:
        data_tuples.append((
            transaction["date"],
            transaction["league_key"],
            transaction["transaction_id"],
            transaction["transaction_type"],
            transaction["player_id"],
            transaction["player_name"],
            transaction["player_position"],
            transaction["player_team"],
            transaction["movement_type"],
            transaction["destination_team_key"],
            transaction["destination_team_name"],
            transaction["source_team_key"],
            transaction["source_team_name"],
            transaction["job_id"]
        ))
    
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
        logging.info(f"Batch inserted {inserted_count} transactions to {table_name}")
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
# Set environment: 'test' for validation, 'production' for full collection
ENVIRONMENT = 'production'  # Changed to production for full data collection

# Date configurations
TEST_DATE_RANGE = ("2025-07-25", "2025-08-01")  # 1 week for validation
PRODUCTION_DATE_RANGE = ("2025-03-27", "2025-08-02")  # Full 2025 season YTD

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print(f"Initializing optimized transaction fetcher for 2025 season ({ENVIRONMENT} mode)...")
    init_database()
    
    token_manager = TokenManager()
    token_manager.initialize()
    
    league_key = LEAGUE_KEYS[2025]
    
    # Select date range based on environment
    if ENVIRONMENT == 'test':
        start_date_str, end_date_str = TEST_DATE_RANGE
        scenario_name = "test_validation_week"
        print("Running TEST validation for 1 week of data")
    else:
        start_date_str, end_date_str = PRODUCTION_DATE_RANGE
        scenario_name = "full_season_2025_ytd"
        print("Running PRODUCTION collection for full 2025 season YTD")
    
    print("\n" + "="*60)
    print(f"COLLECTING TRANSACTION DATA: 2025 SEASON ({ENVIRONMENT.upper()})")
    print("="*60)
    print(f"Date range: {start_date_str} to {end_date_str}")
    print(f"League: {league_key}")
    print(f"Environment: {ENVIRONMENT}")
    print(f"Target table: transactions_{ENVIRONMENT}")
    
    # Run the collection with concurrent processing for better performance
    result = benchmark_scenario(scenario_name, start_date_str, end_date_str, league_key, token_manager, use_concurrency=True, environment=ENVIRONMENT)
    
    # Display results summary
    print("\n" + "="*60)
    print("COLLECTION RESULTS")
    print("="*60)
    print(f"Duration: {result['duration']:.2f} seconds ({result['duration']/60:.1f} minutes)")
    print(f"Total transactions collected: {result['transactions']:,}")
    print(f"Dates processed: {result['dates_processed']}")
    print(f"Processing rate: {result['rate']:.2f} dates/second")
    
    # Get final database stats
    table_name = f"transactions_{ENVIRONMENT}"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE date BETWEEN ? AND ?", (start_date_str, end_date_str))
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT MIN(date), MAX(date) FROM {table_name} WHERE date BETWEEN ? AND ?", (start_date_str, end_date_str))
    date_range = cursor.fetchone()
    conn.close()
    
    print(f"\nDatabase Statistics:")
    print(f"   Environment: {ENVIRONMENT}")
    print(f"   Table: {table_name}")
    print(f"   Total transactions in database for period: {total_transactions:,}")
    print(f"   Date range in database: {date_range[0]} to {date_range[1]}")
    print(f"   Database file: {DB_FILE}")
    
    # Display job summary
    print(f"\nJob Summary:")
    print(f"   Job ID: {result['job_id']}")
    
    if ENVIRONMENT == 'test':
        print(f"\nTEST VALIDATION COMPLETE!")
        print(f"Next steps:")
        print(f"1. Review test data quality and completeness")
        print(f"2. Change ENVIRONMENT to 'production' for full season collection")
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