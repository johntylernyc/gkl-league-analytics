-- ============================================
-- Player Stats Database Schema
-- ============================================
-- 
-- This schema defines tables for MLB player statistics data ingestion
-- following the existing patterns in the GKL League Analytics database.
--
-- Key Design Principles:
-- 1. Integration with existing job_log infrastructure
-- 2. Environment separation (production vs test tables)
-- 3. Performance optimization through proper indexing
-- 4. Data quality enforcement through constraints
-- 5. Alignment with Yahoo Fantasy player identification
--
-- Tables Created:
-- - mlb_batting_stats_staging: Raw batting data from pybaseball
-- - mlb_pitching_stats_staging: Raw pitching data from pybaseball  
-- - player_id_mapping: Yahoo ↔ MLB player ID relationships
-- - daily_gkl_player_stats: Final processed player statistics
--
-- ============================================

-- ============================================
-- Staging Tables for Raw pybaseball Data
-- ============================================

-- Batting statistics staging table
-- Stores raw daily batting data from pybaseball APIs
CREATE TABLE IF NOT EXISTS mlb_batting_stats_staging (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    collection_date DATE NOT NULL,
    data_date DATE NOT NULL,
    
    -- Player identification (from pybaseball)
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    
    -- Core batting statistics
    games_played INTEGER DEFAULT 0,
    at_bats INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    hits INTEGER DEFAULT 0,
    doubles INTEGER DEFAULT 0,
    triples INTEGER DEFAULT 0,
    home_runs INTEGER DEFAULT 0,
    rbis INTEGER DEFAULT 0,
    stolen_bases INTEGER DEFAULT 0,
    caught_stealing INTEGER DEFAULT 0,
    walks INTEGER DEFAULT 0,
    intentional_walks INTEGER DEFAULT 0,
    hit_by_pitch INTEGER DEFAULT 0,
    strikeouts INTEGER DEFAULT 0,
    sacrifice_hits INTEGER DEFAULT 0,
    sacrifice_flies INTEGER DEFAULT 0,
    ground_into_double_play INTEGER DEFAULT 0,
    
    -- Calculated statistics
    batting_avg REAL,
    on_base_pct REAL,
    slugging_pct REAL,
    ops REAL,
    total_bases INTEGER DEFAULT 0,
    
    -- Raw data fields (for debugging and future use)
    raw_data TEXT,  -- JSON of original pybaseball response
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(data_date, player_name, team)
);

-- Pitching statistics staging table  
-- Stores raw daily pitching data from pybaseball APIs
CREATE TABLE IF NOT EXISTS mlb_pitching_stats_staging (
    staging_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    collection_date DATE NOT NULL,
    data_date DATE NOT NULL,
    
    -- Player identification (from pybaseball)
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    
    -- Core pitching statistics
    games_played INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    complete_games INTEGER DEFAULT 0,
    shutouts INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    holds INTEGER DEFAULT 0,
    save_opportunities INTEGER DEFAULT 0,
    blown_saves INTEGER DEFAULT 0,
    
    -- Innings and outs
    innings_pitched REAL DEFAULT 0.0,
    outs INTEGER DEFAULT 0,
    
    -- Hits and runs
    hits_allowed INTEGER DEFAULT 0,
    runs_allowed INTEGER DEFAULT 0,
    earned_runs INTEGER DEFAULT 0,
    home_runs_allowed INTEGER DEFAULT 0,
    
    -- Walks and strikeouts
    walks_allowed INTEGER DEFAULT 0,
    intentional_walks_allowed INTEGER DEFAULT 0,
    hit_batters INTEGER DEFAULT 0,
    strikeouts_pitched INTEGER DEFAULT 0,
    
    -- Other pitching events
    wild_pitches INTEGER DEFAULT 0,
    balks INTEGER DEFAULT 0,
    batters_faced INTEGER DEFAULT 0,
    ground_into_double_play INTEGER DEFAULT 0,
    
    -- Calculated statistics
    era REAL,
    whip REAL,
    strikeouts_per_nine REAL,
    walks_per_nine REAL,
    strikeouts_per_walk REAL,
    quality_starts INTEGER DEFAULT 0,
    
    -- Raw data fields (for debugging and future use)
    raw_data TEXT,  -- JSON of original pybaseball response
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(data_date, player_name, team)
);

-- ============================================
-- Player ID Mapping Table
-- ============================================

-- Maps Yahoo Fantasy player IDs to MLB/pybaseball identifiers
-- Critical for linking fantasy roster data with MLB statistics
CREATE TABLE IF NOT EXISTS player_id_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Yahoo Fantasy identification
    yahoo_player_id TEXT NOT NULL UNIQUE,
    yahoo_player_name TEXT NOT NULL,
    
    -- MLB/pybaseball identification  
    mlb_player_id TEXT,  -- MLB official player ID when available
    fangraphs_id TEXT,   -- Fangraphs player ID
    bbref_id TEXT,       -- Baseball Reference player ID
    
    -- Standardized identification for matching
    standardized_name TEXT NOT NULL,  -- Normalized name for matching
    team_code TEXT,                   -- Current/most recent team
    position_codes TEXT,              -- Position eligibility
    birth_year INTEGER,               -- Birth year for disambiguation
    
    -- Mapping quality and confidence
    confidence_score REAL NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0 confidence
    mapping_method TEXT,              -- 'exact', 'fuzzy', 'manual', 'verified'
    manual_override BOOLEAN DEFAULT FALSE,
    verified_by TEXT,                 -- Who verified the mapping
    verified_at TIMESTAMP,
    
    -- Status tracking
    is_active BOOLEAN DEFAULT TRUE,   -- Currently active mapping
    last_validated DATE,              -- Last validation date
    validation_status TEXT DEFAULT 'pending',  -- 'pending', 'valid', 'failed'
    
    -- Metadata
    notes TEXT,                       -- Additional notes or comments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CHECK (mapping_method IN ('exact', 'fuzzy', 'manual', 'verified')),
    CHECK (validation_status IN ('pending', 'valid', 'failed', 'needs_review'))
);

-- ============================================
-- Final Processed Statistics Table
-- ============================================

-- Daily GKL player statistics - the main table for application use
-- Contains processed and validated statistics for all players in our database
CREATE TABLE IF NOT EXISTS daily_gkl_player_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    
    -- Date and player identification
    date DATE NOT NULL,
    yahoo_player_id TEXT NOT NULL,  -- Links to daily_lineups and transactions
    player_name TEXT NOT NULL,
    team_code TEXT NOT NULL,
    position_codes TEXT,            -- Player's position eligibility
    
    -- Game participation
    games_played INTEGER DEFAULT 0,
    is_starter BOOLEAN DEFAULT FALSE, -- Started the game (for pitchers)
    
    -- Batting statistics (NULL for pitchers with no batting stats)
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
    batting_sacrifice_hits INTEGER,
    batting_sacrifice_flies INTEGER,
    batting_avg REAL,
    batting_obp REAL,
    batting_slg REAL,
    batting_ops REAL,
    
    -- Pitching statistics (NULL for position players)
    pitching_games_started INTEGER,
    pitching_wins INTEGER,
    pitching_losses INTEGER,
    pitching_saves INTEGER,
    pitching_holds INTEGER,
    pitching_blown_saves INTEGER,
    pitching_innings_pitched REAL,
    pitching_hits_allowed INTEGER,
    pitching_runs_allowed INTEGER,
    pitching_earned_runs INTEGER,
    pitching_walks_allowed INTEGER,
    pitching_strikeouts INTEGER,
    pitching_home_runs_allowed INTEGER,
    pitching_era REAL,
    pitching_whip REAL,
    pitching_quality_starts INTEGER,
    
    -- Fantasy scoring (calculated from above stats)
    fantasy_batting_points REAL,     -- Based on league scoring categories
    fantasy_pitching_points REAL,    -- Based on league scoring categories
    fantasy_total_points REAL,       -- Combined batting + pitching
    
    -- Data quality and lineage
    data_source TEXT DEFAULT 'pybaseball',  -- Source of the statistics
    confidence_score REAL DEFAULT 1.0,      -- Data quality confidence
    has_batting_data BOOLEAN DEFAULT FALSE,
    has_pitching_data BOOLEAN DEFAULT FALSE,
    validation_status TEXT DEFAULT 'valid', -- 'valid', 'warning', 'error'
    validation_notes TEXT,                   -- Any data quality issues
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    FOREIGN KEY (yahoo_player_id) REFERENCES player_id_mapping(yahoo_player_id),
    UNIQUE(date, yahoo_player_id),
    
    -- Data quality constraints
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CHECK (validation_status IN ('valid', 'warning', 'error')),
    CHECK (batting_avg IS NULL OR (batting_avg >= 0.0 AND batting_avg <= 1.0)),
    CHECK (batting_obp IS NULL OR (batting_obp >= 0.0 AND batting_obp <= 1.0)),
    CHECK (batting_slg IS NULL OR (batting_slg >= 0.0 AND batting_slg <= 5.0)),
    CHECK (pitching_era IS NULL OR (pitching_era >= 0.0 AND pitching_era <= 30.0)),
    CHECK (pitching_whip IS NULL OR (pitching_whip >= 0.0 AND pitching_whip <= 10.0))
);

-- ============================================
-- Performance Indexes
-- ============================================

-- Staging table indexes
CREATE INDEX IF NOT EXISTS idx_batting_staging_date ON mlb_batting_stats_staging(data_date);
CREATE INDEX IF NOT EXISTS idx_batting_staging_player ON mlb_batting_stats_staging(player_name, team);
CREATE INDEX IF NOT EXISTS idx_batting_staging_job ON mlb_batting_stats_staging(job_id);
CREATE INDEX IF NOT EXISTS idx_batting_staging_collection ON mlb_batting_stats_staging(collection_date);

CREATE INDEX IF NOT EXISTS idx_pitching_staging_date ON mlb_pitching_stats_staging(data_date);
CREATE INDEX IF NOT EXISTS idx_pitching_staging_player ON mlb_pitching_stats_staging(player_name, team);
CREATE INDEX IF NOT EXISTS idx_pitching_staging_job ON mlb_pitching_stats_staging(job_id);
CREATE INDEX IF NOT EXISTS idx_pitching_staging_collection ON mlb_pitching_stats_staging(collection_date);

-- Player mapping indexes
CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo_id ON player_id_mapping(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_id_mapping(standardized_name);
CREATE INDEX IF NOT EXISTS idx_player_mapping_team ON player_id_mapping(team_code);
CREATE INDEX IF NOT EXISTS idx_player_mapping_active ON player_id_mapping(is_active);
CREATE INDEX IF NOT EXISTS idx_player_mapping_confidence ON player_id_mapping(confidence_score);
CREATE INDEX IF NOT EXISTS idx_player_mapping_status ON player_id_mapping(validation_status);

-- Main statistics table indexes (critical for query performance)
CREATE INDEX IF NOT EXISTS idx_gkl_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_player ON daily_gkl_player_stats(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_player_date ON daily_gkl_player_stats(yahoo_player_id, date);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_team ON daily_gkl_player_stats(team_code);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_job ON daily_gkl_player_stats(job_id);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_position ON daily_gkl_player_stats(position_codes);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_validation ON daily_gkl_player_stats(validation_status);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_batting_data ON daily_gkl_player_stats(has_batting_data);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_pitching_data ON daily_gkl_player_stats(has_pitching_data);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_gkl_stats_date_team ON daily_gkl_player_stats(date, team_code);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_date_position ON daily_gkl_player_stats(date, position_codes);
CREATE INDEX IF NOT EXISTS idx_gkl_stats_team_player ON daily_gkl_player_stats(team_code, yahoo_player_id);

-- ============================================
-- Data Quality Views
-- ============================================

-- View for data quality monitoring
CREATE VIEW IF NOT EXISTS player_stats_quality_summary AS
SELECT 
    date,
    COUNT(*) as total_players,
    COUNT(CASE WHEN validation_status = 'valid' THEN 1 END) as valid_players,
    COUNT(CASE WHEN validation_status = 'warning' THEN 1 END) as warning_players,
    COUNT(CASE WHEN validation_status = 'error' THEN 1 END) as error_players,
    COUNT(CASE WHEN has_batting_data THEN 1 END) as players_with_batting,
    COUNT(CASE WHEN has_pitching_data THEN 1 END) as players_with_pitching,
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    COUNT(CASE WHEN confidence_score < 0.8 THEN 1 END) as low_confidence_players
FROM daily_gkl_player_stats
GROUP BY date
ORDER BY date DESC;

-- View for player mapping status
CREATE VIEW IF NOT EXISTS player_mapping_summary AS
SELECT 
    validation_status,
    COUNT(*) as player_count,
    AVG(confidence_score) as avg_confidence,
    COUNT(CASE WHEN manual_override THEN 1 END) as manual_overrides,
    COUNT(CASE WHEN last_validated IS NULL THEN 1 END) as never_validated,
    COUNT(CASE WHEN last_validated < date('now', '-30 days') THEN 1 END) as needs_revalidation
FROM player_id_mapping
WHERE is_active = TRUE
GROUP BY validation_status
ORDER BY validation_status;

-- ============================================
-- Test Environment Tables
-- ============================================

-- Create test environment versions of all tables
-- These will be created automatically by the table naming functions
-- but we include the pattern here for reference:

-- Test tables follow the pattern: {table_name}_test
-- Examples:
-- - mlb_batting_stats_staging_test
-- - mlb_pitching_stats_staging_test  
-- - player_id_mapping_test
-- - daily_gkl_player_stats_test

-- All indexes and constraints are replicated for test tables

-- ============================================
-- Schema Metadata
-- ============================================

-- Track schema version for migrations
CREATE TABLE IF NOT EXISTS player_stats_schema_version (
    version_id INTEGER PRIMARY KEY,
    version_number TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by TEXT DEFAULT 'system'
);

-- Insert initial schema version
INSERT OR IGNORE INTO player_stats_schema_version (version_number, description, applied_by)
VALUES ('1.0.0', 'Initial player stats schema with staging tables, mapping, and final stats', 'player_stats_module');

-- ============================================
-- Schema Validation Queries
-- ============================================

-- These queries can be used to validate schema integrity:

/*
-- Check table existence
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%player%' OR name LIKE '%mlb%';

-- Check index existence  
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%gkl_stats%';

-- Validate foreign key relationships
PRAGMA foreign_key_check;

-- Check constraint violations
SELECT * FROM daily_gkl_player_stats WHERE batting_avg > 1.0 OR batting_avg < 0.0;
SELECT * FROM daily_gkl_player_stats WHERE pitching_era > 30.0 OR pitching_era < 0.0;

-- Performance check - ensure indexes are being used
EXPLAIN QUERY PLAN SELECT * FROM daily_gkl_player_stats WHERE yahoo_player_id = '12345' AND date = '2025-08-03';
*/