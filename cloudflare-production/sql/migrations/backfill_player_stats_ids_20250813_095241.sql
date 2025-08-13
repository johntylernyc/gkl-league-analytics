-- Backfill Player IDs in daily_gkl_player_stats
-- Generated: 2025-08-13T09:52:41.465089
-- This updates existing records with Yahoo, Baseball Reference, and Fangraphs IDs

-- Check current state
SELECT 'Before Update' as status,
       COUNT(*) as total_records,
       COUNT(yahoo_player_id) as with_yahoo,
       COUNT(baseball_reference_id) as with_bbref,
       COUNT(fangraphs_id) as with_fg
FROM daily_gkl_player_stats;

-- Update player IDs from player_mapping table
UPDATE daily_gkl_player_stats
SET yahoo_player_id = (
        SELECT yahoo_player_id FROM player_mapping 
        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
    ),
    baseball_reference_id = (
        SELECT baseball_reference_id FROM player_mapping 
        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
    ),
    fangraphs_id = (
        SELECT fangraphs_id FROM player_mapping 
        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
    )
WHERE EXISTS (
    SELECT 1 FROM player_mapping 
    WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
);

-- Check final state
SELECT 'After Update' as status,
       COUNT(*) as total_records,
       COUNT(yahoo_player_id) as with_yahoo,
       COUNT(baseball_reference_id) as with_bbref,
       COUNT(fangraphs_id) as with_fg
FROM daily_gkl_player_stats;
