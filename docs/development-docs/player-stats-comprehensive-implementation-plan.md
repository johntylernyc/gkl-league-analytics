# Player Stats Comprehensive Implementation Plan

**Created**: August 6, 2025  
**Status**: Active Implementation Guide  
**Supersedes**: All previous player stats implementation documents

## Executive Summary

This document outlines the implementation plan for a comprehensive MLB player statistics pipeline that collects daily stats for ALL MLB players (not just fantasy roster players). The system will maintain a complete player ID mapping across multiple platforms (MLB, Yahoo Fantasy, Baseball Reference, FanGraphs) to enable cross-platform analytics and research.

## Objectives

1. **Comprehensive Coverage**: Collect daily statistics for all ~750+ active MLB players
2. **Multi-Platform ID Mapping**: Maintain player IDs across MLB, Yahoo, Baseball Reference, and FanGraphs
3. **Historical Data**: Support backfilling multiple seasons of historical data
4. **Automated Updates**: Daily incremental updates via GitHub Actions
5. **Research Ready**: Enable analysis of any MLB player, not just those on fantasy rosters

## Architecture Overview

### Data Flow
```
PyBaseball API → Player ID Enrichment → Stats Processing → Database Storage
                        ↓
                Player ID Mapping (MLB, Yahoo, BBRef, FanGraphs)
                        ↓
                daily_gkl_player_stats table
```

### Technology Stack
- **Primary Data Source**: PyBaseball (wraps Baseball Reference, FanGraphs, MLB Stats API)
- **ID Mapping**: PyBaseball's playerid_lookup() + custom Yahoo matching
- **Storage**: SQLite (local/prod) and Cloudflare D1
- **Automation**: GitHub Actions with direct D1 writes

## Database Schema

### Player Mapping Table
```sql
CREATE TABLE player_mapping (
    player_mapping_id INTEGER PRIMARY KEY,
    mlb_id INTEGER UNIQUE NOT NULL,
    yahoo_player_id INTEGER,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    player_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    team_code TEXT,
    active BOOLEAN DEFAULT 1,
    last_verified DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(first_name, last_name, mlb_id)
);

CREATE INDEX idx_player_mapping_yahoo ON player_mapping(yahoo_player_id);
CREATE INDEX idx_player_mapping_name ON player_mapping(last_name, first_name);
```

### Daily Player Stats Table
```sql
CREATE TABLE daily_gkl_player_stats (
    job_id TEXT NOT NULL,
    date DATE NOT NULL,
    -- Player identifiers
    mlb_id INTEGER NOT NULL,
    yahoo_player_id INTEGER,
    baseball_reference_id TEXT,
    fangraphs_id TEXT,
    player_name TEXT NOT NULL,
    team_code TEXT,
    position_codes TEXT,
    games_played INTEGER DEFAULT 0,
    
    -- Batting stats (counting)
    batting_plate_appearances INTEGER DEFAULT 0,
    batting_at_bats INTEGER DEFAULT 0,
    batting_hits INTEGER DEFAULT 0,
    batting_singles INTEGER DEFAULT 0,
    batting_doubles INTEGER DEFAULT 0,
    batting_triples INTEGER DEFAULT 0,
    batting_home_runs INTEGER DEFAULT 0,
    batting_runs INTEGER DEFAULT 0,
    batting_rbis INTEGER DEFAULT 0,
    batting_walks INTEGER DEFAULT 0,
    batting_intentional_walks INTEGER DEFAULT 0,
    batting_strikeouts INTEGER DEFAULT 0,
    batting_hit_by_pitch INTEGER DEFAULT 0,
    batting_sacrifice_hits INTEGER DEFAULT 0,
    batting_sacrifice_flies INTEGER DEFAULT 0,
    batting_stolen_bases INTEGER DEFAULT 0,
    batting_caught_stealing INTEGER DEFAULT 0,
    batting_grounded_into_double_plays INTEGER DEFAULT 0,
    
    -- Batting stats (calculated)
    batting_avg REAL DEFAULT 0,
    batting_obp REAL DEFAULT 0,
    batting_slg REAL DEFAULT 0,
    batting_ops REAL DEFAULT 0,
    batting_babip REAL DEFAULT 0,
    batting_iso REAL DEFAULT 0,
    
    -- Pitching stats (counting)
    pitching_games INTEGER DEFAULT 0,
    pitching_games_started INTEGER DEFAULT 0,
    pitching_complete_games INTEGER DEFAULT 0,
    pitching_shutouts INTEGER DEFAULT 0,
    pitching_wins INTEGER DEFAULT 0,
    pitching_losses INTEGER DEFAULT 0,
    pitching_saves INTEGER DEFAULT 0,
    pitching_holds INTEGER DEFAULT 0,
    pitching_blown_saves INTEGER DEFAULT 0,
    pitching_innings_pitched REAL DEFAULT 0,
    pitching_hits_allowed INTEGER DEFAULT 0,
    pitching_runs_allowed INTEGER DEFAULT 0,
    pitching_earned_runs INTEGER DEFAULT 0,
    pitching_home_runs_allowed INTEGER DEFAULT 0,
    pitching_walks_allowed INTEGER DEFAULT 0,
    pitching_intentional_walks_allowed INTEGER DEFAULT 0,
    pitching_strikeouts INTEGER DEFAULT 0,
    pitching_hit_batters INTEGER DEFAULT 0,
    pitching_wild_pitches INTEGER DEFAULT 0,
    pitching_balks INTEGER DEFAULT 0,
    
    -- Pitching stats (calculated)
    pitching_era REAL DEFAULT 0,
    pitching_whip REAL DEFAULT 0,
    pitching_k_per_9 REAL DEFAULT 0,
    pitching_bb_per_9 REAL DEFAULT 0,
    pitching_hr_per_9 REAL DEFAULT 0,
    pitching_k_bb_ratio REAL DEFAULT 0,
    pitching_k_percentage REAL DEFAULT 0,
    pitching_bb_percentage REAL DEFAULT 0,
    pitching_babip REAL DEFAULT 0,
    pitching_lob_percentage REAL DEFAULT 0,
    
    -- Metadata
    has_batting_data BOOLEAN DEFAULT 0,
    has_pitching_data BOOLEAN DEFAULT 0,
    data_source TEXT DEFAULT 'pybaseball',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, mlb_id),
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    FOREIGN KEY (mlb_id) REFERENCES player_mapping(mlb_id)
);

-- Performance indexes
CREATE INDEX idx_player_stats_date ON daily_gkl_player_stats(date);
CREATE INDEX idx_player_stats_yahoo ON daily_gkl_player_stats(yahoo_player_id, date);
CREATE INDEX idx_player_stats_name ON daily_gkl_player_stats(player_name);
```

## Implementation Phases

### Phase 1: Foundation Setup (Day 1)

1. **Archive Old Approach**:
   - Move Yahoo daily stats scripts to archive
   - Archive old PRDs and implementation docs
   - Clean up test database

2. **Create Database Schema**:
   - Create player_mapping table
   - Create enhanced daily_gkl_player_stats table
   - Set up proper indexes and constraints

3. **Initialize Player Mapping**:
   ```python
   # Use PyBaseball to get initial player database
   from pybaseball import playerid_lookup, chadwick_register
   
   # Get comprehensive player registry
   players = chadwick_register()
   
   # Filter to active players (2023-2025)
   active_players = players[players.mlb_played_last >= 2023]
   ```

### Phase 2: Core Implementation (Day 2-3)

1. **Refactor backfill_stats.py**:
   ```python
   def backfill_date(date: str, environment: str = 'production'):
       """Collect stats for all MLB players on given date"""
       
       # 1. Get batting stats from PyBaseball
       batting_stats = batting_stats_range(date, date)
       
       # 2. Get pitching stats from PyBaseball  
       pitching_stats = pitching_stats_range(date, date)
       
       # 3. Enrich with player IDs
       batting_stats = enrich_player_ids(batting_stats)
       pitching_stats = enrich_player_ids(pitching_stats)
       
       # 4. Calculate advanced metrics
       batting_stats = calculate_batting_metrics(batting_stats)
       pitching_stats = calculate_pitching_metrics(pitching_stats)
       
       # 5. Save to database with job tracking
       save_player_stats(batting_stats, pitching_stats, date)
   ```

2. **Create update_stats.py**:
   - Similar to backfill but optimized for recent dates
   - Support --days, --since-last, --date options
   - Minimal output for automation

3. **Implement Player ID Mapping**:
   ```python
   def enrich_player_ids(stats_df):
       """Add all platform IDs to stats dataframe"""
       
       for idx, player in stats_df.iterrows():
           # Get or create mapping
           mapping = get_or_create_player_mapping(
               player['Name'],
               player.get('Team'),
               player.get('mlb_id')
           )
           
           # Add all IDs to dataframe
           stats_df.at[idx, 'yahoo_player_id'] = mapping['yahoo_player_id']
           stats_df.at[idx, 'baseball_reference_id'] = mapping['baseball_reference_id']
           stats_df.at[idx, 'fangraphs_id'] = mapping['fangraphs_id']
       
       return stats_df
   ```

### Phase 3: Yahoo ID Matching (Day 3-4)

1. **Build Yahoo Player Database**:
   ```python
   def build_yahoo_player_registry():
       """Extract all Yahoo players from our historical data"""
       
       # Query unique players from transactions
       transaction_players = get_players_from_transactions()
       
       # Query unique players from lineups
       lineup_players = get_players_from_lineups()
       
       # Combine and deduplicate
       yahoo_players = merge_player_lists(transaction_players, lineup_players)
       
       return yahoo_players
   ```

2. **Implement Fuzzy Matching**:
   ```python
   def match_yahoo_player(mlb_name: str, team: str = None) -> Optional[int]:
       """Find Yahoo player ID using fuzzy name matching"""
       
       candidates = search_yahoo_players(mlb_name, team)
       
       if len(candidates) == 1:
           return candidates[0]['yahoo_player_id']
       
       # Use advanced matching for multiple candidates
       best_match = fuzzy_match_player(mlb_name, candidates)
       
       return best_match['yahoo_player_id'] if best_match else None
   ```

### Phase 4: Testing & Validation (Day 4-5)

1. **Initial Test**:
   - Clear test database
   - Run one day (2025-08-05)
   - Verify ~750 player records
   - Check ID mapping coverage

2. **Validation Queries**:
   ```sql
   -- Check player coverage
   SELECT COUNT(DISTINCT mlb_id) as total_players,
          COUNT(DISTINCT yahoo_player_id) as yahoo_mapped,
          COUNT(DISTINCT baseball_reference_id) as bbref_mapped,
          COUNT(DISTINCT fangraphs_id) as fg_mapped
   FROM daily_gkl_player_stats
   WHERE date = '2025-08-05';
   
   -- Verify known players
   SELECT * FROM daily_gkl_player_stats
   WHERE player_name LIKE '%Muncy%' 
   AND date = '2025-08-05';
   ```

### Phase 5: Production Deployment (Day 5-6)

1. **Update sync_to_production.py**:
   - Add player_mapping table export
   - Handle larger daily_gkl_player_stats volume
   - Optimize for ~750 records/day

2. **GitHub Actions Integration**:
   - Add to data-refresh.yml workflow
   - Run after lineups collection
   - Use update_stats.py with 3-day lookback

3. **D1 Direct Write Support**:
   - Update D1Connection class
   - Add batch insert methods
   - Test with production credentials

## Rate Stat Calculations

### Batting Metrics
```python
# Basic
AVG = H / AB
OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
SLG = (1B + 2*2B + 3*3B + 4*HR) / AB
OPS = OBP + SLG

# Advanced
ISO = SLG - AVG  # Isolated Power
BABIP = (H - HR) / (AB - K - HR + SF)
```

### Pitching Metrics
```python
# Basic
ERA = 9 * ER / IP
WHIP = (H + BB) / IP
K/9 = 9 * K / IP
BB/9 = 9 * BB / IP
K/BB = K / BB

# Advanced
K% = K / TBF  # Strikeout percentage
BB% = BB / TBF  # Walk percentage
HR/9 = 9 * HR / IP
BABIP = (H - HR) / (BIP)  # Balls in play
LOB% = (H + BB + HBP - R) / (H + BB + HBP - 1.4 * HR)
```

## Data Volume Estimates

- **Daily**: ~750 active players × 1 record = 750 records/day
- **Season**: 750 × 180 days = 135,000 records/season
- **Multi-season**: 135,000 × 3 years = 405,000 total records
- **Storage**: ~1-2 KB/record = ~400-800 MB for 3 seasons

## Success Criteria

1. ✓ All MLB players collected daily (~750 records/day)
2. ✓ Player ID mapping >90% complete for active players
3. ✓ Yahoo ID matching for all fantasy-relevant players
4. ✓ Rate stats calculated accurately
5. ✓ Automated daily updates via GitHub Actions
6. ✓ Historical backfill capability

## Migration from Previous Approach

1. **Archive Yahoo-only scripts**
2. **Preserve any useful player mappings**
3. **Clear and rebuild stats tables**
4. **No data migration needed** (different approach)

## Testing Checklist

- [ ] Database schema created successfully
- [ ] Player mapping table populated
- [ ] One day of stats collected (~750 records)
- [ ] All rate stats calculated correctly
- [ ] Yahoo ID matching working
- [ ] Job logging functioning
- [ ] D1 integration tested
- [ ] GitHub Actions configured

## Next Steps

1. Create database schema in test environment
2. Initialize player mapping table
3. Implement PyBaseball collection
4. Build Yahoo ID matching
5. Run test collection
6. Validate results with user
7. Deploy to production

---

*This document represents the current implementation approach for the player stats pipeline. All previous approaches focusing on Yahoo-only or fantasy-roster-only collection should be considered deprecated.*