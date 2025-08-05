#!/usr/bin/env python3
"""Check table schema."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(transactions)')
print('\nColumn info:')
for row in cursor.fetchall():
    print(f'  {row[1]}: {row[2]}')

conn.close()