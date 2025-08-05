# Draft Values Data Pipeline - Implementation Plan

**Author**: Claude Code  
**Date**: August 4, 2025  
**Status**: Stage 1 Complete, Revision in Progress  
**Version**: 2.0  
**Updated**: August 4, 2025 (Post-User Feedback)  

## Executive Summary

This document outlines the implementation plan for adding a draft values data pipeline to the GKL League Analytics platform. The pipeline will collect draft results from the Yahoo Fantasy Sports API, store them in the database, and enable draft ROI analysis. This implementation follows the established patterns from the `daily_lineups` and `league_transactions` pipelines.

## Understanding of Existing Patterns

### 1. Code Structure Pattern

Based on analysis of existing pipelines, each data collection module follows this structure:

```
data_pipeline/
└── [module_name]/
    ├── __init__.py          # Module initialization
    ├── README.md            # Module documentation
    ├── schema.sql           # Database schema
    ├── config.py            # Configuration settings
    ├── collector.py         # Main collection class (Stage 1)
    ├── backfill_[name].py   # Bulk historical collection
    ├── update_[name].py     # Incremental updates
    ├── data_quality_check.py # Data validation
    ├── parser.py            # XML parsing logic
    ├── repository.py        # Database access layer
    └── tests/
        └── test_collector.py # Basic tests
```

### 2. Key Patterns Identified

#### Authentication Pattern
- Uses `YahooTokenManager` from `auth/token_manager.py`
- Automatic token refresh when expired
- Support for both local (tokens.json) and GitHub Actions (env vars)

#### Job Logging Pattern
All operations tracked in `job_log` table:
```python
job_id = f"{job_type}_{environment}_{timestamp}_{uuid}"
# Start job → Track progress → Update completion status
```

#### Environment Support Pattern
```python
def __init__(self, environment='development'):
    self.db_path = get_database_path(environment)
    self.table_name = get_table_name('draft_results', environment)
```

#### Error Handling Pattern
- Try/catch blocks around all API calls
- Exponential backoff for retries
- Comprehensive logging at each stage
- Data quality validation before insertion

#### Rate Limiting Pattern
- 1 request/second to Yahoo API
- Thread-safe rate limiter for parallel processing
- Maximum 4 workers for bulk operations

## Implementation Plan - Stage 1

### Files to Create/Modify

#### 1. Create Directory Structure
```
data_pipeline/draft_results/
├── __init__.py
├── README.md
├── schema.sql
├── config.py
├── collector.py
└── tests/
    └── test_collector.py
```

#### 2. Database Schema (`schema.sql`)
Direct from PRD with job_log foreign key:
```sql
CREATE TABLE draft_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_key TEXT NOT NULL,
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
    FOREIGN KEY (job_id) REFERENCES job_log(job_id)
);

-- Indexes for performance
CREATE INDEX idx_draft_league_season ON draft_results(league_key, season);
CREATE INDEX idx_draft_team ON draft_results(team_key);
CREATE INDEX idx_draft_player ON draft_results(player_id);
CREATE INDEX idx_draft_round_pick ON draft_results(draft_round, draft_pick);
CREATE INDEX idx_draft_job ON draft_results(job_id);
```

#### 3. Configuration (`config.py`)
Following daily_lineups pattern:
```python
# API Configuration
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'
API_DELAY_SECONDS = 1.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Database Configuration
def get_draft_table_name(environment='production'):
    return get_table_name('draft_results', environment)
```

#### 4. Main Collector Class (`collector.py`)
Key methods following the established pattern:
```python
class DraftResultsCollector:
    def __init__(self, environment='development'):
        # Database setup
        self.db_path = get_database_path(environment)
        self.table_name = get_table_name('draft_results', environment)
        
        # Authentication
        self.token_manager = YahooTokenManager()
        
        # Job logging
        self.job_id = None
        self.stats = {...}
    
    def collect_draft_results(self, league_key, season):
        """Main entry point for collection"""
        # 1. Start job logging
        # 2. Fetch draft type from league settings
        # 3. Fetch draft results
        # 4. Validate data
        # 5. Insert to database
        # 6. Update job status
    
    def fetch_draft_data_from_yahoo(self, league_key):
        """API call to Yahoo"""
        # GET /fantasy/v2/league/{league_key}/draftresults
    
    def validate_draft_data(self, draft_data):
        """Data quality checks"""
        # Ensure required fields
        # Validate draft types
        # Check data consistency
    
    def insert_draft_results(self, draft_data):
        """Database insertion with job_id"""
        # Batch insert
        # Handle duplicates
        # Track statistics
```

### Yahoo API Endpoints to Use

1. **League Settings** (to determine draft type):
   ```
   GET /fantasy/v2/league/{league_key}/settings
   ```
   Expected response includes:
   - `draft_type`: "live" (snake) or "auction"
   - `num_teams`: Number of teams
   - `draft_time`: When draft occurred

2. **Draft Results**:
   ```
   GET /fantasy/v2/league/{league_key}/draftresults
   ```
   Expected response format (from PRD):
   ```xml
   <draft_result>
     <pick>1</pick>
     <round>1</round>
     <team_key>431.l.12345.t.1</team_key>
     <player_key>431.p.12345</player_key>
     <player_name>Ronald Acuña Jr.</player_name>
     <cost></cost>  <!-- Only for auction drafts -->
   </draft_result>
   ```

### Error Handling Approach

1. **API Errors**:
   - 401: Token expired → Refresh and retry
   - 404: Draft not found → Log and skip
   - 429: Rate limit → Exponential backoff
   - 5xx: Server error → Retry with backoff

2. **Data Errors**:
   - Missing required fields → Log warning, skip record
   - Invalid draft types → Default to 'snake'
   - Duplicate entries → Use INSERT OR IGNORE

3. **Database Errors**:
   - Connection failures → Retry with backoff
   - Foreign key violations → Ensure job_id exists
   - Constraint violations → Log and investigate

### Testing Approach

1. **Unit Test** (`test_collector.py`):
   ```python
   def test_yahoo_api_connection():
       """Test real API call"""
       collector = DraftResultsCollector(environment='test')
       # Use a known league key
       data = collector.fetch_draft_data_from_yahoo('431.l.6966')
       assert data is not None
   ```

2. **Integration Test**:
   - Fetch real draft data
   - Validate against schema
   - Insert into test database
   - Verify data integrity

## Implementation Stages

### Stage 1: Core Collection (This Implementation)
- Basic collector class
- Schema creation
- Configuration
- Simple test with real API

### Stage 2: Data Management (Future)
- Repository pattern for data access
- Backfill script for historical data
- Update script for incremental updates
- Data quality validation module

### Stage 3: Production Integration (Future)
- Cloudflare Worker endpoints
- D1 database migration
- GitHub Actions automation
- Frontend integration

### Stage 4: Analytics Features (Future)
- Draft ROI calculations
- Value analysis endpoints
- Frontend visualizations

## Success Criteria for Stage 1

1. ✅ Successfully fetch draft data from Yahoo API (real data, no mocks)
2. ✅ Parse both snake and auction draft formats
3. ✅ Store data with proper job logging
4. ✅ Follow established code patterns exactly
5. ✅ Pass basic integration test with real API

## Stage 1 Implementation Results

### Summary
Stage 1 implementation completed successfully on August 4, 2025. All success criteria met.

### Key Achievements
1. **Data Collection**: Successfully collected 378 draft picks from league 458.l.6966
2. **Draft Type Detection**: Correctly identified auction draft (despite API reporting 'snake')
3. **Player Enrichment**: Implemented batch API calls to fetch player names
4. **Job Logging**: Comprehensive tracking with job IDs and statistics
5. **Error Handling**: Robust retry logic and validation

### Technical Discoveries
1. **Player Names Not in Draft API**: Yahoo's draft results API only returns player keys, not names. Solution: Implemented `fetch_player_details()` method that batches player lookups in groups of 25.
2. **Draft Type Ambiguity**: League settings API reported 'snake' but draft data contained costs, indicating auction. Both types handled correctly.
3. **Performance**: Full draft collection with enrichment takes ~30 seconds due to rate limiting and multiple API calls.

### Statistics
- Total API Requests: 19 (1 settings + 1 draft + 1 teams + 16 player batches)
- Records Processed: 378
- Validation Errors: 0
- Processing Time: ~30 seconds

### Files Created
1. ✅ `data_pipeline/draft_results/__init__.py`
2. ✅ `data_pipeline/draft_results/schema.sql`
3. ✅ `data_pipeline/draft_results/config.py`
4. ✅ `data_pipeline/draft_results/collector.py`
5. ✅ `data_pipeline/draft_results/README.md`
6. ✅ `data_pipeline/draft_results/tests/test_collector.py`
7. ✅ `data_pipeline/draft_results/tests/run_test_with_env.py` (helper)
8. ✅ `data_pipeline/draft_results/tests/check_results.py` (verification)

## Risk Mitigation

1. **API Changes**: Use try/catch and log unexpected formats
2. **Missing Historical Data**: Document available seasons in README
3. **Large Drafts**: Implement pagination if needed
4. **Keeper Complexity**: Add keeper_status flag for future use

## Next Steps

Upon approval of this plan:
1. Create directory structure
2. Implement schema.sql
3. Build config.py
4. Develop collector.py with core methods
5. Create basic test_collector.py
6. Test with real Yahoo API data
7. Document in README.md

---

**Note**: This implementation strictly follows the patterns established in `daily_lineups` and `league_transactions` to ensure consistency and maintainability.

## Revised Implementation Plan (v2.0)

Based on user feedback, the implementation approach has been revised to better match the nature of draft data (once per season) and keeper complexity.

### Key Changes from v1.0

1. **Manual Keeper Process**: Instead of automatic detection, provide clear documentation and tools for manual keeper updates
2. **On-Demand Collection**: Remove daily refresh pattern; drafts happen once per season
3. **Direct D1 Push**: Push to production immediately on collection instead of daily sync
4. **Parameterized Collection**: Add league_key and season parameters for flexible collection
5. **Historical Support**: Enable collection of past seasons on demand

### Revised Stage Plan

#### Stage 1.5: Parameter Support (Current)
- ✅ Add league_key and season parameters to collector
- ✅ Remove hardcoded league values
- ✅ Update tests to use parameters

#### Stage 2: Manual Keeper Process
- Create SQL scripts for keeper updates
- Document keeper update process in README
- Add verification queries
- Create helper Python script for bulk updates

#### Stage 3: Direct D1 Push
- Implement push_to_d1() method in collector
- Remove from daily sync patterns
- Add --skip_d1_push flag for testing
- Update deployment documentation

#### Stage 4: Historical Collection
- Create backfill_drafts.py script
- Handle missing seasons gracefully
- Add progress tracking
- Document available seasons

### Implementation Details

#### Collector Updates
```python
# Updated method signature
def collect_draft_results(self, league_key: str, season: int, push_to_d1: bool = True):
    """
    Collect draft results for any league/season.
    
    Args:
        league_key: Yahoo league key (e.g., '458.l.6966')
        season: Season year (e.g., 2025)
        push_to_d1: Whether to push to D1 immediately
    """
    # Implementation
```

#### Manual Keeper Process
```sql
-- README will include these examples
-- Update keepers for a specific team
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = '458.l.6966' 
  AND season = 2025
  AND team_name = 'Mary''s Little Lambs'
  AND player_name = 'Shohei Ohtani (Batter)';

-- Bulk update from list
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = '458.l.6966' 
  AND season = 2025
  AND player_name IN (
    'Aaron Judge',
    'Bobby Witt Jr.',
    'Gunnar Henderson',
    -- ... full list
  );
```

#### Command-Line Interface
```bash
# Basic collection
python draft_results/collector.py --league_key "458.l.6966" --season 2025

# Skip D1 push for testing
python draft_results/collector.py --league_key "458.l.6966" --season 2025 --skip_d1_push

# Historical backfill
python draft_results/backfill_drafts.py --league_key "458.l.6966" --start 2020 --end 2025
```

### Documentation Requirements

The README.md must include:
1. **Annual Draft Collection Checklist**
2. **Keeper Update Instructions** with SQL examples
3. **Verification Queries** to ensure data quality
4. **Troubleshooting Guide** for common issues
5. **Historical Data Limitations** by league

### Success Criteria

1. ✅ Parameterized collection works for any league/season
2. ⏳ Clear keeper update documentation in README
3. ⏳ Direct D1 push eliminates sync delay
4. ⏳ Historical collection supports 5+ years
5. ⏳ No daily overhead for static data