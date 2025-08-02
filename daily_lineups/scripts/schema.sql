-- Daily Lineups Module Database Schema
-- This schema extends the existing league_analytics.db database
-- Created: 2025-08-02

-- ============================================
-- MAIN TABLES
-- ============================================

-- Main daily lineups table
-- Stores historical lineup data for all teams and dates
CREATE TABLE IF NOT EXISTS daily_lineups (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    selected_position TEXT,        -- The position player was started in (C, 1B, 2B, etc.)
    position_type TEXT,            -- B=Bench, P=Pitcher, etc. from Yahoo API
    player_status TEXT,            -- healthy, DTD, IL, etc.
    eligible_positions TEXT,       -- Comma-separated list of eligible positions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(date, team_key, player_id, selected_position)
);

-- Test environment table (identical structure)
CREATE TABLE IF NOT EXISTS daily_lineups_test (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    selected_position TEXT,
    position_type TEXT,
    player_status TEXT,
    eligible_positions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(date, team_key, player_id, selected_position)
);

-- ============================================
-- LOOKUP TABLES
-- ============================================

-- Position definitions and display order
CREATE TABLE IF NOT EXISTS lineup_positions (
    position_code TEXT PRIMARY KEY,
    position_name TEXT NOT NULL,
    position_type TEXT NOT NULL,     -- 'batting', 'pitching', 'bench'
    display_order INTEGER NOT NULL,
    is_flex_position BOOLEAN DEFAULT 0  -- For UTIL, MI, CI positions
);

-- Insert standard positions
INSERT OR IGNORE INTO lineup_positions (position_code, position_name, position_type, display_order, is_flex_position) VALUES
('C', 'Catcher', 'batting', 1, 0),
('1B', 'First Base', 'batting', 2, 0),
('2B', 'Second Base', 'batting', 3, 0),
('3B', 'Third Base', 'batting', 4, 0),
('SS', 'Shortstop', 'batting', 5, 0),
('MI', 'Middle Infield', 'batting', 6, 1),
('CI', 'Corner Infield', 'batting', 7, 1),
('OF', 'Outfield', 'batting', 8, 0),
('UTIL', 'Utility', 'batting', 9, 1),
('SP', 'Starting Pitcher', 'pitching', 10, 0),
('RP', 'Relief Pitcher', 'pitching', 11, 0),
('P', 'Pitcher', 'pitching', 12, 0),
('BN', 'Bench', 'bench', 13, 0),
('IL', 'Injured List', 'bench', 14, 0),
('NA', 'Not Active', 'bench', 15, 0);

-- ============================================
-- AGGREGATION TABLES (for performance)
-- ============================================

-- Player usage summary (refreshed daily)
CREATE TABLE IF NOT EXISTS player_usage_summary (
    player_id TEXT NOT NULL,
    team_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    total_days INTEGER DEFAULT 0,
    days_started INTEGER DEFAULT 0,
    days_benched INTEGER DEFAULT 0,
    days_injured INTEGER DEFAULT 0,
    start_percentage REAL,
    primary_position TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, team_key, season)
);

-- Team lineup patterns (refreshed daily)
CREATE TABLE IF NOT EXISTS team_lineup_patterns (
    team_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    pattern_date DATE NOT NULL,
    lineup_hash TEXT NOT NULL,      -- Hash of starting lineup for comparison
    frequency INTEGER DEFAULT 1,
    last_used DATE,
    PRIMARY KEY (team_key, season, lineup_hash)
);

-- ============================================
-- PERFORMANCE INDEXES
-- ============================================

-- Primary access patterns
CREATE INDEX IF NOT EXISTS idx_lineups_date ON daily_lineups(date);
CREATE INDEX IF NOT EXISTS idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_player ON daily_lineups(player_id);
CREATE INDEX IF NOT EXISTS idx_lineups_date_team ON daily_lineups(date, team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_team_date ON daily_lineups(team_key, date);
CREATE INDEX IF NOT EXISTS idx_lineups_player_date ON daily_lineups(player_id, date);
CREATE INDEX IF NOT EXISTS idx_lineups_position ON daily_lineups(selected_position);
CREATE INDEX IF NOT EXISTS idx_lineups_season ON daily_lineups(season);
CREATE INDEX IF NOT EXISTS idx_lineups_job ON daily_lineups(job_id);

-- Test table indexes
CREATE INDEX IF NOT EXISTS idx_lineups_test_date ON daily_lineups_test(date);
CREATE INDEX IF NOT EXISTS idx_lineups_test_team ON daily_lineups_test(team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_test_player ON daily_lineups_test(player_id);
CREATE INDEX IF NOT EXISTS idx_lineups_test_date_team ON daily_lineups_test(date, team_key);

-- Summary table indexes
CREATE INDEX IF NOT EXISTS idx_usage_player ON player_usage_summary(player_id);
CREATE INDEX IF NOT EXISTS idx_usage_team ON player_usage_summary(team_key);
CREATE INDEX IF NOT EXISTS idx_patterns_team ON team_lineup_patterns(team_key);
CREATE INDEX IF NOT EXISTS idx_patterns_date ON team_lineup_patterns(pattern_date);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Current season lineups with position names
CREATE VIEW IF NOT EXISTS v_current_lineups AS
SELECT 
    dl.*,
    lp.position_name,
    lp.position_type as position_category,
    lp.display_order
FROM daily_lineups dl
LEFT JOIN lineup_positions lp ON dl.selected_position = lp.position_code
WHERE dl.season = (SELECT MAX(season) FROM daily_lineups);

-- Player start/bench frequency
CREATE VIEW IF NOT EXISTS v_player_frequency AS
SELECT 
    player_id,
    player_name,
    team_key,
    team_name,
    season,
    COUNT(*) as total_days,
    SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) as days_started,
    SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as days_benched,
    ROUND(100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) / COUNT(*), 2) as start_percentage
FROM daily_lineups
GROUP BY player_id, team_key, season;

-- Team daily lineup summary
CREATE VIEW IF NOT EXISTS v_team_daily_summary AS
SELECT 
    date,
    team_key,
    team_name,
    season,
    COUNT(DISTINCT CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN player_id END) as starters_count,
    COUNT(DISTINCT CASE WHEN selected_position = 'BN' THEN player_id END) as bench_count,
    COUNT(DISTINCT CASE WHEN selected_position IN ('IL', 'NA') THEN player_id END) as inactive_count,
    COUNT(DISTINCT player_id) as total_roster_size
FROM daily_lineups
GROUP BY date, team_key, season;

-- ============================================
-- TRIGGERS FOR DATA INTEGRITY
-- ============================================

-- Update timestamp on modification
CREATE TRIGGER IF NOT EXISTS update_lineup_timestamp 
AFTER UPDATE ON daily_lineups
BEGIN
    UPDATE daily_lineups 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE lineup_id = NEW.lineup_id;
END;

-- Update player usage summary on lineup insert
CREATE TRIGGER IF NOT EXISTS update_usage_on_insert
AFTER INSERT ON daily_lineups
BEGIN
    INSERT OR REPLACE INTO player_usage_summary (
        player_id, team_key, season, total_days, days_started, days_benched, days_injured, start_percentage
    )
    SELECT 
        player_id,
        team_key,
        season,
        COUNT(*) as total_days,
        SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) as days_started,
        SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as days_benched,
        SUM(CASE WHEN selected_position IN ('IL', 'NA') THEN 1 ELSE 0 END) as days_injured,
        ROUND(100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) / COUNT(*), 2) as start_percentage
    FROM daily_lineups
    WHERE player_id = NEW.player_id 
      AND team_key = NEW.team_key 
      AND season = NEW.season
    GROUP BY player_id, team_key, season;
END;