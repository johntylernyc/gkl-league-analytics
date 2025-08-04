# Production Setup Guide

## ✅ Current Status
- GitHub Actions workflow tested successfully
- All incremental update scripts working
- Yahoo OAuth authentication confirmed
- Database creation automated

## 🎯 Production Setup Steps

### 1. Test with Production Environment

Run another test but with `environment=production`:

1. Go to **GitHub Actions** → **"Scheduled Data Refresh"**
2. Click **"Run workflow"** 
3. Set parameters:
   - Branch: `main`
   - Type: `manual`
   - Environment: **`production`** ← Change this
   - Date range: `2025-08-01,2025-08-04`

This will test the production code path and ensure data is processed correctly.

### 2. Verify Scheduled Times

The workflow is already configured to run automatically at:
- **6:00 AM ET** - Full refresh (7-day lookback for stat corrections)
- **1:00 PM ET** - Incremental refresh (3-day lookback)
- **10:00 PM ET** - Incremental refresh (3-day lookback)

**Note**: Times are converted to UTC in the workflow:
- 6 AM ET = 10 AM UTC (EST) / 11 AM UTC (EDT)
- 1 PM ET = 5 PM UTC (EST) / 6 PM UTC (EDT)  
- 10 PM ET = 2 AM UTC next day (EST) / 3 AM UTC next day (EDT)

### 3. Monitor First Scheduled Run

**Next scheduled run will be**:
- If before 6 AM ET today: Wait for 6 AM run
- If after 6 AM but before 1 PM ET: Wait for 1 PM run
- If after 1 PM but before 10 PM ET: Wait for 10 PM run
- If after 10 PM ET: Wait for tomorrow 6 AM run

### 4. Production Data Flow

Once running automatically, the system will:

#### Morning Run (6 AM ET):
- **Full refresh** with 7-day lookback
- Checks for MLB stat corrections
- Updates all changed data
- Most comprehensive refresh

#### Afternoon Run (1 PM ET):
- **Incremental refresh** with 3-day lookback
- Catches lineup changes made during the day
- Updates recent data only

#### Night Run (10 PM ET):
- **Incremental refresh** with 3-day lookback
- Catches final lineup changes before games
- Updates recent data only

### 5. What Data Gets Updated

Each run will:
- ✅ **Detect changes** using content hashing
- ✅ **Update only modified data** (not duplicates)
- ✅ **Track all changes** in database logs
- ✅ **Log job status** for monitoring

#### Change Detection:
- **Lineup Changes**: Position swaps, player additions/removals
- **Stat Corrections**: MLB official stat adjustments
- **Transaction Updates**: Late-reported trades, waivers

#### Database Updates:
- `daily_lineups` - Roster decisions and positions
- `league_transactions` - Trades, adds, drops
- `daily_gkl_player_stats` - Player performance data
- `lineup_changes` - Change tracking log
- `stat_corrections` - Correction tracking log
- `job_log` - Execution monitoring

## 🔍 Monitoring & Verification

### Check Scheduled Runs:
1. **GitHub Actions tab** - View workflow execution history
2. **Job logs** - Check success/failure status
3. **Database** - Verify data updates (if accessible)

### Success Indicators:
- ✅ Green checkmarks on all jobs
- ✅ "UPDATE SUMMARY" shows processed records
- ✅ Change tracking shows detected modifications
- ✅ No authentication errors

### Failure Indicators:
- ❌ Red X on any job
- ❌ "Bad credentials" errors
- ❌ "No such table" errors (shouldn't happen now)
- ❌ Python import errors

## 📊 Expected Data Volume

Based on your league:
- **Transactions**: 2-10 per day
- **Lineup Changes**: 20-50 per day (during active season)
- **Stat Corrections**: 5-15 per week
- **Job Logs**: 3 entries per day (one per run)

## 🚨 What to Watch For

### First Week:
- [ ] All scheduled runs complete successfully
- [ ] Data is being updated (not just duplicate inserts)
- [ ] Change detection is working (showing actual changes)
- [ ] No authentication failures

### Ongoing:
- [ ] Runs happen at expected times
- [ ] Performance stays reasonable (2-3 minutes per run)
- [ ] No quota/rate limit issues with Yahoo API
- [ ] Database growth is reasonable

## ⚡ Quick Actions

### If a Run Fails:
1. Check the job logs in GitHub Actions
2. Look for specific error messages
3. Most likely: Yahoo token expired (refresh needed)
4. Run manual test to verify fix

### If You Need to Stop Automated Runs:
1. Go to `.github/workflows/data-refresh.yml`
2. Comment out the `schedule:` section
3. Commit and push

### If You Want to Change Schedule:
1. Edit the cron expressions in `.github/workflows/data-refresh.yml`
2. Use https://crontab.guru/ to verify timing
3. Remember times are in UTC

## 🎉 Success!

Once everything is running smoothly:
- ✅ Your fantasy league data will be automatically refreshed 3x daily
- ✅ Only changed data will be updated (efficient)
- ✅ All changes will be tracked and logged
- ✅ System will run reliably without manual intervention

## Optional Enhancements

After the core system is stable:

1. **CloudFlare Worker** - Redundant triggering system
2. **Notifications** - Slack/Discord alerts for failures
3. **Monitoring Dashboard** - Track system health
4. **Data Validation** - Automated quality checks