#!/usr/bin/env python3
"""
Migrate test data from production database to test database.

This script:
1. Exports test data from production database
2. Creates tables in test database
3. Imports test data to test database
4. Verifies migration
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.config.database_config import DATABASE_DIR, PRODUCTION_DB, TEST_DB


def migrate_test_data():
    """Migrate test data from production to test database."""
    
    prod_db_path = DATABASE_DIR / PRODUCTION_DB
    test_db_path = DATABASE_DIR / TEST_DB
    
    print("=" * 60)
    print("TEST DATA MIGRATION")
    print("=" * 60)
    print(f"Source: {prod_db_path}")
    print(f"Target: {test_db_path}")
    print()
    
    # Connect to both databases
    prod_conn = sqlite3.connect(prod_db_path)
    test_conn = sqlite3.connect(test_db_path)
    
    prod_cursor = prod_conn.cursor()
    test_cursor = test_conn.cursor()
    
    try:
        # 1. Create transactions_test table in test database
        print("Creating transactions_test table in test database...")
        
        # Check if table already exists
        test_cursor.execute("SELECT name FROM sqlite_master WHERE name='transactions_test' AND type='table'")
        if test_cursor.fetchone():
            print("  [INFO] Table already exists, clearing existing data...")
            test_cursor.execute("DELETE FROM transactions_test")
        else:
            prod_cursor.execute("SELECT sql FROM sqlite_master WHERE name='transactions_test' AND type='table'")
            create_sql = prod_cursor.fetchone()
            
            if create_sql:
                test_cursor.execute(create_sql[0])
                print("  [OK] Table created")
            else:
                print("  ! transactions_test table not found in production")
        
        # 2. Copy test transaction data
        print("\nMigrating transaction test data...")
        prod_cursor.execute("SELECT COUNT(*) FROM transactions_test")
        count = prod_cursor.fetchone()[0]
        print(f"  Found {count} test transactions to migrate")
        
        if count > 0:
            # Get all data
            prod_cursor.execute("SELECT * FROM transactions_test")
            test_data = prod_cursor.fetchall()
            
            # Get column names
            prod_cursor.execute("PRAGMA table_info(transactions_test)")
            columns = [col[1] for col in prod_cursor.fetchall()]
            
            # Insert into test database
            placeholders = ','.join(['?' for _ in columns])
            test_cursor.executemany(
                f"INSERT INTO transactions_test ({','.join(columns)}) VALUES ({placeholders})",
                test_data
            )
            print(f"  [OK] Migrated {count} records")
        
        # 3. Create and copy indexes
        print("\nCreating indexes...")
        prod_cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='transactions_test' AND sql IS NOT NULL
        """)
        indexes = prod_cursor.fetchall()
        
        for index_sql in indexes:
            test_cursor.execute(index_sql[0])
        print(f"  [OK] Created {len(indexes)} indexes")
        
        # 4. Create daily_lineups_test table (empty, ready for test data)
        print("\nCreating daily_lineups_test table...")
        
        # Check if table already exists
        test_cursor.execute("SELECT name FROM sqlite_master WHERE name='daily_lineups_test' AND type='table'")
        if test_cursor.fetchone():
            print("  [INFO] Table already exists")
        else:
            prod_cursor.execute("SELECT sql FROM sqlite_master WHERE name='daily_lineups' AND type='table'")
            create_sql = prod_cursor.fetchone()
            
            if create_sql:
                # Modify the SQL to create test table
                test_table_sql = create_sql[0].replace('daily_lineups', 'daily_lineups_test')
                test_cursor.execute(test_table_sql)
                print("  [OK] Table created (empty, ready for test data)")
        
        # 5. Migrate test job_log entries
        print("\nMigrating test job_log entries...")
        
        # First ensure job_log exists in test db
        test_cursor.execute("SELECT name FROM sqlite_master WHERE name='job_log' AND type='table'")
        if not test_cursor.fetchone():
            prod_cursor.execute("SELECT sql FROM sqlite_master WHERE name='job_log' AND type='table'")
            create_sql = prod_cursor.fetchone()
            if create_sql:
                test_cursor.execute(create_sql[0])
        else:
            # Clear existing test job entries
            test_cursor.execute("DELETE FROM job_log WHERE environment = 'test'")
        
        # Copy test environment jobs
        prod_cursor.execute("""
            SELECT * FROM job_log 
            WHERE environment = 'test'
        """)
        test_jobs = prod_cursor.fetchall()
        
        if test_jobs:
            # Get column names
            prod_cursor.execute("PRAGMA table_info(job_log)")
            columns = [col[1] for col in prod_cursor.fetchall()]
            
            placeholders = ','.join(['?' for _ in columns])
            test_cursor.executemany(
                f"INSERT INTO job_log ({','.join(columns)}) VALUES ({placeholders})",
                test_jobs
            )
            print(f"  [OK] Migrated {len(test_jobs)} test job entries")
        
        # Commit changes
        test_conn.commit()
        print("\n[OK] Test database migration completed successfully!")
        
        # 6. Verify migration
        print("\nVerification:")
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [t[0] for t in test_cursor.fetchall()]
        print(f"  Tables in test database: {tables}")
        
        for table in tables:
            if table != 'sqlite_sequence':
                test_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = test_cursor.fetchone()[0]
                print(f"    - {table}: {count} records")
        
    except Exception as e:
        print(f"\n[ERROR] Error during migration: {e}")
        test_conn.rollback()
        raise
    
    finally:
        prod_conn.close()
        test_conn.close()


def clean_production_database():
    """Remove test tables from production database."""
    
    prod_db_path = DATABASE_DIR / PRODUCTION_DB
    
    print("\n" + "=" * 60)
    print("PRODUCTION DATABASE CLEANUP")
    print("=" * 60)
    
    conn = sqlite3.connect(prod_db_path)
    cursor = conn.cursor()
    
    try:
        # Remove test transaction data
        print("Removing test data from production...")
        
        # Drop transactions_test table
        cursor.execute("DROP TABLE IF EXISTS transactions_test")
        print("  [OK] Dropped transactions_test table")
        
        # Remove test job entries
        cursor.execute("DELETE FROM job_log WHERE environment = 'test'")
        deleted = cursor.rowcount
        print(f"  [OK] Removed {deleted} test job_log entries")
        
        # Drop test indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE '%_test_%'
        """)
        test_indexes = cursor.fetchall()
        for index in test_indexes:
            cursor.execute(f"DROP INDEX IF EXISTS {index[0]}")
        print(f"  [OK] Dropped {len(test_indexes)} test indexes")
        
        conn.commit()
        print("\n[OK] Production database cleaned successfully!")
        
        # Show remaining tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"\nRemaining tables in production: {tables}")
        
    except Exception as e:
        print(f"\n[ERROR] Error during cleanup: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate test data to test database")
    parser.add_argument('--skip-migration', action='store_true',
                       help='Skip migration, only clean production')
    parser.add_argument('--skip-cleanup', action='store_true',
                       help='Skip cleanup, only migrate')
    
    args = parser.parse_args()
    
    if not args.skip_migration:
        migrate_test_data()
    
    if not args.skip_cleanup:
        clean_production_database()
    
    print("\n[OK] Database separation complete!")
    print("\nNext steps:")
    print("  1. Update scripts to use config.database_config")
    print("  2. Set DATA_ENV=test when running tests")
    print("  3. Default (or DATA_ENV=production) for production")