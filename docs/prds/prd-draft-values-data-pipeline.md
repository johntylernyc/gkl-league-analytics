# PRD: Draft Values Data Pipeline

**Author:** Senior Product Manager  
**Date:** August 4, 2025  
**Status:** Approved  
**Version:** 2.0  

---

## Executive Summary

This PRD outlines the implementation of a draft values data pipeline for the GKL League Analytics platform. The pipeline will retrieve historical draft data from Yahoo Fantasy Baseball, store draft values in our database, and enable analysis of draft performance versus in-season roster usage. As drafts occur only once per season, this pipeline will operate as an on-demand job with manual keeper designation support.

## Problem Statement

### Current State

- The application tracks player usage through daily lineups and transactions
- No visibility into original draft investment for each player
- Cannot analyze draft ROI or identify draft steals/busts
- Missing critical context for player value assessment

### Desired State

- Complete draft history stored in the database
- Draft values linked to daily lineup data
- Analytics comparing draft cost to actual usage
- Manual process for keeper designation with clear documentation
- On-demand data collection with direct D1 updates

## Goals & Objectives

### Primary Goals

1. **Data Collection**: Retrieve and store draft results from Yahoo Fantasy API
2. **Manual Keeper Process**: Support manual keeper designation post-collection
3. **Historical Support**: Enable collection of any league/season combination
4. **Direct D1 Updates**: Push data directly to production on collection

### Success Metrics

- 100% draft data coverage for requested seasons
- Clear documentation for manual keeper updates
- < 5 second collection time per draft
- Zero data quality issues in production

## User Stories

### As a League Commissioner

- I want to run draft collection after our annual draft
- I want clear instructions for marking keeper players
- I want to collect historical draft data from past seasons
- I want draft data immediately available in production

### As a Team Owner

- I want accurate draft data including keeper designations
- I want to track my draft picks' performance
- I want to compare my draft ROI to other teams

### As a Data Analyst

- I want draft data integrated with lineup usage
- I want accurate keeper status for draft analysis
- I want to analyze draft patterns across multiple seasons

## Technical Requirements

### Data Model

```sql
-- Table: draft_results (unchanged)
CREATE TABLE draft_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
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
```

### API Integration

**Yahoo Fantasy API Endpoints:**

- `/{league_key}/settings` - Get draft type (snake/auction)
- `/{league_key}/draftresults` - Retrieve draft results
- `/players;player_keys={keys}` - Enrich player details

**Note on Keeper Status:**
- Yahoo API's `is_keeper` field is unreliable/empty
- Keeper designation requires manual database updates
- Clear documentation provided for this process

### Architecture Changes

**Data Flow:**
```
Yahoo API → Draft Collector → SQLite → Direct D1 Push
                                ↓
                        Manual Keeper Update
```

**Key Differences from Other Pipelines:**
- No daily refresh (draft is once per season)
- Direct push to D1 on collection
- Manual keeper designation process
- Parameterized for any league/season

## Development Plan

### Stage 1: Core Collection Enhancement

**Objective**: Update collector for on-demand operation

**Deliverables**:
- Updated `collector.py` with league_key/season parameters
- Direct D1 push functionality
- Removal of automatic keeper detection
- Clear logging of collection results

**Implementation**:
```python
def collect_draft_results(self, league_key: str, season: int, push_to_d1: bool = True):
    """
    Collect draft results for specified league and season.
    
    Args:
        league_key: Yahoo league key (e.g., '458.l.6966')
        season: Season year (e.g., 2025)
        push_to_d1: Whether to push results to D1 immediately
    """
```

### Stage 2: Manual Keeper Process

**Objective**: Provide tools and documentation for keeper updates

**Deliverables**:
- SQL scripts for keeper updates
- Clear documentation in README
- Helper script for bulk keeper updates
- Verification queries

**Keeper Update Process**:
```sql
-- Update specific players as keepers
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = ? 
  AND season = ?
  AND player_name IN ('Player 1', 'Player 2', ...);

-- Verify keeper count
SELECT team_name, COUNT(*) as keeper_count
FROM draft_results
WHERE keeper_status = 1 AND league_key = ? AND season = ?
GROUP BY team_name;
```

### Stage 3: Historical Collection Support

**Objective**: Enable collection of past seasons

**Deliverables**:
- Backfill script for multiple seasons
- Error handling for missing data
- Progress tracking and reporting
- Documentation for available seasons

**Usage Example**:
```bash
# Collect single season
python draft_results/collector.py --league_key "458.l.6966" --season 2025

# Collect multiple seasons
python draft_results/backfill_drafts.py --league_key "458.l.6966" --start 2020 --end 2025
```

### Stage 4: Production Integration

**Objective**: Streamline production updates

**Deliverables**:
- Direct D1 push implementation
- Removal from daily sync scripts
- Updated deployment documentation
- Monitoring for collection jobs

**D1 Push Implementation**:
```python
def push_to_d1(self, draft_data: List[Dict]):
    """Push collected draft data directly to D1."""
    # Export to SQL
    # Execute against D1
    # Verify insertion
    # Log results
```

## Operational Procedures

### Annual Draft Collection Process

1. **Post-Draft Collection** (Within 24 hours of draft)
   ```bash
   python collector.py --league_key "458.l.6966" --season 2025
   ```

2. **Verify Collection**
   - Check job logs for success
   - Verify record count matches draft
   - Confirm D1 update completed

3. **Update Keepers** (Manual process)
   - Obtain keeper list from league
   - Run keeper update SQL
   - Verify keeper counts (0-3 per team)

4. **Documentation**
   - Update season notes
   - Record any issues
   - Note keeper designations

### Manual Keeper Update Instructions

**Step 1: Identify Keepers**
- Get official keeper list from Yahoo or league commissioner
- Note player names exactly as they appear

**Step 2: Update Database**
```sql
-- Connect to production database
-- Update keeper status
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = '458.l.6966' 
  AND season = 2025
  AND player_name IN (
    'Shohei Ohtani (Batter)',
    'Aaron Judge',
    -- ... other keepers
  );
```

**Step 3: Verify**
```sql
-- Check keeper distribution
SELECT team_name, COUNT(*) as keepers
FROM draft_results
WHERE keeper_status = 1 
  AND league_key = '458.l.6966' 
  AND season = 2025
GROUP BY team_name
ORDER BY team_name;
```

## Risk Mitigation

### Data Risks

1. **Keeper Accuracy**: Manual process may introduce errors
   - *Mitigation*: Verification queries and count validation
   
2. **Missing Historical Data**: Older seasons may be unavailable
   - *Mitigation*: Document available seasons per league

3. **API Changes**: Yahoo may modify endpoints
   - *Mitigation*: Version detection and error handling

### Operational Risks

1. **Forgotten Collection**: Draft might not be collected
   - *Mitigation*: Calendar reminders and documentation
   
2. **Keeper Updates**: Manual process might be skipped
   - *Mitigation*: Checklist and verification steps

## Success Metrics

### Collection Metrics
- Time to collect draft: < 60 seconds
- Success rate: 100% for available seasons
- D1 push success: 100%

### Data Quality Metrics
- Player name enrichment: 100%
- Draft type detection accuracy: 100%
- Keeper designation accuracy: Manual verification required

## Documentation Requirements

### README.md Updates

1. **Collection Instructions**
   - Command-line usage
   - Parameter descriptions
   - Example commands

2. **Keeper Update Process**
   - Step-by-step instructions
   - SQL examples
   - Verification queries

3. **Troubleshooting Guide**
   - Common issues
   - API limitations
   - Error resolution

4. **Annual Checklist**
   - Post-draft collection
   - Keeper updates
   - Verification steps

## Appendix

### A. Command-Line Interface

```bash
# Basic usage
python collector.py --league_key "458.l.6966" --season 2025

# With options
python collector.py \
  --league_key "458.l.6966" \
  --season 2025 \
  --skip_d1_push \
  --verbose

# Historical backfill
python backfill_drafts.py \
  --league_key "458.l.6966" \
  --start_season 2020 \
  --end_season 2025
```

### B. Keeper Patterns by League Type

**Auction Keeper Leagues:**
- Often draft keepers in final rounds
- Keeper cost may be previous year + $5
- 0-3 keepers per team typical

**Snake Keeper Leagues:**
- Keepers cost draft round from previous year
- May lose pick in round where player was kept
- Position in draft varies by keeper count

### C. Yahoo API Limitations

- Draft data available for ~5-7 years
- Player names not included in draft endpoint
- Keeper status field unreliable
- Rate limit: 1 request/second