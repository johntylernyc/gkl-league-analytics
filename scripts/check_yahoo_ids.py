#!/usr/bin/env python3
"""Check Yahoo player ID format issues."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check yahoo_player_id values
cursor.execute("""
    SELECT 
        yahoo_player_id,
        player_name,
        COUNT(*) as count
    FROM daily_gkl_player_stats
    WHERE yahoo_player_id IS NOT NULL 
    AND yahoo_player_id != ''
    LIMIT 10
""")

print('Sample Yahoo player IDs in daily_gkl_player_stats:')
for row in cursor.fetchall():
    print(f'  {row[0]:15} - {row[1]:20} ({row[2]} records)')

# Check the data type
cursor.execute('PRAGMA table_info(daily_gkl_player_stats)')
columns = cursor.fetchall()
for col in columns:
    if 'yahoo' in col[1].lower():
        print(f'\nColumn: {col[1]}, Type: {col[2]}')

# Check if they contain decimals
cursor.execute("""
    SELECT COUNT(*) 
    FROM daily_gkl_player_stats 
    WHERE yahoo_player_id LIKE '%.0'
""")
decimal_count = cursor.fetchone()[0]
print(f'\nYahoo IDs ending in .0: {decimal_count}')

# Get some examples
cursor.execute("""
    SELECT DISTINCT yahoo_player_id, player_name
    FROM daily_gkl_player_stats 
    WHERE yahoo_player_id LIKE '%.0'
    LIMIT 5
""")
examples = cursor.fetchall()
if examples:
    print('\nExamples of IDs with .0:')
    for row in examples:
        print(f'  {row[0]} - {row[1]}')

conn.close()