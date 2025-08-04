# Automated Data Refresh Schedule

## 🕐 Daily Schedule (Eastern Time)

| Time | Type | Purpose | Lookback Period |
|------|------|---------|----------------|
| **6:00 AM ET** | Full Refresh | Stat corrections from MLB | 7 days |
| **1:00 PM ET** | Incremental | Afternoon lineup changes | 3 days |
| **10:00 PM ET** | Incremental | Final lineup changes | 3 days |

## 📅 When Runs Happen

### Morning Run (6:00 AM ET)
- **Purpose**: Catch overnight MLB stat corrections
- **Data**: Full 7-day lookback for stat adjustments
- **Typical Duration**: 2-3 minutes
- **Peak Usage**: During baseball season

### Afternoon Run (1:00 PM ET)  
- **Purpose**: Catch lineup changes made during the day
- **Data**: 3-day lookback for recent roster moves
- **Typical Duration**: 1-2 minutes
- **Peak Usage**: Active trading periods

### Night Run (10:00 PM ET)
- **Purpose**: Final lineup changes before next day's games
- **Data**: 3-day lookback for last-minute moves
- **Typical Duration**: 1-2 minutes
- **Peak Usage**: Day before games start

## 🌍 UTC Conversion

GitHub Actions runs in UTC, so times are converted:

### Eastern Standard Time (EST) - Winter
- 6:00 AM EST = **10:00 AM UTC**
- 1:00 PM EST = **5:00 PM UTC**
- 10:00 PM EST = **2:00 AM UTC** (next day)

### Eastern Daylight Time (EDT) - Summer  
- 6:00 AM EDT = **11:00 AM UTC**
- 1:00 PM EDT = **6:00 PM UTC**
- 10:00 PM EDT = **3:00 AM UTC** (next day)

## 📊 What Each Run Does

### Data Collection:
1. **Fetch** latest data from Yahoo Fantasy API
2. **Compare** with existing data using content hashes
3. **Update** only changed records (no duplicates)
4. **Log** all changes for tracking

### Change Detection:
- **Lineup Changes**: Position swaps, player adds/drops
- **Stat Corrections**: MLB official adjustments
- **Transaction Updates**: Late-reported trades

### Database Updates:
- `daily_lineups` - Updated lineup data
- `league_transactions` - New/modified transactions
- `daily_gkl_player_stats` - Corrected player stats
- `lineup_changes` - Change tracking log
- `stat_corrections` - Correction log
- `job_log` - Execution status

## 🔍 Monitoring

### Check Recent Runs:
```bash
# View recent workflow runs
gh run list --workflow=data-refresh.yml --limit=10

# View logs from latest run
gh run view --log
```

### Local Monitoring:
```bash
# Check system status
python scripts/monitor_system.py
```

### GitHub Actions:
1. Go to repository **Actions** tab
2. Click **"Scheduled Data Refresh"**
3. View recent executions

## ⚙️ Configuration

### Current Cron Schedule:
```yaml
schedule:
  - cron: '0 10 * * *'   # 6 AM ET (EST)
  - cron: '0 17 * * *'   # 1 PM ET (EST)  
  - cron: '0 2 * * *'    # 10 PM ET (EST, runs 2 AM UTC)
```

### To Modify Schedule:
1. Edit `.github/workflows/data-refresh.yml`
2. Update cron expressions
3. Commit and push changes
4. Use https://crontab.guru/ to verify timing

## 🚨 Troubleshooting

### If Runs Don't Happen:
- Check GitHub Actions is enabled
- Verify workflow file is in `main` branch
- Check for syntax errors in YAML

### If Runs Fail:
- Check Yahoo token hasn't expired
- Verify GitHub Secrets are set correctly
- Look at job logs for specific errors

### Common Issues:
- **"Bad credentials"** → Yahoo token expired
- **"No such table"** → Database creation failed
- **"Module not found"** → Python dependency missing

## 🎯 Success Metrics

### Healthy System:
- ✅ 3 successful runs per day
- ✅ Change detection working (shows actual changes)
- ✅ Reasonable execution times (1-3 minutes)
- ✅ No authentication errors

### Normal Data Volumes:
- **Active Season**: 20-50 lineup changes/day
- **Trading Periods**: 5-15 transactions/day
- **Stat Corrections**: 5-15/week
- **Off-Season**: Minimal activity

Your system is now configured to run automatically and efficiently maintain your fantasy baseball data!