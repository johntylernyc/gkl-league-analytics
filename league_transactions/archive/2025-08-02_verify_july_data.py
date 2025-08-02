#!/usr/bin/env python3
"""
Verify July 2025 test data insertion and quality
"""

import sqlite3
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_july_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print("="*60)
    print("JULY 2025 TEST DATA VERIFICATION")
    print("="*60)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Total count of July 2025 records
    cursor.execute("SELECT COUNT(*) FROM transactions_test WHERE date LIKE '2025-07-%'")
    july_count = cursor.fetchone()[0]
    print(f"Total July 2025 records: {july_count:,}")
    
    # Count by job ID
    cursor.execute("SELECT job_id, COUNT(*) FROM transactions_test WHERE date LIKE '2025-07-%' GROUP BY job_id")
    job_counts = cursor.fetchall()
    print(f"\nRecords by job ID:")
    for job_id, count in job_counts:
        print(f"  {job_id}: {count:,} records")
    
    # Date range verification
    cursor.execute("SELECT MIN(date), MAX(date) FROM transactions_test WHERE date LIKE '2025-07-%'")
    date_range = cursor.fetchone()
    print(f"\nDate range: {date_range[0]} to {date_range[1]}")
    
    # Daily transaction counts
    cursor.execute("""
        SELECT date, COUNT(*) as count 
        FROM transactions_test 
        WHERE date LIKE '2025-07-%' 
        GROUP BY date 
        ORDER BY date
    """)
    daily_counts = cursor.fetchall()
    print(f"\nDaily transaction counts:")
    for date, count in daily_counts:
        print(f"  {date}: {count:3d} transactions")
    
    # Transaction type breakdown
    cursor.execute("""
        SELECT transaction_type, COUNT(*) as count 
        FROM transactions_test 
        WHERE date LIKE '2025-07-%' 
        GROUP BY transaction_type 
        ORDER BY count DESC
    """)
    type_counts = cursor.fetchall()
    print(f"\nTransaction types:")
    for txn_type, count in type_counts:
        print(f"  {txn_type}: {count:,} ({count/july_count*100:.1f}%)")
    
    # Movement type breakdown  
    cursor.execute("""
        SELECT movement_type, COUNT(*) as count 
        FROM transactions_test 
        WHERE date LIKE '2025-07-%' 
        GROUP BY movement_type 
        ORDER BY count DESC
    """)
    movement_counts = cursor.fetchall()
    print(f"\nMovement types:")
    for movement_type, count in movement_counts:
        print(f"  {movement_type}: {count:,} ({count/july_count*100:.1f}%)")
    
    # Team data quality check
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(destination_team_key) as has_dest_key,
            COUNT(destination_team_name) as has_dest_name,
            COUNT(source_team_key) as has_source_key,
            COUNT(source_team_name) as has_source_name
        FROM transactions_test 
        WHERE date LIKE '2025-07-%'
    """)
    team_data = cursor.fetchone()
    total, dest_key, dest_name, source_key, source_name = team_data
    
    print(f"\nTeam data quality:")
    print(f"  Total records: {total:,}")
    print(f"  Has destination team key: {dest_key:,} ({dest_key/total*100:.1f}%)")
    print(f"  Has destination team name: {dest_name:,} ({dest_name/total*100:.1f}%)")
    print(f"  Has source team key: {source_key:,} ({source_key/total*100:.1f}%)")
    print(f"  Has source team name: {source_name:,} ({source_name/total*100:.1f}%)")
    
    # Sample records
    cursor.execute("""
        SELECT player_name, transaction_type, movement_type, 
               destination_team_name, source_team_name, player_position
        FROM transactions_test 
        WHERE date LIKE '2025-07-%' 
        LIMIT 10
    """)
    samples = cursor.fetchall()
    
    print(f"\nSample records:")
    for sample in samples:
        player, txn_type, movement, dest, source, position = sample
        print(f"  {player} ({position}) - {txn_type}/{movement} - {source} -> {dest}")
    
    # Unique teams count
    cursor.execute("""
        SELECT COUNT(DISTINCT destination_team_key) as unique_dest,
               COUNT(DISTINCT source_team_key) as unique_source
        FROM transactions_test 
        WHERE date LIKE '2025-07-%'
    """)
    unique_teams = cursor.fetchone()
    dest_teams, source_teams = unique_teams
    
    print(f"\nUnique teams:")
    print(f"  Destination teams: {dest_teams}")
    print(f"  Source teams: {source_teams}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
    
    return july_count > 0

if __name__ == "__main__":
    success = verify_july_data()
    if success:
        print("+ July 2025 test data verification successful")
    else:
        print("- No July 2025 test data found")