-- Database Schema for Cloudflare D1

-- Table: transactions
CREATE TABLE "transactions" (
	"id"	INTEGER,
	"date"	TEXT NOT NULL,
	"league_key"	TEXT NOT NULL,
	"transaction_id"	TEXT NOT NULL,
	"transaction_type"	TEXT NOT NULL,
	"player_id"	TEXT NOT NULL,
	"player_name"	TEXT NOT NULL,
	"player_team"	TEXT,
	"movement_type"	TEXT NOT NULL,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"player_position"	TEXT,
	"destination_team_key"	TEXT,
	"destination_team_name"	TEXT,
	"source_team_key"	TEXT,
	"source_team_name"	TEXT,
	"job_id"	TEXT,
	PRIMARY KEY("id" ),
	UNIQUE("transaction_id","player_id","movement_type")
);

-- Table: daily_lineups
CREATE TABLE daily_lineups (
    lineup_id INTEGER PRIMARY KEY ,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    selected_position TEXT,        -- The position player was started in (C, 1B, 2B, etc.)
    position_type TEXT,            -- B=Bench, P=Pitcher, etc. from Yahoo API
    player_status TEXT,            -- healthy, DTD, IL, etc.
    eligible_positions TEXT,       -- Comma-separated list of eligible positions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, player_team TEXT,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(date, team_key, player_id, selected_position)
);

-- Table: daily_gkl_player_stats
CREATE TABLE "daily_gkl_player_stats" (
            stat_id INTEGER PRIMARY KEY ,
            job_id TEXT NOT NULL,
            date DATE NOT NULL,
            mlb_player_id INTEGER,
            yahoo_player_id TEXT,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
            position_codes TEXT,
            games_played INTEGER DEFAULT 0,
            
            -- Batting statistics (all components)
            batting_plate_appearances INTEGER,
            batting_at_bats INTEGER,
            batting_runs INTEGER,
            batting_hits INTEGER,
            batting_singles INTEGER,
            batting_doubles INTEGER,
            batting_triples INTEGER,
            batting_home_runs INTEGER,
            batting_rbis INTEGER,
            batting_stolen_bases INTEGER,
            batting_caught_stealing INTEGER,
            batting_walks INTEGER,
            batting_intentional_walks INTEGER,
            batting_strikeouts INTEGER,
            batting_hit_by_pitch INTEGER,
            batting_sacrifice_hits INTEGER,
            batting_sacrifice_flies INTEGER,
            batting_ground_into_double_play INTEGER,
            batting_total_bases INTEGER,
            
            -- Pitching statistics (all components)
            pitching_games_started INTEGER,
            pitching_complete_games INTEGER,
            pitching_shutouts INTEGER,
            pitching_wins INTEGER,
            pitching_losses INTEGER,
            pitching_saves INTEGER,
            pitching_blown_saves INTEGER,
            pitching_holds INTEGER,
            pitching_innings_pitched REAL,
            pitching_batters_faced INTEGER,
            pitching_hits_allowed INTEGER,
            pitching_runs_allowed INTEGER,
            pitching_earned_runs INTEGER,
            pitching_home_runs_allowed INTEGER,
            pitching_walks_allowed INTEGER,
            pitching_intentional_walks_allowed INTEGER,
            pitching_strikeouts INTEGER,
            pitching_hit_batters INTEGER,
            pitching_wild_pitches INTEGER,
            pitching_balks INTEGER,
            pitching_quality_starts INTEGER,
            
            -- Data quality
            data_source TEXT DEFAULT 'mlb_stats_api',
            confidence_score REAL DEFAULT 1.0,
            has_batting_data BOOLEAN DEFAULT FALSE,
            has_pitching_data BOOLEAN DEFAULT FALSE,
            validation_status TEXT DEFAULT 'valid',
            validation_notes TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, baseball_reference_id TEXT, fangraphs_id TEXT,
            
            FOREIGN KEY (job_id) REFERENCES job_log(job_id),
            UNIQUE(date, mlb_player_id),
            
            CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
            CHECK (validation_status IN ('valid', 'warning', 'error'))
        );

-- Table: player_id_mapping
CREATE TABLE player_id_mapping ( mapping_id INTEGER PRIMARY KEY , yahoo_player_id TEXT NOT NULL UNIQUE, yahoo_player_name TEXT NOT NULL, mlb_player_id TEXT, fangraphs_id TEXT, bbref_id TEXT, standardized_name TEXT NOT NULL, team_code TEXT, position_codes TEXT, birth_year INTEGER, confidence_score REAL NOT NULL DEFAULT 0.0, mapping_method TEXT, manual_override BOOLEAN DEFAULT FALSE, verified_by TEXT, verified_at TIMESTAMP, is_active BOOLEAN DEFAULT TRUE, last_validated DATE, validation_status TEXT DEFAULT 'pending', notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0), CHECK (mapping_method IN ('exact', 'fuzzy', 'manual', 'verified')), CHECK (validation_status IN ('pending', 'valid', 'failed', 'needs_review')) );

-- Table: job_log
CREATE TABLE job_log (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            environment TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP NULL,
            duration_seconds REAL NULL,
            records_processed INTEGER DEFAULT 0,
            records_inserted INTEGER DEFAULT 0,
            date_range_start TEXT NULL,
            date_range_end TEXT NULL,
            league_key TEXT NULL,
            error_message TEXT NULL,
            metadata TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        , progress_pct REAL DEFAULT 0.0, last_checkpoint TIMESTAMP, estimated_completion TIMESTAMP);

