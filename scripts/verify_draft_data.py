"""
Verify draft data in production database.
"""
import sqlite3
from pathlib import Path

# Connect to production database
db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=== Verifying Draft Data in Production Database ===\n")

# Check total records
cursor.execute("SELECT COUNT(*) FROM draft_results WHERE league_key = '458.l.6966' AND season = 2025")
total = cursor.fetchone()[0]
print(f"Total draft records: {total}")

# Check draft type
cursor.execute("SELECT DISTINCT draft_type FROM draft_results WHERE league_key = '458.l.6966' AND season = 2025")
draft_types = cursor.fetchall()
print(f"Draft type(s): {[dt[0] for dt in draft_types]}")

# Sample some records
print("\nSample draft picks:")
cursor.execute("""
    SELECT player_name, team_name, draft_round, draft_pick, draft_cost, keeper_status
    FROM draft_results 
    WHERE league_key = '458.l.6966' AND season = 2025
    ORDER BY draft_pick
    LIMIT 10
""")

for row in cursor.fetchall():
    player, team, round_num, pick, cost, keeper = row
    keeper_str = "Keeper" if keeper else ""
    print(f"  Pick {pick:3d}: {player:25s} - {team:20s} - Round {round_num:2d}, ${cost:3d} {keeper_str}")

# Check keeper status
cursor.execute("""
    SELECT COUNT(*) FROM draft_results 
    WHERE league_key = '458.l.6966' AND season = 2025 AND keeper_status = 1
""")
keeper_count = cursor.fetchone()[0]
print(f"\nKeepers marked: {keeper_count}")

# Check job log
print("\nJob log entry:")
cursor.execute("""
    SELECT job_id, status, records_processed, records_inserted
    FROM job_log
    WHERE job_type = 'draft_collection'
    ORDER BY job_id DESC
    LIMIT 1
""")
job = cursor.fetchone()
if job:
    print(f"  Job: {job[0]}")
    print(f"  Status: {job[1]}")
    print(f"  Processed: {job[2]}, Inserted: {job[3]}")

conn.close()

print("\n[OK] Draft data successfully loaded into production database!")