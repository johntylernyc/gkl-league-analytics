# Database Stability Improvements - Deployment Guide

## Overview

This guide covers the deployment of SQLite database stability improvements designed to eliminate "database is locked" errors and improve performance.

## Current Implementation Status

### ✅ Fully Implemented in Core Module

**`league_transactions/backfill_transactions_optimized.py`**:
- Feature flag integration
- SQLite version checking
- WAL compatibility validation  
- PRAGMA optimizations (when enabled)
- Graceful shutdown handlers
- Backward compatible batch operations
- `--validate` option for testing

### ⚠️ Partial Implementation in Other Modules

**`daily_lineups/` module**:
- Uses direct `sqlite3.connect()` calls
- No feature flag integration yet
- Will benefit from system-wide PRAGMA settings

**`web-ui/backend/` module**:
- Node.js using `better-sqlite3` library
- Separate connection management
- May need independent configuration

## Feature Flags

All optimizations are **DISABLED by default** for safety. Enable gradually using:

```bash
# View current status
python database/manage_features.py --status

# Enable specific features
python database/manage_features.py --enable pragma_optimizations
python database/manage_features.py --enable explicit_transactions

# Apply predefined profiles
python database/manage_features.py --profile safe      # Basic optimizations only
python database/manage_features.py --profile balanced  # Recommended for production
python database/manage_features.py --profile performance  # Maximum performance
```

### Available Features

| Feature | Description | Risk Level |
|---------|-------------|------------|
| `pragma_optimizations` | Basic SQLite settings (timeout, cache) | Low |
| `wal_mode` | Write-Ahead Logging for concurrency | Medium |
| `explicit_transactions` | Explicit BEGIN/COMMIT/ROLLBACK | Low |
| `retry_logic` | Automatic retry on lock errors | Low |
| `connection_pooling` | Connection resource management | Medium |
| `aggressive_caching` | Large cache and memory mapping | Medium |
| `isolation_levels` | SERIALIZABLE for critical ops | Low |

## Deployment Steps

### Phase 1: Pre-Deployment Validation (Day 0)

```bash
# 1. Validate database compatibility
python league_transactions/backfill_transactions_optimized.py --validate

# 2. Run compatibility tests
python database/test_phase1_stability.py

# 3. Check current database health
python database/monitor_health.py --once

# 4. Backup database
cp database/league_analytics.db database/league_analytics.db.backup
```

### Phase 2: Gradual Feature Rollout (Days 1-14)

#### Days 1-2: Basic Optimizations
```bash
# Enable basic PRAGMA settings
python database/manage_features.py --enable pragma_optimizations

# Monitor for 48 hours
python database/monitor_health.py --interval 300 --duration 172800
```

#### Days 3-4: Transaction Management
```bash
# Enable explicit transactions
python database/manage_features.py --enable explicit_transactions

# Test with a small data collection
python league_transactions/backfill_transactions_optimized.py \
    --environment test \
    --start-date 2025-08-01 \
    --end-date 2025-08-03
```

#### Days 5-6: WAL Mode (if compatible)
```bash
# Check WAL compatibility first
python league_transactions/backfill_transactions_optimized.py --validate

# If compatible, enable WAL
python database/manage_features.py --enable wal_mode

# Monitor WAL file size
watch -n 60 "ls -lh database/*.db*"
```

#### Days 7-8: Retry Logic
```bash
# Enable automatic retries
python database/manage_features.py --enable retry_logic

# Check retry statistics
python -c "
from database.db_utils import get_lock_monitor
monitor = get_lock_monitor()
print(monitor.get_stats())
"
```

#### Days 9-14: Optional Advanced Features
```bash
# Only if needed for performance
python database/manage_features.py --enable connection_pooling
python database/manage_features.py --enable aggressive_caching
```

### Phase 3: Validation & Monitoring

```bash
# Continuous health monitoring
python database/monitor_health.py --interval 60 --save health_report.json

# Check for lock errors in logs
grep -i "database.*locked" fetch_transactions.log

# Verify performance improvements
python database/test_phase1_stability.py
```

## Emergency Procedures

### If Issues Occur

1. **Immediate Rollback**:
```bash
# Disable ALL optimizations instantly
python database/emergency_rollback.py

# Verify rollback successful
python database/emergency_rollback.py --verify
```

2. **Restore from Backup**:
```bash
# Stop all processes
# Then restore
cp database/league_analytics.db.backup database/league_analytics.db
```

3. **Check Status**:
```bash
python database/manage_features.py --status
python database/monitor_health.py --once
```

## Monitoring Commands

```bash
# Real-time monitoring
python database/monitor_health.py

# Single health check
python database/monitor_health.py --once

# Export metrics
python database/monitor_health.py --interval 60 --duration 3600 --save metrics.json

# View feature status
python database/manage_features.py --status

# Check database with new settings
python league_transactions/backfill_transactions_optimized.py --validate
```

## Success Metrics

Monitor these metrics to validate successful deployment:

| Metric | Target | How to Check |
|--------|--------|--------------|
| Lock errors | < 1/hour | `monitor_health.py` |
| Transaction success | > 99.9% | Job log table |
| Write response time | < 100ms | `monitor_health.py` |
| WAL file size | < 100MB | `ls -lh *.db-wal` |
| Memory usage | < +20% | System monitor |

## Rollback Plan

If any issues occur:

1. **Quick Disable** (keeps data):
   ```bash
   python database/emergency_rollback.py
   ```

2. **Full Revert** (if needed):
   ```bash
   # Restore backup
   cp database/league_analytics.db.backup database/league_analytics.db
   
   # Reset all flags
   python database/manage_features.py --reset
   ```

## Integration with Other Modules

### For `daily_lineups/` Module

The module will automatically benefit from system-wide PRAGMA settings when features are enabled. No code changes required initially.

Future enhancement:
```python
# Can add to daily_lineups/collector.py
from database.db_utils import DatabaseConnection
with DatabaseConnection(self.db_path) as conn:
    # Operations use optimized connection
```

### For `web-ui/backend/` Module

Node.js backend uses separate SQLite library. Add to `database.js`:
```javascript
// Apply similar optimizations
db.pragma('busy_timeout = 5000');
db.pragma('journal_mode = WAL');
```

## Troubleshooting

### "Database is locked" still occurring
1. Check if features are enabled: `manage_features.py --status`
2. Verify WAL mode active: `monitor_health.py --once`
3. Check for long transactions in code
4. Increase busy_timeout if needed

### WAL file growing too large
1. Manual checkpoint: `sqlite3 database.db "PRAGMA wal_checkpoint(TRUNCATE)"`
2. Check for open connections
3. Review transaction patterns

### Performance degraded
1. Check cache settings
2. Monitor memory usage
3. Disable aggressive_caching if needed
4. Review fragmentation levels

## Next Steps

1. **Week 1**: Deploy basic optimizations (pragma_optimizations, explicit_transactions)
2. **Week 2**: Add resilience features (wal_mode, retry_logic)
3. **Week 3**: Monitor and tune based on metrics
4. **Future**: Extend optimizations to other modules as needed

## Support

- Implementation Plan: `database/IMPLEMENTATION_PLAN_SQLITE_STABILITY.md`
- PRD: `docs/prds/prd-sqlite-database-stability-improvements.md`
- Emergency Rollback: `database/emergency_rollback.py`
- Health Monitoring: `database/monitor_health.py`
- Feature Management: `database/manage_features.py`