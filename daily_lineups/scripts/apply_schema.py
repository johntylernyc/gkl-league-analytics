"""
Apply the Daily Lineups schema to the database.
This script creates all necessary tables, indexes, and views for the Daily Lineups module.
"""

import sqlite3
import os
from pathlib import Path

def apply_schema():
    """Apply the schema.sql file to the database."""
    
    # Get paths
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "database" / "league_analytics.db"
    schema_path = Path(__file__).parent / "schema.sql"
    
    print(f"Applying schema to database: {db_path}")
    print(f"Schema file: {schema_path}")
    
    # Read schema file
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute schema
        cursor.executescript(schema_sql)
        conn.commit()
        print("[OK] Schema applied successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'daily_lineups%' OR name LIKE 'lineup_%' OR name LIKE 'player_usage%' OR name LIKE 'team_lineup%'
            ORDER BY name
        """)
        
        tables = cursor.fetchall()
        print(f"\n[OK] Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
            
        # Verify indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_lineups%' OR name LIKE 'idx_usage%' OR name LIKE 'idx_patterns%'
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        print(f"\n[OK] Created {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")
            
        # Verify views
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view' AND name LIKE 'v_%'
            ORDER BY name
        """)
        
        views = cursor.fetchall()
        print(f"\n[OK] Created {len(views)} views:")
        for view in views:
            print(f"  - {view[0]}")
            
        # Check lineup_positions data
        cursor.execute("SELECT COUNT(*) FROM lineup_positions")
        position_count = cursor.fetchone()[0]
        print(f"\n[OK] Populated lineup_positions with {position_count} positions")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error applying schema: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_schema()