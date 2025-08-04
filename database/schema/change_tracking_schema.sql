-- Change Tracking Schema for GKL Fantasy Baseball Analytics
-- This schema enables detection and tracking of data changes across all data types
-- Version: 1.0
-- Date: August 2025

-- =====================================================
-- LINEUP CHANGE TRACKING
-- =====================================================

-- Metadata table for tracking lineup content and fetch times
CREATE TABLE IF NOT EXISTS daily_lineups_metadata (
    date TEXT NOT NULL,
    team_key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    PRIMARY KEY (date, team_key)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_lineups_metadata_date ON daily_lineups_metadata(date);
CREATE INDEX IF NOT EXISTS idx_lineups_metadata_team ON daily_lineups_metadata(team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_metadata_fetched ON daily_lineups_metadata(last_fetched);

-- Log table for detected lineup changes
CREATE TABLE IF NOT EXISTS lineup_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT,
    old_hash TEXT,
    new_hash TEXT,
    change_type TEXT, -- 'new', 'modified', 'deleted'
    players_added TEXT, -- JSON array of player IDs
    players_removed TEXT, -- JSON array of player IDs
    position_changes TEXT, -- JSON object of position changes
    change_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_lineup_changes_date ON lineup_changes(date);
CREATE INDEX IF NOT EXISTS idx_lineup_changes_team ON lineup_changes(team_key);
CREATE INDEX IF NOT EXISTS idx_lineup_changes_detected ON lineup_changes(change_detected_at);

-- =====================================================
-- MLB STAT CORRECTIONS TRACKING
-- =====================================================

-- Add metadata columns to existing player stats table if not exists
-- Note: These should be added via ALTER TABLE in migration script
-- ALTER TABLE daily_gkl_player_stats ADD COLUMN content_hash TEXT;
-- ALTER TABLE daily_gkl_player_stats ADD COLUMN has_correction BOOLEAN DEFAULT 0;
-- ALTER TABLE daily_gkl_player_stats ADD COLUMN last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Log table for stat corrections
CREATE TABLE IF NOT EXISTS stat_corrections (
    correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    player_name TEXT,
    date TEXT NOT NULL,
    stat_category TEXT, -- 'batting', 'pitching', 'fielding'
    stat_name TEXT, -- specific stat that changed (e.g., 'hits', 'era')
    old_value TEXT,
    new_value TEXT,
    difference REAL, -- numerical difference if applicable
    correction_source TEXT, -- 'mlb_official', 'yahoo_api', 'manual'
    correction_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_stat_corrections_player ON stat_corrections(player_id);
CREATE INDEX IF NOT EXISTS idx_stat_corrections_date ON stat_corrections(date);
CREATE INDEX IF NOT EXISTS idx_stat_corrections_detected ON stat_corrections(correction_detected_at);
CREATE INDEX IF NOT EXISTS idx_stat_corrections_category ON stat_corrections(stat_category);

-- =====================================================
-- TRANSACTION CHANGE TRACKING
-- =====================================================

-- Metadata table for transaction tracking
CREATE TABLE IF NOT EXISTS transaction_metadata (
    transaction_id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP,
    status TEXT DEFAULT 'active', -- 'active', 'cancelled', 'modified'
    job_id TEXT
);

-- Log table for transaction changes
CREATE TABLE IF NOT EXISTS transaction_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    change_type TEXT NOT NULL, -- 'new', 'modified', 'cancelled'
    field_changed TEXT, -- which field changed (if modified)
    old_data TEXT, -- JSON of old transaction data
    new_data TEXT, -- JSON of new transaction data
    change_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_transaction_changes_id ON transaction_changes(transaction_id);
CREATE INDEX IF NOT EXISTS idx_transaction_changes_detected ON transaction_changes(change_detected_at);
CREATE INDEX IF NOT EXISTS idx_transaction_changes_type ON transaction_changes(change_type);

-- =====================================================
-- SYNC AND JOB TRACKING
-- =====================================================

-- Enhanced job log table with change tracking metrics
CREATE TABLE IF NOT EXISTS job_log_enhanced (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    environment TEXT NOT NULL CHECK(environment IN ('test', 'production', 'development')),
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds REAL,
    date_range_start TEXT,
    date_range_end TEXT,
    league_key TEXT,
    -- Change tracking metrics
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_unchanged INTEGER DEFAULT 0,
    changes_detected INTEGER DEFAULT 0,
    stat_corrections INTEGER DEFAULT 0,
    -- Performance metrics
    api_calls_made INTEGER DEFAULT 0,
    api_errors INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    -- Additional metadata
    error_message TEXT,
    metadata TEXT, -- JSON for flexible additional data
    created_by TEXT DEFAULT 'system',
    UNIQUE(job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_log_type ON job_log_enhanced(job_type);
CREATE INDEX IF NOT EXISTS idx_job_log_status ON job_log_enhanced(status);
CREATE INDEX IF NOT EXISTS idx_job_log_start ON job_log_enhanced(start_time);
CREATE INDEX IF NOT EXISTS idx_job_log_env ON job_log_enhanced(environment);

-- Sync tracking table for local/production synchronization
CREATE TABLE IF NOT EXISTS sync_log (
    sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_type TEXT NOT NULL, -- 'production_to_local', 'local_to_production', 'backup'
    sync_direction TEXT, -- 'push', 'pull'
    environment_source TEXT,
    environment_target TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
    tables_synced TEXT, -- JSON array of table names
    records_synced INTEGER DEFAULT 0,
    changes_synced INTEGER DEFAULT 0,
    duration_seconds REAL,
    error_message TEXT,
    metadata TEXT -- JSON for additional sync details
);

CREATE INDEX IF NOT EXISTS idx_sync_log_date ON sync_log(sync_date);
CREATE INDEX IF NOT EXISTS idx_sync_log_type ON sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);

-- =====================================================
-- CHANGE SUMMARY VIEWS
-- =====================================================

-- View for recent lineup changes
CREATE VIEW IF NOT EXISTS v_recent_lineup_changes AS
SELECT 
    lc.date,
    lc.team_key,
    lc.team_name,
    lc.change_type,
    lc.change_detected_at,
    lc.players_added,
    lc.players_removed,
    lc.position_changes
FROM lineup_changes lc
WHERE lc.change_detected_at >= datetime('now', '-7 days')
ORDER BY lc.change_detected_at DESC;

-- View for recent stat corrections
CREATE VIEW IF NOT EXISTS v_recent_stat_corrections AS
SELECT 
    sc.date,
    sc.player_id,
    sc.player_name,
    sc.stat_category,
    sc.stat_name,
    sc.old_value,
    sc.new_value,
    sc.difference,
    sc.correction_detected_at
FROM stat_corrections sc
WHERE sc.correction_detected_at >= datetime('now', '-7 days')
ORDER BY sc.correction_detected_at DESC;

-- View for job performance metrics
CREATE VIEW IF NOT EXISTS v_job_performance AS
SELECT 
    job_type,
    environment,
    COUNT(*) as total_jobs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_jobs,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
    AVG(duration_seconds) as avg_duration,
    SUM(records_processed) as total_records_processed,
    SUM(changes_detected) as total_changes_detected,
    SUM(stat_corrections) as total_stat_corrections,
    MAX(start_time) as last_run
FROM job_log_enhanced
WHERE start_time >= datetime('now', '-30 days')
GROUP BY job_type, environment;

-- =====================================================
-- DATA INTEGRITY CONSTRAINTS
-- =====================================================

-- Ensure unique lineup entries per date/team/player
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_lineups_unique 
ON daily_lineups(date, team_key, player_id);

-- Ensure unique transactions
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_unique 
ON transactions(transaction_id, player_id, movement_type);

-- Ensure unique player stats per date
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_stats_unique 
ON daily_gkl_player_stats(date, yahoo_player_id);

-- =====================================================
-- MIGRATION NOTES
-- =====================================================
-- 1. Run this schema creation script first
-- 2. Then run the migration script to add columns to existing tables
-- 3. Backfill content_hash values for existing data if needed
-- 4. Set up triggers for automatic timestamp updates (optional)