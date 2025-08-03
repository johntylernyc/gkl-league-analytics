#!/usr/bin/env python3
"""
Player Stats Schema Setup Script

Sets up the database schema for MLB player statistics data ingestion.
Creates all required tables, indexes, and views following the existing
database patterns and performance requirements.
"""

import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

# Add parent directories to path
parent_dir = Path(__file__).parent.parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerStatsSchemaManager:
    """Manages database schema setup and migrations for player stats."""
    
    def __init__(self, environment="production"):
        """
        Initialize schema manager.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.db_path = self.config['database_path']
        self.schema_file = parent_dir / "schema.sql"
        
        logger.info(f"Initialized PlayerStatsSchemaManager for {environment}")
        logger.info(f"Database path: {self.db_path}")
        
    def load_schema_sql(self) -> str:
        """Load the schema SQL from file."""
        if not self.schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_file}")
        
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        logger.info(f"Loaded schema SQL from {self.schema_file}")
        return schema_sql
    
    def apply_environment_naming(self, schema_sql: str) -> str:
        """Apply environment-specific table naming to schema SQL."""
        if self.environment == "test":
            # Replace table names with test versions
            tables_to_replace = [
                'mlb_batting_stats_staging',
                'mlb_pitching_stats_staging',
                'player_id_mapping',
                'daily_gkl_player_stats',
                'player_stats_schema_version'
            ]
            
            for table in tables_to_replace:
                # Replace CREATE TABLE statements
                schema_sql = schema_sql.replace(
                    f"CREATE TABLE IF NOT EXISTS {table}",
                    f"CREATE TABLE IF NOT EXISTS {table}_test"
                )
                
                # Replace CREATE INDEX statements
                schema_sql = schema_sql.replace(
                    f"ON {table}(",
                    f"ON {table}_test("
                )
                
                # Replace view references
                schema_sql = schema_sql.replace(
                    f"FROM {table}",
                    f"FROM {table}_test"
                )
                
                # Replace INSERT statements
                schema_sql = schema_sql.replace(
                    f"INTO {table}",
                    f"INTO {table}_test"
                )
        
        return schema_sql
    
    def check_existing_tables(self) -> dict:
        """Check which tables already exist in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND (name LIKE '%player%' OR name LIKE '%mlb%')
                ORDER BY name
            """)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' 
                AND (name LIKE '%player%' OR name LIKE '%mlb%' OR name LIKE '%gkl%')
                ORDER BY name
            """)
            
            existing_indexes = [row[0] for row in cursor.fetchall()]
            
            return {
                'tables': existing_tables,
                'indexes': existing_indexes
            }
            
        finally:
            conn.close()
    
    def validate_schema_integrity(self) -> dict:
        """Validate the schema integrity after setup."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        validation_results = {
            'tables_created': [],
            'indexes_created': [],
            'foreign_keys_valid': True,
            'constraints_valid': True,
            'errors': []
        }
        
        try:
            # Check created tables
            expected_tables = [
                self.config['batting_staging_table'],
                self.config['pitching_staging_table'],
                self.config['player_mapping_table'],
                self.config['gkl_player_stats_table']
            ]
            
            for table in expected_tables:
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table,))
                
                if cursor.fetchone()[0] > 0:
                    validation_results['tables_created'].append(table)
                else:
                    validation_results['errors'].append(f"Table not created: {table}")
            
            # Check foreign key integrity
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                validation_results['foreign_keys_valid'] = False
                validation_results['errors'].extend([
                    f"Foreign key violation: {violation}" for violation in fk_violations
                ])
            
            # Check critical indexes exist
            expected_indexes = [
                f"idx_gkl_stats_date",
                f"idx_gkl_stats_player", 
                f"idx_gkl_stats_player_date"
            ]
            
            for index_base in expected_indexes:
                index_name = f"{index_base}{'_test' if self.environment == 'test' else ''}"
                cursor.execute("""
                    SELECT COUNT(*) FROM sqlite_master 
                    WHERE type='index' AND name LIKE ?
                """, (f"%{index_base}%",))
                
                if cursor.fetchone()[0] > 0:
                    validation_results['indexes_created'].append(index_name)
                else:
                    validation_results['errors'].append(f"Index not created: {index_name}")
            
            logger.info(f"Schema validation completed with {len(validation_results['errors'])} errors")
            
        except Exception as e:
            validation_results['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"Schema validation failed: {e}")
            
        finally:
            conn.close()
        
        return validation_results
    
    def setup_schema(self, force=False) -> dict:
        """
        Set up the complete database schema.
        
        Args:
            force: If True, recreate tables even if they exist
            
        Returns:
            Dictionary with setup results
        """
        logger.info(f"Starting schema setup for {self.environment} environment")
        
        results = {
            'success': False,
            'tables_created': [],
            'indexes_created': [],
            'errors': [],
            'start_time': datetime.now().isoformat()
        }
        
        try:
            # Check existing state
            existing = self.check_existing_tables()
            logger.info(f"Found {len(existing['tables'])} existing tables, {len(existing['indexes'])} existing indexes")
            
            if existing['tables'] and not force:
                logger.warning("Tables already exist. Use --force to recreate.")
                results['errors'].append("Tables already exist. Use --force to recreate.")
                return results
            
            # Load and prepare schema
            schema_sql = self.load_schema_sql()
            schema_sql = self.apply_environment_naming(schema_sql)
            
            # Execute schema creation
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            
            try:
                # Split SQL into individual statements - handle multi-line statements properly
                all_statements = []
                current_statement = ""
                in_comment_block = False
                
                for line in schema_sql.split('\n'):
                    original_line = line
                    line = line.strip()
                    
                    # Handle multi-line comments
                    if line.startswith('/*'):
                        in_comment_block = True
                        continue
                    if line.endswith('*/'):
                        in_comment_block = False
                        continue
                    if in_comment_block:
                        continue
                    
                    # Skip single-line comments and empty lines
                    if not line or line.startswith('--'):
                        continue
                    
                    # Remove inline comments (-- comment)
                    if '--' in line:
                        line = line.split('--')[0].strip()
                        if not line:  # Line was only a comment
                            continue
                    
                    # Add line to current statement
                    if current_statement:
                        current_statement += " " + line
                    else:
                        current_statement = line
                    
                    # Check if statement is complete (ends with semicolon)
                    if line.endswith(';'):
                        stmt = current_statement.strip()
                        if stmt.endswith(';'):
                            stmt = stmt[:-1].strip()  # Remove semicolon
                        if stmt:
                            all_statements.append(stmt)
                            logger.debug(f"Parsed statement: {stmt[:50]}...")
                        current_statement = ""
                
                # Separate CREATE TABLE and CREATE INDEX statements for proper ordering
                table_statements = [stmt for stmt in all_statements if 'CREATE TABLE' in stmt.upper()]
                index_statements = [stmt for stmt in all_statements if 'CREATE INDEX' in stmt.upper()]
                view_statements = [stmt for stmt in all_statements if 'CREATE VIEW' in stmt.upper()]
                insert_statements = [stmt for stmt in all_statements if 'INSERT' in stmt.upper()]
                
                # Execute in order: tables, indexes, views, inserts
                ordered_statements = table_statements + index_statements + view_statements + insert_statements
                
                logger.info(f"Executing {len(ordered_statements)} SQL statements ({len(table_statements)} tables, {len(index_statements)} indexes)")
                
                # Debug: show first few statements
                for i, stmt in enumerate(ordered_statements[:5]):
                    logger.debug(f"Statement {i+1}: {stmt[:100]}...")
                
                for i, statement in enumerate(ordered_statements):
                    try:
                        # Add semicolon back and execute
                        full_statement = statement + ";"
                        conn.execute(full_statement)
                        conn.commit()  # Commit each statement individually
                        
                        if 'CREATE TABLE' in statement.upper():
                            table_name = statement.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                            results['tables_created'].append(table_name)
                            logger.info(f"Created table: {table_name}")
                        elif 'CREATE INDEX' in statement.upper():
                            index_name = statement.split('CREATE INDEX IF NOT EXISTS')[1].split('ON')[0].strip()
                            results['indexes_created'].append(index_name)
                            logger.debug(f"Created index: {index_name}")
                    except sqlite3.Error as e:
                        error_msg = f"Error in statement {i+1} ({statement[:50]}...): {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                conn.commit()
                logger.info("Schema creation completed successfully")
                
                # Validate the schema
                validation = self.validate_schema_integrity()
                if validation['errors']:
                    results['errors'].extend(validation['errors'])
                else:
                    results['success'] = True
                    
            finally:
                conn.close()
            
        except Exception as e:
            error_msg = f"Schema setup failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        results['end_time'] = datetime.now().isoformat()
        
        return results
    
    def drop_schema(self) -> dict:
        """
        Drop all player stats tables and indexes.
        
        WARNING: This will delete all player stats data!
        
        Returns:
            Dictionary with drop results
        """
        logger.warning(f"Dropping player stats schema for {self.environment} environment")
        
        results = {
            'success': False,
            'tables_dropped': [],
            'indexes_dropped': [],
            'errors': []
        }
        
        try:
            existing = self.check_existing_tables()
            
            conn = sqlite3.connect(self.db_path)
            try:
                # Drop tables
                for table in existing['tables']:
                    try:
                        conn.execute(f"DROP TABLE IF EXISTS {table}")
                        results['tables_dropped'].append(table)
                        logger.info(f"Dropped table: {table}")
                    except sqlite3.Error as e:
                        error_msg = f"Error dropping table {table}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                # Drop indexes (tables will drop their indexes automatically, but manual indexes)
                for index in existing['indexes']:
                    try:
                        conn.execute(f"DROP INDEX IF EXISTS {index}")
                        results['indexes_dropped'].append(index)
                        logger.info(f"Dropped index: {index}")
                    except sqlite3.Error as e:
                        error_msg = f"Error dropping index {index}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                conn.commit()
                results['success'] = True
                logger.info("Schema drop completed successfully")
                
            finally:
                conn.close()
                
        except Exception as e:
            error_msg = f"Schema drop failed: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results


def main():
    """Command-line interface for schema management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Player Stats Database Schema Management")
    parser.add_argument("action", choices=["setup", "drop", "validate", "status"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--force", action="store_true",
                       help="Force recreation of existing tables")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = PlayerStatsSchemaManager(environment=args.env)
    
    if args.action == "setup":
        print(f"Setting up player stats schema for {args.env} environment...")
        print("-" * 60)
        
        results = manager.setup_schema(force=args.force)
        
        if results['success']:
            print("[SUCCESS] Schema setup completed successfully!")
            print(f"Created {len(results['tables_created'])} tables")
            print(f"Created {len(results['indexes_created'])} indexes")
        else:
            print("[FAILED] Schema setup failed!")
            for error in results['errors']:
                print(f"  ERROR: {error}")
        
    elif args.action == "drop":
        print(f"[WARNING] This will delete all player stats data!")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() == 'yes':
            print(f"Dropping player stats schema for {args.env} environment...")
            print("-" * 60)
            
            results = manager.drop_schema()
            
            if results['success']:
                print("[SUCCESS] Schema drop completed successfully!")
                print(f"Dropped {len(results['tables_dropped'])} tables")
                print(f"Dropped {len(results['indexes_dropped'])} indexes")
            else:
                print("[FAILED] Schema drop failed!")
                for error in results['errors']:
                    print(f"  ERROR: {error}")
        else:
            print("Schema drop cancelled.")
    
    elif args.action == "validate":
        print(f"Validating player stats schema for {args.env} environment...")
        print("-" * 60)
        
        validation = manager.validate_schema_integrity()
        
        if not validation['errors']:
            print("[SUCCESS] Schema validation passed!")
            print(f"Found {len(validation['tables_created'])} tables")
            print(f"Found {len(validation['indexes_created'])} indexes")
        else:
            print("[FAILED] Schema validation failed!")
            for error in validation['errors']:
                print(f"  ERROR: {error}")
    
    elif args.action == "status":
        print(f"Player stats schema status for {args.env} environment:")
        print("-" * 60)
        
        existing = manager.check_existing_tables()
        
        print(f"Database: {manager.db_path}")
        print(f"Existing tables ({len(existing['tables'])}):")
        for table in existing['tables']:
            print(f"  - {table}")
        
        print(f"Existing indexes ({len(existing['indexes'])}):")
        for index in existing['indexes']:
            print(f"  - {index}")
        
        if existing['tables']:
            validation = manager.validate_schema_integrity()
            if validation['errors']:
                print("\n[WARNING] Schema validation issues:")
                for error in validation['errors']:
                    print(f"  - {error}")
            else:
                print("\n[SUCCESS] Schema validation passed!")


if __name__ == "__main__":
    main()