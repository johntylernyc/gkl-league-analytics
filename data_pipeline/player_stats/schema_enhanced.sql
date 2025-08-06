-- Enhanced Player Stats Schema for Comprehensive MLB Coverage
-- Created: August 6, 2025
-- This schema supports collecting stats for ALL MLB players with multi-platform ID mapping

-- Player mapping table to track IDs across multiple platforms
CREATE TABLE IF NOT EXISTS player_mapping (
    player_mapping_id INTEGER PRIMARY KEY,
    mlb_id INTEGER UNIQUE NOT NULL,
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
    UNIQUE(first_name, last_name, mlb_id)
);

-- Indexes for player mapping
CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb ON player_mapping(mlb_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_active ON player_mapping(active);

-- Daily player stats table - comprehensive stats for all MLB players
CREATE TABLE IF NOT EXISTS daily_gkl_player_stats (
    job_id TEXT NOT NULL,
    date DATE NOT NULL,
    
    -- Player identifiers
    mlb_id INTEGER NOT NULL,
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
    
    PRIMARY KEY (date, mlb_id),
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    FOREIGN KEY (mlb_id) REFERENCES player_mapping(mlb_id)
);

-- Performance indexes for daily stats
CREATE INDEX IF NOT EXISTS idx_player_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX IF NOT EXISTS idx_player_stats_yahoo ON daily_gkl_player_stats(yahoo_player_id, date);
CREATE INDEX IF NOT EXISTS idx_player_stats_name ON daily_gkl_player_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_player_stats_team ON daily_gkl_player_stats(team_code, date);
CREATE INDEX IF NOT EXISTS idx_player_stats_job ON daily_gkl_player_stats(job_id);

-- View for easy access to player stats with full mapping info
CREATE VIEW IF NOT EXISTS v_player_stats_mapped AS
SELECT 
    ps.*,
    pm.first_name,
    pm.last_name,
    pm.active as player_active
FROM daily_gkl_player_stats ps
JOIN player_mapping pm ON ps.mlb_id = pm.mlb_id;

-- Cleanup existing test data if switching approaches
-- IMPORTANT: Only run these if migrating from old schema
-- DROP TABLE IF EXISTS daily_gkl_player_stats_test;
-- DELETE FROM daily_gkl_player_stats WHERE data_source != 'pybaseball';