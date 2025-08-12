-- Migration to fix column name mismatch between player_mapping and daily_gkl_player_stats
-- Issue: player_mapping has 'mlb_id' but daily_gkl_player_stats expects 'mlb_player_id'
-- Solution: Add mlb_player_id column that mirrors mlb_id for compatibility

-- Step 1: Add mlb_player_id column if it doesn't exist
-- Note: SQLite doesn't support "IF NOT EXISTS" for columns, so we need to handle this carefully
ALTER TABLE player_mapping ADD COLUMN mlb_player_id INTEGER;

-- Step 2: Copy existing mlb_id values to mlb_player_id
UPDATE player_mapping SET mlb_player_id = mlb_id WHERE mlb_player_id IS NULL;

-- Step 3: Create index for performance
CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb_player_id ON player_mapping(mlb_player_id);

-- Step 4: Verify the migration
-- SELECT COUNT(*) as total, 
--        COUNT(mlb_id) as has_mlb_id, 
--        COUNT(mlb_player_id) as has_mlb_player_id 
-- FROM player_mapping;