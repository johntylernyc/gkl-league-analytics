#!/usr/bin/env python3
"""
Fix database schema using WAL mode to avoid locks
"""

import sqlite3
import os
import time

def fix_schema_with_wal():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print("="*60)
    print("DATABASE SCHEMA FIX WITH WAL MODE")
    print("="*60)
    
    try:
        # Enable WAL mode first
        conn = sqlite3.connect(DB_FILE, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.close()
        print("Enabled WAL mode")
        
        # Wait a moment for any locks to clear
        time.sleep(2)
        
        # Now proceed with schema fix
        conn = sqlite3.connect(DB_FILE, timeout=60)
        cursor = conn.cursor()
        
        print("\n1. Current schema check...")
        cursor.execute("PRAGMA table_info(transactions_test)")
        test_columns = [col[1] for col in cursor.fetchall()]
        print(f"transactions_test columns: {test_columns}")
        
        # Method: Use ALTER TABLE to drop columns (SQLite 3.35+)
        print("\n2. Removing obsolete columns...")
        
        try:
            # Try to drop fantasy_team_id column
            cursor.execute("ALTER TABLE transactions_test DROP COLUMN fantasy_team_id")
            print("  Dropped fantasy_team_id from transactions_test")
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print("  fantasy_team_id column doesn't exist")
            else:
                print(f"  Cannot drop fantasy_team_id: {e}")
        
        try:
            # Try to drop position column  
            cursor.execute("ALTER TABLE transactions_test DROP COLUMN position")
            print("  Dropped position from transactions_test")
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print("  position column doesn't exist")
            else:
                print(f"  Cannot drop position: {e}")
        
        try:
            # Try to drop fantasy_team_id from production table
            cursor.execute("ALTER TABLE transactions_production DROP COLUMN fantasy_team_id")
            print("  Dropped fantasy_team_id from transactions_production")
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print("  fantasy_team_id column doesn't exist in production")
            else:
                print(f"  Cannot drop fantasy_team_id from production: {e}")
        
        try:
            # Try to drop position from production table
            cursor.execute("ALTER TABLE transactions_production DROP COLUMN position")
            print("  Dropped position from transactions_production")
        except sqlite3.OperationalError as e:
            if "no such column" in str(e):
                print("  position column doesn't exist in production")
            else:
                print(f"  Cannot drop position from production: {e}")
        
        print("\n3. Dropping unused transactions table...")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        print("  Dropped transactions table")
        
        print("\n4. Verifying final schema...")
        cursor.execute("PRAGMA table_info(transactions_test)")
        test_columns_final = [col[1] for col in cursor.fetchall()]
        print(f"transactions_test final columns: {test_columns_final}")
        
        cursor.execute("PRAGMA table_info(transactions_production)")
        prod_columns_final = [col[1] for col in cursor.fetchall()]
        print(f"transactions_production final columns: {prod_columns_final}")
        
        # Check if obsolete columns still exist
        obsolete_in_test = any(col in test_columns_final for col in ['fantasy_team_id', 'position'])
        obsolete_in_prod = any(col in prod_columns_final for col in ['fantasy_team_id', 'position'])
        
        if obsolete_in_test or obsolete_in_prod:
            print("\n! SQLite version doesn't support DROP COLUMN - will use recreate method")
            return False
        else:
            conn.commit()
            print("\n" + "="*60)
            print("SCHEMA FIX COMPLETE")
            print("="*60)
            print("+ Removed obsolete columns successfully")
            print("+ Dropped unused transactions table")
            return True
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    success = fix_schema_with_wal()
    if not success:
        print("\nWAL method failed - will need to use table recreation method")
    else:
        print("\n+ Schema fix completed successfully")