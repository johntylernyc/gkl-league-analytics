# Database Environment Separation Guide

## Overview
This document describes the test/production database separation architecture implemented in the GKL League Analytics project. The separation ensures that development and testing activities do not interfere with production data.

## Architecture

### Database Files
- **Production Database**: `database/league_analytics.db`
- **Test Database**: `database/league_analytics_test.db`

### Environment Control
The system determines which database to use based on the `DATA_ENV` environment variable:
- `DATA_ENV=test` - Uses test database
- `DATA_ENV=production` or unset - Uses production database (default)

## Configuration Module

### Python Configuration
Location: `config/database_config.py`

Key functions:
- `get_environment(override=None)` - Get current environment
- `get_database_path(environment=None)` - Get database file path
- `get_table_name(base_name, environment=None)` - Get environment-specific table name

### Node.js Configuration
Location: `web-ui/backend/config/database.js`

Key functions:
- `getEnvironment(override)` - Get current environment
- `getDatabasePath(environment)` - Get database file path
- `getTableName(baseName, environment)` - Get environment-specific table name

## Table Naming Convention

### Transactions Tables
- **Production**: `transactions`
- **Test**: `transactions_test`

### Daily Lineups Tables
- **Production**: `daily_lineups`
- **Test**: `daily_lineups_test`

### Shared Tables
- `job_log` - Shared between environments, filtered by `environment` column

## Usage Examples

### Python Scripts

#### Running in Test Mode
```bash
# Set environment variable
export DATA_ENV=test
python league_transactions/backfill_transactions_optimized.py

# Or use command-line argument
python league_transactions/backfill_transactions_optimized.py --environment test
```

#### Running in Production Mode
```bash
# Default (no environment variable needed)
python league_transactions/backfill_transactions_optimized.py

# Or explicitly set
export DATA_ENV=production
python league_transactions/backfill_transactions_optimized.py
```

### Node.js Backend

#### Running in Test Mode
```bash
# Set environment variable
export DATA_ENV=test
npm start

# Or in package.json script
"scripts": {
  "test": "DATA_ENV=test node app.js"
}
```

#### Running in Production Mode
```bash
# Default (no environment variable needed)
npm start

# Or explicitly set
export DATA_ENV=production
npm start
```

## Module Updates

### Updated Modules
All modules have been updated to use the centralized database configuration:

1. **league_transactions/**
   - `backfill_transactions_optimized.py` - Main transaction collection script
   - Uses environment-aware database paths and table names

2. **daily_lineups/**
   - `config.py` - Module configuration
   - `repository.py` - Data access layer
   - `collector.py`, `collector_enhanced.py` - Data collection
   - `backfill_lineups.py`, `update_lineups.py` - Data processing

3. **web-ui/backend/**
   - `config/database.js` - Database configuration
   - `services/database.js` - Database connection service
   - `services/lineupService.js` - Lineup data service

## Migration Process

### Migrating Test Data
A migration script is provided to move test data from production to test database:

```bash
# Run full migration (migrate data and clean production)
python scripts/migrate_test_data.py

# Only migrate data (skip cleanup)
python scripts/migrate_test_data.py --skip-cleanup

# Only clean production (skip migration)
python scripts/migrate_test_data.py --skip-migration
```

The migration script:
1. Creates test tables in test database
2. Copies test data from production database
3. Removes test data from production database
4. Creates appropriate indexes

## Best Practices

### Development Workflow
1. Always use test environment during development:
   ```bash
   export DATA_ENV=test
   ```

2. Run tests against test database to verify functionality

3. Only switch to production for final data collection:
   ```bash
   export DATA_ENV=production
   ```

### Data Safety
- Test scripts automatically write to test tables
- Production scripts require explicit environment setting
- Job logging tracks which environment was used

### Verification
To verify which environment you're using:

**Python:**
```python
from config.database_config import get_environment, get_database_path
print(f"Environment: {get_environment()}")
print(f"Database: {get_database_path()}")
```

**Node.js:**
```javascript
const { getEnvironment, getDatabasePath } = require('./config/database');
console.log(`Environment: ${getEnvironment()}`);
console.log(`Database: ${getDatabasePath()}`);
```

## Troubleshooting

### Common Issues

1. **Wrong database being used**
   - Check `DATA_ENV` environment variable
   - Verify no hardcoded paths in scripts

2. **Table not found errors**
   - Ensure test tables exist in test database
   - Run migration script if needed

3. **Permission errors**
   - Check file permissions on database files
   - Ensure write access to database directory

### Debug Mode
Enable debug output to see configuration details:

**Python:**
```bash
DEBUG_CONFIG=1 python your_script.py
```

**Node.js:**
```bash
DEBUG=true node your_script.js
```

## Maintenance

### Regular Tasks
1. Periodically clean test database to manage size
2. Backup production database before major operations
3. Monitor job_log table for failed jobs

### Database Cleanup
```sql
-- Clean old test data (older than 30 days)
DELETE FROM transactions_test 
WHERE date < date('now', '-30 days');

-- Clean old job logs
DELETE FROM job_log 
WHERE environment = 'test' 
AND created_at < datetime('now', '-7 days');
```

## Summary
The database separation provides:
- **Safety**: Test operations cannot affect production data
- **Flexibility**: Easy switching between environments
- **Clarity**: Clear indication of which environment is in use
- **Consistency**: Unified configuration across Python and Node.js modules

For questions or issues, refer to the configuration modules or this documentation.