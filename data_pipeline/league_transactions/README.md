# League Transactions Data Pipeline

This module handles the collection and management of transaction data from the Yahoo Fantasy Sports API.

## Scripts

### 1. `backfill_transactions.py` - Bulk Historical Data Collection

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
python backfill_transactions.py --season 2025

# Backfill date range with parallel workers
python backfill_transactions.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Backfill multiple seasons
python backfill_transactions.py --seasons 2023,2024,2025

# Backfill all configured seasons
python backfill_transactions.py --all-seasons
```

### 2. `update_transactions.py` - Incremental Daily Updates

Used for regular updates to keep the database current. Designed for automation (cron/scheduled tasks).

**Features:**
- Default 7-day lookback window
- Automatic duplicate detection
- Timestamp-based date correction
- Minimal output for automation
- Job logging for audit trail

**Usage:**
```bash
# Default 7-day update
python update_transactions.py

# Custom lookback period
python update_transactions.py --days 14

# Update from last transaction date
python update_transactions.py --since-last

# Update specific date
python update_transactions.py --date 2025-08-04

# Quiet mode for cron
python update_transactions.py --quiet
```

### 3. `data_quality_check.py` - Data Validation Module

Validates transaction data completeness and quality.

**Features:**
- Field completeness validation
- Add/drop transaction pair checking
- Date format validation
- Batch validation support
- Human-readable reports

**Usage:**
```python
from data_quality_check import TransactionDataQualityChecker

checker = TransactionDataQualityChecker()
results = checker.validate_batch(transactions)
print(checker.generate_report(results))
```

## Data Flow

1. **Initial Setup**: Run `backfill_transactions.py` to populate historical data
2. **Daily Updates**: Schedule `update_transactions.py` to run daily/hourly
3. **Quality Checks**: Both scripts automatically validate data before insertion

## Important Notes

### Date Accuracy
The Yahoo API's date parameter doesn't actually filter transactions. The scripts use the transaction timestamp to determine the actual date and filter accordingly.

### Add/Drop Transactions
Add/drop transactions create two records - one for the add movement and one for the drop movement. The scripts ensure both movements are captured.

### Rate Limiting
Yahoo API has a rate limit of approximately 1 request per second. The scripts automatically handle this with built-in rate limiting.

### Job Logging
All data collection operations are logged in the `job_log` table with:
- Unique job IDs
- Date ranges processed
- Records processed and inserted
- Error tracking
- Execution timestamps

## Database Schema

The scripts work with the following transaction table structure:
- `date` - Transaction date (YYYY-MM-DD)
- `league_key` - Yahoo league identifier
- `transaction_id` - Unique transaction ID
- `transaction_type` - Type (add, drop, add/drop, trade)
- `player_id` - Yahoo player ID
- `player_name` - Player full name
- `player_position` - Player position(s)
- `player_team` - MLB team abbreviation
- `movement_type` - Movement type (add or drop)
- `destination_team_key` - Destination fantasy team key
- `destination_team_name` - Destination fantasy team name
- `source_team_key` - Source fantasy team key
- `source_team_name` - Source fantasy team name
- `job_id` - Job tracking ID

## Automation Example

Add to crontab for daily updates at 6 AM:
```bash
0 6 * * * cd /path/to/data_pipeline/league_transactions && python update_transactions.py --quiet
```

## Troubleshooting

### No New Transactions Found
- Check OAuth token expiration (tokens expire hourly)
- Verify league key is correct for the current season
- Check if transactions actually exist for the date range

### Duplicate Transactions
- The scripts use `INSERT OR IGNORE` to handle duplicates
- Unique constraint on (league_key, transaction_id, player_id, movement_type)

### Invalid Data Warnings
- Check the data quality report for specific issues
- Most common: missing player_position or player_team (API sometimes doesn't provide these)

## Archive

Old scripts have been archived to `archive/2025-08-04-cleanup/` for reference.