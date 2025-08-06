# Player Stats Pipeline Deployment Guide

## Overview

The Player Stats Pipeline collects comprehensive MLB player statistics for all active players (~750+ daily), maintaining multi-platform ID mappings (MLB, Yahoo, Baseball Reference, FanGraphs) to enable features like click-through from player spotlights to Yahoo's fantasy add/drop pages.

## System Architecture

### Data Flow
```
MLB Stats API → PyBaseball → Local Processing → SQLite/D1 → Frontend Features
                     ↓
            Yahoo ID Matching ← Yahoo Fantasy API
```

### Key Components
- **comprehensive_collector.py**: Core stats collection from MLB API
- **yahoo_id_matcher.py**: Fuzzy name matching for Yahoo IDs
- **yahoo_player_search.py**: Yahoo Fantasy API integration
- **backfill_stats.py**: Historical data collection
- **update_stats.py**: Daily incremental updates
- **data_quality_check.py**: Data validation and health monitoring

## Database Schema

### Tables
1. **player_mapping**: Multi-platform player ID mappings
   - 2,779 total players tracked
   - 1,583 with Yahoo IDs (79% coverage)
   - 100% Baseball Reference and FanGraphs coverage

2. **daily_gkl_player_stats**: Daily player statistics
   - Comprehensive batting and pitching stats
   - Rate stats (AVG, OBP, SLG, OPS, ERA, WHIP)
   - Yahoo player IDs for fantasy integration

## Deployment Options

### 1. Local Development (SQLite)

```bash
# Test database
python update_stats.py --environment test

# Production database
python update_stats.py --environment production
```

### 2. Cloudflare D1 (Production)

```bash
# Set environment variables
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-api-token"
export D1_DATABASE_ID="your-database-id"

# Deploy with D1
python update_stats.py --use-d1
```

### 3. GitHub Actions (Automated)

Create `.github/workflows/player-stats-update.yml`:

```yaml
name: Update Player Stats

on:
  schedule:
    - cron: '0 10 * * *'  # Daily at 10 AM UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pybaseball
      
      - name: Update stats
        env:
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          D1_DATABASE_ID: ${{ secrets.D1_DATABASE_ID }}
          YAHOO_CLIENT_ID: ${{ secrets.YAHOO_CLIENT_ID }}
          YAHOO_CLIENT_SECRET: ${{ secrets.YAHOO_CLIENT_SECRET }}
        run: |
          cd data_pipeline/player_stats
          python update_stats.py --days 3 --use-d1 --refresh-yahoo --quiet
```

## Usage Examples

### Daily Updates

```bash
# Update last 7 days (default)
python update_stats.py

# Update last 3 days with Yahoo ID refresh
python update_stats.py --days 3 --refresh-yahoo

# Update specific date
python update_stats.py --date 2024-08-05

# Update since last date in database
python update_stats.py --since-last
```

### Historical Backfill

```bash
# Backfill entire 2024 season
python backfill_stats.py --season 2024

# Backfill specific date range
python backfill_stats.py --start 2024-07-01 --end 2024-07-31

# Parallel processing with 4 workers
python backfill_stats.py --season 2024 --workers 4

# Resume interrupted backfill
python backfill_stats.py --resume
```

### Data Quality Monitoring

```bash
# Basic health check
python data_quality_check.py

# Detailed report with issues
python data_quality_check.py --detailed

# Export issues to CSV
python data_quality_check.py --export issues.csv

# Check specific date range
python data_quality_check.py --start 2024-08-01 --end 2024-08-05
```

## Performance Metrics

### Collection Speed
- ~250-450 players per game day
- ~30 seconds per date for collection
- ~90 seconds for 3-day update

### Coverage Statistics
- **Yahoo IDs**: 79% overall, 97% for daily active players
- **Data Freshness**: Updated daily, typically < 24 hours behind
- **Data Volume**: ~135,000 records per season

## Monitoring

### Health Score Components
- **Completeness** (20%): Missing dates, low player counts
- **Validity** (30%): Invalid stats, negative values
- **ID Mappings** (30%): Yahoo ID coverage
- **Freshness** (20%): Days behind current date

### Grade Scale
- A (90-100): Excellent, production-ready
- B (80-89): Good, minor issues
- C (70-79): Acceptable, needs attention
- D (60-69): Poor, significant issues
- F (0-59): Critical, immediate action needed

## Troubleshooting

### Common Issues

1. **"Missing Yahoo IDs"**
   ```bash
   # Refresh Yahoo IDs
   python update_stats.py --refresh-yahoo
   ```

2. **"High ERA values"**
   - Normal for relief pitchers with < 1 IP
   - Threshold adjustable in data_quality_check.py

3. **"Database behind"**
   ```bash
   # Catch up from last date
   python update_stats.py --since-last
   ```

4. **"D1 Connection Failed"**
   - Verify environment variables are set
   - Check API token has D1 permissions
   - Ensure database ID is correct

### Debug Mode

```bash
# Enable verbose logging
python update_stats.py --date 2024-08-05 --environment test

# Check specific player
sqlite3 database/league_analytics_test.db
SELECT * FROM player_mapping WHERE player_name LIKE '%Ohtani%';
```

## Maintenance

### Regular Tasks
- **Daily**: Run incremental updates
- **Weekly**: Check data quality report
- **Monthly**: Review Yahoo ID coverage
- **Seasonally**: Full backfill for accuracy

### Database Cleanup
```sql
-- Remove old job logs
DELETE FROM job_log WHERE created_at < date('now', '-30 days');

-- Vacuum database
VACUUM;
```

## Security Considerations

1. **Never commit credentials** - Use environment variables
2. **Token refresh** - Yahoo tokens expire hourly
3. **Rate limiting** - Respect API limits (built into scripts)
4. **Data privacy** - No personal player data collected

## Support

For issues or questions:
1. Check job_log table for error details
2. Review data quality report for issues
3. Enable verbose logging for debugging
4. Refer to CLAUDE.md for architectural details

---

*Last Updated: August 2025*
*Version: 1.0.0*