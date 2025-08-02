#!/usr/bin/env python3
"""
Check the actual dates stored in the database after timestamp fix
"""

import sqlite3
import os

def check_dates():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print("="*60)
    print("DATABASE DATE VERIFICATION")
    print("="*60)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check distinct dates in transactions_test
    cursor.execute("""
        SELECT DISTINCT date, COUNT(*) as count 
        FROM transactions_test 
        GROUP BY date 
        ORDER BY date
    """)
    
    dates = cursor.fetchall()
    print(f"Distinct dates in transactions_test:")
    print("-" * 40)
    for date, count in dates:
        print(f"  {date}: {count} transactions")
    
    # Check most recent job's data
    cursor.execute("""
        SELECT job_id, COUNT(*) 
        FROM transactions_test 
        GROUP BY job_id 
        ORDER BY COUNT(*) DESC 
        LIMIT 1
    """)
    
    latest_job = cursor.fetchone()
    if latest_job:
        job_id, count = latest_job
        print(f"\nMost recent job: {job_id} ({count} records)")
        
        # Check dates for this specific job
        cursor.execute("""
            SELECT DISTINCT date, COUNT(*) as count 
            FROM transactions_test 
            WHERE job_id = ?
            GROUP BY date 
            ORDER BY date
        """, (job_id,))
        
        job_dates = cursor.fetchall()
        print(f"Dates for job {job_id}:")
        print("-" * 40)
        for date, count in job_dates:
            print(f"  {date}: {count} transactions")
    
    # Sample records with dates
    cursor.execute("""
        SELECT date, player_name, transaction_type, job_id
        FROM transactions_test 
        ORDER BY ROWID 
        LIMIT 10
    """)
    
    samples = cursor.fetchall()
    print(f"\nSample records with dates:")
    print("-" * 60)
    for date, player, txn_type, job_id in samples:
        print(f"  {date} | {player} | {txn_type} | {job_id}")
    
    conn.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    check_dates()