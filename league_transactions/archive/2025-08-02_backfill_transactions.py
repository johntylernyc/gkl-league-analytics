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
API_SLEEP_TIME = 1.5  # Reduced from 3.0 seconds - more aggressive but still safe
DB_BATCH_SIZE = 50   # Batch database operations for better performance

SEASON_DATES = {
    2025: ("2025-03-27", "2025-09-28")
   #  2024: ("2024-03-28", "2024-09-29"),
   #  2023: ("2023-03-30", "2023-10-01"),
   #  2022: ("2022-04-07", "2022-10-05"),
   #  2021: ("2021-04-01", "2021-10-03"),
   #  2020: ("2020-07-23", "2020-09-27"),
   #  2019: ("2019-03-28", "2019-09-29"),
   #  2018: ("2018-03-29", "2018-09-30"),
   #  2017: ("2017-04-02", "2017-10-01"),
   #  2016: ("2016-04-03", "2016-10-02"),
   #  2015: ("2015-04-05", "2015-10-04"),
   #  2014: ("2014-03-30", "2014-09-28"),
   #  2013: ("2013-03-31", "2013-09-29"),
   #  2012: ("2012-03-28", "2012-10-03"),
   #  2011: ("2011-03-31", "2011-09-28"),
   #  2010: ("2010-04-04", "2010-10-03"),
   #  2009: ("2009-04-05", "2009-10-04"),
   #  2008: ("2008-03-25", "2008-09-28"),
}

LEAGUE_KEYS = {
    2025: "mlb.l.6966"
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

# === HELPERS ===
def get_access_token(refresh_token):
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'redirect_uri': REDIRECT_URI,
        'refresh_token': refresh_token
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    tokens = response.json()
    with open(os.path.join(script_dir, '..', 'auth', 'tokens.json'), 'w') as f:
        json.dump(tokens, f, indent=4)
    return tokens['access_token'], tokens['refresh_token']

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_checkpoint(season, date):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"season": season, "date": date.isoformat()}, f)

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            league_key TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            position TEXT,
            player_team TEXT,
            movement_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(transaction_id, player_id, movement_type)
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transactions_league ON transactions(league_key)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_transactions_player ON transactions(player_id)
    ''')
    
    conn.commit()
    conn.close()

def insert_transactions(transactions):
    if not transactions:
        return 0
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Prepare data for batch insert
    data_tuples = []
    for transaction in transactions:
        data_tuples.append((
            transaction["date"],
            transaction["league_key"],
            transaction["transaction_id"],
            transaction["transaction_type"],
            transaction["player_id"],
            transaction["player_name"],
            transaction["position"],
            transaction["player_team"],
            transaction["movement_type"]
        ))
    
    try:
        # Use executemany for batch insert - much faster than individual inserts
        cursor.executemany('''
            INSERT OR IGNORE INTO transactions 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, position, player_team, movement_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_tuples)
        
        inserted_count = cursor.rowcount
        conn.commit()
        logging.info(f"Batch inserted {inserted_count} transactions")
        return inserted_count
    except sqlite3.Error as e:
        logging.error(f"Error batch inserting transactions: {e}")
        return 0
    finally:
        conn.close()

def get_latest_transaction_date(league_key):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT MAX(date) FROM transactions WHERE league_key = ?
    ''', (league_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        return datetime.datetime.strptime(result[0], "%Y-%m-%d").date()
    return None

def get_transaction_stats():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            league_key,
            COUNT(*) as total_transactions,
            MIN(date) as earliest_date,
            MAX(date) as latest_date
        FROM transactions 
        GROUP BY league_key
        ORDER BY league_key
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def calculate_performance_estimate(start_date, end_date):
    """Calculate estimated performance improvement"""
    date_range = (end_date - start_date).days + 1
    
    # Original performance: 3 seconds per request
    original_time = date_range * 3.0
    
    # Optimized performance: 1.5 seconds per request
    optimized_time = date_range * API_SLEEP_TIME
    
    improvement_factor = original_time / optimized_time
    time_saved = original_time - optimized_time
    
    return {
        'date_range_days': date_range,
        'original_time_seconds': original_time,
        'optimized_time_seconds': optimized_time,
        'improvement_factor': improvement_factor,
        'time_saved_seconds': time_saved,
        'time_saved_minutes': time_saved / 60
    }

def fetch_transactions(access_token, league_key, date):
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/xml"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    xml_text = re.sub(' xmlns=\"[^\"]+\"', '', response.text, count=1)
    root = ET.fromstring(xml_text)
    transactions = []
    for txn in root.findall(".//transaction"):
        txn_id = txn.findtext("transaction_id")
        txn_type = txn.findtext("type")
        players = txn.findall("players/player")
        for player in players:
            name = player.findtext("name/full")
            player_id = player.findtext("player_id")
            pos = player.findtext("position")
            team = player.findtext("editorial_team_abbr")
            transaction_data = player.find("transaction_data")
            type_movement = transaction_data.findtext("type")
            transactions.append({
                "date": date,
                "league_key": league_key,
                "transaction_id": txn_id,
                "transaction_type": txn_type,
                "player_id": player_id,
                "player_name": name,
                "position": pos,
                "player_team": team,
                "movement_type": type_movement
            })
    return transactions

# === DATE OVERRIDES FOR TESTING ===
DATE_OVERRIDE_START = None  # e.g., "2024-04-01"
DATE_OVERRIDE_END = None    # e.g., "2024-04-07"

# === MAIN ===
if __name__ == "__main__":  
    print("🚀 Initializing optimized database...")
    print(f"⚡ Performance settings: {API_SLEEP_TIME}s delay, {DB_BATCH_SIZE} batch size")
    init_database()
    logging.info("Database initialized")
    
    tokens_path = os.path.abspath(os.path.join(script_dir, '..', 'auth', 'tokens.json'))
    with open(tokens_path) as f:
        tokens = json.load(f)
        refresh_token = tokens['refresh_token']

    access_token, refresh_token = get_access_token(refresh_token)
    token_acquired_at = time.time()
    checkpoint = load_checkpoint()
    
    total_start_time = time.time()

    for season in sorted(SEASON_DATES.keys(), reverse=True):
        if season not in LEAGUE_KEYS:
            continue
        start_str, end_str = SEASON_DATES[season]
        start_date = datetime.datetime.strptime(DATE_OVERRIDE_START, "%Y-%m-%d").date() if DATE_OVERRIDE_START else datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(DATE_OVERRIDE_END, "%Y-%m-%d").date() if DATE_OVERRIDE_END else datetime.datetime.strptime(end_str, "%Y-%m-%d").date()

        league_key = LEAGUE_KEYS[season]
        current_date = start_date
        
        # Check database for latest data to resume from
        latest_db_date = get_latest_transaction_date(league_key)
        if latest_db_date and latest_db_date >= current_date:
            current_date = latest_db_date + datetime.timedelta(days=1)
            print(f"Resuming from database: {current_date} for season {season}")
        elif str(season) == str(checkpoint.get("season")) and checkpoint.get("date"):
            checkpoint_date = datetime.datetime.strptime(checkpoint["date"], "%Y-%m-%d").date()
            if checkpoint_date > current_date:
                current_date = checkpoint_date
                print(f"Resuming from checkpoint: {current_date} for season {season}")

        # Batch processing for better performance
        batch_transactions = []
        batch_start_date = current_date
        
        while current_date <= end_date:
            print(f"Processing {season} - {current_date}")
            
            # Check for token refresh
            if time.time() - token_acquired_at > 3600:
                access_token, refresh_token = get_access_token(refresh_token)
                token_acquired_at = time.time()

            transactions = fetch_transactions(access_token, league_key, current_date.isoformat())

            if transactions:
                batch_transactions.extend(transactions)
                print(f"  → Found {len(transactions)} transactions")
            else:
                print(f"  → No transactions")

            # Process batch when it reaches the batch size or at the end
            if len(batch_transactions) >= DB_BATCH_SIZE or current_date == end_date:
                if batch_transactions:
                    inserted_count = insert_transactions(batch_transactions)
                    logging.info(f"Batch inserted {inserted_count} new transactions (of {len(batch_transactions)} total) from {batch_start_date} to {current_date}")
                    print(f"  💾 Batch saved {inserted_count} new transactions to database")
                    batch_transactions = []
                    batch_start_date = current_date + datetime.timedelta(days=1)

            save_checkpoint(season, current_date)
            sleep(API_SLEEP_TIME)
            current_date += datetime.timedelta(days=1)

        print(f"✅ Completed season {season}")
        logging.info(f"✅ Completed season {season}")
    
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    
    # Print final database statistics
    print("\n📊 Final Database Statistics:")
    stats = get_transaction_stats()
    total_transactions = 0
    for league_key, total, earliest, latest in stats:
        print(f"  League {league_key}: {total:,} transactions ({earliest} to {latest})")
        total_transactions += total
    
    # Calculate and display performance improvement
    if total_transactions > 0:
        earliest_date = datetime.datetime.strptime(min(stat[2] for stat in stats), "%Y-%m-%d").date()
        latest_date = datetime.datetime.strptime(max(stat[3] for stat in stats), "%Y-%m-%d").date()
        perf_stats = calculate_performance_estimate(earliest_date, latest_date)
        
        print(f"\n⚡ Performance Report:")
        print(f"  📅 Date range processed: {perf_stats['date_range_days']} days")
        print(f"  ⏱️  Actual time taken: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"  🐌 Original method would take: {perf_stats['original_time_seconds']:.0f} seconds ({perf_stats['original_time_seconds']/60:.1f} minutes)")
        print(f"  🏃‍♂️ Time saved: {perf_stats['time_saved_seconds']:.0f} seconds ({perf_stats['time_saved_minutes']:.1f} minutes)")
        print(f"  📈 Performance improvement: {perf_stats['improvement_factor']:.1f}x faster")
    
    print(f"\n💾 Database saved to: {DB_FILE}")
    logging.info("Data collection completed successfully")
