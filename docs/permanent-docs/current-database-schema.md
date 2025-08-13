# Current Database Schema Documentation
*Last Updated: August 13, 2025*

## Overview
The GKL League Analytics system uses two database environments:
1. **Local SQLite Database** (`database/league_analytics.db`) - Development and data collection
2. **Cloudflare D1 Database** (`gkl-fantasy`) - Production deployment

## Production D1 Schema (As of August 2025)

### Core Data Tables

#### 1. transactions
Stores all league transaction data (adds, drops, trades).

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    league_key TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    yahoo_player_id TEXT NOT NULL,  -- Changed from player_id
    player_name TEXT NOT NULL,
    player_position TEXT,
    player_team TEXT,
    movement_type TEXT NOT NULL,
    destination_team_key TEXT,
    destination_team_name TEXT,
    source_team_key TEXT,
    source_team_name TEXT,
    timestamp INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(league_key, transaction_id, yahoo_player_id, movement_type)
);
```

**Key Changes:**
- `player_id` renamed to `yahoo_player_id` for consistency
- Separate `source_team_*` and `destination_team_*` fields for transaction flow
- `movement_type` indicates 'add' or 'drop'

#### 2. daily_lineups
Stores daily roster decisions for all teams.

```sql
CREATE TABLE daily_lineups (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    yahoo_player_id TEXT NOT NULL,  -- Changed from player_id
    player_name TEXT NOT NULL,
    selected_position TEXT,
    position_type TEXT,
    player_status TEXT,
    eligible_positions TEXT,
    player_team TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(date, team_key, yahoo_player_id, selected_position)
);
```

**Key Changes:**
- `player_id` renamed to `yahoo_player_id`
- `selected_position` is the lineup position (C, 1B, BN, etc.)
- `eligible_positions` stores all positions player can fill

#### 3. job_log
Tracks all data collection jobs for audit and debugging.

```sql
CREATE TABLE job_log (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    environment TEXT,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    error_message TEXT,
    metadata TEXT,
    date_range_start DATE,
    date_range_end DATE,
    league_key TEXT,
    season INTEGER
);
```

#### 4. player_mapping
Maps Yahoo player IDs to other baseball data sources.

```sql
CREATE TABLE player_mapping (
    player_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mlb_id INTEGER,
    mlb_player_id INTEGER,  -- Duplicate column for compatibility
    yahoo_player_id TEXT,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,  -- Stored as string integer
    player_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    team_code TEXT,
    active BOOLEAN DEFAULT 1,
    last_verified TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Known Issues:**
- `fangraphs_id` sometimes stored as float, needs integer conversion
- `yahoo_player_id` may be NULL for unmatched players
- `mlb_id` and `mlb_player_id` are duplicates (legacy issue)

#### 5. daily_gkl_player_stats
Comprehensive MLB player statistics.

```sql
CREATE TABLE daily_gkl_player_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    date DATE NOT NULL,
    yahoo_player_id TEXT,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    mlb_player_id INTEGER,
    player_name TEXT NOT NULL,
    team_code TEXT NOT NULL,
    position_codes TEXT,
    games_played INTEGER DEFAULT 0,
    is_starter BOOLEAN DEFAULT FALSE,
    
    -- Batting statistics (30+ columns)
    batting_at_bats INTEGER,
    batting_runs INTEGER,
    batting_hits INTEGER,
    -- ... many more batting fields ...
    
    -- Pitching statistics (20+ columns)
    pitching_games INTEGER,
    pitching_innings_pitched REAL,
    pitching_wins INTEGER,
    -- ... many more pitching fields ...
    
    -- Data quality fields
    health_score REAL DEFAULT 0.0,
    health_grade TEXT DEFAULT 'F',
    has_batting_data BOOLEAN DEFAULT FALSE,
    has_pitching_data BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id)
);
```

**Known Issues:**
- ID columns sometimes store literal string values instead of actual IDs
- Column name inconsistencies between local and production

#### 6. draft_results
Annual draft data (snake or auction).

```sql
CREATE TABLE draft_results (
    draft_id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT,
    pick_number INTEGER NOT NULL,
    round_number INTEGER,
    yahoo_player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_team TEXT,
    player_position TEXT,
    draft_cost INTEGER,
    is_keeper BOOLEAN DEFAULT FALSE,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(league_key, season, pick_number)
);
```

### Missing/Removed Tables

The following tables exist in documentation but NOT in production:
- `teams` - Team information (referenced in some queries but doesn't exist)
- `players` - Player registry (consolidated into player_mapping)
- `transaction_players` - Detailed transaction movements (merged into transactions)

## Local Development Schema

The local SQLite database generally mirrors the production schema with some variations:
- May use `player_id` instead of `yahoo_player_id` in older tables
- Contains test tables with `_test` suffix
- Includes development/debugging tables

## Schema Migration History

1. **August 5, 2025**: Initial column rename migration (`player_id` → `yahoo_player_id`)
2. **August 7, 2025**: Player stats schema update with proper ID columns
3. **August 13, 2025**: Fixed column references in production queries

## Critical Column Name Mappings

| Table | Old Column | New Column | Status |
|-------|------------|------------|---------|
| transactions | player_id | yahoo_player_id | ✅ Migrated |
| daily_lineups | player_id | yahoo_player_id | ✅ Migrated |
| daily_lineups | position | selected_position | ✅ Migrated |
| daily_gkl_player_stats | mlb_id | mlb_player_id | ⚠️ Both exist |

## Foreign Key Relationships

```
job_log (job_id) ←── transactions (job_id)
                 ←── daily_lineups (job_id)
                 ←── daily_gkl_player_stats (job_id)
                 ←── draft_results (job_id)

player_mapping (yahoo_player_id) ←→ transactions (yahoo_player_id)
                                 ←→ daily_lineups (yahoo_player_id)
                                 ←→ daily_gkl_player_stats (yahoo_player_id)
```

## Data Import Order (Critical)

When importing data to D1, follow this order to avoid foreign key violations:
1. `job_log` - Must be imported FIRST
2. `player_mapping` - Import before player stats
3. Core data tables (`transactions`, `daily_lineups`, `daily_gkl_player_stats`)
4. `draft_results` - Can be imported independently

## Known Issues and Gotchas

1. **Column Name Inconsistencies**: Production uses `yahoo_player_id`, some local code may still reference `player_id`
2. **Missing Tables**: `teams` table referenced in joins but doesn't exist in production
3. **ID Storage Bug**: Player stat ID columns sometimes store column names as strings
4. **Data Type Issues**: `fangraphs_id` stored as float instead of string integer
5. **Duplicate Columns**: `mlb_id` and `mlb_player_id` both exist with same data