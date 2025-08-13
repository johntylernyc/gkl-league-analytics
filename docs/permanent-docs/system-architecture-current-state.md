# System Architecture - Current State
*Last Updated: August 13, 2025*

## Executive Summary

The GKL League Analytics platform is a production fantasy baseball analytics system with significant architectural complexity and known issues. This document provides an accurate snapshot of the current system state, including all recent changes and problems.

## System Components

### 1. Data Collection Layer (Python)

**Location**: `data_pipeline/`

**Components**:
- **Transaction Collection** (`league_transactions/`)
  - `backfill_transactions.py` - Bulk historical collection
  - `update_transactions.py` - Incremental updates
  - Uses `yahoo_player_id` (not `player_id`)
  
- **Lineup Collection** (`daily_lineups/`)
  - `backfill_lineups.py` - Bulk historical collection
  - `update_lineups.py` - Incremental updates
  - Column: `selected_position` (not `position`)
  
- **Player Stats** (`player_stats/`)
  - `comprehensive_collector.py` - Main collection engine
  - `build_player_mappings_d1.py` - ID mapping builder
  - **Known Bug**: ID columns sometimes store literal strings "yahoo_player_id" instead of values
  - **Data Type Issue**: fangraphs_id stored as float, needs string conversion

- **Draft Results** (`draft_results/`)
  - One-time annual collection
  - Manual process after draft completion

### 2. Database Layer

**Two Environments**:
1. **Local SQLite** (`database/league_analytics.db`)
   - Development and data collection
   - May have inconsistent column names
   
2. **Cloudflare D1** (`gkl-fantasy`)
   - Production database
   - ID: `f541fa7b-9356-4a96-a24e-3b7cd06e9cfa`
   - Column migrations applied but inconsistent

**Key Schema Changes**:
- `player_id` → `yahoo_player_id` (mostly complete)
- `position` → `selected_position` in lineups
- `teams` table referenced but doesn't exist
- `mlb_id` and `mlb_player_id` both exist (duplicate)

### 3. API Layer (Cloudflare Workers)

**Deployment**: `https://gkl-fantasy-api.services-403.workers.dev`

**Configuration Issues**:
- Uses `index-with-db.js` (monolithic, 1700+ lines)
- NOT using modular `index.js` with route files
- Many endpoints missing or returning empty data
- Hardcoded placeholders in some endpoints

**Working Endpoints**:
- `/health` ✅
- `/lineups/dates` ✅
- `/lineups/teams` ✅
- `/lineups/date/{date}` ✅ (recently fixed)
- `/lineups/summary/{date}` ✅
- `/transactions` ✅ (paginated list)

**Broken/Empty Endpoints**:
- `/transactions/stats` ❌ (returns empty)
- `/lineups` ❌ (hardcoded empty response)
- Most player endpoints ❌ (not implemented)

### 4. Frontend (React)

**Deployment**: `https://goldenknightlounge.com` (Cloudflare Pages)

**Issues**:
- Getting 500 errors from some API endpoints
- Transaction summary cards not showing (stats endpoint broken)
- Some lineup features working after recent fixes
- CORS errors from Cloudflare Insights (can be ignored)

### 5. Automation (GitHub Actions)

**Schedule**: 3x daily (6 AM, 1 PM, 10 PM ET)

**Workflow**: `.github/workflows/data-refresh.yml`

**Process**:
1. Runs Python update scripts
2. Writes directly to D1 using API
3. Handles job_log dependencies

**Recent Issues**:
- Player stats storing wrong values in ID columns
- Foreign key constraint failures

## Data Flow Architecture

```
Current (Broken in places):
Yahoo API → Python Scripts → SQLite → (Manual/Auto) → D1 → Workers API → Frontend
              ↓                                         ↑
         [ID mapping issues]                    [Column name mismatches]
```

## Critical Problems Summary

### 1. Database Schema Inconsistencies
- Column names differ between local and production
- Missing tables referenced in queries (`teams`)
- Duplicate columns with different names
- Foreign key constraints not always enforced

### 2. API Implementation Issues
- Using old monolithic file instead of modular system
- Many endpoints not implemented or broken
- Hardcoded empty responses in places
- Column name mismatches causing 500 errors

### 3. Data Pipeline Problems
- Player ID columns storing literal strings
- Data type conversions needed (float → string)
- Mapping tables incomplete (yahoo_player_id often NULL)

### 4. Deployment Configuration
- `wrangler.toml` points to `index-with-db.js`
- Modular routes in `src/routes/` not being used
- Multiple environment configs causing confusion

## File Structure Reality

```
cloudflare-production/
├── src/
│   ├── index.js                 # Modular router (NOT USED)
│   ├── index-with-db.js         # Monolithic handler (ACTIVE)
│   ├── routes/                  # Route modules (NOT USED)
│   │   ├── transactions.js
│   │   ├── lineups.js
│   │   └── players.js
│   └── db/
│       └── d1-client.js         # Database wrapper
├── wrangler.toml                 # Points to index-with-db.js
└── sql/
    ├── migrations/               # Schema changes
    └── incremental/              # Data exports
```

## Configuration Files

### wrangler.toml (Current)
```toml
name = "gkl-fantasy-api"
main = "src/index-with-db.js"  # NOT using modular system
compatibility_date = "2024-01-02"

[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "f541fa7b-9356-4a96-a24e-3b7cd06e9cfa"

[[kv_namespaces]]
binding = "CACHE"
id = "27f3df3708b84a6f8d57a0753057ef9f"
```

## Environment Variables

**Required for Data Pipeline**:
```
YAHOO_CLIENT_ID
YAHOO_CLIENT_SECRET
YAHOO_AUTHORIZATION_CODE
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
D1_DATABASE_ID
```

## Recent Changes Log

### August 13, 2025
- Fixed `player_id` → `yahoo_player_id` in lineup summary
- Added missing `/lineups/date/{date}` endpoint
- Fixed player stats ID column literal string bug
- Fixed fangraphs_id data type issue
- Discovered `index-with-db.js` is active file

### August 7, 2025
- Player stats pipeline deployment
- Column rename migrations
- GitHub Actions D1 integration

### August 5, 2025
- Initial production deployment
- Transaction and lineup collection setup

## Recommended Immediate Actions

1. **Standardize Column Names**: Complete migration to yahoo_player_id everywhere
2. **Fix API Endpoints**: Either fix index-with-db.js or switch to modular system
3. **Resolve Schema Issues**: Create missing tables or update queries
4. **Fix Data Pipeline**: Ensure ID columns get actual values, not strings
5. **Update Documentation**: Keep this document current with changes

## System Health Assessment

| Component | Status | Issues |
|-----------|--------|--------|
| Data Collection | ⚠️ Partial | ID mapping problems |
| Database Schema | ❌ Inconsistent | Column name mismatches |
| API Layer | ⚠️ Degraded | Many broken endpoints |
| Frontend | ⚠️ Partial | Some features not working |
| Automation | ✅ Running | Data quality issues |

## Next Steps

1. Complete thorough API endpoint testing
2. Standardize database schema across environments
3. Fix or replace index-with-db.js
4. Implement comprehensive error logging
5. Create data quality validation scripts