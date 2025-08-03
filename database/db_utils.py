"""
Database utility functions for transaction management and connection handling.
"""
import sqlite3
import logging
import time
import functools
import random
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
    from database.feature_flags import is_feature_enabled
    
    # Check if explicit transactions are enabled
    if not is_feature_enabled('explicit_transactions'):
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
        from database.feature_flags import is_feature_enabled
        
        self.conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        
        # Apply optimizations if enabled
        if is_feature_enabled('pragma_optimizations'):
            self._apply_pragmas()
        
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            self.conn.close()
            
    def _apply_pragmas(self):
        """Apply SQLite optimizations based on feature flags."""
        from database.feature_flags import is_feature_enabled
        
        try:
            # Basic optimizations
            self.conn.execute("PRAGMA busy_timeout = 5000")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            
            # WAL mode if enabled
            if is_feature_enabled('wal_mode'):
                result = self.conn.execute("PRAGMA journal_mode = WAL").fetchone()
                if result and result[0].upper() == 'WAL':
                    logger.debug("WAL mode enabled")
                else:
                    logger.warning(f"Failed to enable WAL mode: {result}")
            
            # Aggressive caching if enabled
            if is_feature_enabled('aggressive_caching'):
                self.conn.execute("PRAGMA cache_size = -64000")  # 64MB
                self.conn.execute("PRAGMA temp_store = MEMORY")
                self.conn.execute("PRAGMA mmap_size = 268435456")  # 256MB
                logger.debug("Aggressive caching enabled")
            else:
                self.conn.execute("PRAGMA cache_size = -16000")  # 16MB conservative
                
        except Exception as e:
            logger.error(f"Error applying PRAGMA settings: {e}")
            

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
        operation_name: Name of operation for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from database.feature_flags import is_feature_enabled
            
            # Check if retry logic is enabled
            if not is_feature_enabled('retry_logic'):
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
                        # Record to lock monitor if available
                        try:
                            from database.db_utils import lock_monitor
                            lock_monitor.record_recovery(op_name, attempt + 1)
                        except:
                            pass
                    
                    return result
                    
                except sqlite3.OperationalError as e:
                    if "database is locked" not in str(e):
                        raise
                    
                    last_exception = e
                    
                    # Record lock event
                    try:
                        from database.db_utils import lock_monitor
                        lock_monitor.record_lock(op_name)
                    except:
                        pass
                    
                    if attempt < max_attempts - 1:
                        # Add jitter if enabled
                        if jitter:
                            actual_delay = delay * (0.5 + random.random())
                        else:
                            actual_delay = delay
                        
                        logger.warning(
                            f"Database locked on attempt {attempt + 1}/{max_attempts} for '{op_name}'. "
                            f"Retrying in {actual_delay:.2f} seconds..."
                        )
                        time.sleep(actual_delay)
                        
                        # Exponential backoff
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"Database locked after {max_attempts} attempts for '{op_name}'. Giving up."
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
        self.recovery_stats = {}
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
    
    def record_recovery(self, operation: str, attempts: int):
        """Record successful recovery after retries."""
        if operation not in self.recovery_stats:
            self.recovery_stats[operation] = []
        self.recovery_stats[operation].append(attempts)
    
    def get_stats(self) -> dict:
        """Get lock statistics."""
        current_time = time.time()
        runtime = current_time - self.start_time
        
        # Calculate average recovery attempts
        avg_recovery = {}
        for op, attempts_list in self.recovery_stats.items():
            if attempts_list:
                avg_recovery[op] = sum(attempts_list) / len(attempts_list)
        
        return {
            'total_locks': len(self.lock_times),
            'locks_by_operation': self.lock_counts,
            'runtime_seconds': runtime,
            'locks_per_minute': (len(self.lock_times) / runtime) * 60 if runtime > 0 else 0,
            'recent_locks_1min': len([t for t in self.lock_times if current_time - t < 60]),
            'recent_locks_5min': len([t for t in self.lock_times if current_time - t < 300]),
            'average_recovery_attempts': avg_recovery
        }
    
    def reset(self):
        """Reset all statistics."""
        self.lock_counts = {}
        self.lock_times = []
        self.recovery_stats = {}
        self.start_time = time.time()


# Global lock monitor instance (lazy initialization)
lock_monitor = None

def get_lock_monitor() -> DatabaseLockMonitor:
    """Get or create the global lock monitor."""
    global lock_monitor
    if lock_monitor is None:
        lock_monitor = DatabaseLockMonitor()
    return lock_monitor


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
        from database.feature_flags import is_feature_enabled
        
        if not is_feature_enabled('isolation_levels'):
            return
        
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
    from database.feature_flags import is_feature_enabled
    
    if not is_feature_enabled('isolation_levels'):
        # Fall back to regular transaction
        with transaction(conn):
            yield conn
        return
    
    try:
        IsolationLevel.apply_serializable(conn)
        yield conn
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise