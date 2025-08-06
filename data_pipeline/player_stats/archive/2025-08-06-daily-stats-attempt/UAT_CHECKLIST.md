# Player Stats Pipeline - UAT Checklist

## Current Status: Ready for UAT

The player stats pipeline has been successfully updated and tested with mock data. All critical issues have been resolved.

## What's Working

### ✅ Schema Compatibility
- Removed dependencies on non-existent columns (`content_hash`, `has_correction`)
- Updated to use environment-specific table names
- Fixed all import paths and circular dependencies

### ✅ Job Tracking
- Jobs are properly logged with unique IDs
- Status transitions work correctly (pending → completed)
- Record counts are accurately tracked
- Both test and production environments supported

### ✅ Data Collection Structure
- Mock data demonstrates the expected Yahoo API data structure
- Player ID mapping table ready for Yahoo → MLB ID mapping
- Stats table schema matches Yahoo Fantasy stat categories

### ✅ Incremental Updates
- Script correctly identifies dates within stat correction window (7 days)
- Properly skips older dates marked as "archive data"
- Counts existing records for unchanged tracking

## UAT Testing Steps

### 1. Verify Test Environment Works
```bash
cd data_pipeline/player_stats

# View current test data
python validate_test_data_simple.py

# Run incremental update on test data
python update_stats.py --environment test --days 7

# Check job logs
python validate_test_data_simple.py --all
```

### 2. Test with Real Yahoo API Data

**Prerequisites**: Need to refresh OAuth token
```bash
cd auth
python generate_auth_url.py    # Get new authorization URL
# Visit URL, authorize, copy the code
python initialize_tokens.py    # Exchange code for tokens
```

**Once OAuth is working**:
```bash
cd data_pipeline/player_stats
python test_real_data_collection.py --environment test
```

### 3. Integration Points to Validate

The script currently has placeholders for:
- `fetch_stats_from_mlb_api()` - Will use pybaseball for MLB data
- Player ID mapping from Yahoo IDs to MLB IDs
- Stat correction detection by comparing stored vs fresh data

## Data Flow Validation

1. **Daily Lineups** → Provides player roster (player_id, team, positions)
2. **Yahoo API** → Provides current season stats
3. **PyBaseball/MLB** → Will provide daily game logs
4. **Stat Corrections** → Compare stored vs fresh data within 7-day window

## Expected Data Structure

### Player Stats Table
- `yahoo_player_id`: e.g., "11881" (Josh Jung)
- `player_name`: Full name from Yahoo
- `team_code`: 3-letter team code
- `position_codes`: Comma-separated eligible positions
- `batting_*`: Individual stat columns
- `has_batting_data`: Boolean flag
- `job_id`: Links to job_log for tracking

### Job Log Table
- Tracks every collection run
- Records processed/inserted counts
- Status tracking (pending/completed/failed)
- Metadata includes environment and parameters

## Next Steps After UAT Approval

1. **Complete PyBaseball Integration**
   - Implement `fetch_stats_from_mlb_api()`
   - Add player ID mapping logic
   - Test stat correction detection

2. **Production Testing**
   ```bash
   python update_stats.py --environment production --days 3
   ```

3. **D1 Integration Testing**
   ```bash
   python update_stats.py --use-d1 --days 3
   ```

4. **Enable Automation**
   - Add to GitHub Actions workflow
   - Schedule daily runs
   - Monitor job logs

## Key Files Modified

- `update_stats.py` - Complete rewrite without schema dependencies
- `job_manager.py` - Added start_job/update_job methods
- `config.py` - Environment-specific configuration
- Various imports fixed for proper module paths

## Success Criteria

- [x] Schema compatibility issues resolved
- [x] Job tracking functional
- [x] Test environment working
- [x] Mock data collection demonstrates structure
- [ ] Real Yahoo API data collection (pending OAuth fix)
- [ ] PyBaseball integration (next phase)
- [ ] Production deployment (after UAT)

---
*Ready for UAT approval - 2025-08-06*