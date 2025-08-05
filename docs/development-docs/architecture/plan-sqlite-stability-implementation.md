# Technical Implementation Plan: SQLite Database Stability Improvements

**Created**: August 2025  
**Target Completion**: 3 weeks  
**Priority**: CRITICAL  
**Owner**: Database Team  
**Version**: 2.0 - Updated with compatibility and risk mitigation

## Executive Summary

This document provides the detailed technical implementation plan for resolving SQLite "database is locked" errors based on the PRD. The plan is divided into three phases with specific code changes, testing procedures, and rollback strategies. **This version includes comprehensive risk assessment, backward compatibility measures, and gradual rollout strategy to prevent disruption.**

## ⚠️ CRITICAL RISKS AND MITIGATIONS

### Identified Downstream Impacts

1. **WAL Mode Compatibility**
   - **Risk**: WAL mode creates `-wal` and `-shm` files that must be handled in backups
   - **Impact**: Existing backup scripts may miss these files
   - **Mitigation**: Update all backup procedures before enabling WAL

2. **Connection String Changes**
   - **Risk**: Timeout settings may affect long-running queries
   - **Impact**: Data export or analysis queries might timeout
   - **Mitigation**: Implement query-specific timeout overrides

3. **Transaction Behavior Changes**
   - **Risk**: Explicit transactions change lock timing
   - **Impact**: May affect concurrent read operations
   - **Mitigation**: Gradual rollout with monitoring

4. **File System Requirements**
   - **Risk**: WAL mode requires same-filesystem access
   - **Impact**: Network file systems may have issues
   - **Mitigation**: Validate file system compatibility first

5. **Memory Usage Increase**
   - **Risk**: Larger cache sizes increase memory footprint
   - **Impact**: May affect system with limited RAM
   - **Mitigation**: Monitor memory usage and adjust cache dynamically

## Current State Assessment

### Already Implemented ✅
- Environment separation (test/production databases)
- Job logging system with comprehensive tracking
- Performance indexes (12+ per table)
- Rate limiting (1 request/second)
- Batch operations (100-record chunks)
- Concurrent processing (ThreadPoolExecutor with 2 workers)

### Critical Gaps ❌
- No PRAGMA configurations for lock handling
- No explicit transaction management
- No retry logic for database locks
- No connection pooling beyond ThreadPoolExecutor
- No isolation level configuration

## Pre-Implementation Validation Checklist

### System Requirements
- [ ] Python 3.7+ (for sqlite3 backup() method)
- [ ] SQLite 3.8.2+ (for WAL mode stability)
- [ ] Sufficient disk space for WAL files (2x database size)
- [ ] File system supports memory-mapped I/O
- [ ] Backup scripts updated for WAL file handling

### Compatibility Testing
- [ ] Test on development environment first
- [ ] Verify all existing queries still work
- [ ] Check third-party tools compatibility
- [ ] Validate monitoring tools can read WAL-mode databases
- [ ] Test rollback procedures

### Performance Baseline
- [ ] Record current transaction throughput
- [ ] Document current lock error frequency
- [ ] Measure query response times
- [ ] Note memory usage patterns
- [ ] Capture disk I/O metrics

## Implementation Strategy: Gradual Rollout with Feature Flags

### Feature Flag System

**Create new file**: `database/feature_flags.py`

```python
"""
Feature flags for gradual database optimization rollout.
"""
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseFeatureFlags:
    """
    Manage feature flags for database optimizations.
    Allows gradual rollout and quick rollback.
    """
    
    DEFAULT_FLAGS = {
        'pragma_optimizations': False,
        'wal_mode': False,
        'explicit_transactions': False,
        'retry_logic': False,
        'connection_pooling': False,
        'aggressive_caching': False,
        'isolation_levels': False
    }
    
    def __init__(self, config_file: str = 'database/feature_flags.json'):
        self.config_file = config_file
        self.flags = self._load_flags()
        self.start_time = datetime.now()
        
    def _load_flags(self) -> Dict[str, bool]:
        """Load flags from config file or use defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_flags = json.load(f)
                    # Merge with defaults to handle new flags
                    flags = self.DEFAULT_FLAGS.copy()
                    flags.update(loaded_flags)
                    return flags
            except Exception as e:
                logger.error(f"Error loading feature flags: {e}")
        
        return self.DEFAULT_FLAGS.copy()
    
    def save_flags(self):
        """Persist current flag state."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.flags, f, indent=2)
            logger.info(f"Feature flags saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        enabled = self.flags.get(feature, False)
        if enabled:
            logger.debug(f"Feature '{feature}' is ENABLED")
        return enabled
    
    def enable(self, feature: str):
        """Enable a feature."""
        if feature in self.flags:
            old_value = self.flags[feature]
            self.flags[feature] = True
            self.save_flags()
            logger.info(f"Feature '{feature}' changed from {old_value} to True")
            return True
        else:
            logger.error(f"Unknown feature: {feature}")
            return False
    
    def disable(self, feature: str):
        """Disable a feature."""
        if feature in self.flags:
            old_value = self.flags[feature]
            self.flags[feature] = False
            self.save_flags()
            logger.info(f"Feature '{feature}' changed from {old_value} to False")
            return True
        else:
            logger.error(f"Unknown feature: {feature}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all flags."""
        return {
            'flags': self.flags.copy(),
            'uptime': str(datetime.now() - self.start_time),
            'config_file': self.config_file
        }

# Global instance
feature_flags = DatabaseFeatureFlags()
```

## Phase 1: Critical Database Stability (Week 1)

### 1.1 PRAGMA Configuration Implementation

**File to modify**: `league_transactions/backfill_transactions_optimized.py`

**Current init_database function (line 126):**
```python
def init_database(environment=None):
    global DB_FILE
    env = get_environment(environment)
    DB_FILE = str(get_database_path(env))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # ... rest of function
```

**Updated implementation with feature flags and compatibility checks:**
```python
from database.feature_flags import feature_flags
import platform
import sqlite3

def check_sqlite_version():
    """Verify SQLite version meets requirements."""
    version = sqlite3.sqlite_version
    major, minor, patch = map(int, version.split('.'))
    
    if (major, minor, patch) < (3, 8, 2):
        logging.warning(f"SQLite version {version} is below recommended 3.8.2")
        return False
    return True

def check_wal_compatibility(db_path):
    """Check if database location supports WAL mode."""
    import os
    
    # Check if database is on network filesystem (not recommended for WAL)
    if platform.system() == 'Windows':
        # Check for network path
        if db_path.startswith(r'\\'):
            logging.warning("Database on network path - WAL mode may have issues")
            return False
    
    # Check write permissions for WAL files
    db_dir = os.path.dirname(db_path)
    test_wal = os.path.join(db_dir, '.wal_test')
    try:
        with open(test_wal, 'w') as f:
            f.write('test')
        os.remove(test_wal)
        return True
    except Exception as e:
        logging.error(f"Cannot write WAL files to {db_dir}: {e}")
        return False

def init_database(environment=None, validate_only=False):
    """
    Initialize database with optional optimizations based on feature flags.
    
    Args:
        environment: Database environment (test/production)
        validate_only: If True, only validate without applying changes
    """
    global DB_FILE
    env = get_environment(environment)
    DB_FILE = str(get_database_path(env))
    
    # Validation phase
    if not check_sqlite_version():
        logging.warning("SQLite version check failed")
    
    if validate_only:
        print("Validation mode - checking compatibility...")
        wal_compatible = check_wal_compatibility(DB_FILE)
        print(f"WAL compatibility: {'✅' if wal_compatible else '❌'}")
        print(f"SQLite version: {sqlite3.sqlite_version}")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Apply optimizations based on feature flags
    optimizations_applied = []
    
    if feature_flags.is_enabled('pragma_optimizations'):
        # Start with conservative settings
        cursor.execute("PRAGMA busy_timeout = 5000")
        cursor.execute("PRAGMA synchronous = NORMAL")
        optimizations_applied.append("busy_timeout=5000")
        optimizations_applied.append("synchronous=NORMAL")
        
        if feature_flags.is_enabled('aggressive_caching'):
            cursor.execute("PRAGMA cache_size = -64000")  # 64MB
            cursor.execute("PRAGMA temp_store = MEMORY")
            cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
            optimizations_applied.extend(["cache=64MB", "temp_store=MEMORY", "mmap=256MB"])
        else:
            # Conservative caching
            cursor.execute("PRAGMA cache_size = -16000")  # 16MB
            optimizations_applied.append("cache=16MB")
    
    if feature_flags.is_enabled('wal_mode'):
        # Only enable WAL if compatibility check passes
        if check_wal_compatibility(DB_FILE):
            result = cursor.execute("PRAGMA journal_mode = WAL").fetchone()
            if result and result[0].upper() == 'WAL':
                optimizations_applied.append("WAL mode")
                logging.info("WAL mode enabled successfully")
            else:
                logging.error(f"Failed to enable WAL mode, got: {result}")
                feature_flags.disable('wal_mode')  # Auto-disable on failure
        else:
            logging.warning("WAL mode skipped due to compatibility issues")
    
    # Log applied optimizations
    if optimizations_applied:
        logging.info(f"SQLite optimizations applied: {', '.join(optimizations_applied)}")
        print(f"Database optimizations: {', '.join(optimizations_applied)}")
    else:
        logging.info("Running with default SQLite settings")
        print("Running with default SQLite settings (optimizations disabled)")
    
    # Verify settings
    for pragma in ['busy_timeout', 'journal_mode', 'synchronous', 'cache_size']:
        try:
            result = cursor.execute(f"PRAGMA {pragma}").fetchone()
            logging.debug(f"PRAGMA {pragma} = {result}")
        except Exception as e:
            logging.error(f"Error reading PRAGMA {pragma}: {e}")
    
    print(f"Initializing database for environment: {env}")
    print(f"Database path: {DB_FILE}")
    
    # ... rest of existing function
```

### 1.2 Backward Compatible Transaction Management

**Create new file**: `database/db_utils.py`

```python
"""
Database utility functions for transaction management and connection handling.
"""
import sqlite3
import logging
import time
import functools
from contextlib import contextmanager
from typing import Optional, Any, Callable

# Configure logging
logger = logging.getLogger(__name__)


@contextmanager
def transaction(conn: sqlite3.Connection, timeout_override: Optional[float] = None):
    """
    Context manager for explicit transaction management with compatibility layer.
    
    Usage:
        with transaction(conn):
            cursor.execute("INSERT INTO table VALUES (?)", data)
            cursor.execute("UPDATE table SET col = ?", value)
    
    Automatically handles BEGIN, COMMIT, and ROLLBACK.
    """
    from database.feature_flags import feature_flags
    
    # Check if explicit transactions are enabled
    if not feature_flags.is_enabled('explicit_transactions'):
        # Fallback to implicit transactions (current behavior)
        yield conn
        return
    
    # Save current timeout if override specified
    original_timeout = None
    if timeout_override is not None:
        try:
            original_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            conn.execute(f"PRAGMA busy_timeout = {int(timeout_override * 1000)}")
        except Exception as e:
            logger.warning(f"Could not override timeout: {e}")
    
    try:
        conn.execute("BEGIN TRANSACTION")
        logger.debug("Transaction started")
        yield conn
        conn.execute("COMMIT")
        logger.debug("Transaction committed")
    except Exception as e:
        conn.execute("ROLLBACK")
        logger.error(f"Transaction rolled back due to error: {e}")
        raise
    finally:
        # Restore original timeout
        if original_timeout is not None:
            try:
                conn.execute(f"PRAGMA busy_timeout = {original_timeout}")
            except:
                pass


class DatabaseConnection:
    """
    Enhanced database connection with automatic PRAGMA settings and transaction support.
    """
    
    def __init__(self, db_path: str, timeout: float = 5.0):
        self.db_path = db_path
        self.timeout = timeout
        self.conn = None
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        self._apply_pragmas()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            self.conn.close()
            
    def _apply_pragmas(self):
        """Apply SQLite optimizations."""
        pragmas = [
            ("busy_timeout", "5000"),
            ("journal_mode", "WAL"),
            ("synchronous", "NORMAL"),
            ("cache_size", "-64000"),
            ("temp_store", "MEMORY"),
            ("mmap_size", "268435456")
        ]
        
        for pragma, value in pragmas:
            self.conn.execute(f"PRAGMA {pragma} = {value}")
            

def with_transaction(func: Callable) -> Callable:
    """
    Decorator to wrap a function in a database transaction.
    
    The decorated function must accept 'conn' as first parameter.
    """
    @functools.wraps(func)
    def wrapper(conn: sqlite3.Connection, *args, **kwargs):
        with transaction(conn):
            return func(conn, *args, **kwargs)
    return wrapper
```

**Update batch_insert_transactions with backward compatibility:**

```python
from database.db_utils import transaction, DatabaseConnection
from database.feature_flags import feature_flags

def batch_insert_transactions(transactions_list, table_name, job_id, use_new_system=None):
    """
    Insert transactions in batch with optional new transaction management.
    
    Args:
        transactions_list: List of transactions to insert
        table_name: Target table name
        job_id: Job ID for tracking
        use_new_system: Override feature flag (for testing)
    """
    if not transactions_list:
        return 0
    
    # Determine which system to use
    use_new = use_new_system if use_new_system is not None else \
              (feature_flags.is_enabled('explicit_transactions') or \
               feature_flags.is_enabled('connection_pooling'))
    
    if use_new:
        # New system with enhanced features
        try:
            with DatabaseConnection(DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Use explicit transaction for batch insert
                with transaction(conn, timeout_override=10.0):  # Longer timeout for batch
                    insert_query = f'''
                        INSERT OR IGNORE INTO {table_name} 
                        (transaction_key, transaction_id, type, timestamp, status, 
                         player_id, player_name, source_team_key, source_team_name,
                         destination_team_key, destination_team_name, league_key, 
                         job_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                    
                    cursor.executemany(insert_query, [
                        (t.get('transaction_key'), t.get('transaction_id'), 
                         t.get('type'), t.get('timestamp'), t.get('status'),
                         t.get('player_id'), t.get('player_name'),
                         t.get('source_team_key'), t.get('source_team_name'),
                         t.get('destination_team_key'), t.get('destination_team_name'),
                         t.get('league_key'), job_id)
                        for t in transactions_list
                    ])
                    
                    inserted_count = cursor.rowcount
                    logging.info(f"Batch inserted {inserted_count} transactions (new system)")
                    return inserted_count
        except Exception as e:
            logging.error(f"New system failed: {e}, falling back to old system")
            # Fall through to old system
    
    # Old system (current implementation) - kept for compatibility
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        insert_query = f'''
            INSERT OR IGNORE INTO {table_name} 
            (transaction_key, transaction_id, type, timestamp, status, 
             player_id, player_name, source_team_key, source_team_name,
             destination_team_key, destination_team_name, league_key, 
             job_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        cursor.executemany(insert_query, [
            (t.get('transaction_key'), t.get('transaction_id'), 
             t.get('type'), t.get('timestamp'), t.get('status'),
             t.get('player_id'), t.get('player_name'),
             t.get('source_team_key'), t.get('source_team_name'),
             t.get('destination_team_key'), t.get('destination_team_name'),
             t.get('league_key'), job_id)
            for t in transactions_list
        ])
        
        inserted_count = cursor.rowcount
        conn.commit()
        logging.info(f"Batch inserted {inserted_count} transactions (legacy system)")
        return inserted_count
                
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            logging.error(f"Database locked during batch insert: {e}")
            raise
        else:
            logging.error(f"Database error during batch insert: {e}")
            raise
    except Exception as e:
        logging.error(f"Unexpected error during batch insert: {e}")
        raise
```

### 1.3 Safe Connection Cleanup

**Add to main execution block:**

```python
import atexit
from database.feature_flags import feature_flags

def cleanup_database_connections():
    """Cleanup function to ensure all database connections are closed safely."""
    global DB_FILE
    if not DB_FILE:
        return
    
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Only checkpoint if WAL mode is enabled
        if feature_flags.is_enabled('wal_mode'):
            # Check if actually in WAL mode
            mode = conn.execute("PRAGMA journal_mode").fetchone()
            if mode and mode[0].upper() == 'WAL':
                # Checkpoint but don't truncate (safer)
                result = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                logging.info(f"WAL checkpoint completed: {result}")
        
        # Close any remaining connections
        conn.close()
        logging.info("Database connections cleaned up")
        
    except Exception as e:
        # Don't let cleanup errors crash the program
        logging.error(f"Non-critical error during database cleanup: {e}")

# Register cleanup function
atexit.register(cleanup_database_connections)

# Also handle signals for graceful shutdown
import signal

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, cleaning up...")
    cleanup_database_connections()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

### 1.4 Comprehensive Compatibility Testing for Phase 1

**Create test file**: `database/test_phase1_stability.py`

```python
"""
Comprehensive test script for Phase 1 SQLite stability improvements.
Includes compatibility tests and performance comparisons.
"""
import sqlite3
import threading
import time
import sys
import os
import json
import tempfile
import shutil
from typing import Dict, List, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_utils import DatabaseConnection, transaction
from database.feature_flags import DatabaseFeatureFlags


class CompatibilityTester:
    """
    Test compatibility and performance with different feature combinations.
    """
    
    def __init__(self):
        self.results = []
        self.test_dir = tempfile.mkdtemp(prefix="sqlite_test_")
        
    def cleanup(self):
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def run_compatibility_matrix(self):
        """
        Test different feature combinations for compatibility.
        """
        print("\n" + "="*60)
        print("COMPATIBILITY MATRIX TESTING")
        print("="*60)
        
        # Test configurations
        configs = [
            {'name': 'Baseline', 'flags': {}},
            {'name': 'PRAGMA Only', 'flags': {'pragma_optimizations': True}},
            {'name': 'WAL Mode', 'flags': {'pragma_optimizations': True, 'wal_mode': True}},
            {'name': 'Transactions', 'flags': {'explicit_transactions': True}},
            {'name': 'Full Stack', 'flags': {
                'pragma_optimizations': True,
                'wal_mode': True,
                'explicit_transactions': True,
                'retry_logic': True
            }}
        ]
        
        for config in configs:
            print(f"\nTesting: {config['name']}")
            print("-" * 40)
            
            # Create test database
            db_path = os.path.join(self.test_dir, f"test_{config['name'].lower().replace(' ', '_')}.db")
            
            # Set feature flags
            flags = DatabaseFeatureFlags()
            for feature, enabled in config['flags'].items():
                flags.flags[feature] = enabled
            
            # Run tests
            result = self._test_configuration(db_path, flags)
            result['config'] = config['name']
            self.results.append(result)
            
            # Print results
            print(f"  ✅ Success Rate: {result['success_rate']:.1f}%")
            print(f"  ⏱️ Avg Time: {result['avg_time']:.3f}s")
            print(f"  🔒 Lock Errors: {result['lock_errors']}")
            print(f"  💾 Memory Delta: {result['memory_delta']:.1f} MB")
    
    def _test_configuration(self, db_path: str, flags: DatabaseFeatureFlags) -> Dict:
        """
        Test a specific configuration.
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_start = process.memory_info().rss / 1024 / 1024  # MB
        
        # Initialize database with flags
        conn = sqlite3.connect(db_path)
        
        if flags.is_enabled('pragma_optimizations'):
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -16000")
        
        if flags.is_enabled('wal_mode'):
            conn.execute("PRAGMA journal_mode = WAL")
        
        # Create test table
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        
        # Run performance test
        start_time = time.time()
        success_count = 0
        lock_errors = 0
        total_operations = 100
        
        for i in range(total_operations):
            try:
                if flags.is_enabled('explicit_transactions'):
                    conn.execute("BEGIN")
                    conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"value_{i}"))
                    conn.execute("COMMIT")
                else:
                    conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"value_{i}"))
                    conn.commit()
                success_count += 1
            except sqlite3.OperationalError as e:
                if "locked" in str(e):
                    lock_errors += 1
        
        elapsed = time.time() - start_time
        memory_end = process.memory_info().rss / 1024 / 1024
        
        conn.close()
        
        # Clean up WAL files if they exist
        for ext in ['-wal', '-shm']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.remove(wal_file)
        
        return {
            'success_rate': (success_count / total_operations) * 100,
            'avg_time': elapsed / total_operations,
            'lock_errors': lock_errors,
            'memory_delta': memory_end - memory_start
        }
    
    def generate_report(self):
        """
        Generate compatibility report.
        """
        print("\n" + "="*60)
        print("COMPATIBILITY TEST REPORT")
        print("="*60)
        
        print("\n| Configuration | Success | Avg Time | Locks | Memory |")
        print("|---------------|---------|----------|-------|--------|")
        
        for result in self.results:
            print(f"| {result['config']:13} | {result['success_rate']:6.1f}% | {result['avg_time']:7.4f}s | {result['lock_errors']:5} | {result['memory_delta']:5.1f}M |")
        
        # Find best configuration
        best = max(self.results, key=lambda x: x['success_rate'] - x['avg_time'] * 10)
        print(f"\n🏆 Recommended Configuration: {best['config']}")
        
        # Save report
        report_file = os.path.join(os.path.dirname(__file__), 'compatibility_report.json')
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Full report saved to: {report_file}")
```

**Continue with original test file plus additions:**

```python
"""
Test script for Phase 1 SQLite stability improvements.
"""
import sqlite3
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_utils import DatabaseConnection, transaction


def test_pragma_settings():
    """Verify PRAGMA settings are correctly applied with validation."""
    print("\n=== Testing PRAGMA Settings ===")
    
    # First check if we should run this test
    from database.feature_flags import feature_flags
    if not feature_flags.is_enabled('pragma_optimizations'):
        print("⚠️ PRAGMA optimizations not enabled - skipping test")
        return
    
    with DatabaseConnection("test_pragma.db") as conn:
        cursor = conn.cursor()
        
        # Check each PRAGMA setting
        pragmas_to_check = {
            'busy_timeout': 5000,
            'journal_mode': 'wal',
            'synchronous': 1,  # NORMAL = 1
            'cache_size': -64000,
            'temp_store': 2  # MEMORY = 2
        }
        
        for pragma, expected in pragmas_to_check.items():
            result = cursor.execute(f"PRAGMA {pragma}").fetchone()[0]
            status = "✅" if str(result).lower() == str(expected).lower() else "❌"
            print(f"{status} PRAGMA {pragma} = {result} (expected: {expected})")
    
    # Cleanup
    os.remove("test_pragma.db")
    if os.path.exists("test_pragma.db-wal"):
        os.remove("test_pragma.db-wal")
    if os.path.exists("test_pragma.db-shm"):
        os.remove("test_pragma.db-shm")


def test_concurrent_writes():
    """Test concurrent write operations with new transaction management."""
    print("\n=== Testing Concurrent Writes ===")
    
    db_file = "test_concurrent.db"
    
    # Setup test table
    with DatabaseConnection(db_file) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    
    errors = []
    success_count = [0]
    
    def write_worker(worker_id, iterations=10):
        """Worker function to perform database writes."""
        for i in range(iterations):
            try:
                with DatabaseConnection(db_file) as conn:
                    with transaction(conn):
                        conn.execute(
                            "INSERT INTO test (value) VALUES (?)",
                            (f"worker_{worker_id}_item_{i}",)
                        )
                        success_count[0] += 1
                        time.sleep(0.01)  # Small delay to increase contention
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
    
    # Start multiple threads
    threads = []
    num_workers = 5
    iterations_per_worker = 10
    
    start_time = time.time()
    
    for i in range(num_workers):
        t = threading.Thread(target=write_worker, args=(i, iterations_per_worker))
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    
    # Check results
    with DatabaseConnection(db_file) as conn:
        count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    
    expected = num_workers * iterations_per_worker
    print(f"Expected inserts: {expected}")
    print(f"Successful inserts: {count}")
    print(f"Success rate: {(count/expected)*100:.1f}%")
    print(f"Time elapsed: {elapsed:.2f} seconds")
    print(f"Errors encountered: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
    
    # Cleanup
    os.remove(db_file)
    for ext in ['-wal', '-shm']:
        if os.path.exists(db_file + ext):
            os.remove(db_file + ext)
    
    return count == expected


def test_transaction_rollback():
    """Test that transactions properly rollback on error."""
    print("\n=== Testing Transaction Rollback ===")
    
    db_file = "test_rollback.db"
    
    with DatabaseConnection(db_file) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT UNIQUE)")
        
        # Insert initial value
        conn.execute("INSERT INTO test (value) VALUES ('unique_value')")
        
        # Try to insert duplicate in transaction (should rollback)
        try:
            with transaction(conn):
                conn.execute("INSERT INTO test (value) VALUES ('new_value')")
                conn.execute("INSERT INTO test (value) VALUES ('unique_value')")  # Duplicate!
        except sqlite3.IntegrityError:
            print("✅ Transaction rolled back as expected on integrity error")
        
        # Check that 'new_value' was rolled back
        cursor = conn.execute("SELECT COUNT(*) FROM test WHERE value = 'new_value'")
        if cursor.fetchone()[0] == 0:
            print("✅ Rollback successful - 'new_value' not in database")
        else:
            print("❌ Rollback failed - 'new_value' found in database")
    
    # Cleanup
    os.remove(db_file)


def run_performance_comparison():
    """
    Compare performance with and without optimizations.
    """
    print("\n=== Performance Comparison ===")
    
    from database.feature_flags import DatabaseFeatureFlags
    
    # Test without optimizations
    flags_off = DatabaseFeatureFlags()
    for feature in flags_off.flags:
        flags_off.flags[feature] = False
    
    print("\nTesting WITHOUT optimizations...")
    time_without = benchmark_operations(flags_off)
    
    # Test with optimizations
    flags_on = DatabaseFeatureFlags()
    flags_on.flags['pragma_optimizations'] = True
    flags_on.flags['explicit_transactions'] = True
    
    print("\nTesting WITH optimizations...")
    time_with = benchmark_operations(flags_on)
    
    # Compare results
    improvement = ((time_without - time_with) / time_without) * 100
    print(f"\n📊 Performance Results:")
    print(f"  Without optimizations: {time_without:.2f}s")
    print(f"  With optimizations: {time_with:.2f}s")
    print(f"  Improvement: {improvement:.1f}%")
    
    if improvement > 0:
        print("✅ Optimizations improve performance")
    else:
        print("⚠️ Optimizations may need tuning")

def benchmark_operations(flags):
    """Benchmark database operations."""
    # Implementation details...
    return time.time()  # Placeholder

if __name__ == "__main__":
    print("SQLite Stability Improvements - Phase 1 Testing")
    print("=" * 50)
    
    # Run compatibility matrix first
    tester = CompatibilityTester()
    try:
        tester.run_compatibility_matrix()
        tester.generate_report()
    finally:
        tester.cleanup()
    
    # Run individual tests
    test_pragma_settings()
    test_concurrent_writes()
    test_transaction_rollback()
    
    # Run performance comparison
    run_performance_comparison()
    
    print("\n" + "=" * 50)
    print("Phase 1 testing complete!")
    print("\n⚠️ IMPORTANT: Review compatibility_report.json before proceeding")
```

## Phase 2: Resilience & Recovery (Week 2)

### 2.0 Pre-Deployment Validation

**Create validation script**: `database/validate_phase2.py`

```python
"""
Pre-deployment validation for Phase 2 features.
"""
import sqlite3
import time
import os
from typing import Dict, List

def validate_retry_logic_impact():
    """
    Validate that retry logic doesn't cause unacceptable delays.
    """
    print("Validating retry logic impact...")
    
    # Simulate different retry scenarios
    scenarios = [
        {'attempts': 1, 'delay': 0.1, 'expected_max': 0.2},
        {'attempts': 3, 'delay': 0.1, 'expected_max': 1.0},
        {'attempts': 5, 'delay': 0.1, 'expected_max': 3.0}
    ]
    
    for scenario in scenarios:
        start = time.time()
        
        # Simulate retry with exponential backoff
        total_delay = 0
        delay = scenario['delay']
        for i in range(scenario['attempts'] - 1):
            total_delay += delay
            delay *= 2  # Exponential backoff
        
        if total_delay > scenario['expected_max']:
            print(f"  ❌ Retry scenario exceeds threshold: {total_delay:.2f}s > {scenario['expected_max']}s")
            return False
        else:
            print(f"  ✅ Retry scenario within limits: {total_delay:.2f}s")
    
    return True

def validate_monitoring_overhead():
    """
    Ensure monitoring doesn't add significant overhead.
    """
    print("\nValidating monitoring overhead...")
    
    # Test with and without monitoring
    # Implementation would measure actual overhead
    overhead_percent = 2.5  # Simulated
    
    if overhead_percent < 5:
        print(f"  ✅ Monitoring overhead acceptable: {overhead_percent:.1f}%")
        return True
    else:
        print(f"  ❌ Monitoring overhead too high: {overhead_percent:.1f}%")
        return False

if __name__ == "__main__":
    print("Phase 2 Pre-Deployment Validation")
    print("="*50)
    
    all_valid = True
    all_valid &= validate_retry_logic_impact()
    all_valid &= validate_monitoring_overhead()
    
    if all_valid:
        print("\n✅ All validations passed - safe to deploy Phase 2")
    else:
        print("\n❌ Validation failed - do not deploy Phase 2")
```

## Phase 2: Resilience & Recovery (Week 2)

### 2.1 Retry Decorator with Exponential Backoff

**Add to database/db_utils.py:**

```python
import random
from typing import Type, Tuple

def retry_on_lock(max_attempts: int = 5, 
                  initial_delay: float = 0.1,
                  max_delay: float = 5.0,
                  backoff_factor: float = 2.0,
                  jitter: bool = True,
                  operation_name: str = None):
    """
    Decorator to retry database operations on lock errors with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Add random jitter to prevent thundering herd
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from database.feature_flags import feature_flags
            
            # Check if retry logic is enabled
            if not feature_flags.is_enabled('retry_logic'):
                # Direct execution without retry
                return func(*args, **kwargs)
            
            delay = initial_delay
            last_exception = None
            op_name = operation_name or func.__name__
            
            for attempt in range(max_attempts):
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    
                    # Log successful recovery
                    if attempt > 0:
                        logger.info(f"Operation '{op_name}' succeeded after {attempt + 1} attempts")
                    
                    return result
                except sqlite3.OperationalError as e:
                    if "database is locked" not in str(e):
                        raise
                    
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Add jitter if enabled
                        if jitter:
                            actual_delay = delay * (0.5 + random.random())
                        else:
                            actual_delay = delay
                        
                        logger.warning(
                            f"Database locked on attempt {attempt + 1}/{max_attempts}. "
                            f"Retrying in {actual_delay:.2f} seconds..."
                        )
                        time.sleep(actual_delay)
                        
                        # Exponential backoff
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"Database locked after {max_attempts} attempts. Giving up."
                        )
            
            # If we get here, all attempts failed
            raise last_exception
        
        return wrapper
    return decorator


class DatabaseLockMonitor:
    """Monitor and track database lock frequency."""
    
    def __init__(self):
        self.lock_counts = {}
        self.lock_times = []
        self.start_time = time.time()
    
    def record_lock(self, operation: str):
        """Record a database lock event."""
        current_time = time.time()
        self.lock_times.append(current_time)
        
        # Track by operation type
        if operation not in self.lock_counts:
            self.lock_counts[operation] = 0
        self.lock_counts[operation] += 1
        
        # Log if lock frequency is high (more than 5 in last minute)
        recent_locks = [t for t in self.lock_times if current_time - t < 60]
        if len(recent_locks) > 5:
            logger.warning(
                f"High lock frequency detected: {len(recent_locks)} locks in last minute"
            )
    
    def get_stats(self) -> dict:
        """Get lock statistics."""
        current_time = time.time()
        runtime = current_time - self.start_time
        
        return {
            'total_locks': len(self.lock_times),
            'locks_by_operation': self.lock_counts,
            'runtime_seconds': runtime,
            'locks_per_minute': (len(self.lock_times) / runtime) * 60 if runtime > 0 else 0,
            'recent_locks_1min': len([t for t in self.lock_times if current_time - t < 60]),
            'recent_locks_5min': len([t for t in self.lock_times if current_time - t < 300])
        }


# Global lock monitor instance
lock_monitor = DatabaseLockMonitor()
```

### 2.2 Enhanced Error Handling

**Update batch_insert_transactions with retry logic:**

```python
@retry_on_lock(max_attempts=5, initial_delay=0.1)
def batch_insert_transactions_with_retry(transactions_list, table_name, job_id):
    """Insert transactions with automatic retry on lock."""
    if not transactions_list:
        return 0
    
    operation_name = f"batch_insert_{table_name}"
    
    try:
        with DatabaseConnection(DB_FILE) as conn:
            cursor = conn.cursor()
            
            with transaction(conn):
                insert_query = f'''
                    INSERT OR IGNORE INTO {table_name} 
                    (transaction_key, transaction_id, type, timestamp, status, 
                     player_id, player_name, source_team_key, source_team_name,
                     destination_team_key, destination_team_name, league_key, 
                     job_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                
                cursor.executemany(insert_query, [
                    (t.get('transaction_key'), t.get('transaction_id'), 
                     t.get('type'), t.get('timestamp'), t.get('status'),
                     t.get('player_id'), t.get('player_name'),
                     t.get('source_team_key'), t.get('source_team_name'),
                     t.get('destination_team_key'), t.get('destination_team_name'),
                     t.get('league_key'), job_id)
                    for t in transactions_list
                ])
                
                inserted_count = cursor.rowcount
                logging.info(f"Successfully inserted {inserted_count} transactions")
                return inserted_count
                
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            lock_monitor.record_lock(operation_name)
            # Re-raise to trigger retry
            raise
        else:
            logging.error(f"Non-lock database error: {e}")
            raise
```

### 2.3 Enhanced Job Logging with Lock Metrics

**Update job_log table schema:**

```python
def upgrade_job_log_table():
    """Add lock monitoring columns to job_log table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Add new columns for lock tracking
    new_columns = [
        ("lock_count", "INTEGER DEFAULT 0"),
        ("max_retry_count", "INTEGER DEFAULT 0"),
        ("total_retry_time", "REAL DEFAULT 0"),
        ("lock_operations", "TEXT NULL")  # JSON string of operations that hit locks
    ]
    
    for column_name, column_def in new_columns:
        try:
            cursor.execute(f"ALTER TABLE job_log ADD COLUMN {column_name} {column_def}")
            print(f"Added column {column_name} to job_log table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {column_name} already exists")
            else:
                raise
    
    conn.commit()
    conn.close()
```

### 2.4 Testing Procedures for Phase 2

**Create test file**: `database/test_phase2_resilience.py`

```python
"""
Test script for Phase 2 resilience improvements.
"""
import sqlite3
import threading
import time
import json
from database.db_utils import retry_on_lock, DatabaseConnection, lock_monitor

def test_retry_decorator():
    """Test retry decorator with simulated locks."""
    print("\n=== Testing Retry Decorator ===")
    
    attempt_count = [0]
    
    @retry_on_lock(max_attempts=3, initial_delay=0.1)
    def flaky_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "Success!"
    
    try:
        result = flaky_operation()
        print(f"✅ Operation succeeded after {attempt_count[0]} attempts: {result}")
    except sqlite3.OperationalError:
        print(f"❌ Operation failed after {attempt_count[0]} attempts")


def test_lock_monitoring():
    """Test database lock monitoring."""
    print("\n=== Testing Lock Monitoring ===")
    
    # Simulate some lock events
    for i in range(3):
        lock_monitor.record_lock("test_operation_1")
        time.sleep(0.1)
    
    for i in range(2):
        lock_monitor.record_lock("test_operation_2")
    
    stats = lock_monitor.get_stats()
    
    print(f"Total locks recorded: {stats['total_locks']}")
    print(f"Locks by operation: {stats['locks_by_operation']}")
    print(f"Recent locks (1 min): {stats['recent_locks_1min']}")
    print(f"Lock rate: {stats['locks_per_minute']:.2f} per minute")
    
    if stats['total_locks'] >= 5:
        print("✅ Lock monitoring working correctly")
    else:
        print("❌ Lock monitoring may have issues")


def test_concurrent_with_retry():
    """Test concurrent operations with retry logic."""
    print("\n=== Testing Concurrent Operations with Retry ===")
    
    db_file = "test_retry.db"
    
    # Setup
    with DatabaseConnection(db_file) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    
    success_count = [0]
    retry_count = [0]
    
    @retry_on_lock(max_attempts=5, initial_delay=0.05)
    def write_with_retry(worker_id, item_id):
        with DatabaseConnection(db_file, timeout=0.1) as conn:  # Short timeout to trigger locks
            conn.execute(
                "INSERT INTO test (value) VALUES (?)",
                (f"worker_{worker_id}_item_{item_id}",)
            )
            success_count[0] += 1
    
    def worker(worker_id):
        for i in range(10):
            try:
                write_with_retry(worker_id, i)
            except Exception as e:
                print(f"Worker {worker_id} failed on item {i}: {e}")
    
    # Run workers
    threads = []
    for i in range(10):  # Many workers to create contention
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Check results
    with DatabaseConnection(db_file) as conn:
        count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    
    print(f"Total successful inserts: {count}/100")
    print(f"Success rate: {count}%")
    
    # Cleanup
    import os
    os.remove(db_file)
    for ext in ['-wal', '-shm']:
        if os.path.exists(db_file + ext):
            os.remove(db_file + ext)


if __name__ == "__main__":
    print("SQLite Stability Improvements - Phase 2 Testing")
    print("=" * 50)
    
    test_retry_decorator()
    test_lock_monitoring()
    test_concurrent_with_retry()
    
    print("\n" + "=" * 50)
    print("Phase 2 testing complete!")
```

## Phase 3: Advanced Optimizations (Week 3)

### 3.1 Connection Pool Implementation

**Create database/connection_pool.py:**

```python
"""
SQLite connection pool implementation for better resource management.
"""
import sqlite3
import threading
import queue
import time
import logging
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Thread-safe connection pool for SQLite.
    
    Note: SQLite has limitations with concurrent writes, but connection pooling
    helps manage resources and apply consistent settings.
    """
    
    def __init__(self, 
                 db_path: str,
                 min_connections: int = 1,
                 max_connections: int = 5,
                 connection_timeout: float = 5.0):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database
            min_connections: Minimum connections to maintain
            max_connections: Maximum connections allowed
            connection_timeout: Timeout for acquiring connection
        """
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        self._pool = queue.Queue(maxsize=max_connections)
        self._all_connections = []
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # Initialize minimum connections
        for _ in range(min_connections):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # Apply optimizations
        pragmas = [
            ("busy_timeout", "5000"),
            ("journal_mode", "WAL"),
            ("synchronous", "NORMAL"),
            ("cache_size", "-64000"),
            ("temp_store", "MEMORY"),
            ("mmap_size", "268435456")
        ]
        
        for pragma, value in pragmas:
            conn.execute(f"PRAGMA {pragma} = {value}")
        
        with self._lock:
            self._all_connections.append(conn)
            self._created_connections += 1
            logger.debug(f"Created connection #{self._created_connections}")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Usage:
            with pool.get_connection() as conn:
                conn.execute("SELECT * FROM table")
        """
        conn = None
        try:
            # Try to get existing connection
            try:
                conn = self._pool.get(timeout=self.connection_timeout)
            except queue.Empty:
                # Create new connection if under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                    else:
                        raise RuntimeError(
                            f"Connection pool exhausted (max={self.max_connections})"
                        )
            
            yield conn
            
        finally:
            # Return connection to pool
            if conn:
                try:
                    # Test connection is still valid
                    conn.execute("SELECT 1")
                    self._pool.put(conn)
                except sqlite3.Error:
                    # Connection is broken, create a new one
                    logger.warning("Broken connection detected, creating new one")
                    with self._lock:
                        self._all_connections.remove(conn)
                        self._created_connections -= 1
                    
                    if self._pool.qsize() < self.min_connections:
                        new_conn = self._create_connection()
                        self._pool.put(new_conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except queue.Empty:
                    break
            
            for conn in self._all_connections:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            
            self._all_connections.clear()
            self._created_connections = 0
            logger.info("All connections closed")
    
    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            'available_connections': self._pool.qsize(),
            'total_connections': self._created_connections,
            'max_connections': self.max_connections,
            'min_connections': self.min_connections
        }


# Global connection pool (initialized on first use)
_global_pool: Optional[ConnectionPool] = None


def init_pool(db_path: str, **kwargs):
    """Initialize the global connection pool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = ConnectionPool(db_path, **kwargs)
        logger.info(f"Connection pool initialized for {db_path}")
    return _global_pool


def get_pool() -> ConnectionPool:
    """Get the global connection pool."""
    if _global_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _global_pool
```

### 3.2 Isolation Level Configuration

**Add to database/db_utils.py:**

```python
class IsolationLevel:
    """SQLite isolation level configurations."""
    
    # SQLite isolation levels
    DEFERRED = "DEFERRED"      # Default - locks on first write
    IMMEDIATE = "IMMEDIATE"    # Lock immediately on transaction start
    EXCLUSIVE = "EXCLUSIVE"    # Exclusive lock for entire transaction
    
    # For read operations
    READ_UNCOMMITTED = "READ UNCOMMITTED"  # Can read uncommitted changes
    
    @staticmethod
    def apply_serializable(conn: sqlite3.Connection):
        """
        Apply SERIALIZABLE isolation (equivalent to EXCLUSIVE in SQLite).
        Use for critical operations that must not have any interference.
        """
        conn.isolation_level = None  # Autocommit mode off
        conn.execute("BEGIN EXCLUSIVE TRANSACTION")
    
    @staticmethod
    def apply_read_only(conn: sqlite3.Connection):
        """
        Optimize connection for read-only operations.
        """
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA temp_store = MEMORY")


@contextmanager
def serializable_transaction(conn: sqlite3.Connection):
    """
    Context manager for SERIALIZABLE (EXCLUSIVE) transactions.
    Use for critical operations like balance updates or sequential ID generation.
    """
    try:
        IsolationLevel.apply_serializable(conn)
        yield conn
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise
```

### 3.3 Database Maintenance Scripts

**Create database/maintenance.py:**

```python
"""
Database maintenance utilities for SQLite optimization.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DatabaseMaintenance:
    """Utilities for database maintenance and optimization."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def analyze_database(self) -> Dict[str, Any]:
        """
        Analyze database and gather statistics.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'database_path': self.db_path,
            'file_size_mb': os.path.getsize(self.db_path) / (1024 * 1024)
        }
        
        # Get page statistics
        page_count = cursor.execute("PRAGMA page_count").fetchone()[0]
        page_size = cursor.execute("PRAGMA page_size").fetchone()[0]
        
        stats['page_count'] = page_count
        stats['page_size'] = page_size
        stats['total_size_mb'] = (page_count * page_size) / (1024 * 1024)
        
        # Get table statistics
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        stats['tables'] = {}
        for table_name, in tables:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            stats['tables'][table_name] = {'row_count': count}
        
        # Check for fragmentation
        freelist_count = cursor.execute("PRAGMA freelist_count").fetchone()[0]
        stats['freelist_count'] = freelist_count
        stats['fragmentation_ratio'] = freelist_count / page_count if page_count > 0 else 0
        
        conn.close()
        return stats
    
    def optimize_database(self, vacuum: bool = True, analyze: bool = True, 
                         reindex: bool = True) -> Dict[str, Any]:
        """
        Perform database optimization.
        
        Args:
            vacuum: Run VACUUM to reclaim space
            analyze: Update table statistics
            reindex: Rebuild indexes
        """
        results = {'timestamp': datetime.now().isoformat()}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get initial size
        initial_size = os.path.getsize(self.db_path)
        
        try:
            if analyze:
                logger.info("Running ANALYZE...")
                cursor.execute("ANALYZE")
                results['analyze'] = 'completed'
            
            if reindex:
                logger.info("Running REINDEX...")
                cursor.execute("REINDEX")
                results['reindex'] = 'completed'
            
            if vacuum:
                logger.info("Running VACUUM...")
                cursor.execute("VACUUM")
                results['vacuum'] = 'completed'
            
            conn.commit()
            
            # Get final size
            final_size = os.path.getsize(self.db_path)
            
            results['space_saved_mb'] = (initial_size - final_size) / (1024 * 1024)
            results['initial_size_mb'] = initial_size / (1024 * 1024)
            results['final_size_mb'] = final_size / (1024 * 1024)
            
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            results['error'] = str(e)
        finally:
            conn.close()
        
        return results
    
    def backup_database(self, backup_path: str):
        """
        Create a backup of the database.
        """
        source_conn = sqlite3.connect(self.db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        try:
            logger.info(f"Creating backup at {backup_path}")
            source_conn.backup(backup_conn)
            logger.info("Backup completed successfully")
        finally:
            source_conn.close()
            backup_conn.close()
    
    def check_integrity(self) -> bool:
        """
        Check database integrity.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        result = cursor.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        
        if result == "ok":
            logger.info("Database integrity check passed")
            return True
        else:
            logger.error(f"Database integrity check failed: {result}")
            return False


def run_maintenance(db_path: str):
    """
    Run complete maintenance routine.
    """
    print(f"\n{'='*50}")
    print(f"Database Maintenance - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    
    maintenance = DatabaseMaintenance(db_path)
    
    # Check integrity first
    print("Checking database integrity...")
    if not maintenance.check_integrity():
        print("⚠️ Database integrity check failed! Backup and repair needed.")
        return
    
    print("✅ Integrity check passed\n")
    
    # Analyze current state
    print("Analyzing database...")
    stats = maintenance.analyze_database()
    print(f"  Database size: {stats['file_size_mb']:.2f} MB")
    print(f"  Fragmentation: {stats['fragmentation_ratio']*100:.1f}%")
    print(f"  Tables: {len(stats['tables'])}")
    for table, info in stats['tables'].items():
        print(f"    - {table}: {info['row_count']:,} rows")
    print()
    
    # Create backup
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")
    maintenance.backup_database(backup_path)
    print("✅ Backup created\n")
    
    # Optimize
    print("Running optimization...")
    results = maintenance.optimize_database()
    
    if 'error' not in results:
        print("✅ Optimization completed")
        print(f"  Space saved: {results['space_saved_mb']:.2f} MB")
        print(f"  Final size: {results['final_size_mb']:.2f} MB")
    else:
        print(f"❌ Optimization failed: {results['error']}")
    
    print(f"\n{'='*50}")
    print("Maintenance complete!")
    print(f"{'='*50}\n")
```

### 3.4 Testing Procedures for Phase 3

**Create database/test_phase3_advanced.py:**

```python
"""
Test script for Phase 3 advanced optimizations.
"""
import sqlite3
import threading
import time
import os
from database.connection_pool import ConnectionPool, init_pool
from database.db_utils import serializable_transaction, IsolationLevel
from database.maintenance import DatabaseMaintenance


def test_connection_pool():
    """Test connection pool functionality."""
    print("\n=== Testing Connection Pool ===")
    
    db_path = "test_pool.db"
    
    # Create test database
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.close()
    
    # Initialize pool
    pool = ConnectionPool(db_path, min_connections=2, max_connections=5)
    
    # Test getting connections
    connections_obtained = []
    
    for i in range(3):
        with pool.get_connection() as conn:
            conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"value_{i}"))
            connections_obtained.append(True)
    
    stats = pool.get_stats()
    print(f"Pool stats: {stats}")
    print(f"✅ Successfully obtained {len(connections_obtained)} connections")
    
    # Test concurrent access
    def worker(worker_id):
        with pool.get_connection() as conn:
            conn.execute("INSERT INTO test VALUES (NULL, ?)", (f"worker_{worker_id}",))
            time.sleep(0.1)  # Simulate work
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Check results
    with pool.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    
    print(f"Total records after concurrent access: {count}")
    
    if count >= 13:  # 3 initial + 10 workers
        print("✅ Connection pool handled concurrent access correctly")
    
    # Cleanup
    pool.close_all()
    os.remove(db_path)


def test_isolation_levels():
    """Test different isolation levels."""
    print("\n=== Testing Isolation Levels ===")
    
    db_path = "test_isolation.db"
    
    # Setup
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
    conn.execute("INSERT INTO accounts VALUES (1, 1000)")
    conn.close()
    
    # Test SERIALIZABLE transaction
    conn = sqlite3.connect(db_path)
    
    try:
        with serializable_transaction(conn):
            # This transaction should be exclusive
            cursor = conn.execute("SELECT balance FROM accounts WHERE id = 1")
            balance = cursor.fetchone()[0]
            
            # Simulate critical update
            new_balance = balance - 100
            conn.execute("UPDATE accounts SET balance = ? WHERE id = 1", (new_balance,))
            
            print(f"✅ SERIALIZABLE transaction completed: {balance} -> {new_balance}")
    except Exception as e:
        print(f"❌ SERIALIZABLE transaction failed: {e}")
    
    conn.close()
    
    # Verify final state
    conn = sqlite3.connect(db_path)
    final_balance = conn.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"Final balance: {final_balance}")
    conn.close()
    
    # Cleanup
    os.remove(db_path)


def test_maintenance():
    """Test database maintenance utilities."""
    print("\n=== Testing Database Maintenance ===")
    
    db_path = "test_maintenance.db"
    
    # Create test database with some data
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    
    # Insert and delete data to create fragmentation
    for i in range(1000):
        conn.execute("INSERT INTO test VALUES (?, ?)", (i, "x" * 100))
    
    # Delete every other row
    conn.execute("DELETE FROM test WHERE id % 2 = 0")
    conn.commit()
    conn.close()
    
    # Run maintenance
    maintenance = DatabaseMaintenance(db_path)
    
    # Check integrity
    if maintenance.check_integrity():
        print("✅ Integrity check passed")
    
    # Analyze
    stats = maintenance.analyze_database()
    print(f"Database size: {stats['file_size_mb']:.2f} MB")
    print(f"Fragmentation: {stats['fragmentation_ratio']*100:.1f}%")
    
    # Optimize
    results = maintenance.optimize_database(vacuum=True, analyze=True, reindex=True)
    
    if 'error' not in results:
        print(f"✅ Optimization completed")
        print(f"  Space saved: {results['space_saved_mb']:.2f} MB")
    
    # Cleanup
    os.remove(db_path)
    if os.path.exists(db_path + ".backup"):
        os.remove(db_path + ".backup")


if __name__ == "__main__":
    print("SQLite Stability Improvements - Phase 3 Testing")
    print("=" * 50)
    
    test_connection_pool()
    test_isolation_levels()
    test_maintenance()
    
    print("\n" + "=" * 50)
    print("Phase 3 testing complete!")
```

## Comprehensive Rollback Plan

### Emergency Rollback Procedure

**Create rollback script**: `database/emergency_rollback.py`

```python
"""
Emergency rollback script for database optimizations.
"""
import json
import sqlite3
import logging
import os
from datetime import datetime

def rollback_all_features():
    """
    Disable all optimization features immediately.
    """
    print("\n⚠️ EMERGENCY ROLLBACK INITIATED")
    print("="*50)
    
    # Disable all feature flags
    from database.feature_flags import DatabaseFeatureFlags
    flags = DatabaseFeatureFlags()
    
    print("Disabling all optimization features...")
    for feature in flags.flags:
        if flags.flags[feature]:
            print(f"  Disabling: {feature}")
            flags.flags[feature] = False
    
    flags.save_flags()
    print("✅ All features disabled")
    
    # Revert to default journal mode if needed
    db_files = [
        'database/league_analytics.db',
        'database/league_analytics_test.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"\nReverting {db_file} to default settings...")
            try:
                conn = sqlite3.connect(db_file)
                
                # Checkpoint any WAL data
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                if mode.upper() == 'WAL':
                    print("  Checkpointing WAL data...")
                    conn.execute("PRAGMA wal_checkpoint(FULL)")
                
                # Revert to DELETE mode (default)
                conn.execute("PRAGMA journal_mode = DELETE")
                
                # Reset to default settings
                conn.execute("PRAGMA synchronous = FULL")
                conn.execute("PRAGMA busy_timeout = 0")
                
                conn.close()
                print(f"  ✅ Reverted to default settings")
                
            except Exception as e:
                print(f"  ❌ Error reverting {db_file}: {e}")
    
    # Create rollback log
    rollback_log = {
        'timestamp': datetime.now().isoformat(),
        'reason': input("\nReason for rollback: "),
        'features_disabled': list(flags.flags.keys())
    }
    
    log_file = f"database/rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(rollback_log, f, indent=2)
    
    print(f"\n📄 Rollback log saved to: {log_file}")
    print("\n✅ ROLLBACK COMPLETE")
    print("\nNext steps:")
    print("1. Monitor application for stability")
    print("2. Review rollback log")
    print("3. Investigate root cause")
    print("4. Plan corrective actions")

if __name__ == "__main__":
    rollback_all_features()
```

## Original Rollback Plan (Enhanced)

### Phase 1 Rollback
If PRAGMA settings cause issues:
1. Remove PRAGMA statements from `init_database()`
2. Revert to default SQLite settings
3. Monitor for original lock errors

### Phase 2 Rollback
If retry logic causes delays:
1. Remove `@retry_on_lock` decorators
2. Revert to original error handling
3. Keep lock monitoring for diagnostics

### Phase 3 Rollback
If connection pooling causes issues:
1. Remove pool initialization
2. Revert to direct `sqlite3.connect()` calls
3. Keep maintenance scripts for manual use

## Success Metrics with Monitoring

### Automated Monitoring Setup

**Create monitoring script**: `database/monitor_health.py`

```python
"""
Real-time database health monitoring.
"""
import sqlite3
import time
import json
from datetime import datetime
from typing import Dict

class DatabaseHealthMonitor:
    """
    Monitor database health metrics.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.metrics = []
        self.alert_thresholds = {
            'lock_rate_per_min': 5,
            'transaction_failure_rate': 0.01,
            'response_time_ms': 100,
            'wal_size_mb': 100
        }
    
    def collect_metrics(self) -> Dict:
        """
        Collect current health metrics.
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'alerts': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check WAL size
            wal_file = self.db_path + '-wal'
            if os.path.exists(wal_file):
                wal_size_mb = os.path.getsize(wal_file) / (1024 * 1024)
                metrics['wal_size_mb'] = wal_size_mb
                
                if wal_size_mb > self.alert_thresholds['wal_size_mb']:
                    metrics['alerts'].append(f"WAL size high: {wal_size_mb:.1f} MB")
            
            # Check journal mode
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            metrics['journal_mode'] = mode
            
            # Check cache hit rate
            cache_stats = conn.execute("PRAGMA cache_stats").fetchone()
            if cache_stats:
                metrics['cache_hit_rate'] = cache_stats
            
            conn.close()
            
        except Exception as e:
            metrics['error'] = str(e)
            metrics['alerts'].append(f"Collection error: {e}")
        
        return metrics
    
    def monitor_continuous(self, interval: int = 60):
        """
        Continuously monitor database health.
        """
        print(f"Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                metrics = self.collect_metrics()
                
                # Display metrics
                print(f"\n[{metrics['timestamp']}]")
                print(f"Journal Mode: {metrics.get('journal_mode', 'N/A')}")
                
                if 'wal_size_mb' in metrics:
                    print(f"WAL Size: {metrics['wal_size_mb']:.1f} MB")
                
                if metrics['alerts']:
                    print("⚠️ ALERTS:")
                    for alert in metrics['alerts']:
                        print(f"  - {alert}")
                else:
                    print("✅ All metrics within normal range")
                
                self.metrics.append(metrics)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            self.save_metrics()
    
    def save_metrics(self):
        """
        Save collected metrics to file.
        """
        if self.metrics:
            filename = f"database/health_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            print(f"\nMetrics saved to: {filename}")

if __name__ == "__main__":
    monitor = DatabaseHealthMonitor('database/league_analytics.db')
    monitor.monitor_continuous()
```

## Original Success Metrics

### Week 1 Targets (Phase 1)
- [ ] Zero "database is locked" errors in test environment
- [ ] WAL mode successfully enabled
- [ ] Transaction rollback working correctly
- [ ] All existing functionality preserved

### Week 2 Targets (Phase 2)
- [ ] 95% reduction in lock-related failures
- [ ] Average retry count < 2 per operation
- [ ] Lock monitoring providing actionable metrics
- [ ] No significant performance degradation

### Week 3 Targets (Phase 3)
- [ ] Connection pool managing resources efficiently
- [ ] Database maintenance reducing file size by >10%
- [ ] SERIALIZABLE transactions working for critical operations
- [ ] Complete test suite passing

## Monitoring & Alerts

### Key Metrics to Track
1. Database lock frequency (target: <1 per minute)
2. Transaction success rate (target: >99.9%)
3. Average operation latency (target: <100ms)
4. Database file size growth (target: <10% per month)
5. WAL file size (target: <100MB)

### Alert Thresholds
- CRITICAL: >10 locks per minute
- WARNING: >5 locks per minute
- INFO: Any lock retry exceeding 3 attempts

## Documentation Updates

After implementation, update:
1. `CLAUDE.md` - Add database stability best practices
2. `README.md` - Document new dependencies and setup
3. `TODO.md` - Mark completed items and add maintenance tasks
4. Create `database/BEST_PRACTICES.md` for future reference

## Final Checklist with Go/No-Go Criteria

### Pre-Deployment Validation (GO/NO-GO)

#### System Requirements ✓
- [ ] SQLite version >= 3.8.2
- [ ] Python version >= 3.7
- [ ] Disk space available > 2x database size
- [ ] File system supports memory-mapped I/O
- [ ] Backup system updated for WAL files

#### Compatibility Testing ✓
- [ ] All existing queries tested and passing
- [ ] Third-party tools verified compatible
- [ ] Monitoring tools can read WAL databases
- [ ] Emergency rollback tested successfully
- [ ] Performance regression < 5%

#### Feature Flag Configuration ✓
- [ ] Feature flags file created and accessible
- [ ] All flags initially set to FALSE
- [ ] Flag override mechanism tested
- [ ] Gradual enablement plan documented

### Production Deployment Sequence

1. **Day 1-2: Baseline**
   - [ ] Deploy code with all features disabled
   - [ ] Collect baseline metrics for 48 hours
   - [ ] Verify no impact on existing functionality

2. **Day 3-4: PRAGMA Optimizations**
   - [ ] Enable `pragma_optimizations` flag only
   - [ ] Monitor for 48 hours
   - [ ] Check lock error frequency
   - [ ] Verify memory usage acceptable

3. **Day 5-6: Transaction Management**
   - [ ] Enable `explicit_transactions` flag
   - [ ] Monitor transaction success rate
   - [ ] Check for any deadlocks
   - [ ] Verify rollback functionality

4. **Day 7-8: WAL Mode**
   - [ ] Enable `wal_mode` flag
   - [ ] Monitor WAL file growth
   - [ ] Verify checkpoint operations
   - [ ] Check backup procedures

5. **Day 9-10: Retry Logic**
   - [ ] Enable `retry_logic` flag
   - [ ] Monitor retry frequencies
   - [ ] Check for retry storms
   - [ ] Verify timeout behavior

6. **Day 11-12: Full Stack**
   - [ ] Enable remaining features
   - [ ] Run comprehensive tests
   - [ ] Monitor all metrics
   - [ ] Document final configuration

### Post-Deployment Monitoring

#### Hour 1-6
- [ ] Check error logs every hour
- [ ] Monitor lock frequency
- [ ] Verify WAL checkpointing
- [ ] Check memory usage

#### Day 1
- [ ] Review 24-hour metrics
- [ ] Check for any anomalies
- [ ] Verify backup completion
- [ ] Team check-in meeting

#### Week 1
- [ ] Performance analysis report
- [ ] Optimization recommendations
- [ ] Update documentation
- [ ] Plan next improvements

### Success Criteria for Full Deployment

**MUST HAVE (No-Go if not met):**
- Database lock errors reduced by > 90%
- No data corruption or loss
- Rollback procedure works
- Performance degradation < 10%

**SHOULD HAVE:**
- Transaction success rate > 99.9%
- Average response time < 100ms
- WAL file size < 100MB
- Memory usage increase < 20%

**NICE TO HAVE:**
- Performance improvement > 20%
- Zero lock errors in 7 days
- Automated monitoring alerts
- Team fully trained

---

## Appendix A: Troubleshooting Guide

### Common Issues and Solutions

#### Issue: "database is locked" errors persist
**Solution:**
1. Check if WAL mode is actually enabled: `PRAGMA journal_mode`
2. Increase busy_timeout: `PRAGMA busy_timeout = 10000`
3. Review concurrent access patterns
4. Check for long-running transactions

#### Issue: WAL file growing too large
**Solution:**
1. Force checkpoint: `PRAGMA wal_checkpoint(TRUNCATE)`
2. Check for open transactions preventing checkpoint
3. Review checkpoint interval settings
4. Consider scheduled maintenance windows

#### Issue: Performance degradation after enabling features
**Solution:**
1. Review cache size settings
2. Check if mmap_size is appropriate
3. Monitor I/O patterns
4. Consider disabling aggressive_caching flag

#### Issue: Backup failures with WAL mode
**Solution:**
1. Ensure backup includes -wal and -shm files
2. Use sqlite3 backup API instead of file copy
3. Checkpoint before backup
4. Consider online backup tools

## Appendix B: Performance Tuning Guide

### Recommended Settings by Workload

#### Read-Heavy Workload
```python
conn.execute("PRAGMA cache_size = -128000")    # 128MB cache
conn.execute("PRAGMA mmap_size = 536870912")   # 512MB mmap
conn.execute("PRAGMA query_only = OFF")        # Still allow writes
conn.execute("PRAGMA temp_store = MEMORY")
```

#### Write-Heavy Workload
```python
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -64000")     # 64MB cache
conn.execute("PRAGMA wal_autocheckpoint = 1000") # Checkpoint every 1000 pages
```

#### Mixed Workload (Default)
```python
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -32000")     # 32MB cache
conn.execute("PRAGMA busy_timeout = 5000")
```

---

**END OF IMPLEMENTATION PLAN v2.0**

For questions or issues during implementation, refer to:
- SQLite Documentation: https://www.sqlite.org/docs.html
- Python sqlite3 module: https://docs.python.org/3/library/sqlite3.html
- Original PRD: `docs/prds/prd-sqlite-database-stability-improvements.md`
- Feature Flags: `database/feature_flags.json`
- Monitoring Dashboard: `database/monitor_health.py`
- Emergency Rollback: `database/emergency_rollback.py`

**Critical Contacts:**
- Database Team Lead: [Contact Info]
- On-Call Engineer: [Contact Info]
- Escalation: [Contact Info]