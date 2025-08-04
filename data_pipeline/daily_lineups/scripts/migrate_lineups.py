"""
Database migration script for Daily Lineups module.
Handles schema updates and data migrations.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class LineupMigration:
    """Manages database migrations for the Daily Lineups module."""
    
    def __init__(self, db_path=None):
        """Initialize migration manager."""
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "database" / "league_analytics.db"
        
        self.db_path = db_path
        self.migration_table = "lineup_migrations"
        self._ensure_migration_table()
    
    def _ensure_migration_table(self):
        """Create migration tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lineup_migrations (
                migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed'
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_current_version(self):
        """Get the current schema version."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version FROM lineup_migrations 
            ORDER BY migration_id DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else "0.0.0"
    
    def apply_migration(self, version, description, migration_sql):
        """Apply a migration to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if migration already applied
            cursor.execute(
                "SELECT 1 FROM lineup_migrations WHERE version = ?",
                (version,)
            )
            
            if cursor.fetchone():
                print(f"[SKIP] Migration {version} already applied")
                return False
            
            # Apply migration
            print(f"[APPLYING] Migration {version}: {description}")
            cursor.executescript(migration_sql)
            
            # Record migration
            cursor.execute("""
                INSERT INTO lineup_migrations (version, description)
                VALUES (?, ?)
            """, (version, description))
            
            conn.commit()
            print(f"[OK] Migration {version} completed")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Migration {version} failed: {e}")
            
            # Record failed migration
            cursor.execute("""
                INSERT INTO lineup_migrations (version, description, status)
                VALUES (?, ?, 'failed')
            """, (version, f"{description} - ERROR: {str(e)}"))
            
            conn.commit()
            raise
            
        finally:
            conn.close()
    
    def run_migrations(self):
        """Run all pending migrations."""
        migrations = self.get_migrations()
        applied_count = 0
        
        for migration in migrations:
            if self.apply_migration(**migration):
                applied_count += 1
        
        if applied_count == 0:
            print("[INFO] No new migrations to apply")
        else:
            print(f"[OK] Applied {applied_count} migration(s)")
        
        print(f"[INFO] Current version: {self.get_current_version()}")
    
    def get_migrations(self):
        """Define all migrations."""
        return [
            {
                "version": "1.0.0",
                "description": "Initial Daily Lineups schema",
                "migration_sql": """
                    -- This migration is handled by schema.sql
                    -- Recording it for version tracking
                    SELECT 1;
                """
            },
            {
                "version": "1.0.1",
                "description": "Add player_team column for MLB team tracking",
                "migration_sql": """
                    -- Add MLB team column to daily_lineups
                    ALTER TABLE daily_lineups 
                    ADD COLUMN player_team TEXT;
                    
                    -- Add to test table
                    ALTER TABLE daily_lineups_test 
                    ADD COLUMN player_team TEXT;
                    
                    -- Add index for MLB team queries
                    CREATE INDEX IF NOT EXISTS idx_lineups_player_team 
                    ON daily_lineups(player_team);
                    
                    CREATE INDEX IF NOT EXISTS idx_lineups_test_player_team 
                    ON daily_lineups_test(player_team);
                """
            },
            {
                "version": "1.0.2",
                "description": "Add game_info tracking for daily matchups",
                "migration_sql": """
                    -- Create game info table
                    CREATE TABLE IF NOT EXISTS daily_game_info (
                        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        player_id TEXT NOT NULL,
                        opponent TEXT,
                        is_home BOOLEAN,
                        game_started BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, player_id)
                    );
                    
                    -- Add index for game lookups
                    CREATE INDEX IF NOT EXISTS idx_game_info_date 
                    ON daily_game_info(date);
                    
                    CREATE INDEX IF NOT EXISTS idx_game_info_player 
                    ON daily_game_info(player_id);
                """
            }
        ]
    
    def rollback(self, version):
        """Rollback to a specific version (not implemented)."""
        print(f"[WARNING] Rollback to {version} not implemented")
        print("[INFO] Please restore from backup if rollback is needed")
    
    def status(self):
        """Show migration status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT version, description, applied_at, status
            FROM lineup_migrations
            ORDER BY migration_id DESC
            LIMIT 10
        """)
        
        migrations = cursor.fetchall()
        conn.close()
        
        print("\nMigration History:")
        print("-" * 80)
        print(f"{'Version':<10} {'Status':<10} {'Applied At':<20} {'Description':<40}")
        print("-" * 80)
        
        for migration in migrations:
            version, desc, applied_at, status = migration
            desc_short = desc[:37] + "..." if len(desc) > 40 else desc
            print(f"{version:<10} {status:<10} {applied_at:<20} {desc_short:<40}")
        
        print(f"\nCurrent Version: {self.get_current_version()}")


def main():
    """Run migrations from command line."""
    import sys
    
    migration = LineupMigration()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            migration.status()
        elif command == "migrate":
            migration.run_migrations()
        elif command == "version":
            print(f"Current version: {migration.get_current_version()}")
        elif command == "rollback" and len(sys.argv) > 2:
            migration.rollback(sys.argv[2])
        else:
            print("Usage: python migrate_lineups.py [status|migrate|version|rollback <version>]")
    else:
        # Default action is to run migrations
        migration.run_migrations()


if __name__ == "__main__":
    main()