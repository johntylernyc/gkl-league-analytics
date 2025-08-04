#!/usr/bin/env python3
"""
Verify job logging is working correctly
"""

import sqlite3
import os

def verify_job_logging():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print("="*60)
    print("JOB LOGGING VERIFICATION")
    print("="*60)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check recent jobs
    cursor.execute("""
        SELECT job_id, job_type, environment, status, start_time, 
               records_processed, records_inserted, date_range_start, date_range_end
        FROM job_log 
        ORDER BY start_time DESC 
        LIMIT 5
    """)
    
    jobs = cursor.fetchall()
    print(f"Recent jobs in job_log:")
    print("-" * 120)
    print(f"{'Job Type':<20} {'Env':<5} {'Status':<10} {'Start Time':<20} {'Processed':<10} {'Inserted':<10} {'Date Range':<20}")
    print("-" * 120)
    
    for job in jobs:
        job_id, job_type, env, status, start_time, processed, inserted, date_start, date_end = job
        date_range = f"{date_start} to {date_end}" if date_start and date_end else "N/A"
        print(f"{job_type:<20} {env:<5} {status:<10} {start_time:<20} {processed or 0:<10} {inserted or 0:<10} {date_range:<20}")
        print(f"  Job ID: {job_id}")
    
    # Check if transactions have proper job_id
    cursor.execute("""
        SELECT job_id, COUNT(*) 
        FROM transactions_test 
        WHERE job_id IS NOT NULL 
        GROUP BY job_id 
        ORDER BY COUNT(*) DESC
    """)
    
    job_data = cursor.fetchall()
    print(f"\nTransaction records by job_id:")
    print("-" * 80)
    for job_id, count in job_data:
        print(f"  {job_id}: {count} transactions")
    
    conn.close()
    print("\n" + "="*60)
    print("JOB LOGGING VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    verify_job_logging()