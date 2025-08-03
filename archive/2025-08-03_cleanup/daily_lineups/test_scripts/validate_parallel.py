#!/usr/bin/env python3
"""
Validation Script for Daily Lineups Parallel Collection
Non-interactive validation of the parallel collection infrastructure
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daily_lineups.archive.test_scripts.parallel_collection import ParallelCollectionManager
from daily_lineups.config import get_league_key, SEASON_DATES

def validate_parallel_infrastructure():
    """Validate the parallel collection infrastructure without running actual collection."""
    
    print("=" * 60)
    print("Validating Daily Lineups Parallel Collection Infrastructure")
    print("=" * 60)
    
    results = {
        "token_check": False,
        "manager_init": False,
        "date_splitting": False,
        "database_access": False,
        "job_tracking": False
    }
    
    # 1. Check token availability
    print("\n1. Token Availability:")
    token_path = Path(__file__).parent.parent / "auth" / "tokens.json"
    if token_path.exists():
        print("   [OK] Tokens file found")
        results["token_check"] = True
    else:
        print(f"   [ERROR] Tokens file not found at {token_path}")
        print("   Please run auth/initialize_tokens.py first")
    
    # 2. Test manager initialization
    print("\n2. Parallel Manager Initialization:")
    try:
        manager = ParallelCollectionManager(
            environment="test",
            num_processes=2
        )
        print("   [OK] Manager initialized successfully")
        results["manager_init"] = True
    except Exception as e:
        print(f"   [ERROR] Failed to initialize: {e}")
        return results
    
    # 3. Test date range splitting
    print("\n3. Date Range Splitting:")
    test_start = "2025-07-01"
    test_end = "2025-07-10"
    
    try:
        chunks = manager.split_date_range(test_start, test_end, 3)
        print(f"   [OK] Split {test_start} to {test_end} into {len(chunks)} chunks:")
        for i, (start, end) in enumerate(chunks, 1):
            start_dt = datetime.strptime(start, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end, "%Y-%m-%d").date()
            days = (end_dt - start_dt).days + 1
            print(f"       Process {i}: {start} to {end} ({days} days)")
        results["date_splitting"] = True
    except Exception as e:
        print(f"   [ERROR] Date splitting failed: {e}")
    
    # 4. Test database access
    print("\n4. Database Access:")
    try:
        # Check for uncollected dates
        uncollected = manager.find_uncollected_dates("2025-07-01", "2025-07-03")
        print(f"   [OK] Database query successful")
        print(f"   Found {len(uncollected)} uncollected dates in test range")
        results["database_access"] = True
    except Exception as e:
        print(f"   [ERROR] Database access failed: {e}")
    
    # 5. Check job tracking infrastructure
    print("\n5. Job Tracking Infrastructure:")
    import sqlite3
    try:
        conn = sqlite3.connect('database/league_analytics.db')
        cursor = conn.cursor()
        
        # Check job_log table structure
        cursor.execute("PRAGMA table_info(job_log)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_cols = ['job_id', 'job_type', 'status', 'progress_pct', 'records_processed']
        missing = [col for col in required_cols if col not in columns]
        
        if not missing:
            print("   [OK] Job log table has all required columns")
            
            # Check for recent lineup jobs
            cursor.execute("""
                SELECT COUNT(*), MAX(created_at) 
                FROM job_log 
                WHERE job_type LIKE '%lineup%'
            """)
            count, last_job = cursor.fetchall()[0]
            if count > 0:
                print(f"   [OK] Found {count} lineup collection jobs")
                print(f"       Last job: {last_job}")
            else:
                print("   [INFO] No previous lineup collection jobs found")
            
            results["job_tracking"] = True
        else:
            print(f"   [ERROR] Missing columns: {missing}")
        
        conn.close()
    except Exception as e:
        print(f"   [ERROR] Job tracking check failed: {e}")
    
    return results

def check_parallel_processes():
    """Check if parallel processes can be spawned."""
    print("\n6. Process Spawning Test:")
    
    from multiprocessing import Process, Queue
    import time
    
    def test_worker(worker_id, result_queue):
        """Simple test worker."""
        import time
        time.sleep(0.5)
        result_queue.put(f"Worker {worker_id} completed")
    
    try:
        processes = []
        result_queue = Queue()
        
        # Spawn test processes
        for i in range(2):
            p = Process(target=test_worker, args=(i+1, result_queue))
            processes.append(p)
            p.start()
        
        # Wait for processes
        for p in processes:
            p.join(timeout=2)
        
        # Check results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        if len(results) == 2:
            print("   [OK] Successfully spawned and completed 2 parallel processes")
            for result in results:
                print(f"       {result}")
            return True
        else:
            print(f"   [WARNING] Expected 2 results, got {len(results)}")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Process spawning failed: {e}")
        return False

def main():
    """Main validation routine."""
    print("Daily Lineups Parallel Collection Infrastructure Validation")
    print("This script validates the parallel collection setup without")
    print("actually collecting data from the Yahoo API.")
    print("")
    
    # Run infrastructure validation
    results = validate_parallel_infrastructure()
    
    # Test process spawning
    process_test = check_parallel_processes()
    results["process_spawning"] = process_test
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "[OK]" if passed else "[FAILED]"
        check_name = check.replace("_", " ").title()
        print(f"{status:8} {check_name}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All validation checks passed!")
        print("The parallel collection infrastructure is ready for use.")
        print("\nTo run actual data collection, use:")
        print("  python daily_lineups/archive/test_scripts/parallel_collection.py collect \\")
        print("    --start 2025-07-01 --end 2025-07-31 --processes 2")
    else:
        print("FAILED: Some validation checks failed.")
        print("Please fix the issues above before running parallel collection.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())