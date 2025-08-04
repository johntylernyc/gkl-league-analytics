#!/usr/bin/env python3
"""
Test API responses for different dates to diagnose duplicate data issue
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import fetch_transactions_for_date, TokenManager, LEAGUE_KEYS

def test_api_dates():
    print("Testing API responses for different dates...")
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.initialize()
    
    league_key = LEAGUE_KEYS[2025]
    test_dates = ["2025-07-01", "2025-07-15", "2025-07-31"]
    
    for date_str in test_dates:
        print(f"\nTesting {date_str}...")
        date_result, transactions = fetch_transactions_for_date(token_manager, league_key, date_str, f"test_{date_str}")
        
        if transactions:
            print(f"  Found {len(transactions)} transactions")
            print(f"  First transaction ID: {transactions[0]['transaction_id']}")
            print(f"  Last transaction ID: {transactions[-1]['transaction_id']}")
            
            # Check for unique transaction IDs within this date
            txn_ids = [t['transaction_id'] for t in transactions]
            unique_ids = set(txn_ids)
            print(f"  Unique transaction IDs: {len(unique_ids)}")
            
            if len(unique_ids) < len(txn_ids):
                print(f"  WARNING: Duplicate transaction IDs found within same date!")
        else:
            print(f"  No transactions found")

if __name__ == "__main__":
    test_api_dates()