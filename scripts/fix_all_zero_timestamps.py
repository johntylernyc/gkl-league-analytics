#!/usr/bin/env python3
"""
Fix all transactions with timestamp = 0 in production by matching them to local data.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.common.d1_connection import D1Connection

def main():
    """Fix all zero timestamps in production."""
    
    # Connect to local SQLite
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all transactions with timestamps from local database
    # We'll match them by transaction_id and date
    cursor.execute("""
        SELECT transaction_id, date, timestamp, player_id, player_name
        FROM transactions 
        WHERE timestamp IS NOT NULL AND timestamp > 0
        ORDER BY date DESC, transaction_id
    """)
    
    local_transactions = {}
    for row in cursor.fetchall():
        trans_id, date, timestamp, player_id, player_name = row
        # Create composite key for matching
        key = f"{date}|{trans_id}|{player_id}"
        local_transactions[key] = timestamp
    
    conn.close()
    
    print(f"Loaded {len(local_transactions)} transactions with timestamps from local database")
    
    # Connect to D1
    try:
        d1_conn = D1Connection()
        
        # Get transactions with timestamp = 0 from production
        result = d1_conn.execute("""
            SELECT id, date, transaction_id, player_id, player_name
            FROM transactions 
            WHERE timestamp = 0 OR timestamp IS NULL
            ORDER BY id
            LIMIT 1000
        """)
        
        prod_transactions = result.get('results', [])
        print(f"Found {len(prod_transactions)} transactions with zero/null timestamps in production")
        
        if not prod_transactions:
            print("No transactions need updating")
            return
        
        # Match and prepare updates
        updates = []
        matched = 0
        unmatched = []
        
        for trans in prod_transactions:
            # Create matching key
            key = f"{trans['date']}|{trans['transaction_id']}|{trans['player_id']}"
            
            if key in local_transactions:
                timestamp = local_transactions[key]
                updates.append((trans['id'], timestamp))
                matched += 1
            else:
                unmatched.append(trans)
        
        print(f"Matched {matched} transactions to local timestamps")
        if unmatched:
            print(f"Could not match {len(unmatched)} transactions (may be new or different)")
        
        if not updates:
            print("No updates to apply")
            return
        
        # Generate SQL file for backup
        sql_file = Path('cloudflare-production/sql/migrations') / f'fix_all_zero_timestamps_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
        sql_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sql_file, 'w') as f:
            f.write(f"-- Fix all zero timestamps in production\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Count: {len(updates)}\n\n")
            
            for prod_id, timestamp in updates:
                f.write(f"UPDATE transactions SET timestamp = {timestamp} WHERE id = {prod_id};\n")
        
        print(f"Generated backup SQL file: {sql_file}")
        
        # Apply updates
        print("\nApplying updates to production...")
        batch_size = 50
        success_count = 0
        error_count = 0
        
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i+batch_size]
            statements = []
            
            for prod_id, timestamp in batch:
                query = "UPDATE transactions SET timestamp = ? WHERE id = ?"
                params = [timestamp, prod_id]
                statements.append((query, params))
            
            results = d1_conn.execute_batch(statements)
            
            for result in results:
                if result.get('success', True):
                    success_count += result.get('changes', 0)
                else:
                    error_count += 1
            
            print(f"Processed batch {i//batch_size + 1}/{(len(updates) + batch_size - 1)//batch_size}")
        
        print(f"\nUpdate complete: {success_count} records updated, {error_count} errors")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nYou can apply the SQL file manually:")
        print("cd cloudflare-production")
        print(f"npx wrangler d1 execute gkl-fantasy --file={sql_file.name} --remote")

if __name__ == "__main__":
    main()