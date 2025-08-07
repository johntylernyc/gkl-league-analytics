#!/usr/bin/env python3
"""Export ALL corrected player stats data for D1 production."""

import sqlite3
from datetime import datetime
from pathlib import Path

def export_all_stats():
    """Export all player stats with corrected data."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # First, get all unique job_ids
    cursor.execute("""
        SELECT DISTINCT job_id 
        FROM daily_gkl_player_stats 
        WHERE job_id IS NOT NULL
        ORDER BY job_id
    """)
    job_ids = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(job_ids)} unique job_ids")
    
    # Export job_log entries
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_log_file = Path('cloudflare-production/sql/incremental') / f'all_stats_job_logs_{timestamp}.sql'
    job_log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(job_log_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Complete player stats job_log export\n")
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
    
    print(f"Exported job_logs to: {job_log_file.name}")
    
    # Export ALL daily_gkl_player_stats (in batches for manageable file size)
    cursor.execute("SELECT COUNT(*) FROM daily_gkl_player_stats")
    total_records = cursor.fetchone()[0]
    
    # Get column names
    cursor.execute("PRAGMA table_info(daily_gkl_player_stats)")
    columns = [col[1] for col in cursor.fetchall()]
    
    batch_size = 20000  # Records per file
    num_batches = (total_records + batch_size - 1) // batch_size
    
    print(f"\nExporting {total_records:,} player stats in {num_batches} files...")
    
    for batch_num in range(num_batches):
        offset = batch_num * batch_size
        
        cursor.execute(f"""
            SELECT * FROM daily_gkl_player_stats 
            ORDER BY date, yahoo_player_id
            LIMIT {batch_size} OFFSET {offset}
        """)
        
        stats = cursor.fetchall()
        
        stats_file = Path('cloudflare-production/sql/incremental') / f'all_player_stats_{timestamp}_batch{batch_num+1:02d}.sql'
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Player stats export batch {batch_num+1}/{num_batches}\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Records in this batch: {len(stats)}\n\n")
            
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
        
        print(f"  Batch {batch_num+1}: {len(stats)} records -> {stats_file.name}")
    
    conn.close()
    
    print(f"\nExport complete!")
    print(f"\nTo import to D1, run these commands in order:")
    print("cd cloudflare-production")
    print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{job_log_file.name} --remote")
    
    for batch_num in range(num_batches):
        stats_file_name = f'all_player_stats_{timestamp}_batch{batch_num+1:02d}.sql'
        print(f"npx wrangler d1 execute gkl-fantasy --file=sql/incremental/{stats_file_name} --remote")

if __name__ == "__main__":
    export_all_stats()