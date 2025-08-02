#!/usr/bin/env python3
"""
Investigate production data collection results
"""

import sqlite3
import os

def investigate_production_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, 'database', 'league_analytics.db')
    
    print("="*80)
    print("PRODUCTION DATA INVESTIGATION")
    print("="*80)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check production job details
    cursor.execute("""
        SELECT job_id, job_type, environment, status, records_processed, records_inserted, 
               date_range_start, date_range_end, start_time, error_message
        FROM job_log 
        WHERE environment = 'production' 
        ORDER BY start_time DESC 
        LIMIT 3
    """)
    
    jobs = cursor.fetchall()
    print("Production jobs:")
    for job in jobs:
        job_id, job_type, env, status, processed, inserted, start_date, end_date, start_time, error = job
        print(f"  {job_id}")
        print(f"    Status: {status}")
        print(f"    Processed: {processed:,} | Inserted: {inserted:,}")
        print(f"    Date range: {start_date} to {end_date}")
        print(f"    Error: {error or 'None'}")
        print()
    
    # Check production table content
    cursor.execute("SELECT COUNT(*) FROM transactions_production")
    total_count = cursor.fetchone()[0]
    print(f"Total records in transactions_production: {total_count:,}")
    
    # Check date distribution
    cursor.execute("""
        SELECT DISTINCT date, COUNT(*) as count 
        FROM transactions_production 
        GROUP BY date 
        ORDER BY date 
        LIMIT 10
    """)
    
    dates = cursor.fetchall()
    print(f"\nFirst 10 dates in production:")
    for date, count in dates:
        print(f"  {date}: {count} transactions")
    
    # Check for duplicates by transaction_id
    cursor.execute("""
        SELECT transaction_id, COUNT(*) as count 
        FROM transactions_production 
        GROUP BY transaction_id 
        HAVING COUNT(*) > 1 
        ORDER BY count DESC 
        LIMIT 5
    """)
    
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"\nDuplicate transaction IDs (top 5):")
        for txn_id, count in duplicates:
            print(f"  {txn_id}: {count} occurrences")
    else:
        print(f"\nNo duplicate transaction IDs found")
    
    # Check unique constraint violations (what INSERT OR IGNORE would skip)
    cursor.execute("""
        SELECT transaction_id, player_id, movement_type, COUNT(*) as count
        FROM transactions_production 
        GROUP BY transaction_id, player_id, movement_type 
        HAVING COUNT(*) > 1 
        LIMIT 5
    """)
    
    unique_violations = cursor.fetchall()
    if unique_violations:
        print(f"\nUnique constraint violations:")
        for txn_id, player_id, movement, count in unique_violations:
            print(f"  {txn_id} | {player_id} | {movement}: {count} occurrences")
    else:
        print(f"\nNo unique constraint violations")
    
    # Sample production records
    cursor.execute("""
        SELECT date, player_name, transaction_type, destination_team_name, job_id
        FROM transactions_production 
        ORDER BY date 
        LIMIT 10
    """)
    
    samples = cursor.fetchall()
    print(f"\nSample production records:")
    for date, player, txn_type, team, job_id in samples:
        print(f"  {date} | {player} | {txn_type} | {team}")
    
    conn.close()
    print(f"\n" + "="*80)

if __name__ == "__main__":
    investigate_production_data()