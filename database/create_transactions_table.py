"""Create league_transactions table if it doesn't exist."""

import sqlite3
from pathlib import Path

def create_transactions_table():
    """Create the league_transactions table with indexes."""
    
    db_path = Path(__file__).parent / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS league_transactions (
            -- Primary identification
            transaction_id TEXT NOT NULL,
            league_key TEXT NOT NULL,
            season INTEGER NOT NULL,
            transaction_date DATE NOT NULL,
            
            -- Transaction details
            transaction_type TEXT NOT NULL,  -- 'add', 'drop', 'trade'
            team_key TEXT,
            team_name TEXT,
            player_id TEXT,
            player_name TEXT,
            
            -- Additional fields for trades
            from_team_key TEXT,
            to_team_key TEXT,
            
            -- Change tracking
            content_hash TEXT,
            
            -- Job tracking
            job_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (transaction_id, transaction_date, league_key)
        )
    """)
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON league_transactions(transaction_date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_league ON league_transactions(league_key)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_team ON league_transactions(team_key)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_player ON league_transactions(player_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON league_transactions(transaction_type)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_hash ON league_transactions(content_hash)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_job ON league_transactions(job_id)"
    ]
    
    for idx in indexes:
        cursor.execute(idx)
    
    conn.commit()
    
    # Check if table was created
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='league_transactions'
    """)
    
    if cursor.fetchone():
        print("[OK] league_transactions table created successfully")
        
        # Get table info
        cursor.execute("PRAGMA table_info(league_transactions)")
        columns = cursor.fetchall()
        print(f"    Columns: {len(columns)}")
        
        # Count existing records
        cursor.execute("SELECT COUNT(*) FROM league_transactions")
        count = cursor.fetchone()[0]
        print(f"    Records: {count}")
    else:
        print("[ERROR] Failed to create league_transactions table")
    
    conn.close()


if __name__ == "__main__":
    create_transactions_table()