# Data Pipeline Architecture

## Overview

The GKL League Analytics data pipeline is a comprehensive system for collecting, processing, and storing Yahoo Fantasy Baseball league data. The pipeline is designed for reliability, data quality, and performance optimization.

## Core Components

### 1. Authentication System (`auth/`)

The authentication layer manages OAuth2 token lifecycle for Yahoo Fantasy Sports API access.

**Key Components:**
- **Token Manager**: Handles automatic token refresh (tokens expire hourly)
- **Configuration**: Secure credential storage using environment variables
- **Token Persistence**: JSON-based token storage with automatic refresh

**Authentication Flow:**
1. Initial authorization via OAuth2 consent flow
2. Exchange authorization code for access/refresh tokens
3. Automatic token refresh before expiration
4. Persistent token storage for session continuity

### 2. Data Collection Modules (`data_pipeline/`)

#### 2.1 Transaction Collection (`league_transactions/`)

Collects all league transactions including adds, drops, and trades through two specialized scripts.

**Core Scripts:**
- **`backfill_transactions.py`**: Bulk historical data collection
  - Parallel processing (up to 4 workers)
  - Multi-season support
  - Resume capability for interrupted jobs
  - Optimized for large date ranges
  
- **`update_transactions.py`**: Incremental daily updates
  - 7-day default lookback window
  - Automatic duplicate detection
  - Minimal output for automation
  - Multiple update modes (days back, since last, specific date)

- **`data_quality_check.py`**: Data validation module
  - Field completeness validation
  - Add/drop transaction pair verification
  - Human-readable quality reports

**Key Improvements (August 2025):**
- Fixed date accuracy using transaction timestamps (Yahoo API date parameter doesn't filter)
- Complete field extraction (player_position, player_team, all team keys)
- Proper add/drop handling (both movements captured)
- Consolidated from 10+ scripts to 2 clean implementations

**Data Flow:**
1. Query Yahoo API with date parameter
2. Parse XML and extract transaction timestamps
3. Filter transactions by actual timestamp date
4. Extract complete transaction data including both add/drop movements
5. Validate data quality before insertion
6. Store in database with duplicate detection

#### 2.2 Daily Lineups Collection (`daily_lineups/`)

Captures daily roster decisions for all teams through two specialized scripts.

**Core Scripts:**
- **`backfill_lineups.py`**: Bulk historical data collection
  - Parallel processing (up to 4 workers)
  - Multi-season support
  - Resume capability for interrupted jobs
  - Processes all teams for each date
  
- **`update_lineups.py`**: Incremental daily updates
  - 7-day default lookback window
  - Automatic duplicate detection
  - Minimal output for automation
  - Multiple update modes (days back, since last, specific date)

- **`data_quality_check.py`**: Data validation module
  - Position validation against allowed positions
  - Field completeness validation
  - Date range validation (no future dates)
  - Season coverage analysis

**Key Improvements (August 2025):**
- Fixed league key accuracy (458.l.6966 for 2025)
- Complete roster data extraction for all teams
- Consolidated from 6+ scripts to 2 clean implementations
- Standardized job logging and data quality validation

**Data Flow:**
1. Query Yahoo API for each team's roster on specified date
2. Parse XML to extract player positions and status
3. Validate data quality before insertion
4. Store in database with unique constraints
5. Handle 18 teams × ~25 players = ~450 records per day

#### 2.3 Draft Results Collection (`draft_results/`)

Captures annual draft data including picks, costs, and keeper designations.

**Core Scripts:**
- **`collector.py`**: Main collection module with CLI interface
  - Automatic draft type detection (snake vs auction)
  - Player name enrichment via batch API calls
  - Keeper detection for auction drafts (rounds 20-21)
  - D1 export using sync_to_production pattern
  - Command-line parameters for any league/season

**Key Design Decisions (August 2025):**
- **Manual Annual Process**: Run once per season after draft completes
- **No Automation**: Unlike transactions/lineups, drafts don't need daily updates
- **Manual Keeper Updates**: Keeper designation requires post-collection SQL
- **Test-First Approach**: Always test on league_analytics_test.db before production
- **Sync Pattern**: Uses established sync_to_production.py export methodology

**Data Flow:**
1. Query Yahoo API for league settings (draft type)
2. Fetch draft results with pick order
3. Enrich player data with names via batch API
4. Store in test database first for validation
5. Run on production database after verification
6. Export to D1 using collector's push_to_d1() method
7. Manually update keeper status via SQL

#### 2.4 Player Statistics Integration (`player_stats/`)

Integrates Yahoo player data with MLB statistics.

**Components:**
- **Player ID Mapper**: Links Yahoo IDs to MLB player IDs
- **PyBaseball Integration**: Fetches advanced MLB statistics
- **Data Validator**: Ensures data quality and consistency

**Data Sources:**
- Yahoo Fantasy player statistics
- MLB official statistics via PyBaseball
- Fangraphs advanced metrics
- Baseball Reference historical data

### 3. Shared Infrastructure (`data_pipeline/common/`)

#### Season Manager
Centralizes season and league key management across all modules.

**Capabilities:**
- Multi-season support (2008-2025)
- Dynamic league key resolution
- Season date boundary management
- Profile season detection

#### Configuration Management (`data_pipeline/config/`)
Provides environment-aware configuration for all components.

**Features:**
- Test/Production environment separation
- Database path resolution
- Table name management
- Environment variable integration

## Data Processing Pipeline

### Stage 1: Collection Scheduling

**Trigger Mechanisms:**
1. Manual execution for backfilling
2. Scheduled workers for incremental updates
3. GitHub Actions for automated daily refreshes

### Stage 2: API Interaction

**Request Management:**
- Rate limiting: 1 second delay between requests
- Concurrent workers: Maximum 2 parallel requests
- Retry logic: Exponential backoff for failures
- Timeout handling: 30-second request timeout

### Stage 3: Data Transformation

**Processing Steps:**
1. **XML Parsing**: Convert Yahoo API responses to structured data
2. **Data Enrichment**: Add metadata and computed fields
3. **Normalization**: Transform to database schema format
4. **Validation**: Ensure data integrity and completeness

### Stage 4: Storage Operations

**Database Operations:**
- Batch insertions for performance
- Transaction management for consistency
- Duplicate detection and handling
- Index optimization for query performance

## Data Synchronization

### Local to Production Flow

The pipeline follows a unidirectional flow from local collection to production deployment:

1. **Collection Phase**: Yahoo API → Python Pipeline → Local SQLite
2. **Export Phase**: SQLite → SQL export scripts → Incremental SQL files  
3. **Import Phase**: SQL files → Cloudflare D1 → Production API

### Foreign Key Dependency Management

**Critical**: Data must be imported in the correct order to satisfy foreign key constraints:

1. **job_log** entries (referenced by all data tables)
2. **transactions** (independent table)
3. **daily_lineups** (references job_log.job_id)
4. **daily_gkl_player_stats** (references job_log.job_id)
5. **draft_results** (references job_log.job_id)

The `sync_to_production.py` script automatically:
- Extracts all referenced job_ids from data exports
- Creates job_log export file with required entries
- Provides import commands in the correct order
- Uses INSERT OR IGNORE for job_logs to handle duplicates
- Uses REPLACE for data tables to handle updates

### Export Strategy

```python
# Export process handled by sync_to_production.py
1. Export recent transactions (2 days default)
2. Export recent lineups (7 days default)
3. Extract all job_ids referenced in exports
4. Export corresponding job_log entries
5. Generate import commands in dependency order

# Draft results use dedicated export in collector.py
1. Annual manual process (not automated)
2. Test on league_analytics_test.db first
3. Export draft data for specific league/season
4. Extract job_ids and export job_log entries
5. Generate D1 import commands to sql/incremental/
6. Manual execution following sync_to_production pattern
```

### Import Order Requirements

```bash
# MUST follow this order to avoid foreign key errors:
npx wrangler d1 execute gkl-fantasy --file=job_logs.sql --remote    # First
npx wrangler d1 execute gkl-fantasy --file=transactions.sql --remote # Second
npx wrangler d1 execute gkl-fantasy --file=lineups.sql --remote      # Third
```

## Job Management System

### Job Logging Architecture

Every data processing operation is tracked through a comprehensive job logging system.

**Job Lifecycle:**
1. **Job Creation**: Generate unique job ID with metadata
2. **Progress Tracking**: Update records processed/inserted
3. **Status Management**: Track running/completed/failed states
4. **Error Logging**: Capture and store failure details

**Job Record Structure:**
```
job_id: {type}_{environment}_{timestamp}_{uuid}
job_type: Classification of operation
environment: test/production
status: running/completed/failed
date_range: Data collection period
records_processed: Total records from source
records_inserted: Successfully stored records
error_message: Failure details if applicable
```

## Performance Optimizations

### API Optimization
- Concurrent request processing
- Connection pooling
- Response caching
- Batch date processing

### Database Optimization
- Prepared statement usage
- Bulk insert operations
- Index strategy for common queries
- WAL mode for concurrent access

### Memory Management
- Streaming XML parsing
- Chunked data processing
- Garbage collection optimization
- Limited in-memory caching

## Error Handling

### Failure Recovery
1. **Transient Failures**: Automatic retry with backoff
2. **API Errors**: Rate limit detection and adjustment
3. **Data Errors**: Validation and logging for review
4. **System Errors**: Graceful degradation and alerting

### Data Quality Assurance
- Input validation at collection
- Constraint checking before storage
- Duplicate detection algorithms
- Data completeness verification

## Monitoring and Observability

### Metrics Tracked
- API request counts and latency
- Data collection success rates
- Processing throughput
- Error rates by type

### Logging Strategy
- Structured logging with context
- Log levels for filtering
- Centralized log aggregation
- Retention policies

## Security Considerations

### Credential Management
- Environment variable storage
- No hardcoded credentials
- Token encryption at rest
- Secure transmission protocols

### Access Control
- OAuth2 scope limitations
- Read-only API access
- Database user permissions
- File system restrictions

## Scalability Design

### Horizontal Scaling
- Stateless worker processes
- Distributed job processing
- Load balancing capability
- Queue-based architecture ready

### Vertical Scaling
- Configurable worker counts
- Adjustable batch sizes
- Memory allocation tuning
- Database connection pooling

## Future Enhancements

### Planned Improvements
1. Real-time data streaming
2. Machine learning integration
3. Advanced analytics pipeline
4. Multi-league support
5. Historical data archival

### Architecture Evolution
- Microservices migration path
- Cloud-native deployment options
- Event-driven processing
- GraphQL API layer