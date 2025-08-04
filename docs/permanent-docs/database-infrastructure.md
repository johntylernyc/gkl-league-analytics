# Database Infrastructure

## Overview

The GKL League Analytics database infrastructure is built on SQLite, deployed globally through Cloudflare D1 for production and local SQLite for development. The system features a normalized relational schema optimized for fantasy baseball analytics with comprehensive indexing, job tracking, and data integrity constraints.

## Database Architecture

### Technology Stack

#### Production Environment
- **Database**: Cloudflare D1 (Distributed SQLite)
- **Replication**: Automatic global distribution
- **Backup**: Daily automated exports
- **Access**: Wrangler CLI and SQL console

#### Development Environment
- **Database**: Local SQLite 3.x
- **File**: `database/league_analytics.db`
- **Testing**: `database/league_analytics_test.db`
- **Management**: Python sqlite3, DB Browser

### Database Schema

#### Core Tables Structure

##### 1. Players Table
```sql
CREATE TABLE players (
    yahoo_player_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    positions TEXT,
    team_abbr TEXT,
    player_image_url TEXT,
    mlb_player_id INTEGER,
    espn_player_id INTEGER,
    fangraphs_id TEXT,
    bbref_id TEXT,
    statcast_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_players_full_name ON players(full_name);
CREATE INDEX idx_players_mlb_id ON players(mlb_player_id);
CREATE INDEX idx_players_team ON players(team_abbr);
```

**Purpose**: Master player registry linking Yahoo IDs to external data sources

**Key Features:**
- Primary key on Yahoo player ID
- Multiple external ID mappings
- Position eligibility tracking
- Audit timestamps

##### 2. Transactions Table
```sql
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_key TEXT UNIQUE NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    timestamp INTEGER NOT NULL,
    week INTEGER,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    manager_name TEXT,
    player_id INTEGER,
    player_name TEXT,
    player_team TEXT,
    player_position TEXT,
    transaction_detail TEXT,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id),
    CHECK (transaction_type IN ('add', 'drop', 'trade', 'commish'))
);

-- Indexes
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_player ON transactions(player_id);
CREATE INDEX idx_transactions_team ON transactions(team_key);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_job ON transactions(job_id);
```

**Purpose**: Complete transaction history for the league

**Transaction Types:**
- `add`: Waiver wire additions
- `drop`: Player drops
- `trade`: Trades between teams
- `commish`: Commissioner moves

##### 3. Daily Lineups Table
```sql
CREATE TABLE daily_lineups (
    lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date DATE NOT NULL,
    team_key TEXT NOT NULL,
    team_name TEXT NOT NULL,
    manager_name TEXT,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    player_team TEXT,
    position_assigned TEXT NOT NULL,
    is_starting BOOLEAN NOT NULL,
    is_injured BOOLEAN DEFAULT FALSE,
    injury_status TEXT,
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id),
    UNIQUE(game_date, team_key, player_id)
);

-- Indexes
CREATE INDEX idx_lineups_date ON daily_lineups(game_date);
CREATE INDEX idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX idx_lineups_player ON daily_lineups(player_id);
CREATE INDEX idx_lineups_starting ON daily_lineups(is_starting);
CREATE INDEX idx_lineups_job ON daily_lineups(job_id);
```

**Purpose**: Daily roster decisions and lineup tracking

**Key Features:**
- Unique constraint prevents duplicate entries
- Starting vs. bench tracking
- Injury status monitoring
- Position assignment history

##### 4. Daily Player Stats Table
```sql
CREATE TABLE daily_gkl_player_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date DATE NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    team_abbr TEXT,
    -- Batting Statistics
    games_played INTEGER DEFAULT 0,
    at_bats INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    hits INTEGER DEFAULT 0,
    doubles INTEGER DEFAULT 0,
    triples INTEGER DEFAULT 0,
    home_runs INTEGER DEFAULT 0,
    rbi INTEGER DEFAULT 0,
    stolen_bases INTEGER DEFAULT 0,
    caught_stealing INTEGER DEFAULT 0,
    walks INTEGER DEFAULT 0,
    strikeouts INTEGER DEFAULT 0,
    batting_average REAL,
    on_base_percentage REAL,
    slugging_percentage REAL,
    ops REAL,
    -- Pitching Statistics
    games_pitched INTEGER DEFAULT 0,
    games_started INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    holds INTEGER DEFAULT 0,
    innings_pitched REAL DEFAULT 0,
    hits_allowed INTEGER DEFAULT 0,
    runs_allowed INTEGER DEFAULT 0,
    earned_runs INTEGER DEFAULT 0,
    home_runs_allowed INTEGER DEFAULT 0,
    walks_allowed INTEGER DEFAULT 0,
    strikeouts_pitched INTEGER DEFAULT 0,
    era REAL,
    whip REAL,
    -- Metadata
    data_source TEXT DEFAULT 'yahoo',
    job_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id),
    UNIQUE(game_date, player_id, data_source)
);

-- Indexes
CREATE INDEX idx_stats_date ON daily_gkl_player_stats(game_date);
CREATE INDEX idx_stats_player ON daily_gkl_player_stats(player_id);
CREATE INDEX idx_stats_source ON daily_gkl_player_stats(data_source);
```

**Purpose**: Comprehensive daily performance statistics

##### 5. Job Log Table
```sql
CREATE TABLE job_log (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    environment TEXT NOT NULL CHECK(environment IN ('test', 'production')),
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    date_range_start DATE,
    date_range_end DATE,
    league_key TEXT,
    error_message TEXT,
    metadata TEXT
);

-- Indexes
CREATE INDEX idx_job_type ON job_log(job_type);
CREATE INDEX idx_job_status ON job_log(status);
CREATE INDEX idx_job_environment ON job_log(environment);
CREATE INDEX idx_job_started ON job_log(started_at);
```

**Purpose**: Comprehensive audit trail for all data operations

**Job ID Format**: `{type}_{environment}_{timestamp}_{uuid}`

### Data Integrity

#### Constraints

##### Foreign Key Relationships

**Critical Dependencies:**
```sql
-- All data tables reference job_log for audit trail
transactions.job_id → job_log.job_id
daily_lineups.job_id → job_log.job_id  
daily_gkl_player_stats.job_id → job_log.job_id

-- Transaction to Player (optional, not enforced in D1)
FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id)

-- Lineup to Player (optional, not enforced in D1)
FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id)

-- Stats to Player (optional, not enforced in D1)
FOREIGN KEY (player_id) REFERENCES players(yahoo_player_id)
```

**Import Order for Foreign Key Compliance:**
1. `job_log` - Must be imported first (referenced by all data tables)
2. `players` - If enforcing player foreign keys
3. `transactions` - Can be imported after job_log
4. `daily_lineups` - Must be imported after job_log
5. `daily_gkl_player_stats` - Must be imported after job_log

##### Unique Constraints
```sql
-- Prevent duplicate transactions
UNIQUE(transaction_key)

-- Prevent duplicate lineups
UNIQUE(game_date, team_key, player_id)

-- Prevent duplicate stats
UNIQUE(game_date, player_id, data_source)
```

##### Check Constraints
```sql
-- Valid transaction types
CHECK (transaction_type IN ('add', 'drop', 'trade', 'commish'))

-- Valid environments
CHECK(environment IN ('test', 'production'))

-- Valid job status
CHECK(status IN ('running', 'completed', 'failed'))
```

### Indexing Strategy

#### Primary Indexes
All primary keys are automatically indexed:
- `players.yahoo_player_id`
- `transactions.transaction_id`
- `daily_lineups.lineup_id`
- `daily_gkl_player_stats.stat_id`
- `job_log.job_id`

#### Query Optimization Indexes

##### Date-based Queries
```sql
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_lineups_date ON daily_lineups(game_date);
CREATE INDEX idx_stats_date ON daily_gkl_player_stats(game_date);
```

##### Player Lookups
```sql
CREATE INDEX idx_transactions_player ON transactions(player_id);
CREATE INDEX idx_lineups_player ON daily_lineups(player_id);
CREATE INDEX idx_stats_player ON daily_gkl_player_stats(player_id);
CREATE INDEX idx_players_full_name ON players(full_name);
```

##### Team Queries
```sql
CREATE INDEX idx_transactions_team ON transactions(team_key);
CREATE INDEX idx_lineups_team ON daily_lineups(team_key);
CREATE INDEX idx_players_team ON players(team_abbr);
```

##### Job Tracking
```sql
CREATE INDEX idx_transactions_job ON transactions(job_id);
CREATE INDEX idx_lineups_job ON daily_lineups(job_id);
CREATE INDEX idx_job_type ON job_log(job_type);
CREATE INDEX idx_job_status ON job_log(status);
```

## Database Operations

### Connection Management

#### Python Connection Pattern
```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

#### Cloudflare Worker Connection
```javascript
export default {
  async fetch(request, env) {
    const db = env.DB;
    const stmt = db.prepare('SELECT * FROM players WHERE yahoo_player_id = ?');
    const result = await stmt.bind(playerId).first();
    return Response.json(result);
  }
}
```

#### D1 Direct HTTP API Connection (GitHub Actions)
```python
from data_pipeline.common.d1_connection import D1Connection

# Initialize with environment variables
d1 = D1Connection()

# Execute query with automatic retry and error handling
result = d1.execute("SELECT COUNT(*) FROM job_log WHERE status = ?", ["completed"])

# Batch operations (implemented as individual queries)
statements = [
    ("INSERT INTO job_log (job_id, job_type) VALUES (?, ?)", ["job1", "test"]),
    ("INSERT INTO transactions (transaction_key, job_id) VALUES (?, ?)", ["tx1", "job1"])
]
results = d1.execute_batch(statements)
```

**D1 Connection Features:**
- **Automatic Retry**: Exponential backoff for transient failures
- **Response Parsing**: Handles D1 API result format (list → meta extraction)
- **Batch Workaround**: Individual query execution when batch endpoint fails
- **Foreign Key Management**: Ensures job_log entries exist before data insertion
- **Debug Logging**: Comprehensive request/response logging

### Transaction Management

#### ACID Compliance
- **Atomicity**: All operations in transaction succeed or fail together
- **Consistency**: Data integrity constraints enforced
- **Isolation**: Read/write conflicts managed
- **Durability**: Committed data persists

#### Transaction Patterns
```python
# Batch insert with transaction
with get_db_connection(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute('BEGIN TRANSACTION')
    try:
        for record in records:
            cursor.execute(insert_query, record)
        cursor.execute('COMMIT')
    except Exception:
        cursor.execute('ROLLBACK')
        raise
```

### Query Optimization

#### Query Planning
```sql
-- Analyze query plan
EXPLAIN QUERY PLAN
SELECT t.*, p.full_name
FROM transactions t
JOIN players p ON t.player_id = p.yahoo_player_id
WHERE t.transaction_date >= '2025-01-01'
ORDER BY t.transaction_date DESC;
```

#### Performance Tips
1. Use prepared statements
2. Leverage indexes effectively
3. Avoid SELECT *
4. Use LIMIT for pagination
5. Batch operations when possible

### Data Migration

#### Schema Migrations
```sql
-- Migration versioning
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Apply migrations
BEGIN TRANSACTION;
-- Migration SQL here
INSERT INTO schema_version (version) VALUES (1);
COMMIT;
```

#### Data Import/Export

##### Export to SQL
```bash
# Export full database
sqlite3 league_analytics.db .dump > backup.sql

# Export specific table
sqlite3 league_analytics.db ".dump transactions" > transactions.sql
```

##### Import to D1
```bash
# Import to Cloudflare D1
wrangler d1 execute gkl-fantasy --file backup.sql
```

## Performance Optimization

### Query Performance

#### Optimization Techniques
1. **Index Usage**: Ensure queries use appropriate indexes
2. **Query Rewriting**: Optimize complex queries
3. **Denormalization**: Strategic denormalization for read performance
4. **Caching**: Implement application-level caching
5. **Partitioning**: Date-based partitioning for large tables

#### Performance Monitoring
```sql
-- Analyze table statistics
ANALYZE;

-- Check index usage
SELECT * FROM sqlite_stat1;

-- Monitor slow queries (application level)
```

### Database Tuning

#### SQLite Pragmas
```sql
-- Performance settings
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;  -- 256MB memory map
```

#### Connection Pool Settings
```python
# Connection pool configuration
pool_config = {
    'max_connections': 10,
    'min_connections': 2,
    'connection_timeout': 30,
    'idle_timeout': 300
}
```

## Backup and Recovery

### Backup Strategy

#### Automated Backups
```python
import shutil
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    source = 'database/league_analytics.db'
    destination = f'database/backups/league_analytics_backup_{timestamp}.db'
    shutil.copy2(source, destination)
```

#### D1 Backups
```bash
# Export D1 database
wrangler d1 export gkl-fantasy --output backup.sql

# Create point-in-time backup
wrangler d1 backup create gkl-fantasy
```

### Recovery Procedures

#### Local Recovery
```bash
# Restore from backup
cp database/backups/league_analytics_backup_20250804.db database/league_analytics.db
```

#### D1 Recovery
```bash
# Restore from backup
wrangler d1 execute gkl-fantasy --file backup.sql

# Restore to specific point in time
wrangler d1 backup restore gkl-fantasy --backup-id <id>
```

## Security

### Access Control

#### Database Permissions
- Read-only access for API queries
- Write access limited to data pipeline
- Admin access for migrations only

#### SQL Injection Prevention
```python
# Use parameterized queries
cursor.execute(
    "SELECT * FROM players WHERE yahoo_player_id = ?",
    (player_id,)  # Safe parameter binding
)

# Never use string formatting
# BAD: f"SELECT * FROM players WHERE id = {user_input}"
```

### Data Privacy

#### Sensitive Data Handling
- No password storage
- OAuth tokens encrypted
- Personal information minimized
- Audit logs for compliance

## Monitoring

### Health Checks

#### Database Health
```python
def check_database_health():
    checks = {
        'connection': test_connection(),
        'tables': verify_tables_exist(),
        'indexes': verify_indexes(),
        'size': check_database_size(),
        'integrity': run_integrity_check()
    }
    return all(checks.values())
```

#### Performance Metrics
- Query execution time
- Connection pool usage
- Cache hit rates
- Database size growth
- Transaction throughput

### Alerting

#### Alert Conditions
1. Database size > 90% of limit
2. Query time > 1 second
3. Connection failures
4. Integrity check failures
5. Backup failures

## Future Enhancements

### Planned Improvements

#### Short-term
1. Implement read replicas
2. Add query result caching
3. Optimize slow queries
4. Enhance monitoring dashboard
5. Automate maintenance tasks

#### Long-term
1. Migrate to PostgreSQL option
2. Implement sharding strategy
3. Add time-series optimizations
4. GraphQL query layer
5. Real-time change data capture

### Scalability Roadmap

#### Vertical Scaling
- Increase cache size
- Optimize indexes
- Query optimization
- Connection pool tuning

#### Horizontal Scaling
- Read replica distribution
- Database sharding
- Caching layer expansion
- Load balancing

## Best Practices

### Development Guidelines
1. Always use transactions for multi-statement operations
2. Test migrations in development first
3. Maintain referential integrity
4. Document schema changes
5. Monitor query performance

### Operational Guidelines
1. Regular backup verification
2. Periodic index optimization
3. Monitor database growth
4. Plan capacity ahead
5. Document recovery procedures

## Conclusion

The database infrastructure provides a robust, scalable foundation for the GKL League Analytics platform. Through careful schema design, comprehensive indexing, and operational best practices, the system delivers high performance while maintaining data integrity and reliability. The architecture supports future growth while remaining simple to manage and maintain.