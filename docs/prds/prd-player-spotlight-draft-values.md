# PRD: Player Spotlight Draft Values Enhancement

## Product Requirements Document

**Version**: 1.0  
**Date**: August 5, 2025  
**Author**: Claude Code  
**Status**: Draft

## Executive Summary

This PRD outlines the requirements for adding draft value information to the Player Spotlight page in the GKL League Analytics platform. This enhancement will display a player's draft cost (auction value) and draft position information on the player card at the top of the Player Spotlight page, providing immediate context about the player's perceived value at the start of the season.

## Background

The GKL League Analytics platform recently ingested draft results data into the database, including:
- Draft cost (auction values)
- Draft round and pick number
- Team that drafted the player
- Keeper status
- Draft type (auction/snake)

Currently, the Player Spotlight page displays player information without any draft context, missing an opportunity to provide valuable insights about player value and draft strategy.

## Objectives

1. **Primary Goal**: Display current season draft information on the Player Spotlight player card
2. **User Value**: Help users understand player draft value and compare current performance against draft expectations
3. **Technical Goal**: Integrate draft_results table data with existing player spotlight API and UI

## Scope

### In Scope
- Display draft cost (auction value) on the player card for the current season
- Show draft round/pick information
- Display which team originally drafted the player
- Handle cases where players went undrafted
- Keeper designation display
- Support only the current season initially (2025)

### Out of Scope (Future Enhancements)
- Historical draft value comparisons across seasons
- Draft value trends and analytics
- Draft strategy insights
- Value over replacement calculations
- Trade value assessments based on draft cost

## User Stories

1. **As a league member**, I want to see what a player cost in our draft so I can evaluate if they're meeting expectations
2. **As a team manager**, I want to know which team originally drafted a player to understand roster construction strategies
3. **As an analyst**, I want draft context when reviewing player performance to identify value picks and busts

## Requirements

### Functional Requirements

#### Frontend Requirements

1. **Player Card Enhancement**
   - Add draft information section to PlayerHeader component
   - Display format: "$X draft cost" for auction drafts
   - Show draft round/pick for snake drafts (if applicable)
   - Include team that drafted the player
   - Handle undrafted players gracefully ("Undrafted" label)

2. **Visual Design**
   - Draft cost should be prominently displayed but not dominate the card
   - Use consistent styling with existing player card elements
   - Maintain responsive design for mobile devices

3. **Data Display Logic**
   - Only show draft data for the selected season
   - If player has no draft data for current season, show "Undrafted"
   - Format auction values with dollar sign and no decimals
   - Show keeper status if marked

#### Backend Requirements

1. **API Enhancement**
   - Modify `/players/{playerId}/spotlight` endpoint to include draft data
   - Join with draft_results table based on player_id and season
   - Return draft_cost, draft_round, draft_pick, team_name, draft_type
   - Handle null cases for undrafted players

2. **Database Query**
   - Add efficient join between player data and draft_results
   - Filter by current season
   - Include appropriate indexes for performance

3. **Data Model Updates**
   - Extend player spotlight response to include draft information
   - Ensure backward compatibility with existing API consumers

### Non-Functional Requirements

1. **Performance**
   - Draft data query should not significantly impact page load time
   - Consider caching draft data as it doesn't change during season
   - Maintain sub-200ms API response time

2. **Compatibility**
   - Support all modern browsers
   - Maintain mobile responsiveness
   - Ensure graceful degradation if draft data unavailable

3. **Data Quality**
   - Handle edge cases (undrafted, traded, waived players)
   - Validate draft data integrity
   - Support both auction and snake draft formats

## Technical Architecture

### Current State
```
Frontend (React) → API (Cloudflare Workers) → D1 Database
PlayerSpotlight.js → PlayerHeader.js → /players/{id}/spotlight → player data
```

### Proposed Changes

#### Frontend Changes
1. **PlayerHeader.js**
   - Add draft information display section
   - Conditionally render based on data availability
   - Style consistently with existing elements

2. **PlayerSpotlight.js**
   - No changes needed (data passed through props)

3. **API Service**
   - No changes needed (existing endpoint structure maintained)

#### Backend Changes
1. **player-spotlight.js** (Cloudflare Workers)
   - Modify `getPlayerSpotlight` function
   - Add draft_results join to existing query
   - Include draft fields in response

2. **Database Schema**
   - No schema changes required
   - Utilize existing draft_results table
   - Leverage existing indexes

### API Response Structure

Current response includes:
```json
{
  "player": {
    "player_name": "A.J. Minter",
    "player_team": "NYM",
    "position_type": "P",
    "current_fantasy_team": null,
    "eligible_positions": "RP,P,IL"
  },
  "usage_breakdown": {...},
  "monthly_data": [...],
  "available_seasons": [...]
}
```

Enhanced response will include:
```json
{
  "player": {
    "player_name": "A.J. Minter",
    "player_team": "NYM",
    "position_type": "P",
    "current_fantasy_team": null,
    "eligible_positions": "RP,P,IL",
    "draft_info": {
      "draft_cost": 15,
      "draft_round": 12,
      "draft_pick": 216,
      "drafted_by": "The ShapeShifters",
      "draft_type": "auction",
      "keeper_status": false
    }
  },
  // ... rest of response unchanged
}
```

## Implementation Plan

### Phase 1: Backend Implementation (2 hours)
1. Update player-spotlight.js to query draft_results
2. Modify API response structure
3. Test with various player scenarios
4. Verify performance impact

### Phase 2: Frontend Implementation (2 hours)
1. Update PlayerHeader component
2. Add draft information display
3. Style and responsive design
4. Handle edge cases in UI

### Phase 3: Testing & Validation (1 hour)
1. Test drafted vs undrafted players
2. Verify season filtering works correctly
3. Performance testing
4. Cross-browser testing

### Phase 4: Deployment (30 minutes)
1. Deploy API changes to Cloudflare Workers
2. Deploy frontend to Cloudflare Pages
3. Verify in production
4. Monitor for issues

## Success Metrics

1. **Technical Success**
   - API response time remains under 200ms
   - No increase in error rates
   - Draft data displays correctly for all players

2. **User Success**
   - Users can immediately see draft context
   - No confusion about data presentation
   - Positive feedback on added value

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing draft data for some players | Medium | Show "Undrafted" gracefully |
| Performance degradation | High | Add indexes, implement caching |
| UI clutter | Medium | Careful design, user testing |
| Data inconsistencies | Low | Validation, error handling |

## Future Enhancements

1. **Historical Draft Comparisons**
   - Show draft values across multiple seasons
   - Track value trends over time

2. **Advanced Analytics**
   - Value over replacement calculations
   - ROI metrics (performance vs draft cost)
   - Trade value assessments

3. **Draft Strategy Insights**
   - Team draft strategy analysis
   - Position value heat maps
   - Keeper value projections

4. **Interactive Features**
   - Draft value filters on player explorer
   - Sort by value/performance ratio
   - Draft recap integration

## Appendix

### Database Schema Reference

```sql
-- draft_results table structure
CREATE TABLE draft_results (
    id INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL,
    league_key TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_position TEXT,
    player_team TEXT,
    draft_round INTEGER NOT NULL,
    draft_pick INTEGER NOT NULL,
    draft_cost INTEGER,
    draft_type TEXT NOT NULL,
    keeper_status BOOLEAN DEFAULT FALSE,
    drafted_datetime TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Current Player Spotlight Query Pattern

The existing query pattern in player-spotlight.js focuses on daily_gkl_player_stats table. We'll need to join with draft_results on player_id and filter by season.

---

**End of PRD**