-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_source_team ON transactions(source_team_key);
CREATE INDEX IF NOT EXISTS idx_transactions_dest_team ON transactions(destination_team_key);
CREATE INDEX IF NOT EXISTS idx_transactions_player ON transactions(player_name);
CREATE INDEX IF NOT EXISTS idx_lineups_date ON daily_lineups(date);
CREATE INDEX IF NOT EXISTS idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX IF NOT EXISTS idx_lineups_player ON daily_lineups(player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX IF NOT EXISTS idx_player_stats_mlb_id ON daily_gkl_player_stats(mlb_player_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_yahoo_id ON daily_gkl_player_stats(yahoo_player_id);
CREATE INDEX IF NOT EXISTS idx_job_log_status ON job_log(status);
CREATE INDEX IF NOT EXISTS idx_job_log_type ON job_log(job_type);