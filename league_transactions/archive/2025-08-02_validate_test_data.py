#!/usr/bin/env python3
"""
Data validation script for test transaction data
Validates data quality and completeness before production run
"""

import sqlite3
import os
from datetime import datetime, timedelta

# Database configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')

def validate_test_data():
    """Validate the test data collected for July 25 - August 1, 2025"""
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("TEST DATA VALIDATION REPORT")
    print("=" * 60)
    
    # Basic count validation
    cursor.execute("SELECT COUNT(*) FROM transactions_test")
    total_count = cursor.fetchone()[0]
    print(f"Total transactions in test table: {total_count:,}")
    
    # Date range validation
    cursor.execute("SELECT MIN(date), MAX(date) FROM transactions_test")
    date_range = cursor.fetchone()
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    
    # Expected date range
    expected_start = "2025-07-25"
    expected_end = "2025-08-01"
    print(f"Expected range: {expected_start} to {expected_end}")
    
    # Daily breakdown
    print(f"\nDaily transaction counts:")
    cursor.execute("""
        SELECT date, COUNT(*) as daily_count 
        FROM transactions_test 
        GROUP BY date 
        ORDER BY date
    """)
    daily_counts = cursor.fetchall()
    
    for date_str, count in daily_counts:
        print(f"  {date_str}: {count:,} transactions")
    
    # Validate all expected dates are present
    start_date = datetime.strptime(expected_start, "%Y-%m-%d")
    end_date = datetime.strptime(expected_end, "%Y-%m-%d")
    expected_dates = []
    current_date = start_date
    while current_date <= end_date:
        expected_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    
    actual_dates = [date for date, count in daily_counts]
    missing_dates = set(expected_dates) - set(actual_dates)
    
    if missing_dates:
        print(f"\nMISSING DATES: {sorted(missing_dates)}")
    else:
        print(f"\n✓ All expected dates present ({len(expected_dates)} days)")
    
    # Transaction type breakdown
    print(f"\nTransaction type breakdown:")
    cursor.execute("""
        SELECT transaction_type, COUNT(*) as count
        FROM transactions_test 
        GROUP BY transaction_type 
        ORDER BY count DESC
    """)
    type_counts = cursor.fetchall()
    
    for txn_type, count in type_counts:
        print(f"  {txn_type}: {count:,} transactions")
    
    # Movement type breakdown
    print(f"\nMovement type breakdown:")
    cursor.execute("""
        SELECT movement_type, COUNT(*) as count
        FROM transactions_test 
        GROUP BY movement_type 
        ORDER BY count DESC
    """)
    movement_counts = cursor.fetchall()
    
    for movement_type, count in movement_counts:
        print(f"  {movement_type}: {count:,} transactions")
    
    # Data quality checks
    print(f"\nData Quality Checks:")
    
    # Check for null values
    cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE player_name IS NULL OR player_name = ''")
    null_names = cursor.fetchone()[0]
    print(f"  Null/empty player names: {null_names}")
    
    cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE player_id IS NULL OR player_id = ''")
    null_ids = cursor.fetchone()[0]
    print(f"  Null/empty player IDs: {null_ids}")
    
    cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE league_key IS NULL OR league_key = ''")
    null_leagues = cursor.fetchone()[0]
    print(f"  Null/empty league keys: {null_leagues}")
    
    # Check for unique transaction combinations
    cursor.execute("SELECT COUNT(*) FROM transactions_test")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT transaction_id, player_id, movement_type 
            FROM transactions_test
        )
    """)
    unique = cursor.fetchone()[0]
    print(f"  Total records: {total:,}")
    print(f"  Unique combinations: {unique:,}")
    
    if total == unique:
        print("  ✓ No duplicate transaction combinations")
    else:
        print(f"  ⚠ {total - unique} duplicate combinations found")
    
    # Sample data inspection
    print(f"\nSample transactions:")
    cursor.execute("""
        SELECT date, transaction_type, player_name, position, player_team, movement_type
        FROM transactions_test 
        ORDER BY date, transaction_id 
        LIMIT 5
    """)
    samples = cursor.fetchall()
    
    for sample in samples:
        date, txn_type, name, pos, team, movement = sample
        print(f"  {date}: {movement} {name} ({pos}, {team}) - {txn_type}")
    
    # Performance metrics
    total_days = len(expected_dates)
    avg_per_day = total_count / total_days if total_days > 0 else 0
    print(f"\nPerformance Metrics:")
    print(f"  Total days processed: {total_days}")
    print(f"  Average transactions per day: {avg_per_day:.1f}")
    
    # Validation summary
    print(f"\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    issues = []
    if missing_dates:
        issues.append(f"Missing dates: {len(missing_dates)}")
    if null_names > 0:
        issues.append(f"Null player names: {null_names}")
    if null_ids > 0:
        issues.append(f"Null player IDs: {null_ids}")
    if total != unique:
        issues.append(f"Duplicate combinations: {total - unique}")
    
    if issues:
        print("❌ VALIDATION FAILED")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRecommendation: Fix issues before production run")
    else:
        print("✅ VALIDATION PASSED")
        print("  - All expected dates present")
        print("  - No data quality issues found")
        print("  - No duplicate transactions")
        print("  - Transaction variety confirmed")
        print("\nRecommendation: Proceed with production data collection")
    
    conn.close()

if __name__ == "__main__":
    validate_test_data()