-- D1 Player Stats Truncation Commands
-- Run these commands in the Cloudflare D1 console
-- https://dash.cloudflare.com/ -> Workers & Pages -> D1 SQL Database -> gkl-fantasy

-- Step 1: Check current state
SELECT COUNT(*) as total_records FROM daily_gkl_player_stats;
SELECT COUNT(DISTINCT yahoo_player_id) as unique_players FROM daily_gkl_player_stats;
SELECT COUNT(*) as records_with_decimal FROM daily_gkl_player_stats WHERE yahoo_player_id LIKE '%.0';
SELECT COUNT(*) as bad_positions FROM daily_gkl_player_stats WHERE position_codes = 'POS';

-- Step 2: TRUNCATE the table (WARNING: This deletes ALL data!)
DELETE FROM daily_gkl_player_stats;

-- Step 3: Verify truncation
SELECT COUNT(*) FROM daily_gkl_player_stats;

-- After truncation:
-- 1. Merge feature/player-stats-fixes branch to main
-- 2. Go to GitHub Actions: https://github.com/johntylernyc/gkl-league-analytics/actions
-- 3. Run "Scheduled Data Refresh" workflow with:
--    - Refresh Type: manual
--    - Environment: production
--    - Date Range: 2025-03-27,2025-08-07