# Draft Results Data Pipeline

This module handles the collection and management of draft data from the Yahoo Fantasy Sports API.

## Overview

**Status**: Stage 1-3 Complete (v2.0 Implementation)

**Important**: This is an annual job that runs once per season after the draft completes. It does NOT require daily updates.

**Testing Strategy**: Always test on `league_analytics_test.db` before running on production `league_analytics.db`.

The draft results pipeline collects historical draft data including:
- Snake draft pick order and selections
- Auction draft costs and nominations
- Player assignments to teams
- Draft metadata (date, type, settings)
- Player details enrichment via batch API calls
- Manual keeper designation support

## Scripts

### 1. `collector.py` - Core Collection Class

The main DraftResultsCollector class that handles API interactions and data storage.

**Features:**
- ✅ Automatic draft type detection (snake vs auction)
- ✅ Comprehensive job logging
- ✅ Data quality validation
- ✅ Player name enrichment (batch processing)
- ✅ Support for keeper leagues with automatic detection
- ✅ Rate limiting (1 req/sec per Yahoo guidelines)
- ✅ Keeper identification for auction drafts (high cost in late rounds)

**Command-Line Usage:**
```bash
# Collect draft results for current season
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025

# Collect without pushing to D1 (for testing)
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025 --skip_d1_push

# Collect historical draft
python -m data_pipeline.draft_results.collector --league_key "431.l.6966" --season 2024
```

**Python Usage:**
```python
from data_pipeline.draft_results.collector import DraftResultsCollector

# Test environment first
collector = DraftResultsCollector(environment='test')
stats = collector.collect_draft_results('458.l.6966', 2025)

# Then production after verification
collector = DraftResultsCollector(environment='production')
stats = collector.collect_draft_results('458.l.6966', 2025)

# Export to D1 after keeper updates
collector.push_to_d1('458.l.6966', 2025)
```

### Supporting Files

- `schema.sql` - Database table definition
- `config.py` - Configuration constants
- `__init__.py` - Module initialization
- `tests/test_collector.py` - Basic integration tests

## Database Schema

The module uses the `draft_results` table with the following structure:
- `job_id` - Job tracking ID (foreign key to job_log)
- `league_key` - Yahoo league identifier
- `season` - Draft year
- `team_key` - Yahoo team identifier
- `team_name` - Fantasy team name
- `player_id` - Yahoo player ID
- `player_name` - Player full name
- `player_position` - Player position(s)
- `player_team` - MLB team abbreviation
- `draft_round` - Round number
- `draft_pick` - Overall pick number
- `draft_cost` - Auction cost (NULL for snake drafts)
- `draft_type` - 'snake' or 'auction'
- `keeper_status` - Whether player was kept (auto-detected for auction drafts)
- `drafted_datetime` - When draft occurred

### Unique Constraint
- `(league_key, season, player_id, team_key)` - Prevents duplicate entries

## Yahoo API Endpoints

### League Settings
```
GET /fantasy/v2/league/{league_key}/settings
```
Used to determine:
- Draft type (snake vs auction)
- Number of teams
- Draft date/time
- Keeper rules

### Draft Results
```
GET /fantasy/v2/league/{league_key}/draftresults
```
Returns:
- Pick order
- Player selections
- Team assignments
- Auction costs (if applicable)

## Data Flow

1. **Initial Collection**: Use `collector.collect_draft_results()` to fetch draft data
2. **Validation**: Automatic validation ensures data quality
3. **Storage**: Data stored with job tracking for audit trail
4. **Future Updates**: Keeper status can be updated as season progresses

## Configuration

Key configuration values in `config.py`:
- `API_DELAY_SECONDS = 1.0` - Rate limiting
- `MAX_RETRIES = 3` - Retry attempts for failed requests
- `BATCH_SIZE = 100` - Database insert batch size

## Testing

### Basic Test
```python
# test_collector.py example
def test_real_draft_collection():
    collector = DraftResultsCollector(environment='test')
    
    # Use known league with draft data
    stats = collector.collect_draft_results('458.l.6966', 2025)
    
    assert stats['records_processed'] > 0
    assert stats['errors'] == 0
    # Note: records_inserted may be 0 if data already exists
```

### Test Results (Stage 1 Complete)
- Successfully collected 378 draft picks from league 458.l.6966
- Enriched all player names via batch API calls
- Fixed draft type detection (now correctly identifies auction drafts via `is_auction_draft` field)
- All data validated successfully
- Correctly identifies 32 keeper players (all drafted in rounds 20-21)

## Annual Draft Collection Process

### Step 1: Test Collection on Test Database (Recommended)

**IMPORTANT**: Always test on the test database first to verify the collection works correctly before running on production.

```bash
# Test the collection on test database
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025 --environment test --skip_d1_push

# Verify the test data
sqlite3 database/league_analytics_test.db
sqlite> SELECT COUNT(*) FROM draft_results WHERE league_key = '458.l.6966' AND season = 2025;
sqlite> SELECT player_name, draft_cost, keeper_status FROM draft_results LIMIT 10;
sqlite> .quit
```

### Step 2: Collect Draft Data on Production Database

After verifying the test collection worked correctly:

```bash
# Run on production database (default)
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025 --skip_d1_push

# Or explicitly specify production environment
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025 --environment production --skip_d1_push
```

This will:
1. Connect to Yahoo API and fetch draft results
2. Enrich player names via batch API calls
3. Store in local production database (league_analytics.db) with job logging
4. Skip D1 push (we'll do that after keeper updates)

### Step 3: Manually Update Keeper Status

**IMPORTANT**: Keeper detection cannot be fully automated. Yahoo's API does not reliably provide keeper information, and keeper patterns vary by league. You MUST manually update keeper status after collection.

#### Getting Keeper Information

1. **From Yahoo Fantasy:**
   - Go to your league page
   - Click "Draft" → "Keeper Players"
   - Note all keeper players and their teams

2. **From League Commissioner:**
   - Request the official keeper list
   - Ensure player names match exactly

#### Updating Keeper Status in Database

**Option 1: Update by Player List**
```sql
-- Connect to your database
-- Update all keepers at once
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = '458.l.6966' 
  AND season = 2025
  AND player_name IN (
    'Aaron Judge',
    'Bobby Witt Jr.',
    'Gunnar Henderson',
    'Shohei Ohtani (Batter)',
    -- ... add all keeper names here
  );
```

**Option 2: Update by Team**
```sql
-- Update keepers for a specific team
UPDATE draft_results 
SET keeper_status = 1
WHERE league_key = '458.l.6966' 
  AND season = 2025
  AND team_name = 'Mary''s Little Lambs'
  AND player_name IN ('Shohei Ohtani (Batter)');
```

**Option 3: Using Python Helper Script**
```python
# keeper_update.py
keepers = [
    ('IWU Tang Clan', ['Aaron Judge', 'Clarke Schmidt', 'Ethan Salas']),
    ('Mary\'s Little Lambs', ['Shohei Ohtani (Batter)']),
    # ... add all teams and their keepers
]

# Run the update
python draft_results/scripts/update_keepers.py --league_key "458.l.6966" --season 2025
```

### Step 4: Verify Keeper Updates

```sql
-- Check keeper count by team (should be 0-3 per team)
SELECT team_name, COUNT(*) as keeper_count
FROM draft_results
WHERE keeper_status = 1 
  AND league_key = '458.l.6966' 
  AND season = 2025
GROUP BY team_name
ORDER BY team_name;

-- List all keepers
SELECT player_name, team_name, draft_round, draft_cost
FROM draft_results
WHERE keeper_status = 1
  AND league_key = '458.l.6966'
  AND season = 2025
ORDER BY team_name, player_name;

-- Verify total keeper count
SELECT COUNT(*) as total_keepers
FROM draft_results
WHERE keeper_status = 1
  AND league_key = '458.l.6966'
  AND season = 2025;
```

### Step 5: Push to Cloudflare D1

The draft results module uses the standard `sync_to_production.py` pattern for D1 deployment:

```bash
# Option 1: Use the collector's built-in D1 export
python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season 2025

# This will:
# 1. Export draft data to cloudflare-production/sql/incremental/
# 2. Export required job_log entries
# 3. Provide manual import commands

# Option 2: Use sync_to_production.py if you've made manual updates
python scripts/sync_to_production.py

# Note: sync_to_production.py exports transactions and lineups by default.
# Draft data must be exported using the collector's push_to_d1() method.
```

**Import to D1 (follow the provided commands):**
```bash
cd cloudflare-production

# First time only - create the table:
npx wrangler d1 execute gkl-fantasy --file=../data_pipeline/draft_results/schema.sql --remote

# Import in this order:
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/draft_job_logs_*.sql --remote
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/draft_results_*.sql --remote

# Verify the import:
npx wrangler d1 execute gkl-fantasy --command="SELECT COUNT(*) FROM draft_results WHERE league_key = '458.l.6966' AND season = 2025" --remote
```

## Error Handling

The collector handles various error scenarios:
- **Token Expiration**: Automatic refresh
- **API Errors**: Exponential backoff retry
- **Missing Data**: Defaults for optional fields
- **Duplicate Data**: INSERT OR IGNORE pattern

## Job Logging

All collection operations are logged in the `job_log` table with:
- Unique job IDs
- Start/end timestamps
- Records processed and inserted
- Error tracking
- Environment tracking

## Performance Considerations

### Data Volume
- Typical draft: 200-300 picks (12-16 teams × 15-25 rounds)
- Processing time: ~5-10 seconds per league
- Storage: ~50KB per draft

### Rate Limiting
Yahoo API limit of 1 request/second is enforced. Each draft collection requires:
- 1 request for league settings
- 1 request for draft results
- 1 request for team names
- 15-20 requests for player details (batched in groups of 25)
- Total: ~20-30 seconds per league with player enrichment

## Operational Notes

### When to Run

- **Post-Draft**: Run within 24-48 hours after your league's draft
- **Historical**: Can collect past seasons anytime (Yahoo typically keeps 5-7 years)
- **NOT Daily**: This job runs once per season, not daily

### Direct D1 Push

Unlike other pipelines, draft results push directly to D1 on collection:
- No daily sync delay
- Immediate availability in production
- Use `--skip_d1_push` flag for testing only

### Historical Collection

```bash
# Collect multiple seasons
for season in 2020 2021 2022 2023 2024 2025; do
    python -m data_pipeline.draft_results.collector --league_key "458.l.6966" --season $season
done

# Or use the backfill script (when available)
python -m data_pipeline.draft_results.backfill_drafts --league_key "458.l.6966" --start 2020 --end 2025
```

## Implementation Status

### Completed Features (v2.0)
- ✅ Core collector with CLI interface
- ✅ Automatic draft type detection
- ✅ Player name enrichment via batch API
- ✅ Keeper detection for auction drafts
- ✅ Manual keeper update documentation
- ✅ D1 push using sync_to_production pattern
- ✅ Parameterized collection for any league/season
- ✅ Comprehensive job logging

### D1 Database Setup

**IMPORTANT**: Before pushing draft data to D1 for the first time, you must create the table:

```bash
# Navigate to cloudflare-production directory
cd cloudflare-production

# Create draft_results table in D1
npx wrangler d1 execute gkl-fantasy --file=../data_pipeline/draft_results/schema.sql --remote
```

### Future Enhancements

#### Planned Features
- ⏳ Helper scripts for bulk keeper updates
- ⏳ Historical data backfill script
- ⏳ Available season detection
- ⏳ Draft analytics endpoints

## Annual Draft Collection Checklist

### Post-Draft Tasks (Complete within 48 hours)

- [ ] **1. Test Draft Collection**
  ```bash
  python -m data_pipeline.draft_results.collector --league_key "YOUR_LEAGUE_KEY" --season YEAR --environment test --skip_d1_push
  ```
  - Verify job completes successfully
  - Check record count in test database

- [ ] **2. Run Production Collection**
  ```bash
  python -m data_pipeline.draft_results.collector --league_key "YOUR_LEAGUE_KEY" --season YEAR --skip_d1_push
  ```
  - Check job logs show "completed" status
  - Verify record count matches number of draft picks

- [ ] **3. Get Keeper List**
  - From Yahoo: League → Draft → Keeper Players
  - Or from league commissioner
  - Note exact player names

- [ ] **4. Update Keeper Status**
  - Run SQL update with keeper names
  - Each team should have 0-3 keepers

- [ ] **5. Verify Keeper Updates**
  - Run verification queries
  - Confirm keeper count per team
  - Check total keeper count

- [ ] **6. Push to D1**
  ```bash
  python -m data_pipeline.draft_results.collector --league_key "YOUR_LEAGUE_KEY" --season YEAR
  ```
  - Follow the D1 import instructions
  - Verify data in production D1

- [ ] **7. Document Completion**
  - Note any issues encountered
  - Save keeper list for reference
  - Update season documentation

## Troubleshooting

### No Draft Data Found
- Verify league has completed a draft
- Check if league key and season are correct
- Some older seasons may not have draft data available

### Authentication Issues
- Ensure OAuth tokens are valid (expire hourly)
- Run `python auth/initialize_tokens.py` to refresh

### Data Quality Issues
- Check logs for validation warnings
- Missing positions/teams are replaced with defaults
- Review invalid_records in validation output

### Keeper Update Issues
- Ensure player names match exactly (including parentheses)
- Check for special characters in team names (apostrophes)
- Verify you're updating the correct season

### Yahoo API Limitations
- **Keeper Status**: The `is_keeper` field in Yahoo's API is unreliable/empty
- **Player Names**: Not included in draft endpoint; requires additional API calls
- **Historical Data**: Typically available for 5-7 years
- **Rate Limits**: 1 request per second enforced