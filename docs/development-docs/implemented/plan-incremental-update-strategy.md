# Transaction Incremental Updates

This directory contains scripts for incrementally updating the transaction database with new data from the Yahoo Fantasy API.

## Overview

Instead of running full backfills from scratch, these scripts identify the most recent transaction in the database and fetch only new transactions since that date.

## Scripts

### `quick_update.py` - Daily Updates
Simple script for routine daily updates:

```bash
# Update production database (default)
python quick_update.py

# Update test database
python quick_update.py test

# Show help
python quick_update.py --help
```

**Features:**
- Looks back 7 days from today
- Minimal user interaction
- Automatic duplicate detection
- Works with SQLite optimizations

### `update_recent_transactions.py` - Flexible Updates
Full-featured script with more options:

```bash
# Update production with 30-day lookback (default)
python update_recent_transactions.py --environment production

# Update test with 7-day lookback
python update_recent_transactions.py --environment test --max-days 7

# Dry run to see what would be updated
python update_recent_transactions.py --dry-run

# Verbose output for debugging
python update_recent_transactions.py --verbose
```

**Features:**
- Configurable lookback period
- Dry-run mode
- Verbose logging
- Production confirmation prompt
- Detailed status reporting

## How It Works

1. **Check Latest Date**: Query database for most recent transaction date
2. **Calculate Range**: Determine date range to fetch (latest date + 1 to today)
3. **Fetch Data**: Call Yahoo API for each date in range
4. **Parse & Insert**: Process XML responses and insert new transactions
5. **Duplicate Handling**: Database constraints prevent duplicate insertions

## Database Integration

The incremental update system:
- Uses the same database schema as full backfills
- Integrates with job logging system
- Respects environment separation (test/production)
- Works with SQLite optimizations (busy_timeout, WAL mode)
- Maintains data consistency with existing records

## Core Functions

### `get_latest_transaction_date(environment, league_key)`
Returns the most recent transaction date in the database.

### `get_date_range_for_update(environment, league_key, max_days_back)`
Calculates the date range for incremental updates.

### `run_incremental_update(environment, league_key, max_days_back)`
Performs the complete incremental update process.

### `parse_transaction_xml(xml_data, date_str, league_key, job_id)`
Parses Yahoo API XML responses into structured transaction records.

## Error Handling

- **API Failures**: Individual date failures don't stop the entire update
- **Authentication**: Token refresh is handled automatically
- **Database Locks**: Uses SQLite busy_timeout for lock handling
- **Network Issues**: Includes rate limiting (1 req/sec) and retries

## Best Practices

1. **Daily Updates**: Run `quick_update.py` daily to keep database current
2. **Monitor Logs**: Check `fetch_transactions.log` for any issues
3. **Dry Run First**: Use `--dry-run` before production updates
4. **Backup Data**: Ensure database backups before large updates

## Example Workflows

### Daily Maintenance
```bash
# Quick daily update
cd league_transactions
python quick_update.py
```

### Catch-up After Downtime
```bash
# Check what needs updating
python update_recent_transactions.py --dry-run --max-days 14

# Perform the update
python update_recent_transactions.py --max-days 14
```

### Debugging Issues
```bash
# Verbose update to see detailed progress
python update_recent_transactions.py --verbose --max-days 3
```

## Performance

- **Rate Limiting**: 1 second delay between API calls
- **Batch Processing**: Transactions inserted in batches
- **Memory Efficient**: Processes one date at a time
- **SQLite Optimized**: Uses pragma optimizations when enabled

## Integration with Existing Code

The incremental update functions are added to `backfill_transactions_optimized.py` and use the same:
- Token management system
- Database schema and connections
- Job logging infrastructure
- Error handling patterns
- Configuration management

This ensures consistency across all transaction data collection methods.