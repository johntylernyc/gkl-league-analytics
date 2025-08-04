#!/usr/bin/env python3
"""
Run transaction collection without job logging to avoid database lock issues
"""

import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions from the main script
from backfill_transactions_optimized import (
    fetch_transactions_for_date, TokenManager, batch_insert_transactions, init_database,
    MAX_WORKERS, LEAGUE_KEYS, PRODUCTION_DATE_RANGE
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime

def run_collection_simple():
    print("Running simplified transaction collection without job logging...")
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    # Initialize token manager
    print("Initializing token manager...")
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Configuration - Full season 2025 YTD collection
    league_key = LEAGUE_KEYS[2025]
    start_date_str, end_date_str = PRODUCTION_DATE_RANGE  # Full season March 27 - August 1
    environment = 'production'
    
    print(f"\n{'='*60}")
    print(f"COLLECTING TRANSACTION DATA: 2025 SEASON (PRODUCTION)")
    print(f"{'='*60}")
    print(f"Date range: {start_date_str} to {end_date_str}")
    print(f"League: {league_key}")
    print(f"Environment: {environment}")
    print(f"Target table: transactions_{environment}")
    
    # Generate date list
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.isoformat())
        current_date += datetime.timedelta(days=1)
    
    print(f"Processing {len(dates)} dates...")
    
    start_time = time.time()
    all_transactions = []
    
    # Use concurrent processing
    print(f"Using {MAX_WORKERS} concurrent workers")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_date = {
            executor.submit(fetch_transactions_for_date, token_manager, league_key, date_str): date_str 
            for date_str in dates
        }
        
        completed = 0
        for future in as_completed(future_to_date):
            date_str, transactions = future.result()
            completed += 1
            
            if transactions:
                all_transactions.extend(transactions)
                print(f"  [{completed:3d}/{len(dates)}] {date_str}: {len(transactions)} transactions")
            else:
                print(f"  [{completed:3d}/{len(dates)}] {date_str}: no transactions")
    
    # Batch insert all transactions
    inserted_count = 0
    if all_transactions:
        print(f"\nInserting {len(all_transactions)} transactions...")
        inserted_count = batch_insert_transactions(all_transactions, environment)
        print(f"Inserted {inserted_count} transactions to database ({environment} environment)")
        
        # Count unique teams for reporting
        unique_teams = set()
        for txn in all_transactions:
            if txn.get("destination_team_key"):
                unique_teams.add(txn["destination_team_key"])
            if txn.get("source_team_key"):
                unique_teams.add(txn["source_team_key"])
        
        if unique_teams:
            print(f"Found {len(unique_teams)} unique fantasy teams")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print("COLLECTION RESULTS")
    print(f"{'='*60}")
    print(f"Duration: {duration:.2f} seconds ({duration/60:.1f} minutes)")
    print(f"Total transactions collected: {len(all_transactions):,}")
    print(f"Dates processed: {len(dates)}")
    print(f"Processing rate: {len(dates)/duration:.2f} dates/second")
    print(f"Transactions inserted: {inserted_count:,}")
    
    print(f"\nPRODUCTION DATA COLLECTION COMPLETE!")

if __name__ == "__main__":
    run_collection_simple()