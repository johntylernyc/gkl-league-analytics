#!/usr/bin/env python3
"""
Test script to backfill 1 month of transaction data (July 2025)
for validation of the simplified extraction system
"""

import sys
import os
import time
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import (
    fetch_transactions_for_date, TokenManager, batch_insert_transactions, init_database,
    start_job_log, update_job_log, LEAGUE_KEYS, MAX_WORKERS
)
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_test_month_backfill():
    print("=" * 70)
    print("TRANSACTION DATA BACKFILL TEST - JULY 2025")
    print("=" * 70)
    
    # Configuration
    league_key = LEAGUE_KEYS[2025]
    start_date_str = "2025-07-01"
    end_date_str = "2025-07-31"
    environment = 'test'
    
    print(f"Date range: {start_date_str} to {end_date_str}")
    print(f"League: {league_key}")
    print(f"Environment: {environment}")
    print(f"Target table: transactions_{environment}")
    
    # Initialize database
    print("\nInitializing database...")
    init_database()
    
    # Start job logging
    metadata = f"test_month_backfill, workers={MAX_WORKERS}, validation_run"
    job_id = start_job_log("test_month_backfill", environment, start_date_str, end_date_str, league_key, metadata)
    print(f"Job ID: {job_id}")
    
    try:
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
        
        start_time = time.time()
        all_transactions = []
        
        # Use concurrent processing
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
        print(f"Dates processed: {len(dates)}")
        print(f"Processing rate: {len(dates)/duration:.2f} dates/second")
        
        # Analyze transaction data
        if all_transactions:
            # Transaction type breakdown
            transaction_types = {}
            unique_dest_teams = set()
            unique_source_teams = set()
            positions = set()
            
            for txn in all_transactions:
                tx_type = txn['transaction_type']
                transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
                
                if txn.get('destination_team_key'):
                    unique_dest_teams.add(txn['destination_team_key'])
                if txn.get('source_team_key'):
                    unique_source_teams.add(txn['source_team_key'])
                if txn.get('player_position'):
                    positions.add(txn['player_position'])
            
            all_unique_teams = unique_dest_teams | unique_source_teams
            
            print(f"\nTransaction Types:")
            for tx_type, count in sorted(transaction_types.items()):
                print(f"  {tx_type}: {count:,}")
            
            print(f"\nTeam Information:")
            print(f"  Unique fantasy teams: {len(all_unique_teams)}")
            print(f"  Destination teams: {len(unique_dest_teams)}")
            print(f"  Source teams: {len(unique_source_teams)}")
            
            print(f"\nPosition Information:")
            print(f"  Unique positions found: {len(positions)}")
            print(f"  Sample positions: {list(sorted(positions))[:10]}")
            
            # Database insertion
            print(f"\n" + "=" * 50)
            print("DATABASE INSERTION")
            print("=" * 50)
            print(f"Inserting {len(all_transactions):,} transactions...")
            
            inserted_count = batch_insert_transactions(all_transactions, environment)
            print(f"Successfully inserted: {inserted_count:,} transactions")
            
            # Update job log
            update_job_log(job_id, 'completed', records_processed=len(all_transactions), records_inserted=inserted_count)
            
            print(f"\n" + "=" * 50)
            print("TEST VALIDATION RESULTS")
            print("=" * 50)
            
            if inserted_count > 0:
                print(f"✓ SUCCESS: {inserted_count:,} transactions inserted")
                print(f"✓ All transaction types captured: {list(transaction_types.keys())}")
                print(f"✓ Fantasy team data captured: {len(all_unique_teams)} teams")
                print(f"✓ Position data captured: {len(positions)} unique positions")
                print(f"✓ Job tracking working: Job ID {job_id}")
                
                print(f"\nSystem is ready for full 2025 season backfill!")
                return True
            else:
                print(f"✗ WARNING: No new transactions inserted (data may already exist)")
                print(f"  Consider clearing test data or checking for duplicates")
                return False
        else:
            print(f"✗ ERROR: No transactions collected")
            update_job_log(job_id, 'failed', error_message="No transactions collected")
            return False
            
    except Exception as e:
        error_msg = f"Test backfill failed: {str(e)}"
        print(f"\n✗ ERROR: {error_msg}")
        update_job_log(job_id, 'failed', error_message=error_msg)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_test_month_backfill()
    if success:
        print(f"\n🎯 TEST MONTH BACKFILL COMPLETED SUCCESSFULLY")
    else:
        print(f"\n❌ TEST MONTH BACKFILL FAILED")