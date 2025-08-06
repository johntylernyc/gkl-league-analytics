# Test GitHub Actions - Quick Guide

## ✅ Your Current Status
- GitHub Secrets are configured with new Yahoo credentials
- GitHub Actions workflow is committed and pushed
- Incremental update scripts are in the repository

## Step 1: Go to GitHub Actions

1. Open your repository on GitHub: `https://github.com/YOUR_USERNAME/gkl-league-analytics`
2. Click on the **Actions** tab (between "Pull requests" and "Projects")

## Step 2: Find Your Workflow

You should see:
- **"Scheduled Data Refresh"** in the left sidebar under "All workflows"
- If you don't see it, the workflow file might not be in your default branch

Click on **"Scheduled Data Refresh"**

## Step 3: Run Manual Test

1. Click the **"Run workflow"** button (blue/green button on the right)
2. A dropdown will appear with options:

   | Field | Value to Select |
   |-------|----------------|
   | Use workflow from | `main` (or your default branch) |
   | Type of refresh | `manual` |
   | Environment | `test` |
   | Date range | `2025-08-01,2025-08-04` |

3. Click the green **"Run workflow"** button

## Step 4: Monitor the Run

1. Refresh the page after a few seconds
2. You should see a new workflow run starting (yellow dot spinning)
3. Click on the workflow run title to see details
4. Watch the jobs execute:
   - ✅ Determine Refresh Parameters (10 seconds)
   - ✅ Refresh Transactions (30-60 seconds)
   - ✅ Refresh Daily Lineups (30-60 seconds)
   - ✅ Refresh Player Stats (30-60 seconds)
   - ✅ Send Notifications (5 seconds)

## What Success Looks Like

All jobs should show green checkmarks ✅

Example successful log output:
```
============================================================
TRANSACTION INCREMENTAL UPDATE
============================================================
Date range: 2025-08-01 to 2025-08-04
League: mlb.l.6966
Environment: test
...
UPDATE SUMMARY
============================================================
Transactions checked: 8
New transactions: 0
Updated transactions: 1
```

## Troubleshooting

### If Actions Tab Doesn't Appear:
1. Make sure you've pushed to GitHub: `git push origin main`
2. Go to Settings → Actions → General
3. Ensure "Allow all actions" is selected

### If Workflow Fails:

#### "Bad credentials" or Authentication Error:
- Your GitHub Secrets might be wrong
- Check that you're using `YAHOO_REFRESH_TOKEN` (not AUTHORIZATION_CODE)
- Verify the refresh token value from `auth/tokens.json`

#### "No such table" Error:
- The database tables might not exist
- This is expected for GitHub Actions (uses different database)
- Consider skipping database operations for test environment

#### Python Module Not Found:
- Check if all dependencies are installed in the workflow
- May need to add to requirements.txt

### Common Issues and Fixes:

| Error | Solution |
|-------|----------|
| "Workflow not found" | Push the workflow file to main branch |
| "Bad credentials" | Check YAHOO_REFRESH_TOKEN secret |
| "Module not found" | Add missing module to workflow |
| "No such table" | Expected - GitHub uses fresh database |
| "Waiting for runner" | Normal - wait 10-30 seconds |

## After Successful Test

Once the manual test works:

### Scheduled Runs Will Happen Automatically:
- **6:00 AM ET** - Full refresh (7-day lookback)
- **1:00 PM ET** - Incremental (3-day lookback)  
- **10:00 PM ET** - Incremental (3-day lookback)

### Monitor Schedule:
The workflow will run automatically at scheduled times. You can:
1. Check Actions tab daily to see scheduled runs
2. Set up notifications (Slack/Discord) for alerts
3. Download artifacts to check data updates

## Next Steps After Testing

1. **Monitor first scheduled run** (next 6 AM, 1 PM, or 10 PM ET)
2. **Optional: Set up CloudFlare Worker** for redundancy
3. **Optional: Configure notifications** for success/failure alerts

## Quick Commands

### Check Recent Workflow Runs (GitHub CLI)
```bash
gh run list --workflow=data-refresh.yml --limit=5
```

### Trigger Manually via CLI
```bash
gh workflow run data-refresh.yml \
  -f refresh_type=manual \
  -f environment=test \
  -f date_range="2025-08-01,2025-08-04"
```

### View Logs
```bash
gh run view --log
```

## Success! 🎉

Once you see green checkmarks, your automated data refresh system is working! The system will now:
- Run automatically 3 times daily
- Detect changes in lineup and stats
- Only update data that has changed
- Track all operations in job logs