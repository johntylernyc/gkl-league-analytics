# PRD: Draft Values Data Pipeline

# PRD: Draft Values Data Pipeline

**Author:** Senior Product Manager

**Date:** August 4, 2025

**Status:** Draft

**Version:** 1.0

---

## Executive Summary

This PRD outlines the implementation of a draft values data pipeline for the GKL League Analytics platform. The pipeline will retrieve historical draft data from Yahoo Fantasy Baseball, store draft values (draft cost, draft position, draft round) in our database, and enable analysis of draft performance versus in-season roster usage. This feature will follow the established patterns from our existing `daily_lineups` and `league_transactions` pipelines.

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
- Insights into drafting patterns and effectiveness

## Goals & Objectives

### Primary Goals

1. **Data Collection**: Retrieve and store draft results from Yahoo Fantasy API
2. **Data Integration**: Link draft values to existing player and lineup data
3. **Analytics Enablement**: Support draft ROI and value analysis
4. **Historical Coverage**: Backfill all available seasons

### Success Metrics

- 100% draft data coverage for available seasons
- < 5 second query performance for draft analytics
- Zero data quality issues in production
- Automated daily updates with job logging

## User Stories

### As a League Manager

- I want to see which teams drafted the best values
- I want to identify players who outperformed their draft cost
- I want to analyze draft strategies across seasons

### As a Team Owner

- I want to track my draft picks' performance
- I want to compare my draft ROI to other teams
- I want to learn from successful draft strategies

### As a Data Analyst

- I want draft data integrated with lineup usage
- I want to query draft values alongside transactions
- I want to build predictive models using draft data

## Technical Requirements

### Data Model

```
-- New table: draft_results
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

### API Integration

**Yahoo Fantasy API Endpoints:**

- `/{league_key}/draftresults` - Retrieve draft results
- `/{league_key}/settings` - Get draft type and keeper rules

**Data Pipeline Architecture:**

```
Yahoo API → Draft Collector → Data Validator → Database → Analytics
```

### Implementation Patterns

Following established patterns from `daily_lineups` and `league_transactions`:

1. **Job Logging**: All operations tracked in job_log table
2. **Error Handling**: Comprehensive try/catch with logging
3. **Rate Limiting**: Respect Yahoo API limits (1 req/sec)
4. **Batch Processing**: Process multiple seasons efficiently
5. **Environment Support**: Dev/Test/Prod configurations

## Development Plan

### Stage 1: Initial Script Development (Week 1)

**Objective**: Create core draft data collection functionality

**Deliverables**:

- `draft_results/[collector.py](http://collector.py)` - Main collection logic
- `draft_results/schema.sql` - Database schema
- `draft_results/[config.py](http://config.py)` - Configuration settings
- `draft_results/[README.md](http://README.md)` - Module documentation

**Implementation Details**:

```
# draft_results/[collector.py](http://collector.py) structure
class DraftResultsCollector:
    def __init__(self, environment='development'):
        self.db_path = get_database_path(environment)
        self.token_manager = TokenManager()
        self.job_logger = JobLogger(self.db_path)
    
    def collect_draft_results(self, league_key, season):
        """Collect draft results for a specific league/season"""
        # Start job logging
        # Fetch draft results from Yahoo API
        # Validate and transform data
        # Insert into database
        # Update job status
    
    def backfill_all_seasons(self):
        """Backfill draft data for all available seasons"""
        # Iterate through seasons
        # Collect draft results
        # Handle errors gracefully
```

**Acceptance Criteria**:

- Successfully retrieves draft data from Yahoo API
- Handles both snake and auction draft types
- Implements proper job logging
- Follows existing code patterns

### Stage 2: Local Environment Integration (Week 2)

**Objective**: Integrate with local development database

**Deliverables**:

- `draft_results/[repository.py](http://repository.py)` - Data access layer
- `draft_results/[validator.py](http://validator.py)` - Data quality checks
- Test scripts for validation
- Integration with existing tables

**Key Features**:

- Foreign key relationships to players/teams
- Data validation rules
- Duplicate prevention logic
- Transaction management

**Acceptance Criteria**:

- No duplicate draft entries
- Proper foreign key constraints
- Data quality validation passes
- Integration tests pass

### Stage 3: Production Deployment (Week 3)

**Objective**: Deploy to Cloudflare infrastructure

**Deliverables**:

- Cloudflare Worker updates
- D1 database schema migration
- API endpoint for draft data
- Deployment documentation

**Deployment Steps**:

1. Update D1 schema with draft_results table
2. Modify Worker API to include draft endpoints
3. Update sync_to_[production.py](http://production.py) script
4. Deploy and verify in production

**Acceptance Criteria**:

- D1 database accepts draft data
- API endpoints return draft values
- No performance degradation
- Monitoring confirms success

### Stage 4: Automated Updates (Week 4)

**Objective**: Implement automated draft data updates

**Deliverables**:

- `draft_results/update_[draft.py](http://draft.py)` - Incremental updater
- GitHub Actions workflow integration
- Monitoring and alerting setup
- Update documentation

**Automation Features**:

- Daily checks for draft updates
- Keeper designation updates
- Trade impact on draft values
- Season rollover handling

**Acceptance Criteria**:

- Automated updates run successfully
- Job logs show completion
- No manual intervention required
- Alerts configured for failures

## Frontend Integration

### New Features

1. **Draft Board View**: Visual draft recap
2. **Player Cards**: Show draft cost/round
3. **Team Analysis**: Draft performance metrics
4. **League Trends**: Draft pattern analysis

### API Endpoints

```
// New endpoints in Cloudflare Worker
GET /api/draft-results
GET /api/draft-results/:season
GET /api/draft-results/team/:teamKey
GET /api/draft-results/player/:playerId
GET /api/analytics/draft-value
```

## Risk Assessment

### Technical Risks

1. **API Limitations**: Yahoo may not provide historical draft data beyond certain years
    - *Mitigation*: Document available seasons, handle gracefully
2. **Data Volume**: Large drafts (20+ teams) may impact performance
    - *Mitigation*: Implement pagination and caching
3. **Keeper Complexity**: Keeper leagues have complex draft rules
    - *Mitigation*: Add keeper_status flag and special handling

### Data Risks

1. **Missing Data**: Some draft data may be incomplete
    - *Mitigation*: Validation rules and data quality checks
2. **Schema Changes**: Yahoo API may change over time
    - *Mitigation*: Version checking and adapter pattern

## Success Metrics

### Technical Metrics

- API response time < 200ms
- Data collection success rate > 99%
- Zero data integrity issues
- 100% test coverage

### Business Metrics

- User engagement with draft features
- Increased session duration
- New insights discovered
- Feature adoption rate

## Timeline & Milestones

| Stage | Duration | Milestone |
| --- | --- | --- |
| Stage 1 | Week 1 | Core collection script complete |
| Stage 2 | Week 2 | Local database integration |
| Stage 3 | Week 3 | Production deployment |
| Stage 4 | Week 4 | Automation complete |
| Total | 4 weeks | Full feature launch |

## Appendix

### A. Yahoo API Response Format

```
{
  "draft_result": {
    "league_key": "431.l.12345",
    "draft_type": "snake",
    "picks": [{
      "pick": 1,
      "round": 1,
      "team_key": "431.l.12345.t.1",
      "player_key": "431.p.12345",
      "player_name": "Ronald Acuña Jr.",
      "cost": null
    }]
  }
}
```

### B. Database Query Examples

```
-- Get draft values for a team
SELECT * FROM draft_results 
WHERE team_key = ? AND season = ?
ORDER BY draft_round, draft_pick;

-- Find best draft values (most games started vs draft position)
SELECT 
    dr.player_name,
    dr.draft_round,
    dr.draft_pick,
    COUNT(dl.player_id) as games_started
FROM draft_results dr
LEFT JOIN daily_lineups dl ON dr.player_id = dl.player_id
WHERE dr.season = ? AND dl.selected_position != 'BN'
GROUP BY dr.player_id
ORDER BY games_started DESC;
```

### C. File Structure

```
data_pipeline/
└── draft_results/
    ├── __init__.py
    ├── [README.md](http://README.md)
    ├── [collector.py](http://collector.py)          # Main collection logic
    ├── [config.py](http://config.py)            # Configuration
    ├── [repository.py](http://repository.py)        # Data access layer
    ├── [validator.py](http://validator.py)         # Data validation
    ├── schema.sql          # Database schema
    ├── update_[draft.py](http://draft.py)     # Incremental updates
    ├── backfill_[draft.py](http://draft.py)   # Historical backfill
    └── tests/
        ├── test_[collector.py](http://collector.py)
        └── test_[validator.py](http://validator.py)
```