# Daily Lineups Module - Quick Start Guide

## ✅ Current Status (Stages 1-3 Complete)

All integration tests are **PASSING**:
- **Stage 1**: Database Schema ✅
- **Stage 2**: Data Collection ✅  
- **Stage 3**: Job Management ✅

## What You Can Do Right Now

### 1. Run Integration Tests
Verify everything is working:
```bash
python daily_lineups/test_integration.py
```

### 2. Check Database Schema
View all created tables and data:
```bash
python daily_lineups/scripts/test_schema.py
```

### 3. Run Unit Tests
```bash
# Test the parser
python -m unittest daily_lineups.tests.test_parser -v

# Test job manager
python -m unittest daily_lineups.tests.test_job_manager -v

# Test collector
python -m unittest daily_lineups.tests.test_collector -v
```

### 4. Collect Actual Data (Requires Valid Yahoo Tokens)

#### First Time Setup
1. Ensure you have valid tokens in `auth/tokens.json`
2. Tokens must be for the 2025 season (current season)

#### Collect Data for a Date Range
```bash
# Production collection
python daily_lineups/collector_enhanced.py \
    --start 2025-06-01 \
    --end 2025-06-07 \
    --env production

# Test collection (smaller date range)
python daily_lineups/collector_enhanced.py \
    --start 2025-08-01 \
    --end 2025-08-02 \
    --env test
```

#### Resume an Interrupted Collection
```bash
# Check if there's a checkpoint
python daily_lineups/job_manager.py resume

# Resume collection
python daily_lineups/collector_enhanced.py --resume
```

### 5. Monitor Jobs

#### Check Job Status
```bash
# List recent jobs
python daily_lineups/job_manager.py list --env production

# Check specific job
python daily_lineups/job_manager.py status --job-id <job_id>

# View statistics
python daily_lineups/job_manager.py stats --env production
```

### 6. Validate Data Completeness

#### Check for Missing Dates
```bash
python daily_lineups/collector_enhanced.py \
    --missing \
    --start 2025-06-01 \
    --end 2025-06-30
```

#### Validate Data Completeness
```bash
python daily_lineups/collector_enhanced.py \
    --validate \
    --start 2025-06-01 \
    --end 2025-06-30
```

## Database Access

### View Collected Data
```sql
-- Connect to database
sqlite3 database/league_analytics.db

-- View recent lineups
SELECT date, team_name, COUNT(*) as players
FROM daily_lineups
GROUP BY date, team_name
ORDER BY date DESC
LIMIT 10;

-- Check player usage
SELECT * FROM v_player_frequency LIMIT 10;

-- View team summaries
SELECT * FROM v_team_daily_summary LIMIT 10;
```

## Common Issues

### 1. "No token manager provided"
- Ensure `auth/tokens.json` exists
- Run token initialization if needed

### 2. "401 Client Error: Unauthorized"
- Tokens have expired (they expire hourly)
- Re-run token initialization

### 3. "No league key configured for season"
- The league key for the requested season isn't in config
- Update `daily_lineups/config.py` with the correct league key

## Module Status

### ✅ Completed Features
- Database schema with indexes and views
- XML parsing for Yahoo API responses
- Job management with checkpoint/resume
- Progress tracking and reporting
- Data validation and completeness checks
- Comprehensive error handling
- Unit and integration tests

### 🚧 Not Yet Implemented (Stages 4+)
- Historical backfill script
- Parallel processing
- Web UI integration
- Advanced analytics
- MLB data integration

## Test Results Summary

```
Stage 1: Database Schema
- 6 tables created ✅
- 15 positions loaded ✅
- 15 indexes created ✅
- 3 views created ✅

Stage 2: Data Collection  
- XML parser working ✅
- Position type determination ✅
- Data validation working ✅
- Token access verified ✅

Stage 3: Job Management
- Job creation ✅
- Status tracking ✅
- Checkpoint/resume ✅
- Progress calculation ✅
- Statistics reporting ✅
```

## Next Steps

1. **Test with real data**: If you have valid Yahoo tokens, try collecting a day's worth of data
2. **Monitor the collection**: Use job manager commands to track progress
3. **Validate the data**: Use validation commands to ensure completeness
4. **Query the database**: Explore the collected data using SQL

The module is production-ready for basic lineup data collection with full job management and error recovery!