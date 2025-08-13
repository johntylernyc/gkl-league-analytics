# API Endpoints Documentation
*Last Updated: August 13, 2025*

## Overview
The GKL Fantasy API is deployed on Cloudflare Workers at:
- **Production**: `https://gkl-fantasy-api.services-403.workers.dev`
- **Frontend**: `https://goldenknightlounge.com`

The API uses `index-with-db.js` as the main entry point (NOT the modular `index.js`).

## Health & Status Endpoints

### GET /health
Returns API health status and environment information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-13T17:00:00.000Z",
  "environment": "production",
  "database": "connected"
}
```

## Lineup Endpoints

### GET /lineups/dates
Returns list of dates with available lineup data.

**Response:**
```json
["2025-08-13", "2025-08-12", "2025-08-11", ...]
```

### GET /lineups/teams
Returns list of teams in the league.

**Response:**
```json
[
  {
    "team_key": "458.l.6966.t.1",
    "team_name": "IWU Tang Clan"
  },
  ...
]
```

### GET /lineups/date/{date}
Returns all team lineups for a specific date.

**Parameters:**
- `date` (path): Date in YYYY-MM-DD format

**Response:**
```json
{
  "date": "2025-08-13",
  "teams": [
    {
      "team_key": "458.l.6966.t.1",
      "team_name": "IWU Tang Clan",
      "positions": [
        {
          "lineup_id": 67756,
          "yahoo_player_id": "64313",
          "player_name": "Nick Kurtz",
          "selected_position": "1B",
          "position_type": "B",
          "player_team": "ATH",
          ...
        }
      ]
    }
  ]
}
```

### GET /lineups/summary/{date}
Returns summary statistics for lineups on a specific date.

**Parameters:**
- `date` (path): Date in YYYY-MM-DD format

**Response:**
```json
{
  "teams": 18,
  "unique_players": 436,
  "benched": 87,
  "injured": 63
}
```

### GET /lineups
⚠️ **Currently returns empty placeholder data**

## Transaction Endpoints

### GET /transactions
Returns paginated list of transactions.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (max: 100, default: 20)
- `search` (optional): Search term for player names
- `team_key` (optional): Filter by team
- `type` (optional): Filter by transaction type
- `start_date` (optional): Start date filter
- `end_date` (optional): End date filter

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 835,
    "totalPages": 42
  }
}
```

### GET /transactions/filters
Returns available filter options for transactions.

**Response:**
```json
{
  "teams": [...],
  "types": ["add/drop", "trade"],
  "dateRange": {
    "min_date": "2025-03-20",
    "max_date": "2025-08-13"
  }
}
```

### GET /transactions/stats
Returns transaction statistics and analytics.

**Response:**
```json
{
  "overview": {
    "total_transactions": 835,
    "total_teams": 18,
    "unique_players": 234
  },
  "managerStats": [...],
  "recentActivity": [...],
  "mostDroppedPlayer": null
}
```

⚠️ **Known Issue**: Currently returns mostly empty data due to query issues

## Player Endpoints

### GET /players
### GET /players/search
Returns list of players with optional search.

**Query Parameters:**
- `q` (optional): Search query
- `limit` (optional): Results limit

### GET /player-search/positions
Returns list of all player positions.

**Response:**
```json
["C", "1B", "2B", "3B", "SS", "OF", "DH", "SP", "RP"]
```

### GET /player-search/teams
Returns list of MLB teams.

### GET /player-search/gkl-teams
Returns list of fantasy teams in the league.

### GET /player-search/search
Advanced player search with filters.

**Query Parameters:**
- `query`: Search term
- `position`: Position filter
- `team`: Team filter
- `gklTeam`: Fantasy team filter

## Debug Endpoints (Development Only)

### GET /debug/player-stats
Returns sample player statistics data for testing.

### GET /debug/join-test
Tests database join operations.

### GET /debug/tables
Lists all tables in the D1 database.

## Missing/Broken Endpoints

The following endpoints are defined in the modular `index.js` but NOT in the active `index-with-db.js`:
- `/lineups/player/{playerId}` - Player history
- `/lineups/search` - Player search in lineups
- `/players/{playerId}` - Individual player details
- `/players/{playerId}/stats` - Player statistics
- `/spotlight/*` - Player spotlight features

## CORS Configuration

All endpoints include CORS headers:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

## Error Responses

Standard error response format:
```json
{
  "error": "Error Type",
  "message": "Detailed error message"
}
```

Common HTTP status codes:
- `200` - Success
- `404` - Not Found
- `500` - Internal Server Error (often D1 database errors)

## Known Issues

1. **Transaction Stats Empty**: The `/transactions/stats` endpoint returns empty data due to query aggregation issues
2. **Missing Endpoints**: Many endpoints from the modular system are not available
3. **Column Name Errors**: Some endpoints fail with "no such column" errors when column names don't match
4. **Teams Table Missing**: Endpoints that JOIN with `teams` table fail
5. **Empty Placeholders**: Some endpoints return hardcoded empty responses

## Frontend API Usage

The frontend (`goldenknightlounge.com`) primarily uses:
- `/lineups/dates` - Get available dates
- `/lineups/teams` - Get team list
- `/lineups/date/{date}` - Get daily lineups
- `/lineups/summary/{date}` - Get lineup summary
- `/transactions` - Get transactions list
- `/transactions/stats` - Get transaction statistics (currently broken)