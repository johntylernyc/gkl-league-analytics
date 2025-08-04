#!/usr/bin/env python3
"""
Export clean database data to CloudFlare D1.
This script exports data from the restored backup to SQL files for D1 sync.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def export_to_cloudflare():
    """Export clean database to CloudFlare D1 format."""
    
    db_path = Path('database/league_analytics.db')
    export_dir = Path('database/d1_export')
    export_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("CLOUDFLARE D1 CLEAN DATA EXPORT")
    print("="*60)
    print(f"Source database: {db_path}")
    print(f"Export directory: {export_dir}")
    print()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check what we have
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [t[0] for t in cursor.fetchall() if not t[0].startswith('sqlite_')]
    print(f"Tables found: {', '.join(tables)}")
    print()
    
    # Export schema first
    schema_file = export_dir / '01_schema.sql'
    with open(schema_file, 'w') as f:
        f.write("-- CloudFlare D1 Schema Export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        # Get schema for main tables
        for table in ['transactions', 'daily_lineups', 'daily_gkl_player_stats', 'job_log']:
            if table in tables:
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}' AND type='table'")
                create_sql = cursor.fetchone()
                if create_sql:
                    f.write(f"-- Table: {table}\n")
                    f.write(f"DROP TABLE IF EXISTS {table};\n")
                    f.write(create_sql[0] + ";\n\n")
    
    print(f"[OK] Exported schema to: {schema_file}")
    
    # Export job_log first (for foreign keys)
    job_file = export_dir / '02_job_log.sql'
    with open(job_file, 'w') as f:
        f.write("-- Job Log Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        cursor.execute("SELECT * FROM job_log WHERE environment = 'production' ORDER BY start_time")
        jobs = cursor.fetchall()
        
        if jobs:
            # Get column names
            cursor.execute("PRAGMA table_info(job_log)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for job in jobs:
                values = []
                for val in job:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    else:
                        values.append(str(val))
                
                f.write(f"INSERT INTO job_log ({','.join(columns)}) VALUES ({','.join(values)});\n")
    
    print(f"[OK] Exported {len(jobs)} job_log entries to: {job_file}")
    
    # Export transactions
    txn_file = export_dir / '03_transactions.sql'
    with open(txn_file, 'w') as f:
        f.write("-- Transaction Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        cursor.execute("SELECT * FROM transactions ORDER BY date, transaction_id")
        transactions = cursor.fetchall()
        
        if transactions:
            # Get column names
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            for txn in transactions:
                values = []
                for val in txn:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    else:
                        values.append(str(val))
                
                f.write(f"INSERT INTO transactions ({','.join(columns)}) VALUES ({','.join(values)});\n")
    
    print(f"[OK] Exported {len(transactions)} transactions to: {txn_file}")
    
    # Export daily_lineups
    lineup_file = export_dir / '04_daily_lineups.sql'
    with open(lineup_file, 'w') as f:
        f.write("-- Daily Lineups Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        cursor.execute("SELECT COUNT(*) FROM daily_lineups")
        count = cursor.fetchone()[0]
        
        # Export in batches
        batch_size = 1000
        offset = 0
        
        while offset < count:
            cursor.execute(f"SELECT * FROM daily_lineups LIMIT {batch_size} OFFSET {offset}")
            lineups = cursor.fetchall()
            
            if lineups:
                # Get column names on first batch
                if offset == 0:
                    cursor.execute("PRAGMA table_info(daily_lineups)")
                    columns = [col[1] for col in cursor.fetchall()]
                
                for lineup in lineups:
                    values = []
                    for val in lineup:
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                        else:
                            values.append(str(val))
                    
                    f.write(f"INSERT INTO daily_lineups ({','.join(columns)}) VALUES ({','.join(values)});\n")
            
            offset += batch_size
            if offset % 10000 == 0:
                print(f"  Processed {offset}/{count} lineups...")
    
    print(f"[OK] Exported {count} daily_lineups to: {lineup_file}")
    
    # Export daily_gkl_player_stats
    stats_file = export_dir / '05_daily_gkl_player_stats.sql'
    with open(stats_file, 'w') as f:
        f.write("-- Daily Player Stats Data\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        
        cursor.execute("SELECT COUNT(*) FROM daily_gkl_player_stats")
        count = cursor.fetchone()[0]
        
        # Export in batches
        batch_size = 1000
        offset = 0
        
        while offset < count:
            cursor.execute(f"SELECT * FROM daily_gkl_player_stats LIMIT {batch_size} OFFSET {offset}")
            stats = cursor.fetchall()
            
            if stats:
                # Get column names on first batch
                if offset == 0:
                    cursor.execute("PRAGMA table_info(daily_gkl_player_stats)")
                    columns = [col[1] for col in cursor.fetchall()]
                
                for stat in stats:
                    values = []
                    for val in stat:
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                        else:
                            values.append(str(val))
                    
                    f.write(f"INSERT INTO daily_gkl_player_stats ({','.join(columns)}) VALUES ({','.join(values)});\n")
            
            offset += batch_size
            if offset % 10000 == 0:
                print(f"  Processed {offset}/{count} stats...")
    
    print(f"[OK] Exported {count} daily_gkl_player_stats to: {stats_file}")
    
    conn.close()
    
    print()
    print("="*60)
    print("EXPORT COMPLETE")
    print("="*60)
    print("\nTo sync to CloudFlare D1, run:")
    print("  1. Set CLOUDFLARE_API_TOKEN environment variable")
    print("  2. Run these commands in order:")
    for sql_file in sorted(export_dir.glob('*.sql')):
        print(f"     wrangler d1 execute gkl-fantasy --remote --file {sql_file}")
    print()
    print("Note: You may need to clear D1 first with:")
    print("  wrangler d1 execute gkl-fantasy --remote --command \"DROP TABLE IF EXISTS transactions\"")
    print("  wrangler d1 execute gkl-fantasy --remote --command \"DROP TABLE IF EXISTS daily_lineups\"")
    print("  wrangler d1 execute gkl-fantasy --remote --command \"DROP TABLE IF EXISTS daily_gkl_player_stats\"")

if __name__ == "__main__":
    export_to_cloudflare()