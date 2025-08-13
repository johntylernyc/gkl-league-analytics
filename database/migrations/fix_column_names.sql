-- Migration: Fix Column Naming Inconsistencies
-- Date: 2025-08-13
-- Purpose: Standardize player ID column names across all tables
--
-- Changes:
-- 1. Rename player_id to yahoo_player_id in transactions and daily_lineups
-- 2. Rename mlb_id to mlb_player_id in player_mapping
-- 3. Add missing ID columns to daily_gkl_player_stats if needed

-- ============================================
-- STEP 1: Fix transactions table
-- ============================================

-- Rename player_id to yahoo_player_id in transactions
ALTER TABLE league_transactions 
RENAME COLUMN player_id TO yahoo_player_id;

-- Update indexes
DROP INDEX IF EXISTS idx_transactions_player;
CREATE INDEX idx_transactions_yahoo_player ON league_transactions(yahoo_player_id);

-- ============================================
-- STEP 2: Fix daily_lineups table  
-- ============================================

-- Rename player_id to yahoo_player_id in daily_lineups
ALTER TABLE daily_lineups 
RENAME COLUMN player_id TO yahoo_player_id;

-- Update indexes
DROP INDEX IF EXISTS idx_lineups_player;
DROP INDEX IF EXISTS idx_lineups_player_date;
CREATE INDEX idx_lineups_yahoo_player ON daily_lineups(yahoo_player_id);
CREATE INDEX idx_lineups_yahoo_player_date ON daily_lineups(yahoo_player_id, date);

-- Also fix the test table
ALTER TABLE daily_lineups_test
RENAME COLUMN player_id TO yahoo_player_id;

DROP INDEX IF EXISTS idx_lineups_test_player;
CREATE INDEX idx_lineups_test_yahoo_player ON daily_lineups_test(yahoo_player_id);

-- ============================================
-- STEP 3: Fix player_mapping table
-- ============================================

-- Rename mlb_id to mlb_player_id in player_mapping
ALTER TABLE player_mapping
RENAME COLUMN mlb_id TO mlb_player_id;

-- Update indexes
DROP INDEX IF EXISTS idx_player_mapping_mlb;
CREATE INDEX idx_player_mapping_mlb_player ON player_mapping(mlb_player_id);

-- ============================================
-- STEP 4: Add missing columns to daily_gkl_player_stats
-- ============================================

-- Check if columns exist and add if missing
-- SQLite doesn't support conditional column addition, so we'll handle this in the application

-- ============================================
-- STEP 5: Update views to use new column names
-- ============================================

-- Drop and recreate views with new column names
DROP VIEW IF EXISTS v_current_lineups;
CREATE VIEW v_current_lineups AS
SELECT 
    dl.*,
    lp.position_name,
    lp.position_type as position_category,
    lp.display_order
FROM daily_lineups dl
LEFT JOIN lineup_positions lp ON dl.selected_position = lp.position_code
WHERE dl.season = (SELECT MAX(season) FROM daily_lineups);

DROP VIEW IF EXISTS v_player_frequency;
CREATE VIEW v_player_frequency AS
SELECT 
    yahoo_player_id,
    player_name,
    team_key,
    team_name,
    season,
    COUNT(*) as total_days,
    SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) as days_started,
    SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as days_benched,
    ROUND(100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) / COUNT(*), 2) as start_percentage
FROM daily_lineups
GROUP BY yahoo_player_id, team_key, season;

DROP VIEW IF EXISTS v_team_daily_summary;
CREATE VIEW v_team_daily_summary AS
SELECT 
    date,
    team_key,
    team_name,
    season,
    COUNT(DISTINCT CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN yahoo_player_id END) as starters_count,
    COUNT(DISTINCT CASE WHEN selected_position = 'BN' THEN yahoo_player_id END) as bench_count,
    COUNT(DISTINCT CASE WHEN selected_position IN ('IL', 'NA') THEN yahoo_player_id END) as inactive_count,
    COUNT(DISTINCT yahoo_player_id) as total_roster_size
FROM daily_lineups
GROUP BY date, team_key, season;

-- ============================================
-- STEP 6: Update triggers to use new column names
-- ============================================

DROP TRIGGER IF EXISTS update_usage_on_insert;
CREATE TRIGGER update_usage_on_insert
AFTER INSERT ON daily_lineups
BEGIN
    INSERT OR REPLACE INTO player_usage_summary (
        player_id, team_key, season, total_days, days_started, days_benched, days_injured, start_percentage
    )
    SELECT 
        yahoo_player_id,
        team_key,
        season,
        COUNT(*) as total_days,
        SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) as days_started,
        SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as days_benched,
        SUM(CASE WHEN selected_position IN ('IL', 'NA') THEN 1 ELSE 0 END) as days_injured,
        ROUND(100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'NA') THEN 1 ELSE 0 END) / COUNT(*), 2) as start_percentage
    FROM daily_lineups
    WHERE yahoo_player_id = NEW.yahoo_player_id 
      AND team_key = NEW.team_key 
      AND season = NEW.season
    GROUP BY yahoo_player_id, team_key, season;
END;

-- Note: player_usage_summary table also needs to be updated
ALTER TABLE player_usage_summary
RENAME COLUMN player_id TO yahoo_player_id;

DROP INDEX IF EXISTS idx_usage_player;
CREATE INDEX idx_usage_yahoo_player ON player_usage_summary(yahoo_player_id);