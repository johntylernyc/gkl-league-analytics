#!/usr/bin/env python3
"""
Fix database schema by removing obsolete columns and tables
- Remove fantasy_team_id column from transactions_test and transactions_production
- Remove position column from transactions_test and transactions_production  
- Drop unused transactions table
"""

import sqlite3
import os
import sys

def fix_database_schema():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print("="*60)
    print("DATABASE SCHEMA CLEANUP")
    print("="*60)
    print(f"Database: {DB_FILE}")
    
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()
    
    try:
        # Step 1: Check current schema
        print("\n1. CURRENT SCHEMA ANALYSIS")
        for table_name in ['transactions', 'transactions_test', 'transactions_production']:
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"  {table_name}: {[col[1] for col in columns]}")
                
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"    Records: {count}")
            except Exception as e:
                print(f"  {table_name}: {e}")
        
        # Step 2: Create new tables with correct schema
        print("\n2. CREATING NEW TABLES WITH CORRECT SCHEMA")
        
        # Create new transactions_test table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions_test_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                league_key TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_position TEXT,
                player_team TEXT,
                movement_type TEXT NOT NULL,
                destination_team_key TEXT,
                destination_team_name TEXT,
                source_team_key TEXT,
                source_team_name TEXT,
                job_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(transaction_id, player_id, movement_type)
            )
        ''')
        print("  Created transactions_test_new")
        
        # Create new transactions_production table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions_production_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                league_key TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_position TEXT,
                player_team TEXT,
                movement_type TEXT NOT NULL,
                destination_team_key TEXT,
                destination_team_name TEXT,
                source_team_key TEXT,
                source_team_name TEXT,
                job_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(transaction_id, player_id, movement_type)
            )
        ''')
        print("  Created transactions_production_new")
        
        # Step 3: Copy data from old tables to new tables (excluding obsolete columns)
        print("\n3. MIGRATING DATA")
        
        # Migrate test data
        cursor.execute('''
            INSERT INTO transactions_test_new 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, 
             source_team_name, job_id, created_at)
            SELECT date, league_key, transaction_id, transaction_type, player_id, 
                   player_name, player_position, player_team, movement_type,
                   destination_team_key, destination_team_name, source_team_key, 
                   source_team_name, job_id, created_at
            FROM transactions_test
        ''')
        test_migrated = cursor.rowcount
        print(f"  Migrated {test_migrated} records from transactions_test")
        
        # Migrate production data
        cursor.execute('''
            INSERT INTO transactions_production_new 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, player_position, player_team, movement_type,
             destination_team_key, destination_team_name, source_team_key, 
             source_team_name, job_id, created_at)
            SELECT date, league_key, transaction_id, transaction_type, player_id, 
                   player_name, player_position, player_team, movement_type,
                   destination_team_key, destination_team_name, source_team_key, 
                   source_team_name, job_id, created_at
            FROM transactions_production
        ''')
        prod_migrated = cursor.rowcount
        print(f"  Migrated {prod_migrated} records from transactions_production")
        
        # Step 4: Drop old tables
        print("\n4. DROPPING OLD TABLES")
        cursor.execute("DROP TABLE IF EXISTS transactions")
        print("  Dropped transactions table")
        
        cursor.execute("DROP TABLE IF EXISTS transactions_test")
        print("  Dropped old transactions_test table")
        
        cursor.execute("DROP TABLE IF EXISTS transactions_production")
        print("  Dropped old transactions_production table")
        
        # Step 5: Rename new tables
        print("\n5. RENAMING NEW TABLES")
        cursor.execute("ALTER TABLE transactions_test_new RENAME TO transactions_test")
        print("  Renamed transactions_test_new to transactions_test")
        
        cursor.execute("ALTER TABLE transactions_production_new RENAME TO transactions_production")
        print("  Renamed transactions_production_new to transactions_production")
        
        # Step 6: Create indexes
        print("\n6. CREATING INDEXES")
        
        # Test table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_date ON transactions_test(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_league ON transactions_test(league_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_player ON transactions_test(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_dest_team ON transactions_test(destination_team_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_source_team ON transactions_test(source_team_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_test_job ON transactions_test(job_id)')
        print("  Created indexes for transactions_test")
        
        # Production table indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_date ON transactions_production(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_league ON transactions_production(league_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_player ON transactions_production(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_dest_team ON transactions_production(destination_team_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_source_team ON transactions_production(source_team_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_production_job ON transactions_production(job_id)')
        print("  Created indexes for transactions_production")
        
        # Step 7: Verify new schema
        print("\n7. SCHEMA VERIFICATION")
        for table_name in ['transactions_test', 'transactions_production']:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  {table_name}: {[col[1] for col in columns]}")
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Records: {count}")
        
        conn.commit()
        print("\n" + "="*60)
        print("DATABASE SCHEMA CLEANUP COMPLETE")
        print("="*60)
        print("+ Removed obsolete columns: fantasy_team_id, position")
        print("+ Dropped unused transactions table")
        print("+ Migrated all data to new clean schema")
        print("+ Created proper indexes")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = fix_database_schema()
    if success:
        print("\n+ Database schema fix completed successfully")
    else:
        print("\n- Database schema fix failed")