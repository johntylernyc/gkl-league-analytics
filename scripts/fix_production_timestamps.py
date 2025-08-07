#!/usr/bin/env python3
"""
Fix missing timestamps in production D1 database.
Updates transactions with timestamp = 0 by fetching the correct values from local SQLite.
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
    """Fix timestamps in production."""
    
    # Connect to local SQLite
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get transactions that need timestamp updates (IDs > 201352)
    cursor.execute("""
        SELECT id, timestamp 
        FROM transactions 
        WHERE id > 201352 AND timestamp IS NOT NULL AND timestamp > 0
        ORDER BY id
    """)
    
    updates = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(updates)} transactions to update")
    
    if not updates:
        print("No updates needed")
        return
    
    # Generate SQL update file
    sql_file = Path('cloudflare-production/sql/migrations') / f'fix_transaction_timestamps_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    sql_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(sql_file, 'w') as f:
        f.write(f"-- Fix missing timestamps for recent transactions\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Count: {len(updates)}\n\n")
        
        for trans_id, timestamp in updates:
            f.write(f"UPDATE transactions SET timestamp = {timestamp} WHERE id = {trans_id};\n")
    
    print(f"Generated migration file: {sql_file}")
    print("\nTo apply to production:")
    print(f"cd cloudflare-production")
    print(f"npx wrangler d1 execute gkl-fantasy --file={sql_file.name} --remote")
    
    # Option to apply directly via D1 API
    apply_now = input("\nApply to production now? (y/n): ")
    if apply_now.lower() == 'y':
        try:
            d1_conn = D1Connection()
            
            # Apply updates in batches
            batch_size = 100
            success_count = 0
            error_count = 0
            
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i+batch_size]
                statements = []
                
                for trans_id, timestamp in batch:
                    query = "UPDATE transactions SET timestamp = ? WHERE id = ?"
                    params = [timestamp, trans_id]
                    statements.append((query, params))
                
                results = d1_conn.execute_batch(statements)
                
                for result in results:
                    if result.get('success', True):
                        success_count += result.get('changes', 0)
                    else:
                        error_count += 1
                
                print(f"Processed batch {i//batch_size + 1}/{(len(updates) + batch_size - 1)//batch_size}")
            
            print(f"\nUpdate complete: {success_count} updated, {error_count} errors")
            
        except Exception as e:
            print(f"Error applying updates: {e}")
            print("You can still apply manually using the SQL file")

if __name__ == "__main__":
    main()