#!/usr/bin/env python3
"""
Apply column name migration to local SQLite database
Date: 2025-08-13
"""

import sqlite3
import sys
from pathlib import Path

def apply_migration():
    """Apply the column name migration to the local database."""
    
    # Database path
    db_path = Path("R:/GitHub/gkl-league-analytics/database/league_analytics.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting column name migration...")
        
        # Drop views that depend on tables we're modifying
        print("\nDropping dependent views...")
        views_to_drop = [
            'v_player_stats_mapped',
            'v_current_lineups', 
            'v_player_frequency',
            'v_team_daily_summary'
        ]
        for view in views_to_drop:
            try:
                cursor.execute(f"DROP VIEW IF EXISTS {view}")
                print(f"   Dropped view: {view}")
            except:
                pass
        
        # Check current schema first
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='league_transactions'")
        result = cursor.fetchone()
        if result and 'player_id' in result[0] and 'yahoo_player_id' not in result[0]:
            print("\n1. Fixing league_transactions table...")
            
            # Create new table with correct column name
            cursor.execute("""
                CREATE TABLE league_transactions_new (
                    transaction_id TEXT NOT NULL,
                    league_key TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    transaction_date DATE NOT NULL,
                    transaction_type TEXT NOT NULL,
                    team_key TEXT,
                    team_name TEXT,
                    yahoo_player_id TEXT,
                    player_name TEXT,
                    from_team_key TEXT,
                    to_team_key TEXT,
                    content_hash TEXT,
                    job_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (transaction_id, transaction_date, league_key)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO league_transactions_new
                SELECT transaction_id, league_key, season, transaction_date, transaction_type,
                       team_key, team_name, player_id, player_name,
                       from_team_key, to_team_key, content_hash, job_id, created_at, updated_at
                FROM league_transactions
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE league_transactions")
            cursor.execute("ALTER TABLE league_transactions_new RENAME TO league_transactions")
            
            # Recreate indexes
            cursor.execute("CREATE INDEX idx_transactions_yahoo_player ON league_transactions(yahoo_player_id)")
            cursor.execute("CREATE INDEX idx_transactions_date ON league_transactions(transaction_date)")
            cursor.execute("CREATE INDEX idx_transactions_league ON league_transactions(league_key)")
            cursor.execute("CREATE INDEX idx_transactions_team ON league_transactions(team_key)")
            cursor.execute("CREATE INDEX idx_transactions_type ON league_transactions(transaction_type)")
            cursor.execute("CREATE INDEX idx_transactions_hash ON league_transactions(content_hash)")
            cursor.execute("CREATE INDEX idx_transactions_job ON league_transactions(job_id)")
            
            print("   [OK] league_transactions table updated")
        else:
            print("   [OK] league_transactions already has yahoo_player_id column")
        
        # Check and fix daily_lineups
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_lineups'")
        result = cursor.fetchone()
        if result and 'player_id' in result[0] and 'yahoo_player_id' not in result[0]:
            print("\n2. Fixing daily_lineups table...")
            
            # Drop any leftover temporary table
            cursor.execute("DROP TABLE IF EXISTS daily_lineups_new")
            
            # Create new table
            cursor.execute("""
                CREATE TABLE daily_lineups_new (
                    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    date DATE NOT NULL,
                    team_key TEXT NOT NULL,
                    team_name TEXT NOT NULL,
                    yahoo_player_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    selected_position TEXT,
                    position_type TEXT,
                    player_status TEXT,
                    eligible_positions TEXT,
                    player_team TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
                    UNIQUE(date, team_key, yahoo_player_id, selected_position)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO daily_lineups_new
                SELECT lineup_id, job_id, season, date, team_key, team_name,
                       player_id, player_name, selected_position, position_type,
                       player_status, eligible_positions, player_team, created_at, updated_at
                FROM daily_lineups
            """)
            
            # Drop old and rename new
            cursor.execute("DROP TABLE daily_lineups")
            cursor.execute("ALTER TABLE daily_lineups_new RENAME TO daily_lineups")
            
            # Recreate indexes
            cursor.execute("CREATE INDEX idx_lineups_date ON daily_lineups(date)")
            cursor.execute("CREATE INDEX idx_lineups_team ON daily_lineups(team_key)")
            cursor.execute("CREATE INDEX idx_lineups_yahoo_player ON daily_lineups(yahoo_player_id)")
            cursor.execute("CREATE INDEX idx_lineups_date_team ON daily_lineups(date, team_key)")
            cursor.execute("CREATE INDEX idx_lineups_team_date ON daily_lineups(team_key, date)")
            cursor.execute("CREATE INDEX idx_lineups_yahoo_player_date ON daily_lineups(yahoo_player_id, date)")
            cursor.execute("CREATE INDEX idx_lineups_position ON daily_lineups(selected_position)")
            cursor.execute("CREATE INDEX idx_lineups_season ON daily_lineups(season)")
            cursor.execute("CREATE INDEX idx_lineups_job ON daily_lineups(job_id)")
            
            print("   [OK] daily_lineups table updated")
        else:
            print("   [OK] daily_lineups already has yahoo_player_id column")
        
        # Check and fix daily_lineups_test
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_lineups_test'")
        result = cursor.fetchone()
        if result and 'player_id' in result[0] and 'yahoo_player_id' not in result[0]:
            print("\n3. Fixing daily_lineups_test table...")
            
            # Drop any leftover temporary table
            cursor.execute("DROP TABLE IF EXISTS daily_lineups_test_new")
            
            # Create new table
            cursor.execute("""
                CREATE TABLE daily_lineups_test_new (
                    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    date DATE NOT NULL,
                    team_key TEXT NOT NULL,
                    team_name TEXT NOT NULL,
                    yahoo_player_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    selected_position TEXT,
                    position_type TEXT,
                    player_status TEXT,
                    eligible_positions TEXT,
                    player_team TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
                    UNIQUE(date, team_key, yahoo_player_id, selected_position)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO daily_lineups_test_new
                SELECT lineup_id, job_id, season, date, team_key, team_name,
                       player_id, player_name, selected_position, position_type,
                       player_status, eligible_positions, player_team, created_at, updated_at
                FROM daily_lineups_test
            """)
            
            # Drop old and rename new
            cursor.execute("DROP TABLE daily_lineups_test")
            cursor.execute("ALTER TABLE daily_lineups_test_new RENAME TO daily_lineups_test")
            
            print("   [OK] daily_lineups_test table updated")
        else:
            print("   [OK] daily_lineups_test already has yahoo_player_id column")
        
        # Check and fix player_mapping
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='player_mapping'")
        result = cursor.fetchone()
        if result and 'mlb_id' in result[0] and 'mlb_player_id' not in result[0]:
            print("\n4. Fixing player_mapping table...")
            
            # Drop any leftover temporary table
            cursor.execute("DROP TABLE IF EXISTS player_mapping_new")
            
            # Create new table
            cursor.execute("""
                CREATE TABLE player_mapping_new (
                    player_mapping_id INTEGER PRIMARY KEY,
                    mlb_player_id INTEGER UNIQUE NOT NULL,
                    yahoo_player_id INTEGER,
                    baseball_reference_id TEXT,
                    fangraphs_id TEXT,
                    player_name TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    team_code TEXT,
                    active BOOLEAN DEFAULT 1,
                    last_verified DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(first_name, last_name, mlb_player_id)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO player_mapping_new
                SELECT player_mapping_id, mlb_id, yahoo_player_id, baseball_reference_id,
                       fangraphs_id, player_name, first_name, last_name, team_code,
                       active, last_verified, created_at, updated_at
                FROM player_mapping
            """)
            
            # Drop old and rename new
            cursor.execute("DROP TABLE player_mapping")
            cursor.execute("ALTER TABLE player_mapping_new RENAME TO player_mapping")
            
            # Recreate indexes (drop first to be safe)
            cursor.execute("DROP INDEX IF EXISTS idx_player_mapping_yahoo")
            cursor.execute("DROP INDEX IF EXISTS idx_player_mapping_name")
            cursor.execute("DROP INDEX IF EXISTS idx_player_mapping_mlb_player")
            cursor.execute("DROP INDEX IF EXISTS idx_player_mapping_mlb")
            cursor.execute("DROP INDEX IF EXISTS idx_player_mapping_active")
            
            cursor.execute("CREATE INDEX idx_player_mapping_yahoo ON player_mapping(yahoo_player_id)")
            cursor.execute("CREATE INDEX idx_player_mapping_name ON player_mapping(last_name, first_name)")
            cursor.execute("CREATE INDEX idx_player_mapping_mlb_player ON player_mapping(mlb_player_id)")
            cursor.execute("CREATE INDEX idx_player_mapping_active ON player_mapping(active)")
            
            print("   [OK] player_mapping table updated")
        else:
            print("   [OK] player_mapping already has mlb_player_id column")
        
        # Check player_usage_summary
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='player_usage_summary'")
        result = cursor.fetchone()
        if result and 'player_id' in result[0] and 'yahoo_player_id' not in result[0]:
            print("\n5. Fixing player_usage_summary table...")
            
            # Drop any leftover temporary table
            cursor.execute("DROP TABLE IF EXISTS player_usage_summary_new")
            
            # Create new table
            cursor.execute("""
                CREATE TABLE player_usage_summary_new (
                    yahoo_player_id TEXT NOT NULL,
                    team_key TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    total_days INTEGER DEFAULT 0,
                    days_started INTEGER DEFAULT 0,
                    days_benched INTEGER DEFAULT 0,
                    days_injured INTEGER DEFAULT 0,
                    start_percentage REAL,
                    primary_position TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (yahoo_player_id, team_key, season)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO player_usage_summary_new
                SELECT player_id, team_key, season, total_days, days_started, days_benched,
                       days_injured, start_percentage, primary_position, last_updated
                FROM player_usage_summary
            """)
            
            # Drop old and rename new
            cursor.execute("DROP TABLE player_usage_summary")
            cursor.execute("ALTER TABLE player_usage_summary_new RENAME TO player_usage_summary")
            
            # Recreate index
            cursor.execute("CREATE INDEX idx_usage_yahoo_player ON player_usage_summary(yahoo_player_id)")
            cursor.execute("CREATE INDEX idx_usage_team ON player_usage_summary(team_key)")
            
            print("   [OK] player_usage_summary table updated")
        else:
            print("   [OK] player_usage_summary already has yahoo_player_id column")
        
        # Recreate views with updated column names
        print("\n6. Recreating views with new column names...")
        
        # v_current_lineups
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_current_lineups AS
            SELECT 
                dl.*,
                lp.position_name,
                lp.position_type as position_category,
                lp.display_order
            FROM daily_lineups dl
            LEFT JOIN lineup_positions lp ON dl.selected_position = lp.position_code
            WHERE dl.season = (SELECT MAX(season) FROM daily_lineups)
        """)
        print("   [OK] v_current_lineups recreated")
        
        # v_player_frequency
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_player_frequency AS
            SELECT 
                yahoo_player_id,
                player_name,
                team_key,
                team_name,
                season,
                COUNT(*) as total_days,
                SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) as days_started,
                SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as days_benched,
                ROUND(100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) / COUNT(*), 2) as start_percentage
            FROM daily_lineups
            GROUP BY yahoo_player_id, team_key, season
        """)
        print("   [OK] v_player_frequency recreated")
        
        # v_team_daily_summary
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_team_daily_summary AS
            SELECT 
                date,
                team_key,
                team_name,
                season,
                COUNT(DISTINCT CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN yahoo_player_id END) as starters_count,
                COUNT(DISTINCT CASE WHEN selected_position = 'BN' THEN yahoo_player_id END) as bench_count,
                COUNT(DISTINCT CASE WHEN selected_position IN ('IL', 'NA') THEN yahoo_player_id END) as inactive_count,
                COUNT(DISTINCT yahoo_player_id) as total_roster_size
            FROM daily_lineups
            GROUP BY date, team_key, season
        """)
        print("   [OK] v_team_daily_summary recreated")
        
        # v_player_stats_mapped (if daily_gkl_player_stats exists with proper columns)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_gkl_player_stats'")
        if cursor.fetchone():
            cursor.execute("""
                CREATE VIEW IF NOT EXISTS v_player_stats_mapped AS
                SELECT 
                    ps.*,
                    pm.first_name,
                    pm.last_name,
                    pm.active as player_active
                FROM daily_gkl_player_stats ps
                JOIN player_mapping pm ON ps.mlb_player_id = pm.mlb_player_id
            """)
            print("   [OK] v_player_stats_mapped recreated")
        
        # Commit changes
        conn.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        
        # Verify the changes
        print("\nVerifying changes...")
        cursor.execute("SELECT COUNT(*) FROM league_transactions")
        tx_count = cursor.fetchone()[0]
        print(f"   - league_transactions: {tx_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM daily_lineups")
        lineup_count = cursor.fetchone()[0]
        print(f"   - daily_lineups: {lineup_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM player_mapping")
        mapping_count = cursor.fetchone()[0]
        print(f"   - player_mapping: {mapping_count} records")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)