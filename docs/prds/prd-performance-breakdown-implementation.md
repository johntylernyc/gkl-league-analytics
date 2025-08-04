# Performance Breakdown Live Data Integration Plan

## Overview
Integrate the Performance Breakdown component with live MLB player statistics from the `daily_gkl_player_stats` table, supporting both batter and pitcher stats based on player type, and showing performance broken down by roster status (started, benched, injured list, etc.).

## Current State Analysis

### Database Infrastructure ✅
- **Tables Available**: `daily_gkl_player_stats` table exists with comprehensive batting and pitching statistics
- **Schema**: Well-designed with separate columns for batting stats (batting_runs, batting_hits, etc.) and pitching stats (pitching_wins, pitching_saves, etc.)
- **Player Mapping**: `player_id_mapping` table links Yahoo player IDs to MLB data
- **Indexes**: Performance-optimized with proper indexing on player_id, date, and composite keys

### Frontend Component Status 📝
- **Current**: Mock data with hardcoded batting stats (R, H, HR, RBI, SB, AVG, OBP, SLG)
- **Limitation**: Only shows batting stats regardless of player type
- **Structure**: Table format showing stats by roster status (started, benched, etc.)

### Backend Service Status 📝
- **Current**: PlayerSpotlightService provides usage breakdown by roster status
- **Missing**: No method to fetch and aggregate player statistics by roster status
- **Integration Point**: Service already segments data by roster status and date ranges

## Implementation Plan

### Phase 1: Backend Service Enhancement

#### 1.1 Create PlayerStatsService
- **File**: `web-ui/backend/services/playerStatsService.js`
- **Purpose**: Handle all player statistics queries and aggregation
- **Methods**:
  - `getPlayerStatsByUsage(playerId, season)` - Aggregate stats by roster status
  - `determinePlayerType(playerId, season)` - Identify if player is batter/pitcher/both
  - `aggregateStatsByDateRange(playerId, dateRanges, playerType)` - Sum stats across date ranges

#### 1.2 Enhance PlayerSpotlightService
- **Add**: Integration with PlayerStatsService
- **Method**: `getPlayerPerformanceBreakdown(playerId, season)`
- **Logic**: 
  - Determine player type (batter/pitcher)
  - Get usage breakdown by roster status (existing)
  - For each usage period, aggregate relevant stats from `daily_gkl_player_stats`
  - Return performance data structured by usage type

#### 1.3 Update API Endpoints
- **Route**: `GET /api/players/:id/performance-breakdown/:season`
- **Response Structure**:
```json
{
  "player_type": "batter|pitcher|both",
  "usage_breakdown": {
    "started": {
      "days": 120,
      "stats": {
        "batting": { "R": 65, "H": 140, "3B": 3, "HR": 25, "RBI": 85, "SB": 12, "AVG": 0.298, "OBP": 0.365, "SLG": 0.485 },
        "pitching": null
      }
    },
    "benched": { /* similar structure */ },
    "injured_list": { /* similar structure */ }
  }
}
```

### Phase 2: Frontend Component Updates

#### 2.1 Update PerformanceBreakdown Component
- **Dynamic Stat Categories**: Show batting vs pitching stats based on player type
- **Stat Definitions**:
  - **Batters**: R, H, 3B, HR, RBI, SB, AVG, OBP, SLG
  - **Pitchers**: APP, W, SV, K, HLD, ERA, WHIP, K/BB, QS
- **Calculated Ratios**: Compute AVG, OBP, SLG, ERA, WHIP, K/BB from component stats
- **Hybrid Players**: Show both batting and pitching sections if player has both

#### 2.2 Add Player Type Detection
- **API Integration**: Fetch player type from backend
- **Header Updates**: Show "Batting Performance" / "Pitching Performance" / "Overall Performance"
- **Table Structure**: Dynamically render appropriate columns

#### 2.3 Enhanced Data Display
- **Zero Handling**: Show "0" for usage periods with 0 days (not null)
- **Rate Calculations**: Properly handle division by zero for averages
- **Tooltips**: Add context for calculated stats (e.g., "ERA = (Earned Runs × 9) ÷ Innings Pitched")

### Phase 3: Database Query Optimization

#### 3.1 Performance Queries
- **Indexes**: Utilize existing composite indexes for optimal performance
- **Query Pattern**: 
```sql
SELECT usage_period, 
       SUM(batting_runs) as total_runs,
       SUM(batting_hits) as total_hits,
       SUM(batting_at_bats) as total_at_bats,
       -- calculated ratios in application layer
FROM daily_gkl_player_stats s
JOIN daily_lineups l ON s.yahoo_player_id = l.player_id AND s.date = l.date
WHERE s.yahoo_player_id = ? AND s.date BETWEEN ? AND ?
GROUP BY usage_period
```

#### 3.2 Caching Strategy
- **Service Level**: Cache aggregated stats for 1 hour (stats don't change frequently)
- **Redis Integration**: Use existing caching patterns if available
- **Cache Keys**: `player_performance_${playerId}_${season}`

### Phase 4: Data Quality & Edge Cases

#### 4.1 Missing Data Handling
- **Scenario**: Player has roster data but no stats data
- **Solution**: Show "No stats available" with explanation
- **Graceful Degradation**: Show available data even if incomplete

#### 4.2 Player Type Edge Cases
- **Two-Way Players**: Players like Shohei Ohtani with both batting and pitching stats
- **Position Changes**: Players who change positions during season
- **Rookies**: Players with limited historical data

#### 4.3 Data Validation
- **Sanity Checks**: Validate calculated ratios (AVG ≤ 1.000, ERA ≥ 0.00)
- **Outlier Detection**: Flag unusual statistical outliers for review
- **Completeness**: Track data coverage percentage

### Phase 5: Testing & Validation

#### 5.1 Unit Tests
- **Backend**: Test stat aggregation logic with various player types
- **Frontend**: Test component rendering with different data structures
- **Calculations**: Verify all ratio calculations are correct

#### 5.2 Integration Tests
- **API Endpoints**: Test full data flow from database to frontend
- **Performance**: Verify query response times under load
- **Edge Cases**: Test with players having unusual data patterns

#### 5.3 User Acceptance Testing
- **Data Accuracy**: Compare calculated stats with official sources
- **UI/UX**: Verify proper display of both batter and pitcher stats
- **Performance**: Ensure acceptable load times

## Implementation Timeline

### Sprint 1 (Week 1)
- Create PlayerStatsService
- Update database queries
- Basic API endpoint implementation

### Sprint 2 (Week 2)
- Frontend component updates
- Player type detection
- Dynamic stat display

### Sprint 3 (Week 3)
- Performance optimization
- Caching implementation
- Edge case handling

### Sprint 4 (Week 4)
- Testing and validation
- Documentation updates
- Performance monitoring

## Success Metrics

### Technical Metrics
- **Query Performance**: < 500ms response time for performance breakdown
- **Data Completeness**: 95%+ coverage for rostered players
- **Accuracy**: Calculated ratios match official MLB stats within 0.001

### User Experience Metrics
- **Load Time**: Component loads within 2 seconds
- **Usability**: Clear distinction between batter/pitcher stats
- **Data Quality**: Zero incorrect statistical calculations

## Risk Mitigation

### Technical Risks
- **Performance**: Use proper indexing and caching
- **Data Quality**: Implement validation and monitoring
- **Complexity**: Phase implementation to manage complexity

### Data Risks
- **Missing Stats**: Graceful handling of incomplete data
- **Calculation Errors**: Comprehensive testing of all formulas
- **Player Mapping**: Validation of Yahoo ID to MLB player mapping

## Dependencies

### Internal Dependencies
- `daily_gkl_player_stats` table must be populated with current season data
- `player_id_mapping` table must have accurate mappings
- Existing PlayerSpotlightService structure

### External Dependencies
- None (all data is internal to our database)

## Files to Create/Modify

### New Files
- `web-ui/backend/services/playerStatsService.js`
- `web-ui/backend/routes/playerStats.js`
- `docs/performance-breakdown-implementation.md` (this document)

### Modified Files
- `web-ui/backend/services/playerSpotlightService.js`
- `web-ui/frontend/src/components/player-spotlight/PerformanceBreakdown.js`
- `web-ui/backend/app.js` (register new routes)

This implementation will transform the Performance Breakdown from a mock component into a powerful tool showing actual MLB performance statistics segmented by fantasy roster usage, providing valuable insights for fantasy baseball decision-making.