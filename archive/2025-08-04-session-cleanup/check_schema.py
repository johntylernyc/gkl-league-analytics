import sqlite3

conn = sqlite3.connect('database/league_analytics.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(transactions)')
print('Transactions columns:')
for col in cursor.fetchall():
    print(f'  {col[1]}: {col[2]}')

conn.close()