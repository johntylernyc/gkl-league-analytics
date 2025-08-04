-- Schema for league transactions with change tracking
-- This table stores all fantasy league transaction data

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
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_date 
    ON league_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_league 
    ON league_transactions(league_key);
CREATE INDEX IF NOT EXISTS idx_transactions_team 
    ON league_transactions(team_key);
CREATE INDEX IF NOT EXISTS idx_transactions_player 
    ON league_transactions(player_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type 
    ON league_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_hash 
    ON league_transactions(content_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_job 
    ON league_transactions(job_id);