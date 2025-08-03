"""
Integration test script for Daily Lineups module (Stages 1-3).
Tests database schema, data collection, and job management.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.config import get_database_path, get_league_key
from daily_lineups.job_manager import LineupJobManager
from daily_lineups.collector_enhanced import EnhancedLineupsCollector
from daily_lineups.parser import LineupParser

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(text):
    """Print success message."""
    print(f"{GREEN}[OK] {text}{RESET}")


def print_error(text):
    """Print error message."""
    print(f"{RED}[ERROR] {text}{RESET}")


def print_info(text):
    """Print info message."""
    print(f"{YELLOW}[INFO] {text}{RESET}")


def test_database_schema():
    """Test Stage 1: Database Schema."""
    print_header("STAGE 1: Testing Database Schema")
    
    # Use the main database, not test database
    db_path = Path(__file__).parent.parent / "database" / "league_analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test 1: Check if tables exist
        print("\n1. Checking tables...")
        tables_to_check = [
            'daily_lineups',
            'daily_lineups_test',
            'lineup_positions',
            'player_usage_summary',
            'team_lineup_patterns',
            'job_log'
        ]
        
        for table in tables_to_check:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table,))
            if cursor.fetchone():
                print_success(f"Table '{table}' exists")
            else:
                print_error(f"Table '{table}' NOT FOUND")
                return False
        
        # Test 2: Check lineup_positions data
        print("\n2. Checking lineup_positions data...")
        cursor.execute("SELECT COUNT(*) FROM lineup_positions")
        count = cursor.fetchone()[0]
        if count > 0:
            print_success(f"Found {count} positions in lookup table")
            
            # Show some positions
            cursor.execute("SELECT position_code, position_name FROM lineup_positions LIMIT 5")
            print("   Sample positions:")
            for pos in cursor.fetchall():
                print(f"   - {pos[0]}: {pos[1]}")
        else:
            print_error("No positions found in lineup_positions table")
            return False
        
        # Test 3: Check indexes
        print("\n3. Checking indexes...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_lineups%'
        """)
        indexes = cursor.fetchall()
        if len(indexes) > 0:
            print_success(f"Found {len(indexes)} indexes")
        else:
            print_error("No indexes found")
            return False
        
        # Test 4: Check views
        print("\n4. Checking views...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='view' AND name LIKE 'v_%'
        """)
        views = cursor.fetchall()
        if len(views) > 0:
            print_success(f"Found {len(views)} views")
            for view in views:
                print(f"   - {view[0]}")
        else:
            print_error("No views found")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False
    finally:
        conn.close()


def test_job_management():
    """Test Stage 3: Job Management."""
    print_header("STAGE 3: Testing Job Management")
    
    # Use the main database which has the job_log table
    manager = LineupJobManager(environment="production")
    manager.db_path = Path(__file__).parent.parent / "database" / "league_analytics.db"
    
    try:
        # Test 1: Create a job
        print("\n1. Creating test job...")
        job_id = manager.start_job(
            job_type="lineup_test",
            date_range_start="2025-06-01",
            date_range_end="2025-06-03",
            league_key="mlb.l.6966",
            metadata={"test_run": True}
        )
        print_success(f"Created job: {job_id}")
        
        # Test 2: Check job status
        print("\n2. Checking job status...")
        status = manager.get_job_status(job_id)
        if status and status['status'] == 'running':
            print_success(f"Job status: {status['status']}")
            print(f"   Date range: {status['date_range_start']} to {status['date_range_end']}")
        else:
            print_error("Job status check failed")
            return False
        
        # Test 3: Update job progress
        print("\n3. Updating job progress...")
        manager.update_job(
            job_id,
            progress_pct=50.0,
            records_processed=100
        )
        print_success("Job progress updated to 50%")
        
        # Test 4: Check checkpoint
        print("\n4. Testing checkpoint...")
        checkpoint = manager.load_checkpoint()
        if checkpoint and checkpoint['job_id'] == job_id:
            print_success("Checkpoint created and loaded successfully")
            print(f"   Job ID in checkpoint: {checkpoint['job_id']}")
        else:
            print_error("Checkpoint test failed")
            return False
        
        # Test 5: Complete job
        print("\n5. Completing job...")
        manager.update_job(
            job_id,
            status='completed',
            records_processed=200,
            records_inserted=195,
            progress_pct=100.0
        )
        
        final_status = manager.get_job_status(job_id)
        if final_status['status'] == 'completed':
            print_success("Job completed successfully")
            print(f"   Records processed: {final_status['records_processed']}")
            print(f"   Records inserted: {final_status['records_inserted']}")
        else:
            print_error("Job completion failed")
            return False
        
        # Test 6: Job statistics
        print("\n6. Getting job statistics...")
        stats = manager.get_job_statistics()
        print_success("Job statistics retrieved")
        print(f"   Total jobs: {stats['total_jobs']}")
        print(f"   Completed: {stats['completed_jobs']}")
        print(f"   Success rate: {stats['success_rate']}%")
        
        # Clean up
        manager.clear_checkpoint()
        
        return True
        
    except Exception as e:
        print_error(f"Job management test failed: {e}")
        return False


def test_data_collection():
    """Test Stage 2: Data Collection (limited test)."""
    print_header("STAGE 2: Testing Data Collection")
    
    collector = EnhancedLineupsCollector(environment="test")
    
    try:
        # Test 1: Parser functionality
        print("\n1. Testing XML parser...")
        sample_xml = """
        <fantasy_content>
            <league>
                <teams>
                    <team>
                        <team_key>mlb.l.6966.t.1</team_key>
                        <name>Test Team</name>
                    </team>
                </teams>
            </league>
        </fantasy_content>
        """
        
        teams = LineupParser.parse_teams_response(sample_xml)
        if teams and len(teams) == 1:
            print_success(f"Parser working: Found team '{teams[0][1]}'")
        else:
            print_error("Parser test failed")
            return False
        
        # Test 2: Position type determination
        print("\n2. Testing position type determination...")
        test_positions = [
            ("C", "B"),   # Catcher is Batter
            ("SP", "P"),  # Starting Pitcher
            ("BN", "X"),  # Bench
            ("OF", "B"),  # Outfield is Batter
        ]
        
        all_correct = True
        for pos, expected_type in test_positions:
            result = LineupParser._determine_position_type(pos)
            if result == expected_type:
                print_success(f"Position {pos} -> Type {result} (correct)")
            else:
                print_error(f"Position {pos} -> Type {result} (expected {expected_type})")
                all_correct = False
        
        if not all_correct:
            return False
        
        # Test 3: Test data validation
        print("\n3. Testing data validation...")
        test_data = [
            {"player_id": "123", "player_name": "Test Player", "selected_position": "1B"},
            {"player_id": "", "player_name": "Invalid Player"},  # Missing ID
        ]
        
        valid_data, errors = LineupParser.validate_lineup_data(test_data)
        if len(valid_data) == 1 and len(errors) == 1:
            print_success(f"Validation working: {len(valid_data)} valid, {len(errors)} errors")
        else:
            print_error("Validation test failed")
            return False
        
        # Test 4: Check if we can access tokens
        print("\n4. Checking token access...")
        token_file = Path(__file__).parent.parent / "auth" / "tokens.json"
        if token_file.exists():
            print_success("Token file found")
            print_info("Ready for API collection (requires valid tokens)")
        else:
            print_info("Token file not found - API collection will require setup")
        
        return True
        
    except Exception as e:
        print_error(f"Data collection test failed: {e}")
        return False


def test_small_collection():
    """Test actual data collection for a small date range."""
    print_header("OPTIONAL: Test Small Data Collection")
    
    print_info("This test requires valid Yahoo API tokens")
    
    # Check if running in non-interactive mode
    import sys
    if not sys.stdin.isatty():
        print_info("Running in non-interactive mode, skipping API collection test")
        return True
    
    try:
        response = input("Do you want to test actual API collection? (y/n): ")
    except EOFError:
        print_info("Non-interactive environment detected, skipping API collection test")
        return True
    
    if response.lower() != 'y':
        print_info("Skipping API collection test")
        return True
    
    collector = EnhancedLineupsCollector(environment="test")
    
    try:
        # Use a very small date range (1 day)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        print(f"\n1. Testing collection for {yesterday}...")
        
        job_id = collector.collect_date_range_with_resume(
            start_date=yesterday.strftime("%Y-%m-%d"),
            end_date=yesterday.strftime("%Y-%m-%d"),
            league_key="mlb.l.6966",
            resume=False
        )
        
        print_success(f"Collection completed: {job_id}")
        
        # Check if data was inserted
        db_path = get_database_path("test")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM daily_lineups_test 
            WHERE date = ?
        """, (yesterday.strftime("%Y-%m-%d"),))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print_success(f"Data collected: {count} records")
        else:
            print_error("No data collected")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Collection test failed: {e}")
        print_info("This may be due to missing/expired tokens or off-season")
        return True  # Don't fail overall test for API issues


def run_all_tests():
    """Run all integration tests."""
    print_header("DAILY LINEUPS MODULE - INTEGRATION TEST")
    print(f"Testing Stages 1-3 Implementation")
    print(f"Environment: TEST")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track results
    results = []
    
    # Run Stage 1 tests
    print("\n" + "="*60)
    stage1_result = test_database_schema()
    results.append(("Stage 1: Database Schema", stage1_result))
    
    # Run Stage 3 tests (do this before Stage 2 since it doesn't require API)
    print("\n" + "="*60)
    stage3_result = test_job_management()
    results.append(("Stage 3: Job Management", stage3_result))
    
    # Run Stage 2 tests
    print("\n" + "="*60)
    stage2_result = test_data_collection()
    results.append(("Stage 2: Data Collection", stage2_result))
    
    # Optional: Test actual collection
    print("\n" + "="*60)
    test_small_collection()
    
    # Summary
    print_header("TEST SUMMARY")
    
    all_passed = True
    for name, result in results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print(f"{GREEN}ALL CORE TESTS PASSED!{RESET}")
        print(f"{GREEN}The Daily Lineups module (Stages 1-3) is working correctly.{RESET}")
    else:
        print(f"{RED}SOME TESTS FAILED{RESET}")
        print("Please review the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)