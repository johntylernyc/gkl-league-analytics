# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for Yahoo Fantasy Sports league analytics, specifically focused on fetching and analyzing fantasy baseball league data from Yahoo Fantasy Baseball leagues. The project uses OAuth2 authentication to access Yahoo's Fantasy Sports API and processes transaction data (adds, drops, trades), matchup data (head-to-head matchups, category scores, total wins and losses), standings data, roster data (which players started in which positions, bench players, etc.) and more details for historical analysis. It combines Yahoo Fantasy Baseball data from the league with MLB data using the pybaseball Python library to gather additional insights and details from Fangraphs, Baseball Reference, Statcast, and other MLB data sources.

Additionally, this project has a user interface written in Node.js to access these insights and explore league data alongside MLB data.

**Current Implementation Status**: The codebase contains a production-ready Yahoo Fantasy API integration for transaction data collection with optimized database schema, comprehensive job logging, and performance-tuned queries. The matchup data, standings data, roster data, pybaseball integration, and Node.js UI components are planned features not yet implemented.

## Common Development Commands

This is a Python project without standard build tools. Run Python scripts directly:

```bash
# Initialize OAuth tokens (first time setup)
python helpers/generate_auth_url.py  # Generates auth URL for user consent
python helpers/initiailize_tokens.py  # Exchanges auth code for tokens

# Test authentication and fetch stat mappings
python helpers/test_auth.py

# Main data collection script
python league_transactions/backfill_transactions_optimized.py

# Test data collection (July 2025)
python league_transactions/run_july_backfill.py
```

**Future Commands** (when implemented):
```bash
# Install Python dependencies
pip install -r requirements.txt  # Will include pybaseball and other MLB data libraries

# Install Node.js UI dependencies
cd ui && npm install

# Start Node.js development server
cd ui && npm run dev

# Run data collection for all data types
python scripts/collect_all_data.py
```

## Project Architecture

### Current Directory Structure
- `auth/` - OAuth2 authentication and configuration utilities
- `league_transactions/` - Transaction data collection scripts (production-ready)
- `database/` - SQLite database with optimized schema

### Planned Directory Structure
- `helpers/` - Authentication and configuration utilities
- `data_collection/` - Scripts for all Yahoo Fantasy data types (transactions, matchups, standings, rosters)
- `mlb_integration/` - pybaseball integration for MLB data enrichment
- `analysis/` - Data analysis and insight generation scripts
- `ui/` - Node.js web interface
- `data/` - Output directory for CSV files and processed data

### Core Components

**Authentication Flow** (`auth/`):
- `config.py` - Yahoo API credentials and configuration constants
- `generate_auth_url.py` - Generates OAuth2 authorization URL for user consent
- `initialize_tokens.py` - Exchanges authorization code for access/refresh tokens
- `test_auth.py` - Tests authentication and fetches stat category mappings

**Current Data Collection** (`league_transactions/`):
- `backfill_transactions_optimized.py` - Production transaction data collection with job logging
- `run_july_backfill.py` - Test validation script for data collection verification
- `archive/` - Historical development and debug scripts

**Planned Data Collection Components**:
- Matchup data collection - Head-to-head weekly matchups with category scores
- Standings data collection - Season-long team standings and records
- Roster data collection - Daily lineup/bench decisions and player ownership
- pybaseball integration - MLB stats, Fangraphs data, Statcast metrics

### Key Features

**Implemented**:
1. **OAuth2 Token Management**: Automatic token refresh (hourly expiration)
2. **Comprehensive Job Logging**: Standardized job tracking for all data processing
3. **Optimized Database Schema**: Normalized structure with performance indexes
4. **Multi-Environment Support**: Test/production data separation
5. **Rate Limiting**: 1-second delays between API calls with concurrent processing
6. **Error Handling**: Robust logging with job status tracking
7. **Data Quality**: Actual transaction timestamps and direct team information extraction

**Planned**:
1. **Comprehensive Data Collection**: All Yahoo Fantasy data types
2. **MLB Data Integration**: pybaseball library for external baseball data
3. **Web UI**: Node.js interface for data exploration
4. **Advanced Analytics**: Player performance correlation with real MLB stats
5. **Historical Trend Analysis**: Multi-season insights and patterns

### Yahoo Fantasy Sports API Integration

**Base URL**: `https://fantasysports.yahooapis.com/fantasy/v2`

**Current Endpoints**:
- Transactions: `/league/{league_key}/transactions;types=add,drop,trade;date={date}`
- Stat Categories: `/game/{game_key}/stat_categories`

**Planned Endpoints**:
- Matchups: `/league/{league_key}/scoreboard;week={week}`
- Standings: `/league/{league_key}/standings`
- Rosters: `/team/{team_key}/roster;date={date}`
- Player Stats: `/league/{league_key}/players;player_keys={player_keys}/stats`

### Data Flow Architecture

**Current Flow**:
1. OAuth authentication and token management
2. Date-by-date transaction data collection
3. XML parsing and CSV output

**Planned Enhanced Flow**:
1. OAuth authentication and token management
2. Multi-threaded data collection across all data types
3. Real-time MLB data enrichment via pybaseball
4. Normalized database storage (SQLite/PostgreSQL)
5. REST API for web UI consumption
6. Interactive web dashboard for analysis

### Job Logging Architecture

**CRITICAL: ALL data processing scripts MUST implement standardized job logging**

**Job Logging Requirements**:
```python
# Required pattern for ALL data processing scripts
from backfill_transactions_optimized import start_job_log, update_job_log

# 1. Start job logging
job_id = start_job_log(
    job_type="your_job_type",          # Descriptive job identifier
    environment="test",                # 'test' or 'production'  
    date_range_start="2025-07-01",     # Data collection start
    date_range_end="2025-07-31",       # Data collection end
    league_key="mlb.l.6966",           # League identifier
    metadata="additional context"       # Optional metadata
)

# 2. Include job_id in ALL data records
your_data_processing(job_id=job_id)

# 3. Update job status on completion/failure
update_job_log(job_id, 'completed', records_processed=N, records_inserted=M)
# OR
update_job_log(job_id, 'failed', error_message=str(error))
```

**Database Schema - job_log table**:
- `job_id`: Unique identifier (format: `{type}_{env}_{timestamp}_{uuid}`)
- `job_type`: Type of processing (e.g., "transaction_collection")
- `environment`: "test" or "production"
- `status`: "running", "completed", "failed"
- `records_processed`: Total records collected from API
- `records_inserted`: Records successfully stored in database
- `date_range_start/end`: Data collection date range
- `error_message`: Failure details for debugging

### Configuration Management

**League Configuration**:
- `LEAGUE_KEYS`: Season-to-league-key mapping
- `SEASON_DATES`: Season start/end dates for data collection
- Currently focused on 2025 season

**API Configuration**:
- Yahoo OAuth2 credentials in `config.py`
- Rate limiting and retry logic (1 req/sec, 2 concurrent workers)
- Environment-based table separation (test/production)

## Project Management

See `TODO.md` in the project root for current development status, future feature planning, and task management. This file serves as the central project management hub for tracking all development work, technical debt, and enhancement requests.

### Development Notes

- **Dependencies**: Currently minimal (requests, standard library). Will expand to include pybaseball, pandas, numpy for MLB integration
- **Data Storage**: SQLite database with optimized schema and 12+ performance indexes per table
- **API Limits**: Yahoo API rate limits; 1-second delays with 2 concurrent workers for optimal throughput
- **Token Management**: Tokens expire hourly and auto-refresh seamlessly
- **Database Schema**: Simplified normalized structure with direct team storage (no complex lookup tables)
- **Job Logging**: Comprehensive job tracking with data lineage for all processing operations
- **Data Quality**: Actual transaction timestamps extracted from API (not request dates)
- **Error Handling**: Robust logging with job status tracking and recovery mechanisms