-- Simple migration to fix column names in D1
-- This approach creates new tables without dropping data

-- 1. Create new transactions table with correct column names
CREATE TABLE IF NOT EXISTS transactions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    league_key TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    yahoo_player_id TEXT NOT NULL,
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

-- 2. Copy existing data if old table exists
INSERT OR IGNORE INTO transactions_new (
    date, league_key, transaction_id, transaction_type,
    yahoo_player_id, player_name, player_position, player_team,
    movement_type, destination_team_key, destination_team_name,
    source_team_key, source_team_name, timestamp, job_id
)
SELECT 
    date, league_key, transaction_id, transaction_type,
    player_id, player_name, player_position, player_team,
    movement_type, destination_team_key, destination_team_name,
    source_team_key, source_team_name, timestamp, job_id
FROM transactions
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='transactions');

-- 3. Create new daily_lineups table with correct column names
CREATE TABLE IF NOT EXISTS daily_lineups_new (
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
);

-- 4. Copy existing data if old table exists
INSERT OR IGNORE INTO daily_lineups_new (
    job_id, season, date, team_key, team_name,
    yahoo_player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team
)
SELECT 
    job_id, season, date, team_key, team_name,
    player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team
FROM daily_lineups
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='daily_lineups');

-- 5. Drop old tables and rename new ones
DROP TABLE IF EXISTS transactions;
ALTER TABLE transactions_new RENAME TO transactions;

DROP TABLE IF EXISTS daily_lineups;
ALTER TABLE daily_lineups_new RENAME TO daily_lineups;

-- 6. Create indexes
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_yahoo_player ON transactions(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_daily_lineups_date ON daily_lineups(date);
CREATE INDEX IF NOT EXISTS idx_daily_lineups_yahoo_player ON daily_lineups(yahoo_player_id);