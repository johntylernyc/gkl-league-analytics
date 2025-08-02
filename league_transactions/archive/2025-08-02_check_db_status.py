#!/usr/bin/env python3
"""
Check database status and attempt to release any locks
"""

import sqlite3
import os
import time

def check_database_status():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')
    
    print(f"Checking database status: {DB_FILE}")
    
    # Try connecting with a short timeout to see if it's locked
    try:
        conn = sqlite3.connect(DB_FILE, timeout=5)
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        result = cursor.fetchone()
        
        print("Database is accessible")
        print(f"Sample table: {result}")
        
        # Check for any lingering transactions
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("ROLLBACK")
        
        print("No active transactions found")
        
        conn.close()
        print("Database check completed - ready for schema update")
        return True
        
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            print("Database is currently locked")
            print("Waiting for lock to be released...")
            time.sleep(5)
            return False
        else:
            print(f"Database error: {e}")
            return False

if __name__ == "__main__":
    for attempt in range(3):
        print(f"\nAttempt {attempt + 1}:")
        if check_database_status():
            print("Database is ready")
            break
        else:
            if attempt < 2:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Database remains locked after multiple attempts")