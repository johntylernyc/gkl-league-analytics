#!/usr/bin/env python3
"""
Apply enhanced player stats schema to database

This script creates the new schema with:
- player_mapping table for multi-platform ID tracking
- Enhanced daily_gkl_player_stats table for all MLB players
- Proper indexes and constraints
"""

import sys
import sqlite3
import argparse
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment


def apply_schema(environment='test', clear_existing=False):
    """Apply the enhanced schema to the database"""
    
    config = get_config_for_environment(environment)
    db_path = config['database_path']
    
    print(f"Applying enhanced schema to {environment} database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Read schema file
        schema_path = Path(__file__).parent.parent / 'schema_enhanced.sql'
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Optionally clear existing data
        if clear_existing:
            print("\nClearing existing data...")
            cursor.execute("DROP TABLE IF EXISTS daily_gkl_player_stats_test")
            cursor.execute("DROP TABLE IF EXISTS daily_gkl_player_stats")
            cursor.execute("DROP TABLE IF EXISTS player_mapping")
            cursor.execute("DROP VIEW IF EXISTS v_player_stats_mapped")
            print("Existing tables dropped")
        
        # Execute schema
        print("\nCreating schema...")
        cursor.executescript(schema_sql)
        
        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('player_mapping', 'daily_gkl_player_stats')
            ORDER BY name
        """)
        
        tables = cursor.fetchall()
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
            # Show column count
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print(f"    Columns: {len(columns)}")
        
        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' 
            AND name LIKE 'idx_%'
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        print("\nCreated indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")
        
        conn.commit()
        print("\nSchema applied successfully!")
        
        # Show sample queries
        print("\nSample queries to test:")
        print("  -- Check player mapping:")
        print("  SELECT COUNT(*) FROM player_mapping;")
        print("\n  -- Check daily stats:")
        print("  SELECT COUNT(*) FROM daily_gkl_player_stats;")
        print("\n  -- Check specific player:")
        print("  SELECT * FROM daily_gkl_player_stats WHERE player_name LIKE '%Muncy%';")
        
    except Exception as e:
        print(f"\nError applying schema: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Apply enhanced player stats schema')
    parser.add_argument('--environment', default='test', 
                       choices=['test', 'production'],
                       help='Environment to apply schema to')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing tables before applying schema')
    
    args = parser.parse_args()
    
    if args.clear and args.environment == 'production':
        response = input("WARNING: Clear existing production data? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted")
            return
    
    apply_schema(args.environment, args.clear)


if __name__ == '__main__':
    main()