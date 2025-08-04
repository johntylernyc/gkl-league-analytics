# GitHub Actions D1 Integration

## Overview

The GKL League Analytics system uses GitHub Actions to automatically refresh data in the production Cloudflare D1 database. This implementation provides direct database writes from GitHub Actions runners, eliminating the previous two-step process of local collection → manual sync.

## Architecture

### Previous Architecture (Deprecated)
```
Local Development → SQLite → Export Scripts → Manual D1 Import
```

### Current Architecture
```
GitHub Actions → Direct D1 Writes → Production API
```

### Key Benefits
- **Automated**: No manual intervention required
- **Fast**: Sub-2-minute execution times
- **Reliable**: 99%+ successful write rate  
- **Scalable**: Runs on GitHub's infrastructure
- **Secure**: Credentials managed via GitHub Secrets

## Workflow Schedule

The data refresh workflow runs automatically three times daily:

| Time | Purpose | Data Range | Trigger |
|------|---------|------------|---------|
| 6:00 AM ET | Morning corrections | 7 days | Scheduled |
| 1:00 PM ET | Midday updates | 3 days | Scheduled |
| 10:00 PM ET | End-of-day sync | 3 days | Scheduled |

### Schedule Configuration
```yaml
schedule:
  - cron: '0 10 * * *'   # 6:00 AM ET (10:00 UTC)
  - cron: '0 17 * * *'   # 1:00 PM ET (17:00 UTC)  
  - cron: '0 2 * * *'    # 10:00 PM ET (02:00 UTC next day)
```

## Workflow Jobs

### 1. Parameter Determination
**Job**: `determine-refresh-params`
- Calculates date ranges based on trigger type
- Sets environment (production/test)
- Configures refresh parameters

### 2. Transaction Refresh
**Job**: `refresh-transactions`
- Runs `data_pipeline/league_transactions/update_transactions.py`
- Uses `--use-d1` flag for direct D1 writes
- Handles Yahoo API authentication
- Processes transaction data with job logging

### 3. Lineup Refresh  
**Job**: `refresh-lineups`
- Runs `data_pipeline/daily_lineups/update_lineups.py`
- Uses `--use-d1` flag for direct D1 writes
- Processes all team lineups for date range
- Maintains comprehensive audit trail

### 4. Notification
**Job**: `notify-completion`
- Sends status notifications via Slack/Discord
- Reports success/failure metrics
- Includes execution details

## Database Connection

### Connection Module
The workflow uses `data_pipeline/common/d1_connection.py` for all database operations:

```python
from data_pipeline.common.d1_connection import D1Connection

# Auto-detects D1 vs SQLite based on environment variables
d1 = D1Connection()

# Direct D1 operations
d1.execute("SELECT COUNT(*) FROM transactions")
d1.execute_batch([(query, params), ...])
```

### Environment Variables
Required GitHub Secrets:

| Secret | Purpose |
|--------|---------|
| `YAHOO_CLIENT_ID` | Yahoo API authentication |
| `YAHOO_CLIENT_SECRET` | Yahoo API authentication |  
| `YAHOO_REFRESH_TOKEN` | Yahoo API token refresh |
| `CLOUDFLARE_ACCOUNT_ID` | D1 database access |
| `CLOUDFLARE_API_TOKEN` | D1 database authentication |
| `D1_DATABASE_ID` | Target D1 database identifier |

### Auto-Detection Logic
```python
# Scripts automatically detect database type:
if D1_AVAILABLE and is_d1_available():
    use_d1 = True  # Direct D1 writes
else:
    use_d1 = False  # Local SQLite
```

## Foreign Key Management

### Automatic Dependency Handling
The D1 connection module automatically ensures proper foreign key relationships:

1. **Job Creation**: `d1_conn.ensure_job_exists()` creates job_log entries first
2. **Data Insertion**: References valid job_id from job_log table
3. **Batch Operations**: Maintains consistency across multiple records

### Database Constraints
```sql
-- All data tables reference job_log
FOREIGN KEY (job_id) REFERENCES job_log(job_id)

-- Insert order is handled automatically:
-- 1. job_log entries (created first)
-- 2. transaction/lineup data (references job_log.job_id)
```

## Script Modifications

### Dual Database Support
Both update scripts support SQLite (development) and D1 (production):

```python
class TransactionUpdater:
    def __init__(self, environment='production', use_d1=None):
        if use_d1 is None:
            # Auto-detect based on environment variables
            self.use_d1 = D1_AVAILABLE and is_d1_available()
        else:
            self.use_d1 = use_d1
```

### Command-Line Interface
```bash
# Local development (SQLite)
python update_transactions.py --use-sqlite

# Production (D1)  
python update_transactions.py --use-d1

# Auto-detect (default)
python update_transactions.py
```

## Error Handling & Reliability

### Retry Logic
The D1 connection implements exponential backoff:
```python
@retry_d1_operation(max_attempts=3, backoff_factor=2.0)
def execute(self, query, params):
    # Automatic retry for transient failures
```

### Batch Operations
D1 API limits are handled automatically:
- Max 100 statements per batch
- Max 1MB response size
- 30-second query timeout
- 1000 requests per minute rate limit

### Monitoring
- GitHub Actions execution logs
- Job status tracking in D1 job_log table
- Slack/Discord notifications for failures
- Comprehensive error messages and context

## Performance Optimization

### Execution Time Targets
- **Target**: < 2 minutes per workflow run
- **Current**: ~1.5 minutes average
- **Factors**: API rate limits, data volume, network latency

### Optimization Techniques
1. **Parallel Jobs**: Transactions and lineups run concurrently
2. **Batch Inserts**: Up to 100 records per D1 batch operation
3. **Efficient Queries**: Optimized for D1 performance characteristics
4. **Rate Limiting**: 1 request/second to Yahoo API (per guidelines)

## Testing & Validation

### Test Script
`scripts/test_d1_connection.py` validates:
- Environment variable configuration
- D1 connectivity and authentication
- Basic CRUD operations
- Foreign key constraint handling
- Batch operation functionality

### Local Testing
```bash
# Test D1 connection
python scripts/test_d1_connection.py

# Test scripts with D1
python data_pipeline/league_transactions/update_transactions.py --use-d1 --environment test
```

## Security Considerations

### Credential Management
- All sensitive data stored in GitHub Secrets
- No credentials in code or logs
- Least-privilege API tokens
- Environment-based access control

### API Token Scopes
- **Yahoo API**: Read-only access to fantasy data
- **Cloudflare API**: D1 database write permissions only
- **GitHub**: Workflow execution and secret access

### Audit Trail
- Every operation logged with job_id
- Complete data lineage tracking
- GitHub Actions execution history
- D1 query logs available in Cloudflare dashboard

## Migration Strategy

### Phase 1: Parallel Operation (Completed)
- Existing manual sync process continues
- GitHub Actions runs in parallel
- Results compared for accuracy

### Phase 2: Primary Operations (Current)
- GitHub Actions becomes primary data source
- Manual sync available as backup
- Monitor for stability and performance

### Phase 3: Full Migration (Planned)
- Remove manual sync dependencies
- Archive legacy sync scripts
- GitHub Actions as sole production update mechanism

## Troubleshooting

### Common Issues

**Environment Variables Missing**
```bash
# Check required variables are set
python scripts/test_d1_connection.py
```

**D1 Connection Failures**
```bash
# Verify API token permissions
curl -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/d1/database"
```

**Foreign Key Violations**
- Check job_log entries exist before data insertion
- Verify job_id format and uniqueness
- Review D1 constraint enforcement

**Workflow Failures**
- Check GitHub Actions logs for detailed error messages
- Verify all GitHub Secrets are configured
- Review Yahoo API authentication status

### Recovery Procedures

**Failed Workflow Run**
1. Check GitHub Actions logs for error details
2. Verify external service availability (Yahoo API, Cloudflare D1)
3. Re-run workflow manually if transient failure
4. Update credentials if authentication issue

**Data Inconsistency**
1. Run data quality validation scripts
2. Compare with expected results from local development
3. Manual sync specific date ranges if needed
4. Monitor subsequent automated runs

## Future Enhancements

### Planned Improvements
1. **Player Statistics Integration**: Add MLB data collection
2. **Multi-League Support**: Handle multiple fantasy leagues
3. **Real-Time Updates**: Reduce refresh frequency to hourly
4. **Advanced Monitoring**: Integration with observability platforms
5. **Cost Optimization**: Analyze GitHub Actions usage and optimize

### Scalability Roadmap
- **Horizontal Scaling**: Multiple concurrent workflows
- **Data Partitioning**: Separate workflows by data type
- **Caching Layer**: Reduce API calls through intelligent caching
- **Event-Driven Updates**: Webhook-based triggering instead of scheduled runs