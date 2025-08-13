-- Migration: Fix Column Naming Inconsistencies for Cloudflare D1
-- Date: 2025-08-13
-- Purpose: Standardize player ID column names across all tables
--
-- D1 Note: ALTER TABLE RENAME COLUMN is not supported in D1
-- We need to recreate tables with correct column names

-- ============================================
-- STEP 1: Create new tables with correct column names
-- ============================================

-- Create new transactions table with yahoo_player_id
CREATE TABLE league_transactions_new (
    transaction_id TEXT NOT NULL,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type TEXT NOT NULL,
    team_key TEXT,
    team_name TEXT,
    yahoo_player_id TEXT,  -- Changed from player_id
    player_name TEXT,
    from_team_key TEXT,
    to_team_key TEXT,
    content_hash TEXT,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (transaction_id, transaction_date, league_key)
);

-- Create new daily_lineups table with yahoo_player_id
CREATE TABLE daily_lineups_new (
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

-- ============================================
-- STEP 2: Copy data from old tables to new
-- ============================================

-- Copy transactions data
INSERT INTO league_transactions_new (
    transaction_id, league_key, season, transaction_date, transaction_type,
    team_key, team_name, yahoo_player_id, player_name,
    from_team_key, to_team_key, content_hash, job_id, created_at, updated_at
)
SELECT 
    transaction_id, league_key, season, transaction_date, transaction_type,
    team_key, team_name, player_id, player_name,
    from_team_key, to_team_key, content_hash, job_id, created_at, updated_at
FROM league_transactions;

-- Copy daily_lineups data
INSERT INTO daily_lineups_new (
    lineup_id, job_id, season, date, team_key, team_name,
    yahoo_player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team, created_at, updated_at
)
SELECT 
    lineup_id, job_id, season, date, team_key, team_name,
    player_id, player_name, selected_position, position_type,
    player_status, eligible_positions, player_team, created_at, updated_at
FROM daily_lineups;

-- ============================================
-- STEP 3: Drop old tables and rename new ones
-- ============================================

-- Drop old tables
DROP TABLE league_transactions;
DROP TABLE daily_lineups;

-- Rename new tables
ALTER TABLE league_transactions_new RENAME TO league_transactions;
ALTER TABLE daily_lineups_new RENAME TO daily_lineups;

-- ============================================
-- STEP 4: Recreate indexes with new column names
-- ============================================

-- Transactions indexes
CREATE INDEX idx_transactions_date ON league_transactions(transaction_date);
CREATE INDEX idx_transactions_league ON league_transactions(league_key);
CREATE INDEX idx_transactions_team ON league_transactions(team_key);
CREATE INDEX idx_transactions_yahoo_player ON league_transactions(yahoo_player_id);
CREATE INDEX idx_transactions_type ON league_transactions(transaction_type);
CREATE INDEX idx_transactions_hash ON league_transactions(content_hash);
CREATE INDEX idx_transactions_job ON league_transactions(job_id);

-- Daily lineups indexes
CREATE INDEX idx_lineups_date ON daily_lineups(date);
CREATE INDEX idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX idx_lineups_yahoo_player ON daily_lineups(yahoo_player_id);
CREATE INDEX idx_lineups_date_team ON daily_lineups(date, team_key);
CREATE INDEX idx_lineups_team_date ON daily_lineups(team_key, date);
CREATE INDEX idx_lineups_yahoo_player_date ON daily_lineups(yahoo_player_id, date);
CREATE INDEX idx_lineups_position ON daily_lineups(selected_position);
CREATE INDEX idx_lineups_season ON daily_lineups(season);
CREATE INDEX idx_lineups_job ON daily_lineups(job_id);

-- ============================================
-- STEP 5: Fix daily_gkl_player_stats columns
-- ============================================

-- Create new daily_gkl_player_stats table with all ID columns
CREATE TABLE daily_gkl_player_stats_new (
    job_id TEXT NOT NULL,
    date DATE NOT NULL,
    
    -- Player identifiers - ALL properly named
    mlb_player_id INTEGER NOT NULL,
    yahoo_player_id INTEGER,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    player_name TEXT NOT NULL,
    team_code TEXT,
    position_codes TEXT,
    games_played INTEGER DEFAULT 0,
    
    -- Batting stats (counting)
    batting_plate_appearances INTEGER DEFAULT 0,
    batting_at_bats INTEGER DEFAULT 0,
    batting_hits INTEGER DEFAULT 0,
    batting_singles INTEGER DEFAULT 0,
    batting_doubles INTEGER DEFAULT 0,
    batting_triples INTEGER DEFAULT 0,
    batting_home_runs INTEGER DEFAULT 0,
    batting_runs INTEGER DEFAULT 0,
    batting_rbis INTEGER DEFAULT 0,
    batting_walks INTEGER DEFAULT 0,
    batting_intentional_walks INTEGER DEFAULT 0,
    batting_strikeouts INTEGER DEFAULT 0,
    batting_hit_by_pitch INTEGER DEFAULT 0,
    batting_sacrifice_hits INTEGER DEFAULT 0,
    batting_sacrifice_flies INTEGER DEFAULT 0,
    batting_stolen_bases INTEGER DEFAULT 0,
    batting_caught_stealing INTEGER DEFAULT 0,
    batting_grounded_into_double_plays INTEGER DEFAULT 0,
    
    -- Batting stats (calculated)
    batting_avg REAL DEFAULT 0,
    batting_obp REAL DEFAULT 0,
    batting_slg REAL DEFAULT 0,
    batting_ops REAL DEFAULT 0,
    batting_babip REAL DEFAULT 0,
    batting_iso REAL DEFAULT 0,
    
    -- Pitching stats (counting)
    pitching_games INTEGER DEFAULT 0,
    pitching_games_started INTEGER DEFAULT 0,
    pitching_complete_games INTEGER DEFAULT 0,
    pitching_shutouts INTEGER DEFAULT 0,
    pitching_wins INTEGER DEFAULT 0,
    pitching_losses INTEGER DEFAULT 0,
    pitching_saves INTEGER DEFAULT 0,
    pitching_holds INTEGER DEFAULT 0,
    pitching_blown_saves INTEGER DEFAULT 0,
    pitching_innings_pitched REAL DEFAULT 0,
    pitching_hits_allowed INTEGER DEFAULT 0,
    pitching_runs_allowed INTEGER DEFAULT 0,
    pitching_earned_runs INTEGER DEFAULT 0,
    pitching_home_runs_allowed INTEGER DEFAULT 0,
    pitching_walks_allowed INTEGER DEFAULT 0,
    pitching_intentional_walks_allowed INTEGER DEFAULT 0,
    pitching_strikeouts INTEGER DEFAULT 0,
    pitching_hit_batters INTEGER DEFAULT 0,
    pitching_wild_pitches INTEGER DEFAULT 0,
    pitching_balks INTEGER DEFAULT 0,
    
    -- Pitching stats (calculated)
    pitching_era REAL DEFAULT 0,
    pitching_whip REAL DEFAULT 0,
    pitching_k_per_9 REAL DEFAULT 0,
    pitching_bb_per_9 REAL DEFAULT 0,
    pitching_hr_per_9 REAL DEFAULT 0,
    pitching_k_bb_ratio REAL DEFAULT 0,
    pitching_k_percentage REAL DEFAULT 0,
    pitching_bb_percentage REAL DEFAULT 0,
    pitching_babip REAL DEFAULT 0,
    pitching_lob_percentage REAL DEFAULT 0,
    
    -- Metadata
    has_batting_data BOOLEAN DEFAULT 0,
    has_pitching_data BOOLEAN DEFAULT 0,
    data_source TEXT DEFAULT 'pybaseball',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, mlb_player_id),
    FOREIGN KEY (job_id) REFERENCES job_log(job_id)
);

-- Copy existing data, handling nulls
INSERT INTO daily_gkl_player_stats_new
SELECT * FROM daily_gkl_player_stats
WHERE mlb_player_id IS NOT NULL;

-- Drop old table and rename new one
DROP TABLE daily_gkl_player_stats;
ALTER TABLE daily_gkl_player_stats_new RENAME TO daily_gkl_player_stats;

-- Recreate indexes
CREATE INDEX idx_player_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX idx_player_stats_yahoo ON daily_gkl_player_stats(yahoo_player_id, date);
CREATE INDEX idx_player_stats_name ON daily_gkl_player_stats(player_name);
CREATE INDEX idx_player_stats_team ON daily_gkl_player_stats(team_code, date);
CREATE INDEX idx_player_stats_job ON daily_gkl_player_stats(job_id);