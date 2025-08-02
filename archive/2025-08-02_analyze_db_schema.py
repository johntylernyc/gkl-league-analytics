#!/usr/bin/env python3
"""
Analyze database schema and identify issues
"""

import sqlite3
import os

def analyze_database():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, 'database', 'league_analytics.db')
    
    print('=== DATABASE SCHEMA ANALYSIS ===')
    print(f'Database: {DB_FILE}')
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check all transaction tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%transaction%'")
        tables = cursor.fetchall()
        print(f'\nTransaction tables: {[t[0] for t in tables]}')

        # Check job_log table
        cursor.execute("SELECT COUNT(*) FROM job_log")
        job_count = cursor.fetchone()[0]
        print(f'Records in job_log: {job_count}')

        if job_count > 0:
            cursor.execute("SELECT job_id, job_type, status, start_time FROM job_log ORDER BY start_time DESC LIMIT 3")
            recent_jobs = cursor.fetchall()
            print('Recent jobs:')
            for job in recent_jobs:
                print(f'  {job[0]} - {job[1]} - {job[2]} - {job[3]}')

        # Check schema of each transaction table
        for table_name in ['transactions', 'transactions_test', 'transactions_production']:
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f'\n{table_name} columns:')
                for col in columns:
                    print(f'  {col[1]} ({col[2]})')
                
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f'  Records: {count}')
                
                if count > 0:
                    cursor.execute(f"SELECT DISTINCT date FROM {table_name} ORDER BY date LIMIT 5")
                    dates = cursor.fetchall()
                    print(f'  Sample dates: {[d[0] for d in dates]}')
            except Exception as e:
                print(f'{table_name}: {e}')

        conn.close()
        return True
        
    except Exception as e:
        print(f'Database error: {e}')
        return False

if __name__ == "__main__":
    analyze_database()