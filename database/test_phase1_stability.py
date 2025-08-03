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

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import new modules (may not exist yet)
try:
    from database.db_utils import DatabaseConnection, transaction
    from database.feature_flags import DatabaseFeatureFlags
    HAS_NEW_MODULES = True
except ImportError:
    HAS_NEW_MODULES = False
    print("Warning: New database modules not found, some tests will be skipped")


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
        if not HAS_NEW_MODULES:
            print("Skipping compatibility matrix - modules not available")
            return
            
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
    
    def _test_configuration(self, db_path: str, flags: 'DatabaseFeatureFlags') -> Dict:
        """
        Test a specific configuration.
        """
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_start = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            memory_start = 0
        
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
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_end = process.memory_info().rss / 1024 / 1024
        except ImportError:
            memory_end = 0
        
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
        if not self.results:
            print("No test results to report")
            return
            
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


def test_pragma_settings():
    """Verify PRAGMA settings are correctly applied with validation."""
    print("\n=== Testing PRAGMA Settings ===")
    
    if not HAS_NEW_MODULES:
        print("⚠️ New modules not available - testing basic SQLite")
        
        # Test basic SQLite functionality
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Test basic PRAGMA settings
            cursor.execute("PRAGMA busy_timeout = 5000")
            result = cursor.execute("PRAGMA busy_timeout").fetchone()[0]
            print(f"  Busy timeout: {result} ms")
            
            cursor.execute("PRAGMA journal_mode = WAL")
            result = cursor.execute("PRAGMA journal_mode").fetchone()[0]
            print(f"  Journal mode: {result}")
            
            conn.close()
            os.unlink(db_path)
            
            print("✅ Basic PRAGMA settings work")
        except Exception as e:
            print(f"❌ Error testing PRAGMA: {e}")
        return
    
    # Test with feature flags
    from database.feature_flags import get_feature_flags
    feature_flags = get_feature_flags()
    
    if not feature_flags.is_enabled('pragma_optimizations'):
        print("⚠️ PRAGMA optimizations not enabled - skipping test")
        return
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    with DatabaseConnection(db_path) as conn:
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
    os.unlink(db_path)
    if os.path.exists(db_path + "-wal"):
        os.unlink(db_path + "-wal")
    if os.path.exists(db_path + "-shm"):
        os.unlink(db_path + "-shm")


def test_concurrent_writes():
    """Test concurrent write operations with new transaction management."""
    print("\n=== Testing Concurrent Writes ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_file = tmp.name
    
    # Setup test table
    if HAS_NEW_MODULES:
        with DatabaseConnection(db_file) as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    else:
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.close()
    
    errors = []
    success_count = [0]
    
    def write_worker(worker_id, iterations=10):
        """Worker function to perform database writes."""
        for i in range(iterations):
            try:
                if HAS_NEW_MODULES:
                    with DatabaseConnection(db_file) as conn:
                        with transaction(conn):
                            conn.execute(
                                "INSERT INTO test (value) VALUES (?)",
                                (f"worker_{worker_id}_item_{i}",)
                            )
                            success_count[0] += 1
                            time.sleep(0.01)  # Small delay to increase contention
                else:
                    conn = sqlite3.connect(db_file)
                    conn.execute(
                        "INSERT INTO test (value) VALUES (?)",
                        (f"worker_{worker_id}_item_{i}",)
                    )
                    conn.commit()
                    conn.close()
                    success_count[0] += 1
                    time.sleep(0.01)
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
    if HAS_NEW_MODULES:
        with DatabaseConnection(db_file) as conn:
            count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
    else:
        conn = sqlite3.connect(db_file)
        count = conn.execute("SELECT COUNT(*) FROM test").fetchone()[0]
        conn.close()
    
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
    os.unlink(db_file)
    for ext in ['-wal', '-shm']:
        if os.path.exists(db_file + ext):
            os.unlink(db_file + ext)
    
    return count == expected


def test_transaction_rollback():
    """Test that transactions properly rollback on error."""
    print("\n=== Testing Transaction Rollback ===")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_file = tmp.name
    
    if HAS_NEW_MODULES:
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
    else:
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT UNIQUE)")
        conn.execute("INSERT INTO test (value) VALUES ('unique_value')")
        
        try:
            conn.execute("BEGIN")
            conn.execute("INSERT INTO test (value) VALUES ('new_value')")
            conn.execute("INSERT INTO test (value) VALUES ('unique_value')")  # Duplicate!
            conn.execute("COMMIT")
        except sqlite3.IntegrityError:
            conn.execute("ROLLBACK")
            print("✅ Transaction rolled back as expected on integrity error")
        
        cursor = conn.execute("SELECT COUNT(*) FROM test WHERE value = 'new_value'")
        if cursor.fetchone()[0] == 0:
            print("✅ Rollback successful - 'new_value' not in database")
        else:
            print("❌ Rollback failed - 'new_value' found in database")
        
        conn.close()
    
    # Cleanup
    os.unlink(db_file)


def run_performance_comparison():
    """
    Compare performance with and without optimizations.
    """
    print("\n=== Performance Comparison ===")
    
    if not HAS_NEW_MODULES:
        print("⚠️ New modules not available - skipping comparison")
        return
    
    from database.feature_flags import DatabaseFeatureFlags
    
    # Test without optimizations
    flags_off = DatabaseFeatureFlags()
    for feature in flags_off.flags:
        flags_off.flags[feature] = False
    
    print("\nTesting WITHOUT optimizations...")
    # Simple benchmark
    start = time.time()
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    for i in range(100):
        conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"value_{i}"))
    conn.commit()
    conn.close()
    time_without = time.time() - start
    os.unlink(db_path)
    
    # Test with optimizations
    flags_on = DatabaseFeatureFlags()
    flags_on.flags['pragma_optimizations'] = True
    flags_on.flags['explicit_transactions'] = True
    
    print("\nTesting WITH optimizations...")
    start = time.time()
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    with DatabaseConnection(db_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        with transaction(conn):
            for i in range(100):
                conn.execute("INSERT INTO test VALUES (?, ?)", (i, f"value_{i}"))
    time_with = time.time() - start
    os.unlink(db_path)
    
    # Compare results
    improvement = ((time_without - time_with) / time_without) * 100 if time_without > 0 else 0
    print(f"\n📊 Performance Results:")
    print(f"  Without optimizations: {time_without:.3f}s")
    print(f"  With optimizations: {time_with:.3f}s")
    print(f"  Improvement: {improvement:.1f}%")
    
    if improvement > 0:
        print("✅ Optimizations improve performance")
    else:
        print("⚠️ Optimizations may need tuning")


if __name__ == "__main__":
    print("SQLite Stability Improvements - Phase 1 Testing")
    print("=" * 50)
    
    # Check Python and SQLite versions
    print(f"Python version: {sys.version}")
    print(f"SQLite version: {sqlite3.sqlite_version}")
    print()
    
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
    
    if HAS_NEW_MODULES:
        print("\n⚠️ IMPORTANT: Review compatibility_report.json before proceeding")
    else:
        print("\n⚠️ Some tests were skipped - install new modules for full testing")