import sqlite3
from datetime import datetime, date

# Connect to database
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()

# Get current date
today = date.today().isoformat()

# Check latest transaction date
cursor.execute("""
    SELECT MAX(date) as latest_date, 
           COUNT(DISTINCT date) as days_with_data,
           COUNT(DISTINCT transaction_id) as total_transactions,
           COUNT(*) as total_rows
    FROM transactions_production
""")

result = cursor.fetchone()
print("Current Database Status:")
print("="*50)
print(f"Latest transaction date: {result[0]}")
print(f"Days with data: {result[1]}")
print(f"Total unique transactions: {result[2]}")
print(f"Total rows in database: {result[3]}")
print(f"Today's date: {today}")

# Check if we need to update
if result[0]:
    latest = datetime.strptime(result[0], "%Y-%m-%d").date()
    today_date = date.today()
    days_behind = (today_date - latest).days
    print(f"\nDays behind: {days_behind}")
    
    if days_behind > 0:
        print(f"Need to fetch {days_behind} days of data")
    else:
        print("Database is up to date!")
else:
    print("\nNo data in database - need full collection")

# Check data coverage for 2025 season
cursor.execute("""
    SELECT MIN(date) as earliest, MAX(date) as latest
    FROM transactions_production
    WHERE date LIKE '2025-%'
""")

season_data = cursor.fetchone()
if season_data[0]:
    print(f"\n2025 Season Coverage:")
    print(f"  From: {season_data[0]}")
    print(f"  To: {season_data[1]}")

conn.close()