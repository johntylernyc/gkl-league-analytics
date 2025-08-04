import sqlite3

conn = sqlite3.connect('database/backups/league_analytics_backup_20250804_102540.db')
cursor = conn.cursor()

tables = ['transactions', 'daily_lineups', 'daily_gkl_player_stats', 'job_log']
for t in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'{t}: {cursor.fetchone()[0]} records')

conn.close()