-- Simple Column Name Fix for D1
-- Date: 2025-08-13
-- Fixes player_id to yahoo_player_id naming

-- Check current column structure first with simple query
SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions' LIMIT 1;