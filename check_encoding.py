import sqlite3

# Check local database
conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()

print("Checking player names with potential encoding issues...")
print()

# Check transactions
cursor.execute("""
    SELECT DISTINCT player_name 
    FROM transactions 
    WHERE player_name LIKE '%Garc%' 
       OR player_name LIKE '%ñ%'
       OR player_name LIKE '%é%'
       OR player_name LIKE '%á%'
       OR player_name LIKE '%í%'
       OR player_name LIKE '%ó%'
       OR player_name LIKE '%ú%'
       OR player_name LIKE '%�%'
    ORDER BY player_name
""")

print("Players in transactions table:")
affected_players = []
for row in cursor.fetchall():
    name = row[0]
    # Check for replacement character
    if '�' in name:
        print(f"  [ERROR] {name}")
        affected_players.append(name)
    else:
        print(f"  [OK] {name}")

print(f"\nTotal affected in transactions: {len(affected_players)}")

# Check daily_lineups
cursor.execute("""
    SELECT COUNT(DISTINCT player_name) 
    FROM daily_lineups 
    WHERE player_name LIKE '%�%'
""")
count = cursor.fetchone()[0]
print(f"\nPlayers with encoding issues in daily_lineups: {count}")

# Check daily_gkl_player_stats
cursor.execute("""
    SELECT COUNT(DISTINCT player_name) 
    FROM daily_gkl_player_stats 
    WHERE player_name LIKE '%�%'
""")
count = cursor.fetchone()[0]
print(f"Players with encoding issues in daily_gkl_player_stats: {count}")

# Get some examples
print("\nExample corrupted names:")
cursor.execute("""
    SELECT DISTINCT player_name 
    FROM transactions 
    WHERE player_name LIKE '%�%'
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

conn.close()