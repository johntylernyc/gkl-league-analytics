#!/usr/bin/env python3
"""Export player stats data for Cloudflare D1 import."""

import sqlite3
from datetime import datetime
from pathlib import Path

def export_player_stats(start_date='2025-08-04', end_date='2025-08-07'):
    """Export recent player stats to SQL file."""
    
    # Connect to local database
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get job_ids for the date range
    cursor.execute("""
        SELECT DISTINCT job_id 
        FROM daily_gkl_player_stats 
        WHERE date BETWEEN ? AND ?
    """, (start_date, end_date))
    job_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"Found {len(job_ids)} job_ids for date range {start_date} to {end_date}")
    
    # Export job_log entries
    job_log_file = Path('cloudflare-production/sql/incremental') / f'stats_job_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    job_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(job_log_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Player stats job_log export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Count: {len(job_ids)}\n\n")
        
        for job_id in job_ids:
            cursor.execute("SELECT * FROM job_log WHERE job_id = ?", (job_id,))
            job = cursor.fetchone()
            if job:
                values = []
                for val in job:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    else:
                        values.append(str(val))
                
                f.write(f"INSERT OR IGNORE INTO job_log VALUES ({', '.join(values)});\n")
    
    print(f"Exported job_log to: {job_log_file}")
    
    # Export daily_gkl_player_stats
    cursor.execute("""
        SELECT * FROM daily_gkl_player_stats 
        WHERE date BETWEEN ? AND ?
        ORDER BY date, yahoo_player_id
    """, (start_date, end_date))
    
    stats = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(daily_gkl_player_stats)")
    columns = [col[1] for col in cursor.fetchall()]
    
    stats_file = Path('cloudflare-production/sql/incremental') / f'player_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Player stats export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Date range: {start_date} to {end_date}\n")
        f.write(f"-- Count: {len(stats)}\n\n")
        
        for row in stats:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                elif isinstance(val, float):
                    values.append(str(val))
                else:
                    values.append(str(val))
            
            f.write(f"INSERT OR REPLACE INTO daily_gkl_player_stats ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
    
    print(f"Exported {len(stats)} player stats to: {stats_file}")
    
    conn.close()
    
    print("\nTo import to D1:")
    print("cd cloudflare-production")
    print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{job_log_file.name} --remote")
    print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{stats_file.name} --remote")

if __name__ == "__main__":
    export_player_stats()