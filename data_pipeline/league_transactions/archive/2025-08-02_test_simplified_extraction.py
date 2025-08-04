#!/usr/bin/env python3
"""
Test script for simplified transaction extraction
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions from the main script
from backfill_transactions_optimized import (
    fetch_transactions_for_date, TokenManager, batch_insert_transactions, init_database,
    start_job_log, update_job_log
)

def test_simplified_extraction():
    print("Testing simplified transaction extraction...")
    
    # Initialize database
    init_database()
    
    # Start a test job
    job_id = start_job_log("test_extraction", "test", "2025-07-25", "2025-07-25", "mlb.l.6966", "simplified extraction test")
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Test single date
    date_str = "2025-07-25"
    league_key = "mlb.l.6966"
    
    print(f"Fetching transactions for {date_str} with job_id: {job_id}")
    
    try:
        date_str, transactions = fetch_transactions_for_date(token_manager, league_key, date_str, job_id)
        
        print(f"API response:")
        print(f"  Date: {date_str}")
        print(f"  Transactions found: {len(transactions)}")
        
        # Show first few transactions with new schema
        print(f"  Sample transactions:")
        for i, txn in enumerate(transactions[:3]):
            print(f"    {i+1}: {txn['player_name']} ({txn['movement_type']}) - Job ID: {txn['job_id']}")
            print(f"        Position: {txn['player_position']}")
            print(f"        Destination: {txn['destination_team_key']} - {txn['destination_team_name']}")
            print(f"        Source: {txn['source_team_key']} - {txn['source_team_name']}")
        
        # Count transactions by type
        transaction_types = {}
        team_keys = set()
        for txn in transactions:
            tx_type = txn['transaction_type']
            transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
            
            if txn.get('destination_team_key'):
                team_keys.add(txn['destination_team_key'])
            if txn.get('source_team_key'):
                team_keys.add(txn['source_team_key'])
        
        print(f"\n  Transaction types:")
        for tx_type, count in transaction_types.items():
            print(f"    {tx_type}: {count}")
        
        print(f"\n  Unique fantasy teams found: {len(team_keys)}")
        
        # Test database insertion
        if transactions:
            print(f"\nTesting database insertion...")
            inserted = batch_insert_transactions(transactions, 'test')
            print(f"  Inserted: {inserted} transactions")
            
            # Update job log
            update_job_log(job_id, 'completed', records_processed=len(transactions), records_inserted=inserted)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        update_job_log(job_id, 'failed', error_message=str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simplified_extraction()
    if success:
        print("\n✅ Simplified extraction test PASSED")
    else:
        print("\n❌ Simplified extraction test FAILED")