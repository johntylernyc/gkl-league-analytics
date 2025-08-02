#!/usr/bin/env python3
"""
Analyze current database structure after user's manual cleanup
"""

import sqlite3
import os

def analyze_current_database():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, 'database', 'league_analytics.db')
    
    print("="*80)
    print("CURRENT DATABASE STRUCTURE ANALYSIS")
    print("="*80)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"Tables in database: {[t[0] for t in tables]}")
    
    # Analyze each table
    for table_name, in tables:
        print(f"\n{'-'*60}")
        print(f"TABLE: {table_name}")
        print(f"{'-'*60}")
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("Columns:")
        for col in columns:
            col_id, name, data_type, not_null, default, pk = col
            pk_str = " PRIMARY KEY" if pk else ""
            not_null_str = " NOT NULL" if not_null else ""
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  {name} ({data_type}){pk_str}{not_null_str}{default_str}")
        
        # Get record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Records: {count:,}")
        
        # Get indexes for this table
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        if indexes:
            print("Indexes:")
            for idx in indexes:
                idx_name = idx[1]
                is_unique = idx[2]
                unique_str = " (UNIQUE)" if is_unique else ""
                
                cursor.execute(f"PRAGMA index_info({idx_name})")
                idx_columns = cursor.fetchall()
                column_names = [col[2] for col in idx_columns]
                
                print(f"  {idx_name}: {', '.join(column_names)}{unique_str}")
        else:
            print("Indexes: None")
    
    # Check for any orphaned indexes
    print(f"\n{'-'*60}")
    print("ALL INDEXES IN DATABASE")
    print(f"{'-'*60}")
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
    all_indexes = cursor.fetchall()
    
    current_table = None
    for idx_name, table_name in all_indexes:
        if table_name != current_table:
            print(f"\n{table_name}:")
            current_table = table_name
        print(f"  {idx_name}")
    
    conn.close()
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    analyze_current_database()