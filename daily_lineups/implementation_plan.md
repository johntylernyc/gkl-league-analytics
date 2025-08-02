# Daily Lineups Module - Implementation Plan

## Overview
This document outlines the staged development plan for the Daily Lineups feature, which provides comprehensive historical roster analysis capabilities for Yahoo Fantasy Baseball leagues.

## Architecture Overview

### Integration Points
- **Database**: Uses existing `database/league_analytics.db` SQLite database
- **Authentication**: Leverages existing `auth/TokenManager` for Yahoo API OAuth2
- **Job Logging**: Integrates with standardized job logging system from `backfill_transactions_optimized.py`
- **API Client**: Extends existing Yahoo Fantasy API integration patterns

### Data Flow
1. OAuth2 token management (auto-refresh on hourly expiration)
2. Daily batch collection of roster data from Yahoo API
3. XML parsing and data extraction
4. Database storage with job tracking
5. Web UI consumption via REST API

## Implementation Stages

### Stage 1: Database Schema & Infrastructure (Week 1)
**Goal**: Establish database foundation and core infrastructure

**Tasks**:
- [ ] Create `daily_lineups` table schema
- [ ] Create `lineup_positions` lookup table
- [ ] Add performance indexes for common queries
- [ ] Create migration script for schema updates
- [ ] Set up test/production table separation

**Deliverables**:
- `database/schema_lineups.sql`
- `database/migrate_lineups.py`
- Updated database with new tables

**Success Criteria**:
- Tables created with proper constraints
- Indexes optimize query performance (<500ms for date/team queries)
- Test/production data separation working

### Stage 2: Core Data Collection Module (Week 1-2)
**Goal**: Implement robust Yahoo API data collection

**Tasks**:
- [ ] Create `DailyLineupsCollector` class
- [ ] Implement token management integration
- [ ] Add XML parsing for roster responses
- [ ] Implement retry logic and error handling
- [ ] Add rate limiting (2-second delays)

**Deliverables**:
- `daily_lineups/collector.py`
- `daily_lineups/parser.py`
- Unit tests for core functionality

**Code Structure** (adapted from `backfill_rosters.py`):
```python
class DailyLineupsCollector:
    def __init__(self, token_manager, db_connection):
        self.token_manager = token_manager
        self.db = db_connection
        
    def fetch_team_roster(self, team_key, date):
        # Adapted from backfill_rosters.py line 124-161
        # Returns parsed roster data
        
    def process_date_range(self, start_date, end_date, job_id):
        # Batch processing with checkpoint support
```

### Stage 3: Job Management & Logging (Week 2)
**Goal**: Integrate with existing job logging system

**Tasks**:
- [ ] Implement job logging for lineup collection
- [ ] Add checkpoint/resume capability
- [ ] Create progress tracking
- [ ] Implement data lineage tracking
- [ ] Add job status reporting

**Deliverables**:
- `daily_lineups/job_manager.py`
- Integration with existing `job_log` table

**Pattern** (from `backfill_transactions_optimized.py`):
```python
job_id = start_job_log(
    job_type="lineup_collection",
    environment="production",
    date_range_start=start_date,
    date_range_end=end_date,
    league_key=league_key
)
```

### Stage 4: Historical Backfill Script (Week 2-3)
**Goal**: Enable bulk historical data collection

**Tasks**:
- [ ] Create backfill script for 2025 season
- [ ] Implement parallel processing (2 concurrent workers)
- [ ] Add duplicate detection
- [ ] Create validation reports
- [ ] Implement incremental update mode

**Deliverables**:
- `daily_lineups/backfill_lineups.py`
- `daily_lineups/update_lineups.py`
- Validation scripts

**Key Features**:
- Resume from checkpoint on failure
- UPSERT logic to prevent duplicates
- Comprehensive error logging
- Progress reporting

### Stage 5: Data Access Layer (Week 3)
**Goal**: Create efficient data access patterns

**Tasks**:
- [ ] Create `LineupRepository` class
- [ ] Implement query optimization
- [ ] Add caching layer
- [ ] Create aggregation queries
- [ ] Build usage analytics queries

**Deliverables**:
- `daily_lineups/repository.py`
- Query performance benchmarks

**Key Queries**:
```python
def get_lineup_by_date(team_key, date)
def get_player_usage_stats(player_id, date_range)
def get_bench_decisions(team_key, date_range)
def get_optimal_lineup(team_key, date)
```

### Stage 6: REST API Development (Week 3-4)
**Goal**: Expose lineup data via REST API

**Tasks**:
- [ ] Create lineup endpoints
- [ ] Implement filtering and pagination
- [ ] Add player usage endpoints
- [ ] Create analytics endpoints
- [ ] Add export functionality

**Deliverables**:
- `web-ui/backend/routes/lineupRoutes.js`
- `web-ui/backend/services/lineupService.js`
- API documentation

**Endpoints**:
```
GET /api/lineups/:date/:teamId
GET /api/lineups/player/:playerId/usage
GET /api/lineups/analytics/bench-value
GET /api/lineups/export
```

### Stage 7: Frontend - Lineup Viewer (Week 4)
**Goal**: Build core lineup viewing interface

**Tasks**:
- [ ] Create LineupExplorer page component
- [ ] Build lineup card components
- [ ] Implement date navigation
- [ ] Add team selector
- [ ] Create position display grid

**Deliverables**:
- `web-ui/frontend/src/pages/LineupExplorer.js`
- `web-ui/frontend/src/components/LineupCard.js`
- `web-ui/frontend/src/components/DateNavigator.js`

### Stage 8: Frontend - Player Usage Analytics (Week 5)
**Goal**: Implement player usage visualization

**Tasks**:
- [ ] Create player timeline component
- [ ] Build usage statistics cards
- [ ] Implement start/sit pattern viz
- [ ] Add position utilization charts
- [ ] Create bench frequency analysis

**Deliverables**:
- `web-ui/frontend/src/components/PlayerUsageTimeline.js`
- `web-ui/frontend/src/components/UsageStats.js`
- Updated player profile pages

### Stage 9: Frontend - Team Analytics (Week 5)
**Goal**: Build team-level analytics views

**Tasks**:
- [ ] Create lineup consistency metrics
- [ ] Build streaming pattern detection
- [ ] Implement optimal lineup comparison
- [ ] Add bench value analysis
- [ ] Create position depth charts

**Deliverables**:
- `web-ui/frontend/src/components/TeamLineupAnalytics.js`
- `web-ui/frontend/src/components/OptimalLineupComparison.js`

### Stage 10: Search & Discovery Features (Week 6)
**Goal**: Enable powerful search capabilities

**Tasks**:
- [ ] Implement player search with autocomplete
- [ ] Add advanced filtering (position, team, date)
- [ ] Create "find similar lineups" feature
- [ ] Build lineup pattern search
- [ ] Add saved searches

**Deliverables**:
- `web-ui/frontend/src/components/LineupSearch.js`
- `web-ui/frontend/src/components/LineupFilters.js`
- Search index optimization

### Stage 11: Export & Integration (Week 6)
**Goal**: Enable data export and external integration

**Tasks**:
- [ ] Implement CSV export
- [ ] Add JSON API endpoints
- [ ] Create lineup report generation
- [ ] Build email digest feature
- [ ] Add webhook notifications

**Deliverables**:
- Export functionality in API
- Report templates
- Integration documentation

### Stage 12: Performance Optimization & Polish (Week 7)
**Goal**: Optimize performance and user experience

**Tasks**:
- [ ] Implement frontend caching
- [ ] Add lazy loading for large datasets
- [ ] Optimize database queries
- [ ] Add loading states and skeletons
- [ ] Implement error boundaries
- [ ] Add user preferences storage

**Deliverables**:
- Performance improvements
- Enhanced UX
- Production deployment checklist

## Technical Specifications

### Database Schema
```sql
-- Main lineup table
CREATE TABLE daily_lineups (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    selected_position TEXT,
    position_type TEXT,
    player_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id),
    UNIQUE(date, team_key, player_id, selected_position)
);

-- Performance indexes
CREATE INDEX idx_lineups_date ON daily_lineups(date);
CREATE INDEX idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX idx_lineups_player ON daily_lineups(player_id);
CREATE INDEX idx_lineups_date_team ON daily_lineups(date, team_key);
```

### API Response Format
```json
{
  "date": "2025-06-15",
  "team": {
    "key": "mlb.l.6966.t.1",
    "name": "Bash Brothers"
  },
  "lineup": {
    "starting": [
      {
        "position": "C",
        "player": {
          "id": "12345",
          "name": "Will Smith",
          "status": "healthy"
        }
      }
    ],
    "bench": [
      {
        "player": {
          "id": "67890",
          "name": "Mike Trout",
          "status": "DTD"
        }
      }
    ]
  }
}
```

## Testing Strategy

### Unit Tests
- Parser functions for XML responses
- Database operations (CRUD)
- API endpoint handlers
- Business logic calculations

### Integration Tests
- End-to-end data collection flow
- API authentication and token refresh
- Database transaction handling
- Job logging and recovery

### Performance Tests
- Query response times
- Bulk data loading
- Concurrent user load
- Memory usage under load

## Monitoring & Metrics

### Key Metrics
- Data collection success rate
- API response times
- Query performance (p50, p95, p99)
- Data freshness lag
- User engagement metrics

### Alerting Thresholds
- Collection failure rate > 5%
- API response time > 2s
- Data lag > 24 hours
- Database connection pool exhaustion

## Risk Mitigation

### Technical Risks
1. **Yahoo API Rate Limits**
   - Mitigation: Implement exponential backoff, request queuing
   - Fallback: Reduce collection frequency

2. **Large Data Volume**
   - Mitigation: Pagination, lazy loading, data archival
   - Fallback: Limit historical data to 5 years

3. **Token Expiration**
   - Mitigation: Proactive refresh, retry logic
   - Fallback: Manual re-authentication flow

### Data Risks
1. **Missing Historical Data**
   - Mitigation: Clear UI messaging, progressive backfill
   - Fallback: Focus on current season

2. **Data Quality Issues**
   - Mitigation: Validation rules, anomaly detection
   - Fallback: Manual data correction tools

## Success Metrics

### Launch Criteria (MVP)
- [ ] Current season data collection working
- [ ] Basic lineup viewer functional
- [ ] Player usage stats available
- [ ] <2s page load times
- [ ] 99% uptime

### Long-term Success
- 80% of active users accessing daily
- <500ms median query time
- 100% data completeness for current season
- 5-star user satisfaction rating

## Dependencies

### External
- Yahoo Fantasy Sports API
- OAuth2 authentication service
- SQLite database

### Internal
- Existing authentication module
- Job logging system
- Transaction data (for context)
- Web UI framework

## Timeline Summary

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1 | Infrastructure Ready | Database schema, tables created |
| 2 | Collection Working | API integration, job logging |
| 3 | Data Access Layer | Repository, REST API |
| 4 | Basic UI | Lineup viewer functional |
| 5 | Analytics | Usage patterns, team insights |
| 6 | Search & Export | Discovery, data export |
| 7 | Production Ready | Optimized, tested, deployed |

## Next Steps

1. Review and approve implementation plan
2. Create database schema
3. Set up development environment
4. Begin Stage 1 implementation
5. Schedule weekly progress reviews