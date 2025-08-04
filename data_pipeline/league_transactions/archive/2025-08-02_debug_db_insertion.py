#!/usr/bin/env python3
"""
Debug database insertion issues
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import (
    fetch_transactions_for_date, TokenManager, init_database
)

def debug_database_insertion():
    print("Debugging database insertion...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print(f"Database file: {DB_FILE}")
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.initialize()
    
    # Get a small sample of transaction data
    date_str = "2025-07-25"
    league_key = "mlb.l.6966"
    job_id = "debug_test_12345"
    
    print(f"Fetching sample data for {date_str}...")
    date_str, transactions = fetch_transactions_for_date(token_manager, league_key, date_str, job_id)
    
    print(f"Retrieved {len(transactions)} transactions")
    
    if not transactions:
        print("No transactions to test with")
        return
    
    # Test direct database insertion
    print("Testing direct database insertion...")
    
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        cursor = conn.cursor()
        
        # Check if table exists and schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions_test'")
        table_exists = cursor.fetchone()
        print(f"Table exists: {bool(table_exists)}")
        
        if table_exists:
            cursor.execute("PRAGMA table_info(transactions_test)")
            columns = cursor.fetchall()
            print(f"Table columns: {[col[1] for col in columns]}")
        
        # Initialize database to ensure schema is up to date
        print("Initializing database schema...")
        init_database()
        
        # Test single transaction insertion
        test_txn = transactions[0]
        print(f"Testing with transaction: {test_txn['player_name']}")
        
        cursor.execute('''
            INSERT OR IGNORE INTO transactions_test 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, 
             source_team_name, job_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_txn["date"],
            test_txn["league_key"],
            test_txn["transaction_id"],
            test_txn["transaction_type"],
            test_txn["player_id"],
            test_txn["player_name"],
            test_txn["player_position"],
            test_txn["player_team"],
            test_txn["movement_type"],
            test_txn["destination_team_key"],
            test_txn["destination_team_name"],
            test_txn["source_team_key"],
            test_txn["source_team_name"],
            test_txn["job_id"]
        ))
        
        inserted = cursor.rowcount
        print(f"Single insert rowcount: {inserted}")
        
        conn.commit()
        
        # Check if record exists
        cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE transaction_id = ?", (test_txn["transaction_id"],))
        exists = cursor.fetchone()[0]
        print(f"Record exists after insert: {exists}")
        
        # Try batch insert with first 10 transactions
        print("Testing batch insert with 10 transactions...")
        
        data_tuples = []
        for txn in transactions[:10]:
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
        
        cursor.executemany('''
            INSERT OR IGNORE INTO transactions_test 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, 
             source_team_name, job_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_tuples)
        
        batch_inserted = cursor.rowcount
        print(f"Batch insert rowcount: {batch_inserted}")
        
        conn.commit()
        
        # Final count
        cursor.execute("SELECT COUNT(*) FROM transactions_test")
        total_count = cursor.fetchone()[0]
        print(f"Total records in transactions_test: {total_count}")
        
        if total_count > 0:
            cursor.execute("SELECT player_name, transaction_type, job_id FROM transactions_test LIMIT 3")
            samples = cursor.fetchall()
            print("Sample records:")
            for sample in samples:
                print(f"  {sample[0]} - {sample[1]} - {sample[2]}")
        
        print("Database insertion test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    debug_database_insertion()