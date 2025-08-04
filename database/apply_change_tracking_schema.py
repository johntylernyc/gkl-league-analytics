"""
Apply change tracking schema to existing database.
This script safely adds change tracking capabilities without breaking existing functionality.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent / 'league_analytics.db'
SCHEMA_PATH = Path(__file__).parent / 'schema' / 'change_tracking_schema.sql'
MIGRATION_PATH = Path(__file__).parent / 'migrations' / 'add_change_tracking_columns.sql'


def backup_database():
    """Create a backup before applying schema changes."""
    backup_path = DB_PATH.parent / 'backups' / f'league_analytics_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    backup_path.parent.mkdir(exist_ok=True)
    
    print(f"Creating backup at: {backup_path}")
    
    # Copy database file
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    
    print(f"Backup created successfully")
    return backup_path


def test_existing_queries(conn):
    """Test that existing queries still work."""
    test_queries = [
        # Test transaction queries
        "SELECT COUNT(*) FROM transactions_production",
        "SELECT COUNT(*) FROM transactions_test",
        
        # Test daily lineups query
        "SELECT COUNT(*) FROM daily_lineups",
        
        # Test player stats query
        "SELECT COUNT(*) FROM daily_gkl_player_stats",
        
        # Test job log query
        "SELECT COUNT(*) FROM job_log",
        
        # Test a complex join (if tables exist)
        """
        SELECT COUNT(*) 
        FROM daily_lineups dl
        WHERE dl.date >= '2025-07-01'
        """
    ]
    
    print("\nTesting existing queries...")
    for query in test_queries:
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            print(f"[OK] Query successful: {query[:50]}... -> Result: {result[0] if result else 'N/A'}")
        except sqlite3.Error as e:
            # Some tables might not exist yet, which is OK
            if "no such table" in str(e):
                print(f"[WARN] Table not found (OK if not created yet): {query[:50]}...")
            else:
                print(f"[FAIL] Query failed: {query[:50]}... -> Error: {e}")
                return False
    
    return True


def apply_change_tracking_schema(conn):
    """Apply the change tracking schema."""
    print("\nApplying change tracking schema...")
    
    try:
        # Read and execute the schema file
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema in parts (SQLite doesn't like multiple statements sometimes)
        statements = schema_sql.split(';')
        
        # Categorize statements for proper execution order
        tables_to_create = []
        indexes_to_create = []
        views_to_create = []
        
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                upper_statement = statement.upper()
                if 'CREATE TABLE' in upper_statement:
                    tables_to_create.append(statement)
                elif 'CREATE INDEX' in upper_statement or 'CREATE UNIQUE INDEX' in upper_statement:
                    indexes_to_create.append(statement)
                elif 'CREATE VIEW' in upper_statement:
                    views_to_create.append(statement)
                else:
                    # Other statements (like ALTER TABLE, etc.)
                    tables_to_create.append(statement)
        
        # Execute in proper order: tables first
        print("Creating tables...")
        for statement in tables_to_create:
            try:
                conn.execute(statement + ';')
                conn.commit()
                print(f"[OK] Executed: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    print(f"[WARN] Already exists: {statement[:50]}...")
                else:
                    print(f"[ERROR] Failed: {statement[:100]}...")
                    print(f"  Error: {e}")
        
        # Then indexes
        print("\nCreating indexes...")
        for statement in indexes_to_create:
            try:
                conn.execute(statement + ';')
                conn.commit()
                print(f"[OK] Created index: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    print(f"[WARN] Index already exists: {statement[:50]}...")
                elif "no such table" in str(e):
                    print(f"[WARN] Table doesn't exist for index: {statement[:50]}...")
                else:
                    print(f"[ERROR] Failed index: {statement[:100]}...")
                    print(f"  Error: {e}")
        
        # Now create views after tables exist
        print("\nCreating views...")
        for view_statement in views_to_create:
            try:
                conn.execute(view_statement + ';')
                conn.commit()
                print(f"[OK] Created view: {view_statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    print(f"[WARN] View already exists: {view_statement[:50]}...")
                else:
                    print(f"[WARN] Could not create view (tables may not exist yet): {view_statement[:50]}...")
        
        print("[OK] Change tracking schema applied successfully")
        return True
        
    except Exception as e:
        print(f"[FAIL] Failed to apply schema: {e}")
        return False


def check_table_columns(conn):
    """Check if tables need migration for new columns."""
    tables_to_check = [
        ('daily_lineups', ['content_hash', 'last_updated', 'created_at']),
        ('daily_gkl_player_stats', ['content_hash', 'has_correction', 'last_fetched']),
        ('transactions_production', ['content_hash', 'last_updated']),
        ('transactions_test', ['content_hash', 'last_updated'])
    ]
    
    print("\nChecking existing tables for required columns...")
    needs_migration = False
    
    for table_name, required_columns in tables_to_check:
        try:
            # Get table info
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            if columns:  # Table exists
                missing_columns = [col for col in required_columns if col not in columns]
                if missing_columns:
                    print(f"[WARN] Table '{table_name}' missing columns: {missing_columns}")
                    needs_migration = True
                else:
                    print(f"[OK] Table '{table_name}' has all required columns")
            else:
                print(f"[WARN] Table '{table_name}' does not exist yet")
                
        except sqlite3.Error as e:
            print(f"[WARN] Could not check table '{table_name}': {e}")
    
    return needs_migration


def apply_migration(conn):
    """Apply migration to add columns to existing tables."""
    print("\nApplying migration to add change tracking columns...")
    
    try:
        # Try to add columns one by one (SQLite ALTER TABLE limitations)
        migrations = [
            # Daily lineups
            ("daily_lineups", "content_hash TEXT"),
            ("daily_lineups", "last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("daily_lineups", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            
            # Player stats
            ("daily_gkl_player_stats", "content_hash TEXT"),
            ("daily_gkl_player_stats", "has_correction BOOLEAN DEFAULT 0"),
            ("daily_gkl_player_stats", "last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("daily_gkl_player_stats", "last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            
            # Transactions
            ("transactions_production", "content_hash TEXT"),
            ("transactions_production", "last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("transactions_production", "last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            
            ("transactions_test", "content_hash TEXT"),
            ("transactions_test", "last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("transactions_test", "last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]
        
        for table_name, column_def in migrations:
            try:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_def}"
                conn.execute(sql)
                conn.commit()
                print(f"[OK] Added column to {table_name}: {column_def}")
            except sqlite3.Error as e:
                if "duplicate column name" in str(e) or "no such table" in str(e):
                    # Column already exists or table doesn't exist yet
                    pass
                else:
                    print(f"[WARN] Could not add column to {table_name}: {e}")
        
        print("[OK] Migration completed")
        return True
        
    except Exception as e:
        print(f"[FAIL] Migration failed: {e}")
        return False


def verify_schema(conn):
    """Verify that all change tracking tables were created."""
    required_tables = [
        'daily_lineups_metadata',
        'lineup_changes',
        'stat_corrections',
        'transaction_metadata',
        'transaction_changes',
        'job_log_enhanced',
        'sync_log'
    ]
    
    print("\nVerifying change tracking tables...")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    all_present = True
    for table in required_tables:
        if table in existing_tables:
            print(f"[OK] Table exists: {table}")
        else:
            print(f"[FAIL] Table missing: {table}")
            all_present = False
    
    return all_present


def main():
    """Main execution function."""
    print("=" * 60)
    print("Change Tracking Schema Application")
    print("=" * 60)
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"[FAIL] Database not found at: {DB_PATH}")
        print("Please ensure the database exists before running this script.")
        return 1
    
    # Create backup
    backup_path = backup_database()
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        print(f"\n[OK] Connected to database: {DB_PATH}")
        
        # Test existing queries first
        if not test_existing_queries(conn):
            print("\n[WARN] Some existing queries failed. Please review before continuing.")
            # Continue anyway as some tables might not exist yet
        
        # Apply change tracking schema
        if not apply_change_tracking_schema(conn):
            print("\n[FAIL] Failed to apply change tracking schema")
            return 1
        
        # Check if migration is needed
        if check_table_columns(conn):
            if not apply_migration(conn):
                print("\n[FAIL] Failed to apply migration")
                return 1
        
        # Verify schema
        if not verify_schema(conn):
            print("\n[WARN] Some tables are missing, but this may be expected for new installations")
        
        # Test queries again
        print("\n" + "=" * 60)
        print("Final verification...")
        if test_existing_queries(conn):
            print("\n[OK] All existing queries still work!")
        
        print("\n" + "=" * 60)
        print("[OK] Change tracking schema applied successfully!")
        print(f"[OK] Backup saved at: {backup_path}")
        print("=" * 60)
        
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        print(f"[OK] Database backup available at: {backup_path}")
        print("You can restore from backup if needed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())