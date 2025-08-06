# Testing Your Deployment

This guide helps you verify that your automated data refresh system is working correctly.

## Test Sequence

Follow these tests in order to verify each component:

### 1. Test GitHub Actions Manually (No CloudFlare Required)

This tests that your GitHub secrets are set correctly:

#### Via GitHub Web UI
1. Go to your repository on GitHub
2. Click **Actions** tab
3. Click **Scheduled Data Refresh** workflow
4. Click **Run workflow**
5. Fill in:
   - Use workflow from: `main`
   - Type of refresh: `manual`
   - Environment: `test`
   - Date range: `2025-08-01,2025-08-04`
6. Click **Run workflow** (green button)

#### Check Results
1. Refresh the Actions page
2. You should see a new workflow run starting
3. Click on it to see progress
4. Each job (transactions, lineups, stats) should show green checkmarks

**Expected Result:** All jobs complete successfully (green checkmarks)

**If it fails:** Check the logs - likely missing GitHub secrets

### 2. Test CloudFlare Worker Health

After deploying the CloudFlare Worker:

```bash
# Replace YOUR-SUBDOMAIN with your actual CloudFlare subdomain
curl https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-04T15:30:00.000Z",
  "timezone": "America/New_York"
}
```

### 3. Test CloudFlare → GitHub Integration

This verifies CloudFlare can trigger GitHub Actions:

```bash
# First, check current GitHub workflow runs
curl https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/status
```

Note the current runs, then trigger a new one:

```bash
# You need to set up AUTH_TOKEN first (see CloudFlare setup guide)
curl -X POST https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/trigger \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshType": "manual"}'
```

**Expected Response:**
```json
{
  "success": true,
  "refreshType": "manual",
  "workflowRun": 123456789,
  "timestamp": "2025-08-04T15:30:00.000Z"
}
```

Then verify on GitHub:
1. Go to Actions tab
2. You should see a new workflow run triggered by "workflow_dispatch"

### 4. Test Database Updates

After a successful workflow run, verify data was updated:

```bash
cd R:\GitHub\gkl-league-analytics

# Check job logs
python -c "
import sqlite3
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT job_id, job_type, status, start_time, end_time
    FROM job_log
    WHERE job_type LIKE '%incremental%'
    ORDER BY start_time DESC
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} - {row[2]} ({row[3]} to {row[4]})')
"
```

### 5. Test Scheduled Triggers

To verify scheduled triggers are set up:

1. Go to CloudFlare Dashboard
2. Navigate to Workers & Pages
3. Click on `gkl-fantasy-analytics`
4. Click **Triggers** tab
5. Verify you see 3 cron triggers

To monitor when they run:
```bash
# Start tailing logs before a scheduled time
wrangler tail

# Leave this running - it will show logs when triggers fire
```

## Verification Checklist

Run through this checklist to ensure everything is configured:

### GitHub Setup
- [ ] Repository has `.github/workflows/data-refresh.yml`
- [ ] GitHub Actions is enabled (Settings → Actions → General)
- [ ] Secrets are set (Settings → Secrets → Actions)
  - [ ] YAHOO_CLIENT_ID
  - [ ] YAHOO_CLIENT_SECRET
  - [ ] YAHOO_REDIRECT_URI
  - [ ] YAHOO_AUTHORIZATION_CODE
- [ ] Manual workflow run succeeds

### CloudFlare Setup
- [ ] Worker deployed (shows URL after `wrangler deploy`)
- [ ] Secrets configured (`wrangler secret list`)
  - [ ] GITHUB_TOKEN
  - [ ] AUTH_TOKEN (for manual triggers)
- [ ] Health endpoint responds
- [ ] Scheduled triggers visible in dashboard

### Integration
- [ ] Manual trigger from CloudFlare creates GitHub workflow
- [ ] GitHub workflow completes successfully
- [ ] Database shows new job_log entries
- [ ] Data refresh actually updates records

## Common Issues and Solutions

### Issue: GitHub Action fails with "Bad credentials"
**Solution:** Your GITHUB_TOKEN is invalid or missing `workflow` scope. Generate a new token.

### Issue: CloudFlare trigger returns 401 Unauthorized
**Solution:** AUTH_TOKEN not set or incorrect in request header.

### Issue: GitHub Action runs but no data updates
**Solution:** Check Yahoo OAuth tokens are valid. You may need to refresh them.

### Issue: CloudFlare scheduled triggers don't run
**Solution:** 
1. Check timezone - triggers are in UTC
2. Verify in CloudFlare dashboard → Workers → Triggers
3. Check `wrangler tail` for errors

### Issue: "No such table" errors in Python scripts
**Solution:** Run database creation scripts:
```bash
python database/create_transactions_table.py
python database/schema/apply_schema.py  # If exists
```

## Monitoring Commands

### Check Recent Job Status
```bash
# Shows last 10 jobs
python -c "
import sqlite3
from datetime import datetime
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT job_type, status, 
           datetime(start_time), 
           records_processed, records_inserted
    FROM job_log
    ORDER BY start_time DESC
    LIMIT 10
''')
print('Type | Status | Time | Processed | Inserted')
print('-' * 60)
for row in cursor.fetchall():
    print(f'{row[0][:20]:20} | {row[1]:10} | {row[2][:16]} | {row[3]:9} | {row[4]}')
"
```

### Check for Recent Changes
```bash
# Shows recent lineup changes detected
python -c "
import sqlite3
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT date, team_key, change_type, detected_at
    FROM lineup_changes
    ORDER BY detected_at DESC
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f'{row[0]} - Team {row[1]}: {row[2]} (detected: {row[3]})')
"
```

## Success Indicators

Your system is working correctly when:

1. **Scheduled Runs**: CloudFlare logs show triggers at 6 AM, 1 PM, 10 PM ET
2. **Workflow Success**: GitHub Actions shows green checkmarks daily
3. **Data Updates**: Database has recent job_log entries with status='completed'
4. **Change Detection**: lineup_changes and stat_corrections tables get new entries
5. **Notifications**: You receive Slack/Discord alerts (if configured)

## Next Steps

Once everything is verified:

1. **Monitor for 24 hours** to ensure scheduled triggers work
2. **Check morning refresh** (6 AM ET) processes 7 days of data
3. **Verify incremental updates** (1 PM, 10 PM) only process recent data
4. **Review logs** for any errors or performance issues
5. **Set up alerts** for failures (optional)

## Support

If you encounter issues:

1. Check CloudFlare logs: `wrangler tail`
2. Check GitHub Action logs: Actions tab → Click failed run
3. Check database logs: Query job_log table for error_message
4. Review deployment guides for missed steps