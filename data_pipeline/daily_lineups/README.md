# Daily Lineups Data Pipeline

This module handles the collection and management of daily lineup data from the Yahoo Fantasy Sports API.

## Scripts

### 1. `backfill_lineups.py` - Bulk Historical Data Collection

Used for initial data population or bulk historical data collection.

**Features:**
- Parallel processing with configurable workers (max 4)
- Automatic rate limiting (1 req/sec per Yahoo guidelines)
- Comprehensive job logging
- Resume capability for interrupted jobs
- Data quality validation
- Multi-season support

**Usage:**
```bash
# Backfill entire season
python backfill_lineups.py --season 2025

# Backfill date range with parallel workers
python backfill_lineups.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Backfill multiple seasons
python backfill_lineups.py --seasons 2023,2024,2025

# Backfill all configured seasons
python backfill_lineups.py --all-seasons
```

### 2. `update_lineups.py` - Incremental Daily Updates

Used for regular updates to keep the database current. Designed for automation (cron/scheduled tasks).

**Features:**
- Default 7-day lookback window
- Automatic duplicate detection
- Minimal output for automation
- Job logging for audit trail
- Processes all teams in the league

**Usage:**
```bash
# Default 7-day update
python update_lineups.py

# Custom lookback period
python update_lineups.py --days 14

# Update from last lineup date
python update_lineups.py --since-last

# Update specific date
python update_lineups.py --date 2025-08-04

# Quiet mode for cron
python update_lineups.py --quiet
```

### 3. `data_quality_check.py` - Data Validation Module

Validates lineup data completeness and quality.

**Features:**
- Field completeness validation
- Position validation against allowed positions
- Player status validation
- Date range validation (no future dates)
- Season coverage analysis
- Human-readable reports

**Usage:**
```python
from data_quality_check import LineupDataQualityChecker

checker = LineupDataQualityChecker()
results = checker.validate_batch(lineups)
print(checker.generate_report(results))
```

## Data Flow

1. **Initial Setup**: Run `backfill_lineups.py` to populate historical data
2. **Daily Updates**: Schedule `update_lineups.py` to run daily/hourly
3. **Quality Checks**: Both scripts automatically validate data before insertion

## Supporting Modules

### Core Components
- **collector.py** - Base collector functionality
- **parser.py** - XML response parsing and data extraction
- **repository.py** - Database access layer
- **job_manager.py** - Job tracking and logging
- **config.py** - Configuration settings

## Database Schema

The scripts work with the following lineup table structure:
- `lineup_id` - Unique identifier (auto-increment)
- `job_id` - Job tracking ID
- `season` - Season year
- `date` - Lineup date (YYYY-MM-DD)
- `team_key` - Yahoo team identifier
- `team_name` - Team name
- `player_id` - Yahoo player ID
- `player_name` - Player full name
- `selected_position` - Position player was started in
- `position_type` - Type of position (B=Bench, P=Pitcher, etc.)
- `player_status` - Health status (healthy, DTD, IL, etc.)
- `eligible_positions` - Comma-separated list of eligible positions
- `player_team` - MLB team abbreviation

### Unique Constraint
- `(date, team_key, player_id, selected_position)` - Prevents duplicate entries

## Important Notes

### Data Volume
Each team has approximately 26 players, and with 12 teams in a league, that's about 312 lineup records per day. For a full season (180 days), expect around 56,000 records.

### Rate Limiting
Yahoo API has a rate limit of approximately 1 request per second. The scripts automatically handle this with built-in rate limiting. With 12 teams to process per date, expect about 12-15 seconds per day of data collection.

### Parallel Processing
The backfill script supports parallel processing but limits to 4 workers maximum to respect Yahoo's rate limits while maintaining reasonable performance.

### Job Logging
All data collection operations are logged in the `job_log` table with:
- Unique job IDs
- Date ranges processed
- Records processed and inserted
- Error tracking
- Execution timestamps

## Automation Example

Add to crontab for daily updates at 6 AM:
```bash
0 6 * * * cd /path/to/data_pipeline/daily_lineups && python update_lineups.py --quiet
```

## Troubleshooting

### No New Lineups Found
- Check OAuth token expiration (tokens expire hourly)
- Verify league key is correct for the current season
- Check if games were actually played on the date range

### Duplicate Lineups
- The scripts use `INSERT OR IGNORE` to handle duplicates
- Unique constraint on (date, team_key, player_id, selected_position)

### Invalid Data Warnings
- Check the data quality report for specific issues
- Most common: missing selected_position for bench players (this is normal)

### Performance Issues
- For large date ranges, use the backfill script with parallel workers
- Consider processing one month at a time for historical data
- Monitor the job_log table for processing times

## Testing

### Local Testing
```bash
# Test with a small date range
python backfill_lineups.py --start 2025-08-01 --end 2025-08-03 --environment test

# Test incremental update
python update_lineups.py --days 2 --environment test --verbose
```

### Data Quality Testing
```python
# Run quality check on test data
from data_quality_check import LineupDataQualityChecker
import sqlite3

conn = sqlite3.connect('../../database/league_analytics.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM daily_lineups_test WHERE date = '2025-08-01'")
lineups = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

checker = LineupDataQualityChecker()
results = checker.validate_batch(lineups)
print(checker.generate_report(results))
```

## Archive

Old scripts have been archived to `archive/2025-08-04-lineup-cleanup/` for reference.