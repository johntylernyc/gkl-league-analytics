#!/usr/bin/env python3
"""
Run July 2025 backfill with working database insertion
"""

import sys
import os
import time
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import (
    fetch_transactions_for_date, TokenManager, init_database, LEAGUE_KEYS, MAX_WORKERS,
    start_job_log, update_job_log
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

def run_july_backfill():
    print("=" * 70)
    print("JULY 2025 TRANSACTION BACKFILL")
    print("=" * 70)
    
    # Configuration
    league_key = LEAGUE_KEYS[2025]
    start_date_str = "2025-07-01"
    end_date_str = "2025-07-31"
    
    # Start job logging
    try:
        metadata = f"test_backfill, workers={MAX_WORKERS}, purpose=validation"
        job_id = start_job_log("transaction_collection", "test", start_date_str, end_date_str, league_key, metadata)
        print(f"Started job logging with ID: {job_id}")
    except Exception as e:
        print(f"Warning: Could not start job logging: {e}")
        job_id = f"july_2025_backfill_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print(f"Date range: {start_date_str} to {end_date_str}")
    print(f"League: {league_key}")
    print(f"Job ID: {job_id}")
    print(f"Database: {DB_FILE}")
    
    # Clear existing test data
    print("\nClearing existing test data...")
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions_test')
        conn.commit()
        print("Test data cleared")
        conn.close()
    except Exception as e:
        print(f"Warning: Could not clear test data: {e}")
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    # Initialize token manager
    print("Initializing token manager...")
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Generate date list
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.isoformat())
        current_date += datetime.timedelta(days=1)
    
    print(f"Processing {len(dates)} dates...")
    
    # Collect all transactions
    start_time = time.time()
    all_transactions = []
    
    print(f"Using {MAX_WORKERS} concurrent workers")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_date = {
            executor.submit(fetch_transactions_for_date, token_manager, league_key, date_str, job_id): date_str 
            for date_str in dates
        }
        
        completed = 0
        for future in as_completed(future_to_date):
            date_str, transactions = future.result()
            completed += 1
            
            if transactions:
                all_transactions.extend(transactions)
                print(f"  [{completed:2d}/{len(dates)}] {date_str}: {len(transactions):3d} transactions")
            else:
                print(f"  [{completed:2d}/{len(dates)}] {date_str}: no transactions")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n" + "=" * 50)
    print("COLLECTION SUMMARY")
    print("=" * 50)
    print(f"Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
    print(f"Total transactions collected: {len(all_transactions):,}")
    
    if not all_transactions:
        print("No transactions to insert")
        return False
    
    # Database insertion with working approach
    print(f"\n" + "=" * 50)
    print("DATABASE INSERTION")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        
        # Prepare data for insertion
        data_tuples = []
        for txn in all_transactions:
            data_tuples.append((
                txn["date"],
                txn["league_key"],
                txn["transaction_id"],
                txn["transaction_type"],
                txn["player_id"],
                txn["player_name"],
                txn["player_position"],
                txn["player_team"],
                txn["movement_type"],
                txn["destination_team_key"],
                txn["destination_team_name"],
                txn["source_team_key"],
                txn["source_team_name"],
                txn["job_id"]
            ))
        
        print(f"Inserting {len(data_tuples):,} transactions...")
        
        # Batch insert using the working schema
        cursor.executemany('''
            INSERT OR IGNORE INTO transactions_test 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, 
             source_team_name, job_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_tuples)
        
        inserted_count = cursor.rowcount
        conn.commit()
        
        print(f"Successfully inserted: {inserted_count:,} transactions")
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE job_id = ?", (job_id,))
        job_count = cursor.fetchone()[0]
        print(f"Records with job ID {job_id}: {job_count}")
        
        # Sample data verification
        cursor.execute("""
            SELECT player_name, transaction_type, destination_team_name, source_team_name 
            FROM transactions_test WHERE job_id = ? LIMIT 5
        """, (job_id,))
        samples = cursor.fetchall()
        
        print(f"\nSample inserted records:")
        for sample in samples:
            print(f"  {sample[0]} - {sample[1]} - Dest: {sample[2]} - Source: {sample[3]}")
        
        conn.close()
        
        print(f"\n" + "=" * 50)
        print("JULY 2025 BACKFILL COMPLETE")
        print("=" * 50)
        print(f"+ {len(all_transactions):,} transactions collected")
        print(f"+ {inserted_count:,} transactions inserted")
        print(f"+ Data available in transactions_test table")
        print(f"+ Job ID: {job_id}")
        
        # Update job log with success
        try:
            update_job_log(job_id, 'completed', records_processed=len(all_transactions), records_inserted=inserted_count)
        except Exception as log_e:
            print(f"Warning: Could not update job log: {log_e}")
        
        return True
        
    except Exception as e:
        print(f"Database insertion failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Update job log with failure
        try:
            error_msg = f"July backfill failed: {str(e)}"
            update_job_log(job_id, 'failed', error_message=error_msg)
        except Exception as log_e:
            print(f"Warning: Could not update job log: {log_e}")
        
        return False

if __name__ == "__main__":
    success = run_july_backfill()
    if success:
        print(f"\n+ JULY 2025 BACKFILL SUCCESSFUL")
    else:
        print(f"\n- JULY 2025 BACKFILL FAILED")