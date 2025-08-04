"""
Create a minimal test database for GitHub Actions.
This creates the basic tables needed for incremental update scripts to run.
"""

import sqlite3
import os
from pathlib import Path

def create_test_database():
    """Create minimal database structure for testing."""
    
    # Create database directory if it doesn't exist
    db_dir = Path('database')
    db_dir.mkdir(exist_ok=True)
    
    db_path = db_dir / 'league_analytics.db'
    
    print(f"Creating test database at: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create minimal job_log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_log (
            job_id TEXT PRIMARY KEY,
            job_type TEXT,
            environment TEXT,
            status TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            date_range_start DATE,
            date_range_end DATE,
            league_key TEXT,
            records_processed INTEGER,
            records_inserted INTEGER,
            error_message TEXT,
            metadata TEXT
        )
    """)
    
    # Create minimal league_transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_transactions (
            transaction_id TEXT,
            league_key TEXT,
            season INTEGER,
            transaction_date DATE,
            transaction_type TEXT,
            team_key TEXT,
            team_name TEXT,
            player_id TEXT,
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
    
    # Create minimal daily_lineups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_lineups (
            job_id TEXT,
            season INTEGER,
            date DATE,
            team_key TEXT,
            team_name TEXT,
            player_id TEXT,
            player_name TEXT,
            selected_position TEXT
        )
    """)
    
    # Create minimal daily_lineups_metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_lineups_metadata (
            date DATE,
            team_key TEXT,
            content_hash TEXT,
            last_fetched TIMESTAMP,
            job_id TEXT,
            PRIMARY KEY (date, team_key)
        )
    """)
    
    # Create minimal daily_gkl_player_stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_gkl_player_stats (
            yahoo_player_id INTEGER,
            date DATE,
            content_hash TEXT,
            has_correction INTEGER DEFAULT 0,
            has_batting_data INTEGER DEFAULT 0,
            batting_hits INTEGER,
            batting_runs INTEGER,
            batting_rbis INTEGER,
            batting_home_runs INTEGER,
            batting_stolen_bases INTEGER
        )
    """)
    
    # Create minimal lineup_changes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lineup_changes (
            date DATE,
            team_key TEXT,
            old_hash TEXT,
            new_hash TEXT,
            change_type TEXT,
            players_added TEXT,
            players_removed TEXT,
            position_changes TEXT,
            job_id TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create minimal stat_corrections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stat_corrections (
            player_id INTEGER,
            date DATE,
            stat_category TEXT,
            stat_name TEXT,
            old_value TEXT,
            new_value TEXT,
            difference REAL,
            correction_source TEXT,
            job_id TEXT,
            correction_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # Add a few test records to prevent empty table errors
    cursor.execute("""
        INSERT OR IGNORE INTO league_transactions 
        (transaction_id, league_key, season, transaction_date, transaction_type, team_key, team_name, player_id, player_name, job_id)
        VALUES ('TEST001', 'mlb.l.6966', 2025, '2025-08-01', 'add', 'mlb.l.6966.t.1', 'Test Team 1', 'mlb.p.12345', 'Test Player', 'test_data')
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO daily_lineups
        (job_id, season, date, team_key, team_name, player_id, player_name, selected_position)
        VALUES ('test_data', 2025, '2025-08-01', 'mlb.l.6966.t.1', 'Test Team 1', 'mlb.p.12345', 'Test Player', 'C')
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO daily_gkl_player_stats
        (yahoo_player_id, date, has_batting_data, batting_hits, batting_runs, batting_rbis)
        VALUES (12345, '2025-08-01', 1, 2, 1, 1)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Test database created successfully")
    print(f"   Database size: {db_path.stat().st_size} bytes")

if __name__ == "__main__":
    create_test_database()