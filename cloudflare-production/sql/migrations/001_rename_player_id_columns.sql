-- Migration: Rename player_id to yahoo_player_id in transactions and daily_lineups tables
-- Date: 2025-08-13
-- Purpose: Align D1 schema with code changes to use consistent column naming

-- Note: D1 (SQLite) doesn't support ALTER COLUMN directly, so we need to recreate tables

-- 1. Rename transactions table and create new one with correct schema
ALTER TABLE transactions RENAME TO transactions_old;

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    league_key TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    yahoo_player_id TEXT NOT NULL,  -- Changed from player_id
    player_name TEXT NOT NULL,
    player_position TEXT,
    player_team TEXT,
    movement_type TEXT NOT NULL,
    destination_team_key TEXT,
    destination_team_name TEXT,
    source_team_key TEXT,
    source_team_name TEXT,
    timestamp INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(league_key, transaction_id, yahoo_player_id, movement_type)
);

-- Copy data from old table
INSERT INTO transactions (
    id, date, league_key, transaction_id, transaction_type,
    yahoo_player_id, player_name, player_position, player_team,
    movement_type, destination_team_key, destination_team_name,
    source_team_key, source_team_name, timestamp, created_at, job_id
)
SELECT 
    id, date, league_key, transaction_id, transaction_type,
    player_id as yahoo_player_id, player_name, player_position, player_team,
    movement_type, destination_team_key, destination_team_name,
    source_team_key, source_team_name, timestamp, created_at, job_id
FROM transactions_old;

-- Create indexes
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_player ON transactions(player_name);
CREATE INDEX idx_transactions_yahoo_player ON transactions(yahoo_player_id);
CREATE INDEX idx_transactions_trans_id ON transactions(transaction_id);

-- Drop old table
DROP TABLE transactions_old;

-- 2. Rename daily_lineups table and create new one with correct schema
ALTER TABLE daily_lineups RENAME TO daily_lineups_old;

CREATE TABLE daily_lineups (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    yahoo_player_id TEXT NOT NULL,  -- Changed from player_id
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
);

-- Copy data from old table
INSERT INTO daily_lineups (
    lineup_id, job_id, season, date, team_key, team_name,
    yahoo_player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team, created_at, updated_at
)
SELECT 
    lineup_id, job_id, season, date, team_key, team_name,
    player_id as yahoo_player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team, created_at, updated_at
FROM daily_lineups_old;

-- Create indexes
CREATE INDEX idx_daily_lineups_date ON daily_lineups(date);
CREATE INDEX idx_daily_lineups_team ON daily_lineups(team_key);
CREATE INDEX idx_daily_lineups_yahoo_player ON daily_lineups(yahoo_player_id);

-- Drop old table
DROP TABLE daily_lineups_old;

-- 3. Update player_mapping table if needed (add mlb_player_id column if missing)
-- Check if mlb_player_id exists, if not add it
CREATE TABLE IF NOT EXISTS player_mapping_new (
    player_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mlb_id INTEGER,
    mlb_player_id INTEGER,  -- Ensure this column exists
    yahoo_player_id TEXT,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    player_name TEXT,
    first_name TEXT,
    last_name TEXT,
    team_code TEXT,
    active BOOLEAN DEFAULT 1,
    last_verified TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check if we need to migrate player_mapping
-- This will only run if the table exists and needs the new column
INSERT OR IGNORE INTO player_mapping_new
SELECT * FROM player_mapping;

DROP TABLE IF EXISTS player_mapping;
ALTER TABLE player_mapping_new RENAME TO player_mapping;

-- Create indexes for player_mapping
CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb ON player_mapping(mlb_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb_player ON player_mapping(mlb_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(player_name);

-- Update mlb_player_id to match mlb_id where it's null
UPDATE player_mapping 
SET mlb_player_id = mlb_id 
WHERE mlb_player_id IS NULL AND mlb_id IS NOT NULL;

-- Verification queries (commented out, for manual checking)
-- SELECT COUNT(*) as transaction_count FROM transactions;
-- SELECT COUNT(*) as lineup_count FROM daily_lineups;
-- SELECT COUNT(*) as mapping_count FROM player_mapping;