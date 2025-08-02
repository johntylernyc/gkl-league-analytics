#!/usr/bin/env python3
"""
Debug script to test team extraction for a single date
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the functions from the main script
from backfill_transactions_optimized import fetch_transactions_for_date, TokenManager, batch_insert_transactions, init_database

def test_single_date():
    print("Testing single date transaction collection with simplified extraction...")
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Test single date
    date_str = "2025-07-25"
    league_key = "mlb.l.6966"
    job_id = "test_job_12345"
    
    print(f"Fetching transactions for {date_str} with job_id: {job_id}")
    
    try:
        date_str, transactions = fetch_transactions_for_date(token_manager, league_key, date_str, job_id)
        
        print(f"API response:")
        print(f"  Date: {date_str}")
        print(f"  Transactions found: {len(transactions)}")
        
        # Show first few transactions with new simplified schema
        print(f"  Sample transactions:")
        for i, txn in enumerate(transactions[:3]):
            print(f"    {i+1}: {txn['player_name']} ({txn['movement_type']}) - Job ID: {txn['job_id']}")
            print(f"        Position: {txn['player_position']}")
            print(f"        Destination: {txn['destination_team_key']} - {txn['destination_team_name']}")
            print(f"        Source: {txn['source_team_key']} - {txn['source_team_name']}")
        
        # Count unique teams
        unique_teams = set()
        transaction_types = {}
        for txn in transactions:
            if txn.get('destination_team_key'):
                unique_teams.add(txn['destination_team_key'])
            if txn.get('source_team_key'):
                unique_teams.add(txn['source_team_key'])
            
            tx_type = txn['transaction_type']
            transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
        
        print(f"\n  Transaction types:")
        for tx_type, count in transaction_types.items():
            print(f"    {tx_type}: {count}")
        
        print(f"  Unique fantasy teams: {len(unique_teams)}")
        
        # Verify all fields are present
        required_fields = ['date', 'league_key', 'transaction_id', 'transaction_type', 'player_id', 
                          'player_name', 'player_position', 'player_team', 'movement_type',
                          'destination_team_key', 'destination_team_name', 'source_team_key', 
                          'source_team_name', 'job_id']
        
        missing_fields = []
        for field in required_fields:
            if field not in transactions[0]:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n  X Missing fields: {missing_fields}")
        else:
            print(f"\n  + All required fields present")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_single_date()