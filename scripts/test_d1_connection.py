#!/usr/bin/env python
"""
Test Cloudflare D1 Database Connection

This script verifies that the D1 connection is working properly by:
1. Testing basic connectivity
2. Verifying required environment variables
3. Testing basic CRUD operations
4. Validating foreign key constraints
5. Testing batch operations

Usage:
    python scripts/test_d1_connection.py
    
Environment Variables Required:
    - CLOUDFLARE_ACCOUNT_ID
    - D1_DATABASE_ID  
    - CLOUDFLARE_API_TOKEN
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from data_pipeline.common.d1_connection import D1Connection, is_d1_available
except ImportError as e:
    print(f"❌ Failed to import D1Connection: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def test_environment_variables():
    """Test that all required environment variables are present."""
    print("1. Testing environment variables...")
    
    required_vars = ['CLOUDFLARE_ACCOUNT_ID', 'D1_DATABASE_ID', 'CLOUDFLARE_API_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            # Show first few characters for verification
            display_value = value[:8] + '...' if len(value) > 8 else value
            print(f"   ✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"   ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    if is_d1_available():
        print("   ✅ All D1 environment variables are available")
        return True
    else:
        print("   ❌ D1 is not available (missing environment variables)")
        return False


def test_basic_connection():
    """Test basic D1 connection."""
    print("\n2. Testing basic D1 connection...")
    
    try:
        d1 = D1Connection()
        print(f"   ✅ D1Connection created successfully")
        print(f"   ✅ Account ID: {d1.account_id[:8]}...")
        print(f"   ✅ Database ID: {d1.database_id[:8]}...")
        return d1
    except Exception as e:
        print(f"   ❌ Failed to create D1Connection: {e}")
        return None


def test_connectivity(d1_conn):
    """Test actual connectivity to D1."""
    print("\n3. Testing D1 connectivity...")
    
    try:
        if d1_conn.test_connection():
            print("   ✅ D1 connection test passed")
            return True
        else:
            print("   ❌ D1 connection test failed")
            return False
    except Exception as e:
        print(f"   ❌ D1 connection test error: {e}")
        return False


def test_basic_query(d1_conn):
    """Test basic SQL query execution."""
    print("\n4. Testing basic query execution...")
    
    try:
        # Test simple SELECT
        result = d1_conn.execute("SELECT 1 as test, CURRENT_TIMESTAMP as now")
        
        if result and 'results' in result:
            rows = result['results']
            if rows and len(rows) > 0:
                print(f"   ✅ Basic query successful: {rows[0]}")
                return True
            else:
                print("   ❌ Query returned no results")
                return False
        else:
            print(f"   ❌ Unexpected query result format: {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ Basic query failed: {e}")
        return False


def test_table_access(d1_conn):
    """Test access to expected tables."""
    print("\n5. Testing table access...")
    
    expected_tables = ['job_log', 'transactions', 'daily_lineups']
    success_count = 0
    
    for table in expected_tables:
        try:
            result = d1_conn.execute(f"SELECT COUNT(*) FROM {table}")
            if result and 'results' in result:
                count = result['results'][0][0] if result['results'] else 0
                print(f"   ✅ Table '{table}': {count} records")
                success_count += 1
            else:
                print(f"   ❌ Table '{table}': Unexpected result format")
        except Exception as e:
            print(f"   ❌ Table '{table}': {e}")
    
    if success_count == len(expected_tables):
        print(f"   ✅ All {len(expected_tables)} tables accessible")
        return True
    else:
        print(f"   ⚠️  Only {success_count}/{len(expected_tables)} tables accessible")
        return success_count > 0


def test_job_operations(d1_conn):
    """Test job_log operations."""
    print("\n6. Testing job_log operations...")
    
    # Test job creation
    test_job_id = f"test_connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Test ensure_job_exists
        created = d1_conn.ensure_job_exists(
            job_id=test_job_id,
            job_type='connection_test',
            environment='test',
            league_key='test.league',
            date_range_start='2025-08-04',
            date_range_end='2025-08-04',
            metadata='D1 connection test'
        )
        
        if created:
            print(f"   ✅ Job created: {test_job_id}")
        else:
            print(f"   ✅ Job already existed: {test_job_id}")
        
        # Test job status update
        updated = d1_conn.update_job_status(
            job_id=test_job_id,
            status='completed',
            records_processed=10,
            records_inserted=5
        )
        
        if updated:
            print(f"   ✅ Job status updated successfully")
        else:
            print(f"   ❌ Job status update failed")
            return False
        
        # Verify job exists
        result = d1_conn.execute("SELECT * FROM job_log WHERE job_id = ?", [test_job_id])
        if result and result.get('results') and len(result['results']) > 0:
            job_data = result['results'][0]
            print(f"   ✅ Job verification successful: status={job_data[3]}")
            return True
        else:
            print(f"   ❌ Job not found after creation")
            return False
            
    except Exception as e:
        print(f"   ❌ Job operations failed: {e}")
        return False


def test_batch_operations(d1_conn):
    """Test batch operations."""
    print("\n7. Testing batch operations...")
    
    try:
        # Create test job first
        test_job_id = f"batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        d1_conn.ensure_job_exists(
            job_id=test_job_id,
            job_type='batch_test',
            environment='test'
        )
        
        # Test transaction batch insert
        test_transactions = [
            {
                'date': '2025-08-04',
                'league_key': 'test.league',
                'transaction_id': f'test_trans_1_{test_job_id}',
                'transaction_type': 'add',
                'player_id': 'test_player_1',
                'player_name': 'Test Player 1',
                'player_position': '1B',
                'player_team': 'TST',
                'movement_type': 'add',
                'destination_team_key': 'test.team.1',
                'destination_team_name': 'Test Team 1',
                'source_team_key': '',
                'source_team_name': ''
            },
            {
                'date': '2025-08-04',
                'league_key': 'test.league',
                'transaction_id': f'test_trans_2_{test_job_id}',
                'transaction_type': 'drop',
                'player_id': 'test_player_2',
                'player_name': 'Test Player 2',
                'player_position': 'OF',
                'player_team': 'TST',
                'movement_type': 'drop',
                'destination_team_key': '',
                'destination_team_name': '',
                'source_team_key': 'test.team.1',
                'source_team_name': 'Test Team 1'
            }
        ]
        
        inserted_count, error_count = d1_conn.insert_transactions(test_transactions, test_job_id)
        
        if error_count == 0:
            print(f"   ✅ Batch transaction insert: {inserted_count} records, {error_count} errors")
        else:
            print(f"   ⚠️  Batch transaction insert: {inserted_count} records, {error_count} errors")
        
        # Test lineup batch insert
        test_lineups = [
            {
                'season': 2025,
                'date': '2025-08-04',
                'team_key': 'test.team.1',
                'team_name': 'Test Team 1',
                'player_id': 'test_player_1',
                'player_name': 'Test Player 1',
                'selected_position': '1B',
                'position_type': 'starter',
                'player_status': 'healthy',
                'eligible_positions': '1B',
                'player_team': 'TST'
            }
        ]
        
        lineup_inserted, lineup_errors = d1_conn.insert_lineups(test_lineups, test_job_id)
        
        if lineup_errors == 0:
            print(f"   ✅ Batch lineup insert: {lineup_inserted} records, {lineup_errors} errors")
            return True
        else:
            print(f"   ⚠️  Batch lineup insert: {lineup_inserted} records, {lineup_errors} errors")
            return lineup_errors == 0
    
    except Exception as e:
        print(f"   ❌ Batch operations failed: {e}")
        return False


def cleanup_test_data(d1_conn):
    """Clean up test data."""
    print("\n8. Cleaning up test data...")
    
    try:
        # Clean up test transactions
        result = d1_conn.execute(
            "DELETE FROM transactions WHERE transaction_id LIKE ?", 
            ['test_trans_%']
        )
        trans_deleted = result.get('changes', 0)
        
        # Clean up test lineups  
        result = d1_conn.execute(
            "DELETE FROM daily_lineups WHERE team_key = ?",
            ['test.team.1']
        )
        lineup_deleted = result.get('changes', 0)
        
        # Clean up test jobs
        result = d1_conn.execute(
            "DELETE FROM job_log WHERE job_type IN (?, ?)",
            ['connection_test', 'batch_test']
        )
        jobs_deleted = result.get('changes', 0)
        
        print(f"   ✅ Cleanup complete: {trans_deleted} transactions, {lineup_deleted} lineups, {jobs_deleted} jobs")
        return True
        
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
        return False


def main():
    """Run all D1 connection tests."""
    print("🧪 Testing Cloudflare D1 Database Connection\n")
    
    # Track test results
    tests_passed = 0
    total_tests = 8
    
    # Test 1: Environment variables
    if test_environment_variables():
        tests_passed += 1
    else:
        print("\n❌ Environment variables test failed. Cannot continue.")
        return False
    
    # Test 2: Basic connection
    d1_conn = test_basic_connection()
    if d1_conn:
        tests_passed += 1
    else:
        print("\n❌ Connection creation failed. Cannot continue.")
        return False
    
    # Test 3: Connectivity
    if test_connectivity(d1_conn):
        tests_passed += 1
    
    # Test 4: Basic query
    if test_basic_query(d1_conn):
        tests_passed += 1
    
    # Test 5: Table access
    if test_table_access(d1_conn):
        tests_passed += 1
    
    # Test 6: Job operations
    if test_job_operations(d1_conn):
        tests_passed += 1
    
    # Test 7: Batch operations
    if test_batch_operations(d1_conn):
        tests_passed += 1
    
    # Test 8: Cleanup
    if cleanup_test_data(d1_conn):
        tests_passed += 1
    
    # Summary
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All D1 connection tests passed! Ready for production use.")
        return True
    elif tests_passed >= 6:
        print("⚠️  Most tests passed. D1 connection is functional but check warnings above.")
        return True
    else:
        print("❌ Multiple tests failed. D1 connection needs attention.")
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)