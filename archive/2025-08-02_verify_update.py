import sqlite3
from datetime import datetime, date, timedelta

# Connect to database
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()

print("Transaction Update Verification")
print("="*60)

# Check latest transactions
cursor.execute("""
    SELECT date, COUNT(DISTINCT transaction_id) as trans_count, COUNT(*) as row_count
    FROM transactions_production
    WHERE date >= date('now', '-7 days')
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
""")

print("\nRecent transaction data (last 7 days):")
print(f"{'Date':<12} {'Transactions':<15} {'Rows':<10}")
print("-"*40)
for row in cursor.fetchall():
    print(f"{row[0]:<12} {row[1]:<15} {row[2]:<10}")

# Check job log for recent activity
cursor.execute("""
    SELECT job_id, job_type, environment, status, start_time, 
           records_processed, records_inserted, error_message
    FROM job_log
    WHERE datetime(start_time) >= datetime('now', '-1 hour')
    ORDER BY start_time DESC
    LIMIT 5
""")

jobs = cursor.fetchall()
if jobs:
    print("\nRecent job activity (last hour):")
    print("-"*60)
    for job in jobs:
        print(f"Job: {job[0][:40]}...")
        print(f"  Type: {job[1]}, Env: {job[2]}, Status: {job[3]}")
        print(f"  Time: {job[4]}")
        if job[5]:
            print(f"  Processed: {job[5]}, Inserted: {job[6]}")
        if job[7]:
            print(f"  Error: {job[7][:100]}")
        print()

# Get overall stats
cursor.execute("""
    SELECT 
        COUNT(DISTINCT date) as days,
        COUNT(DISTINCT transaction_id) as transactions,
        COUNT(*) as rows,
        MAX(date) as latest_date,
        MAX(created_at) as last_insert
    FROM transactions_production
""")

stats = cursor.fetchone()
print("\nDatabase Summary:")
print(f"  Total days with data: {stats[0]}")
print(f"  Total unique transactions: {stats[1]}")
print(f"  Total rows: {stats[2]}")
print(f"  Latest transaction date: {stats[3]}")
print(f"  Last database insert: {stats[4]}")

# Check if we have today's data
today = date.today().isoformat()
cursor.execute("""
    SELECT COUNT(DISTINCT transaction_id) 
    FROM transactions_production 
    WHERE date = ?
""", (today,))

today_count = cursor.fetchone()[0]
print(f"\nToday's transactions ({today}): {today_count}")

conn.close()