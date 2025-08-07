# Player Stats Production Integration Plan

## Current Issues

1. **Missing Tables in D1**: `player_mapping` table doesn't exist in production
2. **GitHub Actions Failing**: Stats collection jobs failing due to missing schema
3. **UI/UX Updates Needed**: Player search needs to handle expanded universe (750+ MLB players vs just fantasy roster players)

## Implementation Plan

### Phase 1: Database Schema Setup
- [ ] Create and apply D1 schema for player stats tables
  - `player_mapping` table
  - `daily_gkl_player_stats` table (if not exists)
- [ ] Test schema in production D1
- [ ] Document schema changes

### Phase 2: Fix GitHub Actions Pipeline
- [ ] Update the update_stats.py script to handle missing tables gracefully
- [ ] Ensure proper environment detection (D1 vs SQLite)
- [ ] Add schema initialization on first run
- [ ] Test with manual workflow trigger

### Phase 3: Initial Data Population
- [ ] Run backfill for recent dates (August 2025)
- [ ] Populate player_mapping table with Yahoo ID mappings
- [ ] Verify data quality and coverage

### Phase 4: API Updates
- [ ] Update Cloudflare Workers API to serve player stats
- [ ] Add endpoints for:
  - Player stats by ID
  - Player search (expanded universe)
  - Stats trends/aggregations
- [ ] Implement caching strategy for performance

### Phase 5: Frontend Integration
- [ ] Update player search component to handle:
  - Fantasy roster players (priority)
  - Non-roster MLB players (secondary)
  - Clear distinction in UI
- [ ] Add player stats display components
- [ ] Integrate stats into existing player views

### Phase 6: Testing & Deployment
- [ ] Test complete pipeline end-to-end
- [ ] Verify GitHub Actions runs successfully
- [ ] Deploy to production
- [ ] Monitor for issues

## Technical Considerations

### Database Schema Differences
- D1 uses TEXT for Yahoo IDs (not INTEGER)
- Timestamp handling differs between SQLite and D1
- Need to ensure foreign key constraints work

### Data Volume
- ~750 players × 365 days = 273,750 records/year
- Each record ~50 fields
- Estimated 15-20 MB/month growth

### Performance
- Consider pagination for player lists
- Cache frequently accessed stats
- Use indexes on commonly queried fields

### UI/UX Considerations
- Show fantasy roster players first in search
- Visual distinction for non-roster players
- Loading states for stats fetching
- Graceful handling of missing data

## Files to Modify

### Backend
- `/data_pipeline/player_stats/update_stats.py`
- `/data_pipeline/player_stats/d1_schema_update.sql`
- `/cloudflare-production/src/routes/players.js` (new)
- `/cloudflare-production/src/index.js`

### Frontend
- `/web-ui/frontend/src/components/PlayerSearch.js`
- `/web-ui/frontend/src/components/PlayerStats.js` (new)
- `/web-ui/frontend/src/services/api.js`
- `/web-ui/frontend/src/hooks/usePlayerStats.js` (new)

## Timeline Estimate
- Phase 1-2: 1 hour (Schema & Pipeline fixes)
- Phase 3: 30 minutes (Data population)
- Phase 4-5: 2-3 hours (API & Frontend)
- Phase 6: 1 hour (Testing & Deployment)

Total: 4-5 hours of implementation