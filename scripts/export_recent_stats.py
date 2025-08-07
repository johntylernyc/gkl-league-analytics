#!/usr/bin/env python3
"""Export only recent corrected player stats (smaller batch for D1)."""

import sqlite3
from datetime import datetime
from pathlib import Path

def export_recent_stats():
    """Export recent stats in manageable chunks."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Export only July-August data (most recent 2 months)
    start_date = '2025-07-01'
    end_date = '2025-08-07'
    
    # Get relevant job_ids
    cursor.execute("""
        SELECT DISTINCT job_id 
        FROM daily_gkl_player_stats 
        WHERE date BETWEEN ? AND ?
        AND job_id IS NOT NULL
    """, (start_date, end_date))
    job_ids = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(job_ids)} job_ids for {start_date} to {end_date}")
    
    # Export job logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_log_file = Path('cloudflare-production/sql/incremental') / f'recent_job_logs_{timestamp}.sql'
    job_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(job_log_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Recent job_log export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Date range: {start_date} to {end_date}\n\n")
        
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
    
    # Export recent stats
    cursor.execute("""
        SELECT * FROM daily_gkl_player_stats 
        WHERE date BETWEEN ? AND ?
        ORDER BY date, yahoo_player_id
    """, (start_date, end_date))
    
    stats = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(daily_gkl_player_stats)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Split into smaller batches (5000 records each)
    batch_size = 5000
    num_batches = (len(stats) + batch_size - 1) // batch_size
    
    print(f"\nExporting {len(stats):,} recent records in {num_batches} files...")
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(stats))
        batch_stats = stats[start_idx:end_idx]
        
        stats_file = Path('cloudflare-production/sql/incremental') / f'recent_stats_{timestamp}_batch{batch_num+1:02d}.sql'
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Recent stats batch {batch_num+1}/{num_batches}\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Records: {len(batch_stats)}\n\n")
            
            for row in batch_stats:
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
        
        print(f"  Batch {batch_num+1}: {len(batch_stats)} records")
    
    conn.close()
    
    print(f"\nExport complete!")
    print(f"\nImport commands:")
    print("cd cloudflare-production")
    print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{job_log_file.name} --remote")
    
    for batch_num in range(num_batches):
        stats_file_name = f'recent_stats_{timestamp}_batch{batch_num+1:02d}.sql'
        print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{stats_file_name} --remote")

if __name__ == "__main__":
    export_recent_stats()