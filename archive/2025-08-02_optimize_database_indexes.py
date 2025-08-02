#!/usr/bin/env python3
"""
Optimize database indexes for performance and common query patterns
"""

import sqlite3
import os

def optimize_database_indexes():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, 'database', 'league_analytics.db')
    
    print("="*80)
    print("DATABASE INDEX OPTIMIZATION")
    print("="*80)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Step 1: Analyze current indexes
        print("\n1. CURRENT INDEX ANALYSIS")
        print("-" * 40)
        
        for table_name in ['transactions_test', 'transactions_production']:
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            print(f"\n{table_name} current indexes:")
            
            for idx in indexes:
                idx_name = idx[1]
                cursor.execute(f"PRAGMA index_info({idx_name})")
                idx_columns = cursor.fetchall()
                column_names = [col[2] for col in idx_columns]
                print(f"  {idx_name}: {', '.join(column_names)}")
        
        # Step 2: Add strategic composite indexes
        print(f"\n2. ADDING COMPOSITE INDEXES")
        print("-" * 40)
        
        composite_indexes = [
            # Date + League for common filtering patterns
            ("idx_transactions_test_date_league", "transactions_test", "(date, league_key)"),
            ("idx_transactions_production_date_league", "transactions_production", "(date, league_key)"),
            
            # Player + Date for player history queries
            ("idx_transactions_test_player_date", "transactions_test", "(player_id, date)"),
            ("idx_transactions_production_player_date", "transactions_production", "(player_id, date)"),
            
            # Job + Status for job tracking
            ("idx_job_log_status_time", "job_log", "(status, start_time)"),
        ]
        
        for idx_name, table_name, columns in composite_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} {columns}")
                print(f"  + Created {idx_name} on {table_name} {columns}")
            except Exception as e:
                print(f"  - Failed to create {idx_name}: {e}")
        
        # Step 3: Add missing single-column indexes for key fields
        print(f"\n3. ADDING STRATEGIC SINGLE-COLUMN INDEXES")
        print("-" * 40)
        
        single_indexes = [
            # Transaction type for filtering by add/drop/trade
            ("idx_transactions_test_type", "transactions_test", "transaction_type"),
            ("idx_transactions_production_type", "transactions_production", "transaction_type"),
            
            # Created timestamp for temporal queries
            ("idx_transactions_test_created", "transactions_test", "created_at"),
            ("idx_transactions_production_created", "transactions_production", "created_at"),
            
            # Movement type for analysis
            ("idx_transactions_test_movement", "transactions_test", "movement_type"),
            ("idx_transactions_production_movement", "transactions_production", "movement_type"),
        ]
        
        for idx_name, table_name, column in single_indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({column})")
                print(f"  + Created {idx_name} on {table_name}({column})")
            except Exception as e:
                print(f"  - Failed to create {idx_name}: {e}")
        
        # Step 4: Test index performance with common queries
        print(f"\n4. INDEX PERFORMANCE TESTING")
        print("-" * 40)
        
        test_queries = [
            ("Date range query", "SELECT COUNT(*) FROM transactions_test WHERE date BETWEEN '2025-07-01' AND '2025-07-31'"),
            ("Player history", "SELECT COUNT(*) FROM transactions_test WHERE player_id = '11743' ORDER BY date"),
            ("Transaction type filter", "SELECT COUNT(*) FROM transactions_test WHERE transaction_type = 'add'"),
            ("Job tracking", "SELECT * FROM job_log WHERE status = 'completed' ORDER BY start_time DESC LIMIT 5"),
        ]
        
        for description, query in test_queries:
            try:
                cursor.execute(f"EXPLAIN QUERY PLAN {query}")
                plan = cursor.fetchall()
                print(f"\n  {description}:")
                for step in plan:
                    detail = step[3] if len(step) > 3 else str(step)
                    uses_index = "USING INDEX" in detail
                    status = "+" if uses_index else "!"
                    print(f"    {status} {detail}")
            except Exception as e:
                print(f"    - Query failed: {e}")
        
        # Step 5: Final index summary
        print(f"\n5. FINAL INDEX SUMMARY")
        print("-" * 40)
        
        for table_name in ['job_log', 'transactions_test', 'transactions_production']:
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            print(f"\n{table_name} ({len(indexes)} indexes):")
            
            for idx in indexes:
                idx_name = idx[1]
                if not idx_name.startswith('sqlite_autoindex'):
                    cursor.execute(f"PRAGMA index_info({idx_name})")
                    idx_columns = cursor.fetchall()
                    column_names = [col[2] for col in idx_columns]
                    print(f"  {idx_name}: {', '.join(column_names)}")
        
        conn.commit()
        print(f"\n" + "="*80)
        print("DATABASE INDEX OPTIMIZATION COMPLETE")
        print("="*80)
        print("+ Added composite indexes for common query patterns")
        print("+ Added strategic single-column indexes")
        print("+ Tested query performance with EXPLAIN QUERY PLAN")
        print("+ All indexes committed to database")
        
        return True
        
    except Exception as e:
        print(f"\nError during index optimization: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = optimize_database_indexes()
    if success:
        print("\n+ Database index optimization completed successfully")
    else:
        print("\n- Database index optimization failed")