# PRD: GitHub Actions Scheduled Data Refreshes

*Synced from Notion on 2025-08-04 23:02:11*

*Page ID: 2451a736-211e-8194-a4fb-cb451c22d0c1*

---

# PRD: GitHub Actions Scheduled Data Refreshes for Cloudflare D1

## Executive Summary

This PRD defines the implementation requirements for automating the GKL League Analytics data collection pipeline using GitHub Actions that writes directly to Cloudflare D1. The system will run scheduled data refreshes three times daily, collecting data from Yahoo Fantasy API and storing it in the production Cloudflare D1 database.

### Key Features

- Automated data collection at 6 AM, 1 PM, and 10 PM ET

- Direct writes to Cloudflare D1 database from GitHub Actions

- Incremental updates with change detection

- Comprehensive job logging for audit trails

- Foreign key dependency management in D1

- Environment-aware execution (development/staging/production)

## Problem Statement

### Current State

- Data collection scripts run locally and sync to production manually

- Requires manual execution of `sync_to_`[`production.py`](http://production.py/)

- Two-step process: Local SQLite → Export → D1 Import

- Risk of missed updates and sync failures

### Desired State

- GitHub Actions directly writes to Cloudflare D1

- Single-step automated process

- No dependency on local database infrastructure

- Automatic retry and error handling

- Complete audit trail in D1

## Architecture Overview

### Data Flow

```javascript
Yahoo API → GitHub Actions → Cloudflare D1 Database
         ↓
    Job Logging
```

### Key Differences from Local Development

- **No Local SQLite**: GitHub Actions connects directly to D1

- **No Sync Scripts**: Data is written once, directly to production

- **D1 Connection**: Uses Wrangler or D1 HTTP API for database access

- **Environment Variables**: D1 credentials stored in GitHub Secrets

## Technical Requirements

### 1. GitHub Actions Workflow Structure

### File Location

`.github/workflows/data-refresh.yml`

### Schedule Configuration

```yaml
schedule:
  - cron: '0 10 * * *'   # 6:00 AM ET (10:00 UTC)
  - cron: '0 17 * * *'   # 1:00 PM ET (17:00 UTC)
  - cron: '0 2 * * *'    # 10:00 PM ET (02:00 UTC next day)
```

### Workflow Parameters

- `refresh_type`: morning/afternoon/night/manual

- `environment`: development/staging/production (default: production)

- `date_range`: Optional YYYY-MM-DD,YYYY-MM-DD format

### 2. D1 Database Connection

### Connection Methods

**Option A: D1 HTTP API (Recommended)**

```python
import requests

class D1Connection:
    def __init__(self, account_id, database_id, api_token):
        self.base_url = f"[https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}](https://api.cloudflare.com/client/v4/accounts/%7Baccount_id%7D/d1/database/%7Bdatabase_id%7D)"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def execute(self, sql, params=None):
        response = [requests.post](http://requests.post/)(
            f"{self.base_url}/query",
            headers=self.headers,
            json={"sql": sql, "params": params or []}
        )
        return response.json()
```

**Option B: Wrangler in GitHub Actions**

```yaml
- name: Setup Wrangler
  run: npm install -g wrangler

- name: Execute D1 Query
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
  run: |
    echo "$SQL_QUERY" | wrangler d1 execute ${{ secrets.D1_DATABASE_NAME }} --remote
```

### 3. Modified Job Architecture

### Job 1: Setup D1 Connection

**Purpose**: Initialize D1 connection and verify access

**Tasks**:

- Test D1 connectivity

- Create job_log entry

- Verify foreign key constraints exist

### Job 2: Refresh Transactions

**Script**: Modified `data_pipeline/league_transactions/update_transactions_`[`d1.py`](http://d1.py/)

**Changes Required**:

- Replace SQLite connection with D1 connection

- Use D1 HTTP API for database operations

- Handle D1-specific transaction semantics

- Implement retry logic for network failures

### Job 3: Refresh Daily Lineups

**Script**: Modified `data_pipeline/daily_lineups/update_lineups_`[`d1.py`](http://d1.py/)

**Changes Required**:

- Replace SQLite connection with D1 connection

- Batch operations for D1 performance

- Handle D1 query limits (1MB response size)

### Job 4: Verify Data Integrity

**Purpose**: Ensure all foreign keys are satisfied

**Tasks**:

- Verify all job_ids exist in job_log

- Check for orphaned records

- Generate summary report

### 4. Authentication Requirements

### GitHub Secrets Required

```yaml
# Yahoo API Credentials
YAHOO_CLIENT_ID: "your-client-id"
YAHOO_CLIENT_SECRET: "your-client-secret"
YAHOO_REDIRECT_URI: "your-redirect-uri"
YAHOO_REFRESH_TOKEN: "your-refresh-token"

# Cloudflare D1 Credentials
CLOUDFLARE_ACCOUNT_ID: "your-account-id"
CLOUDFLARE_API_TOKEN: "your-api-token"
D1_DATABASE_ID: "your-database-id"
D1_DATABASE_NAME: "gkl-fantasy"
```

### 5. D1-Specific Considerations

### Query Limitations

- **Response Size**: 1MB max per query

- **Batch Size**: 100 statements per batch

- **Timeout**: 30 seconds per query

- **Rate Limits**: 1000 requests per minute

### Foreign Key Handling

```python
# D1 requires explicit foreign key checks
def ensure_job_exists(d1_conn, job_id):
    # Insert job_log entry first
    d1_conn.execute(
        "INSERT OR IGNORE INTO job_log (job_id, job_type, environment, status) VALUES (?, ?, ?, ?)",
        [job_id, "data_refresh", "production", "running"]
    )
```

### Transaction Management

```python
# D1 doesn't support long-running transactions
# Use batch operations instead
def batch_insert_transactions(d1_conn, transactions, job_id):
    # First ensure job exists
    ensure_job_exists(d1_conn, job_id)
    
    # Then insert in batches of 100
    for i in range(0, len(transactions), 100):
        batch = transactions[i:i+100]
        values = [(t['id'], t['date'], job_id) for t in batch]
        d1_conn.execute_batch(
            "INSERT OR REPLACE INTO transactions (id, date, job_id) VALUES (?, ?, ?)",
            values
        )
```

### 6. Environment Management

### Development Environment

- Uses separate D1 database instance

- Limited date range for testing

- Verbose logging enabled

### Staging Environment

- Uses production D1 structure

- Full date range processing

- Performance metrics collection

### Production Environment

- Direct writes to production D1

- Optimized batch sizes

- Minimal logging for performance

## Implementation Details

### Modified Script Structure

```python
# data_pipeline/common/d1_[connection.py](http://connection.py/)
import os
import requests
from typing import List, Dict, Any

class D1Connection:
    def __init__(self):
        self.account_id = os.environ['CLOUDFLARE_ACCOUNT_ID']
        self.database_id = os.environ['D1_DATABASE_ID']
        self.api_token = os.environ['CLOUDFLARE_API_TOKEN']
        self.base_url = f"[https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}](https://api.cloudflare.com/client/v4/accounts/%7Bself.account_id%7D/d1/database/%7Bself.database_id%7D)"
        
    def execute(self, query: str, params: List[Any] = None) -> Dict:
        """Execute a single query against D1"""
        response = [requests.post](http://requests.post/)(
            f"{self.base_url}/query",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            },
            json={
                "sql": query,
                "params": params or []
            }
        )
        
        if not response.ok:
            raise Exception(f"D1 query failed: {response.text}")
            
        return response.json()
    
    def execute_batch(self, query: str, params_list: List[List[Any]]) -> Dict:
        """Execute multiple queries in a batch"""
        # D1 supports up to 100 statements per batch
        for i in range(0, len(params_list), 100):
            batch = params_list[i:i+100]
            statements = []
            for params in batch:
                statements.append({
                    "sql": query,
                    "params": params
                })
            
            response = [requests.post](http://requests.post/)(
                f"{self.base_url}/batch",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                },
                json={"statements": statements}
            )
            
            if not response.ok:
                raise Exception(f"D1 batch query failed: {response.text}")
```

### Error Handling and Retry Logic

```python
import time
from functools import wraps

def retry_d1_operation(max_attempts=3, backoff_factor=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    print(f"D1 operation failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
            
        return wrapper
    return decorator

@retry_d1_operation()
def safe_d1_execute(conn, query, params):
    return conn.execute(query, params)
```

## Testing Strategy

### Local Testing with D1

```bash
# Install Wrangler locally
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create local D1 database for testing
wrangler d1 create test-gkl-fantasy

# Apply schema
wrangler d1 execute test-gkl-fantasy --file=./schema.sql --local

# Test scripts locally
python -m pytest tests/test_d1_[connection.py](http://connection.py/)
```

### GitHub Actions Testing

1. Create test workflow that runs on pull requests

1. Use development D1 database

1. Run with limited date ranges

1. Verify foreign key constraints

## Migration Strategy

### Phase 1: Parallel Run (1 week)

- Keep existing local → sync process

- Run GitHub Actions → D1 in parallel

- Compare results for accuracy

### Phase 2: GitHub Actions Primary (1 week)

- GitHub Actions becomes primary data source

- Local sync runs as backup only

- Monitor for issues

### Phase 3: Deprecate Local Sync (1 week)

- Remove sync_to_[production.py](http://production.py/) dependency

- GitHub Actions only solution

- Archive local sync code

## Performance Optimization

### D1 Query Optimization

```python
# Bad: Individual inserts
for transaction in transactions:
    d1.execute("INSERT INTO transactions VALUES (?, ?, ?)", 
               [[transaction.id](http://transaction.id/), [transaction.date](http://transaction.date/), job_id])

# Good: Batch inserts
values = [([t.id](http://t.id/), [t.date](http://t.date/), job_id) for t in transactions]
d1.execute_batch("INSERT INTO transactions VALUES (?, ?, ?)", values)
```

### Connection Pooling

- Reuse D1 connection across jobs

- Implement connection timeout handling

- Cache authentication tokens

## Monitoring and Alerting

### GitHub Actions Monitoring

- Use GitHub Actions status badges

- Configure email alerts for failures

- Implement Slack/Discord webhooks

### D1 Monitoring

- Track query performance in Cloudflare Analytics

- Monitor D1 storage usage

- Alert on foreign key violations

## Cost Considerations

### GitHub Actions

- Free tier: 2,000 minutes/month

- Each run: ~3 minutes

- Monthly usage: 3 runs/day × 30 days × 3 minutes = 270 minutes

### Cloudflare D1

- Free tier: 100,000 reads/day, 1,000 writes/day

- Estimated usage: Well within free tier

- Storage: 5GB free tier sufficient

## Security Enhancements

### Least Privilege Access

```yaml
# Create D1-specific API token with minimal permissions
- Account: GKL Fantasy Analytics
- Permissions: D1:Write
- Resources: Include - All databases in account
```

### Audit Trail

- All operations logged with job_id

- GitHub Actions logs retained for 90 days

- D1 query logs available in Cloudflare dashboard

## Success Criteria

### Primary Metrics

- **Direct Write Success**: 99%+ successful D1 writes

- **Performance**: < 2 minutes average runtime

- **Data Accuracy**: 100% match with Yahoo API data

### Secondary Metrics

- **Cost Efficiency**: Stay within free tiers

- **Maintenance**: < 1 hour/month maintenance time

- **Reliability**: < 1 failure per month

## Appendix

### A. Sample GitHub Actions Workflow

```yaml
name: D1 Data Refresh
on:
  schedule:
    - cron: '0 10 * * *'
  workflow_dispatch:

jobs:
  refresh-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install requests python-dotenv
      
      - name: Refresh Transactions
        env:
          YAHOO_CLIENT_ID: ${{ [secrets.YAHOO](http://secrets.yahoo/)_CLIENT_ID }}
          YAHOO_CLIENT_SECRET: ${{ [secrets.YAHOO](http://secrets.yahoo/)_CLIENT_SECRET }}
          YAHOO_REFRESH_TOKEN: ${{ [secrets.YAHOO](http://secrets.yahoo/)_REFRESH_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          D1_DATABASE_ID: ${{ secrets.D1_DATABASE_ID }}
        run: |
          python data_pipeline/league_transactions/update_transactions_[d1.py](http://d1.py/) \
            --start-date $(date -d '7 days ago' +%Y-%m-%d) \
            --end-date $(date +%Y-%m-%d)
```

### B. D1 Schema with Foreign Keys

```sql
-- Ensure foreign key support in D1
PRAGMA foreign_keys = ON;

-- Job log table (must be created first)
CREATE TABLE IF NOT EXISTS job_log (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    environment TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    error_message TEXT
);

-- Transactions table with foreign key
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    player_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES job_log(job_id)
);
```
