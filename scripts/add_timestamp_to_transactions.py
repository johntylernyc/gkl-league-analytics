#!/usr/bin/env python3
"""
Add timestamp column to transactions table if it doesn't exist.
"""
import sqlite3
from pathlib import Path

def add_timestamp_column():
    """Add timestamp column to transactions table."""
    # Update both test and production databases
    databases = [
        'database/league_analytics.db',
        'database/league_analytics_test.db'
    ]
    
    for db_name in databases:
        db_path = Path(__file__).parent.parent / db_name
        if not db_path.exists():
            print(f"Skipping {db_name} - not found")
            continue
            
        print(f"\nProcessing {db_name}...")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            # Check if timestamp column exists
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'timestamp' in columns:
                print(f"  timestamp column already exists")
            else:
                print(f"  Adding timestamp column...")
                cursor.execute("""
                    ALTER TABLE transactions 
                    ADD COLUMN timestamp INTEGER DEFAULT 0
                """)
                
                # Create index for timestamp
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_transactions_timestamp 
                    ON transactions(timestamp)
                """)
                
                conn.commit()
                print(f"  timestamp column added successfully")
                
        except sqlite3.Error as e:
            print(f"  Error: {e}")
            conn.rollback()
        finally:
            conn.close()

if __name__ == "__main__":
    add_timestamp_column()
    print("\nDone! You can now run the updated collection scripts.")