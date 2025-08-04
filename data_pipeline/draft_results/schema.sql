-- Draft Results Table Schema
-- Stores historical draft data from Yahoo Fantasy Baseball leagues

CREATE TABLE IF NOT EXISTS draft_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_position TEXT,
    player_team TEXT,
    draft_round INTEGER NOT NULL,
    draft_pick INTEGER NOT NULL,
    draft_cost INTEGER,  -- For auction drafts
    draft_type TEXT NOT NULL,  -- 'snake' or 'auction'
    keeper_status BOOLEAN DEFAULT FALSE,
    drafted_datetime TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(league_key, season, player_id, team_key)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_draft_league_season ON draft_results(league_key, season);
CREATE INDEX IF NOT EXISTS idx_draft_team ON draft_results(team_key);
CREATE INDEX IF NOT EXISTS idx_draft_player ON draft_results(player_id);
CREATE INDEX IF NOT EXISTS idx_draft_round_pick ON draft_results(draft_round, draft_pick);
CREATE INDEX IF NOT EXISTS idx_draft_job ON draft_results(job_id);

-- Add triggers for updated_at
CREATE TRIGGER IF NOT EXISTS update_draft_results_timestamp 
AFTER UPDATE ON draft_results
BEGIN
    UPDATE draft_results SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;