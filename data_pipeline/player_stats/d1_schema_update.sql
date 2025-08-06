-- D1 Database Schema Update for Comprehensive Player Stats
-- Adds comprehensive player_mapping table to support multi-platform IDs

-- Create comprehensive player mapping table
CREATE TABLE IF NOT EXISTS player_mapping (
    player_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mlb_id INTEGER,
    yahoo_player_id TEXT,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    player_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    team_code TEXT,
    active BOOLEAN DEFAULT 1,
    last_verified TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for player_mapping table
CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb ON player_mapping(mlb_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(player_name);
CREATE INDEX IF NOT EXISTS idx_player_mapping_active ON player_mapping(active);

-- Add missing calculated stats columns to daily_gkl_player_stats if they don't exist
-- Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we'll handle this in the application

-- These columns should be added if missing (handling in application code):
-- batting_avg REAL
-- batting_obp REAL  
-- batting_slg REAL
-- batting_ops REAL
-- batting_babip REAL
-- batting_iso REAL
-- pitching_era REAL
-- pitching_whip REAL
-- pitching_k_per_9 REAL
-- pitching_bb_per_9 REAL
-- pitching_hr_per_9 REAL
-- pitching_k_bb_ratio REAL