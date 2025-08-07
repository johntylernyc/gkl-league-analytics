-- Player Stats Schema for Cloudflare D1
-- This creates the necessary tables for the player statistics pipeline

-- 1. Player Mapping Table
-- Maps Yahoo Fantasy IDs to MLB/PyBaseball identifiers
CREATE TABLE IF NOT EXISTS player_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    yahoo_player_id TEXT NOT NULL UNIQUE,
    yahoo_player_name TEXT NOT NULL,
    standardized_name TEXT NOT NULL,
    team_code TEXT,
    position_codes TEXT,
    confidence_score REAL NOT NULL DEFAULT 0.0,
    mapping_method TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    validation_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for player_mapping
CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(standardized_name);
CREATE INDEX IF NOT EXISTS idx_player_mapping_active ON player_mapping(is_active);

-- 2. Daily Player Stats Table
-- Stores comprehensive batting and pitching statistics
CREATE TABLE IF NOT EXISTS daily_gkl_player_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    
    -- Date and player identification
    date DATE NOT NULL,
    yahoo_player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_code TEXT NOT NULL,
    position_codes TEXT,
    
    -- Game participation
    games_played INTEGER DEFAULT 0,
    is_starter BOOLEAN DEFAULT FALSE,
    
    -- Batting statistics
    batting_at_bats INTEGER,
    batting_runs INTEGER,
    batting_hits INTEGER,
    batting_doubles INTEGER,
    batting_triples INTEGER,
    batting_home_runs INTEGER,
    batting_rbis INTEGER,
    batting_stolen_bases INTEGER,
    batting_caught_stealing INTEGER,
    batting_walks INTEGER,
    batting_strikeouts INTEGER,
    batting_hit_by_pitch INTEGER,
    batting_sacrifice_flies INTEGER,
    batting_sacrifice_bunts INTEGER,
    batting_gidp INTEGER,
    batting_total_bases INTEGER,
    
    -- Batting rate stats (calculated)
    batting_avg REAL,
    batting_obp REAL,
    batting_slg REAL,
    batting_ops REAL,
    
    -- Pitching statistics
    pitching_games INTEGER,
    pitching_games_started INTEGER,
    pitching_complete_games INTEGER,
    pitching_shutouts INTEGER,
    pitching_wins INTEGER,
    pitching_losses INTEGER,
    pitching_saves INTEGER,
    pitching_blown_saves INTEGER,
    pitching_holds INTEGER,
    pitching_innings_pitched REAL,
    pitching_hits_allowed INTEGER,
    pitching_runs_allowed INTEGER,
    pitching_earned_runs INTEGER,
    pitching_home_runs_allowed INTEGER,
    pitching_walks_allowed INTEGER,
    pitching_strikeouts INTEGER,
    pitching_wild_pitches INTEGER,
    pitching_balks INTEGER,
    pitching_quality_starts INTEGER,
    
    -- Pitching rate stats (calculated)
    pitching_era REAL,
    pitching_whip REAL,
    pitching_k_per_9 REAL,
    pitching_bb_per_9 REAL,
    
    -- Data quality
    health_score REAL DEFAULT 0.0,
    health_grade TEXT DEFAULT 'F',
    has_batting_data BOOLEAN DEFAULT FALSE,
    has_pitching_data BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite primary key constraint
    UNIQUE(date, yahoo_player_id),
    
    -- Foreign key
    FOREIGN KEY (job_id) REFERENCES job_log(job_id)
);

-- Indexes for daily_gkl_player_stats
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_yahoo_id ON daily_gkl_player_stats(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_daily_stats_player_name ON daily_gkl_player_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_daily_stats_team ON daily_gkl_player_stats(team_code);
CREATE INDEX IF NOT EXISTS idx_daily_stats_job ON daily_gkl_player_stats(job_id);