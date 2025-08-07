#!/usr/bin/env python3
"""Check local database status vs what's in production."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print('LOCAL DATABASE STATUS:')
print('=' * 50)

# Check player stats
cursor.execute("""
    SELECT 
        MIN(date) as first_date,
        MAX(date) as last_date,
        COUNT(*) as total_records,
        COUNT(DISTINCT yahoo_player_id) as unique_players,
        COUNT(CASE WHEN position_codes IS NOT NULL AND position_codes != '' THEN 1 END) as with_positions
    FROM daily_gkl_player_stats
""")

result = cursor.fetchone()
print(f'Date range: {result[0]} to {result[1]}')
print(f'Total records: {result[2]:,}')
print(f'Unique players: {result[3]:,}')
print(f'Records with positions: {result[4]:,} ({result[4]*100/result[2]:.1f}%)')

# Check position quality
cursor.execute("""
    SELECT 
        COUNT(CASE WHEN position_codes = 'POS' THEN 1 END) as generic_pos,
        COUNT(CASE WHEN position_codes LIKE '%,%' THEN 1 END) as multi_position,
        COUNT(CASE WHEN position_codes IN ('C','1B','2B','3B','SS','LF','CF','RF','DH','P') THEN 1 END) as single_position
    FROM daily_gkl_player_stats
    WHERE position_codes IS NOT NULL
""")

result = cursor.fetchone()
print(f'\nPosition quality:')
print(f'  Generic POS: {result[0]:,}')
print(f'  Multi-position eligible: {result[1]:,}')
print(f'  Single position: {result[2]:,}')

# Check Yahoo ID quality
cursor.execute("""
    SELECT COUNT(*) FROM daily_gkl_player_stats WHERE yahoo_player_id LIKE '%.0'
""")
decimal_count = cursor.fetchone()[0]
print(f'\nYahoo IDs with .0: {decimal_count}')

conn.close()

print('\n' + '=' * 50)
print('D1 PRODUCTION STATUS (last pushed Aug 7):')
print('  - Has only ~900 records (Aug 4-7 data)')
print('  - Yahoo IDs likely have .0 suffix')
print('  - Position codes are probably "POS" or NULL')
print('  - Missing all the fixes we made locally')
print('\nNeed to export ALL corrected local data to D1!')