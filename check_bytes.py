import sqlite3

conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()

# Get players with likely accent marks
cursor.execute("""
    SELECT DISTINCT player_name 
    FROM transactions 
    WHERE player_name LIKE 'Jos%' 
       OR player_name LIKE 'Luis Garc%'
    ORDER BY player_name
    LIMIT 20
""")

print("Player names and their byte representation:")
for row in cursor.fetchall():
    name = row[0]
    # Show the actual bytes
    name_bytes = name.encode('utf-8', errors='replace')
    print(f"\nName: {name}")
    print(f"Bytes: {name_bytes}")
    print(f"Hex: {name_bytes.hex()}")
    
    # Check for common issues
    if b'\xef\xbf\xbd' in name_bytes:  # UTF-8 replacement character
        print("  -> Contains replacement character (corrupted)")
    elif b'\xe9' in name_bytes or b'\xe1' in name_bytes or b'\xed' in name_bytes:
        print("  -> Contains proper UTF-8 accented characters")

conn.close()