-- Migration Script: Add Change Tracking Columns to Existing Tables
-- This script adds change tracking capabilities to existing tables
-- Run this AFTER creating the new change tracking tables
-- Version: 1.0
-- Date: August 2025

-- =====================================================
-- ADD COLUMNS TO EXISTING TABLES
-- =====================================================

-- Add change tracking columns to daily_lineups table
ALTER TABLE daily_lineups ADD COLUMN content_hash TEXT;
ALTER TABLE daily_lineups ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE daily_lineups ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add change tracking columns to daily_gkl_player_stats table
ALTER TABLE daily_gkl_player_stats ADD COLUMN content_hash TEXT;
ALTER TABLE daily_gkl_player_stats ADD COLUMN has_correction BOOLEAN DEFAULT 0;
ALTER TABLE daily_gkl_player_stats ADD COLUMN last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE daily_gkl_player_stats ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add change tracking columns to transactions tables
ALTER TABLE transactions_production ADD COLUMN content_hash TEXT;
ALTER TABLE transactions_production ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE transactions_production ADD COLUMN last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE transactions_test ADD COLUMN content_hash TEXT;
ALTER TABLE transactions_test ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE transactions_test ADD COLUMN last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add change tracking to job_log table (if not using job_log_enhanced)
ALTER TABLE job_log ADD COLUMN records_updated INTEGER DEFAULT 0;
ALTER TABLE job_log ADD COLUMN records_unchanged INTEGER DEFAULT 0;
ALTER TABLE job_log ADD COLUMN changes_detected INTEGER DEFAULT 0;
ALTER TABLE job_log ADD COLUMN stat_corrections INTEGER DEFAULT 0;

-- =====================================================
-- CREATE INDEXES FOR PERFORMANCE
-- =====================================================

-- Indexes for daily_lineups change tracking
CREATE INDEX IF NOT EXISTS idx_daily_lineups_hash ON daily_lineups(content_hash);
CREATE INDEX IF NOT EXISTS idx_daily_lineups_updated ON daily_lineups(last_updated);

-- Indexes for player stats change tracking
CREATE INDEX IF NOT EXISTS idx_player_stats_hash ON daily_gkl_player_stats(content_hash);
CREATE INDEX IF NOT EXISTS idx_player_stats_correction ON daily_gkl_player_stats(has_correction);
CREATE INDEX IF NOT EXISTS idx_player_stats_fetched ON daily_gkl_player_stats(last_fetched);

-- Indexes for transactions change tracking
CREATE INDEX IF NOT EXISTS idx_transactions_prod_hash ON transactions_production(content_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_prod_updated ON transactions_production(last_updated);
CREATE INDEX IF NOT EXISTS idx_transactions_test_hash ON transactions_test(content_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_test_updated ON transactions_test(last_updated);

-- =====================================================
-- BACKFILL TIMESTAMPS FOR EXISTING DATA
-- =====================================================

-- Set created_at for existing daily_lineups records (use date as approximation)
UPDATE daily_lineups 
SET created_at = datetime(date || ' 00:00:00'),
    last_updated = datetime(date || ' 00:00:00')
WHERE created_at IS NULL;

-- Set timestamps for existing player stats
UPDATE daily_gkl_player_stats
SET last_fetched = CURRENT_TIMESTAMP,
    last_updated = CURRENT_TIMESTAMP
WHERE last_fetched IS NULL;

-- Set timestamps for existing transactions
UPDATE transactions_production
SET last_fetched = CURRENT_TIMESTAMP,
    last_updated = CURRENT_TIMESTAMP
WHERE last_fetched IS NULL;

UPDATE transactions_test
SET last_fetched = CURRENT_TIMESTAMP,
    last_updated = CURRENT_TIMESTAMP
WHERE last_fetched IS NULL;

-- =====================================================
-- DATA VERIFICATION
-- =====================================================

-- Verify the migration was successful
SELECT 'daily_lineups' as table_name, 
       COUNT(*) as total_records,
       COUNT(content_hash) as records_with_hash,
       COUNT(last_updated) as records_with_timestamp
FROM daily_lineups

UNION ALL

SELECT 'daily_gkl_player_stats' as table_name,
       COUNT(*) as total_records,
       COUNT(content_hash) as records_with_hash,
       COUNT(last_fetched) as records_with_timestamp
FROM daily_gkl_player_stats

UNION ALL

SELECT 'transactions_production' as table_name,
       COUNT(*) as total_records,
       COUNT(content_hash) as records_with_hash,
       COUNT(last_updated) as records_with_timestamp
FROM transactions_production;

-- =====================================================
-- MIGRATION ROLLBACK (IF NEEDED)
-- =====================================================
-- To rollback this migration, you would need to:
-- 1. Drop the newly added columns (SQLite doesn't support DROP COLUMN directly)
-- 2. Create a new table without the columns
-- 3. Copy data from old table
-- 4. Drop old table and rename new table
-- This is complex in SQLite, so ensure you have backups before migrating