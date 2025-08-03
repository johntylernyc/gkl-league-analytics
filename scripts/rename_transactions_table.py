#!/usr/bin/env python3
"""
Rename transactions_production table to transactions in the production database.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.database_config import DATABASE_DIR, PRODUCTION_DB


def rename_transactions_table():
    """Rename transactions_production to transactions."""
    
    prod_db_path = DATABASE_DIR / PRODUCTION_DB
    
    print("=" * 60)
    print("RENAMING TRANSACTIONS TABLE")
    print("=" * 60)
    print(f"Database: {prod_db_path}")
    print()
    
    conn = sqlite3.connect(prod_db_path)
    cursor = conn.cursor()
    
    try:
        # First, drop views that might interfere with table operations
        print("Checking for views that might interfere...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view'
        """)
        views = cursor.fetchall()
        
        if views:
            print(f"Found {len(views)} views, dropping them temporarily...")
            for view in views:
                cursor.execute(f"DROP VIEW IF EXISTS {view[0]}")
                print(f"  [OK] Dropped view {view[0]}")
        
        # Also drop any triggers that might interfere
        print("\nChecking for triggers...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='trigger'
        """)
        triggers = cursor.fetchall()
        
        if triggers:
            print(f"Found {len(triggers)} triggers, dropping them...")
            for trigger in triggers:
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger[0]}")
                print(f"  [OK] Dropped trigger {trigger[0]}")
        
        # Check if transactions_production exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='transactions_production'
        """)
        if not cursor.fetchone():
            print("[INFO] Table 'transactions_production' not found")
            
            # Check if transactions already exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='transactions'
            """)
            if cursor.fetchone():
                print("[OK] Table 'transactions' already exists")
                
                # Get record count
                cursor.execute("SELECT COUNT(*) FROM transactions")
                count = cursor.fetchone()[0]
                print(f"     Contains {count} records")
            else:
                print("[WARNING] Neither 'transactions_production' nor 'transactions' found")
            
            return
        
        # Check if transactions table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='transactions'
        """)
        if cursor.fetchone():
            print("[ERROR] Table 'transactions' already exists!")
            print("        Cannot rename - would create duplicate table")
            
            # Compare record counts
            cursor.execute("SELECT COUNT(*) FROM transactions_production")
            prod_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM transactions")
            trans_count = cursor.fetchone()[0]
            
            print(f"\nTable record counts:")
            print(f"  transactions_production: {prod_count} records")
            print(f"  transactions: {trans_count} records")
            
            if prod_count == trans_count:
                print("\n[INFO] Tables have same record count, likely already migrated")
                print("       Consider dropping transactions_production if no longer needed")
            
            return
        
        # Get record count before rename
        cursor.execute("SELECT COUNT(*) FROM transactions_production")
        record_count = cursor.fetchone()[0]
        print(f"Found 'transactions_production' table with {record_count} records")
        
        # Rename the table
        print("\nRenaming table...")
        cursor.execute("ALTER TABLE transactions_production RENAME TO transactions")
        print("[OK] Table renamed successfully")
        
        # Update indexes
        print("\nUpdating indexes...")
        
        # Get all indexes for the table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='transactions'
        """)
        indexes = cursor.fetchall()
        
        for index in indexes:
            old_name = index[0]
            if '_production_' in old_name:
                # Generate new index name without _production
                new_name = old_name.replace('_production_', '_')
                
                # SQLite doesn't support renaming indexes directly
                # We need to get the index definition and recreate it
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{old_name}'")
                index_sql = cursor.fetchone()[0]
                
                if index_sql:  # Some indexes might not have SQL (e.g., auto-created)
                    # Drop old index
                    cursor.execute(f"DROP INDEX IF EXISTS {old_name}")
                    
                    # Create new index with updated name
                    new_sql = index_sql.replace(old_name, new_name)
                    new_sql = new_sql.replace('transactions_production', 'transactions')
                    cursor.execute(new_sql)
                    
                    print(f"  [OK] Renamed index {old_name} -> {new_name}")
        
        # Verify the rename
        cursor.execute("SELECT COUNT(*) FROM transactions")
        new_count = cursor.fetchone()[0]
        
        if new_count == record_count:
            print(f"\n[OK] Verification successful:")
            print(f"     Table 'transactions' has {new_count} records")
        else:
            print(f"\n[WARNING] Record count mismatch!")
            print(f"          Expected: {record_count}")
            print(f"          Found: {new_count}")
        
        # Commit changes
        conn.commit()
        print("\n[OK] All changes committed successfully!")
        
        # Show final table list
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'transaction%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print("\nTransaction tables in database:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} records")
        
    except Exception as e:
        print(f"\n[ERROR] Error during rename: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    rename_transactions_table()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Test the application to ensure it works with renamed table")
    print("2. Run: export DATA_ENV=production")
    print("3. Test a script: python league_transactions/backfill_transactions_optimized.py --start-date 2025-08-01 --end-date 2025-08-02")
    print("4. Verify data is written to 'transactions' table")