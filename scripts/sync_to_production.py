#!/usr/bin/env python3
"""
Sync local database changes to Cloudflare D1 production database.
This script exports recent data from local SQLite and prepares it for import to D1.
"""

import os
import sys
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def export_recent_transactions(conn, export_dir, days_back=2):
    """Export recent transactions to SQL file."""
    cursor = conn.cursor()
    
    # Get transactions from the last N days
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT * FROM transactions 
        WHERE date >= ? 
        ORDER BY date DESC, created_at DESC
    """, (cutoff_date,))
    
    transactions = cursor.fetchall()
    
    if not transactions:
        print(f"No transactions found since {cutoff_date}")
        return None
    
    # Get column names
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Generate SQL file
    sql_file = export_dir / f'transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Recent transactions export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Transactions since: {cutoff_date}\n")
        f.write(f"-- Count: {len(transactions)}\n\n")
        
        # Use REPLACE to handle duplicates
        for row in transactions:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    # Escape single quotes and handle special characters
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(str(val))
            
            f.write(f"REPLACE INTO transactions ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
    
    print(f"✅ Exported {len(transactions)} transactions to {sql_file}")
    return sql_file

def export_job_logs(conn, export_dir, job_ids):
    """Export job_log entries for the given job_ids."""
    if not job_ids:
        return None
    
    cursor = conn.cursor()
    
    # Create placeholders for SQL query
    placeholders = ','.join(['?' for _ in job_ids])
    
    cursor.execute(f"""
        SELECT * FROM job_log 
        WHERE job_id IN ({placeholders})
    """, list(job_ids))
    
    job_logs = cursor.fetchall()
    
    if not job_logs:
        return None
    
    # Get column names
    cursor.execute("PRAGMA table_info(job_log)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Generate SQL file
    sql_file = export_dir / f'job_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Job log export for foreign key dependencies\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Count: {len(job_logs)}\n\n")
        
        for row in job_logs:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(str(val))
            
            f.write(f"INSERT OR IGNORE INTO job_log ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
    
    print(f"✅ Exported {len(job_logs)} job_log entries to {sql_file}")
    return sql_file

def export_recent_lineups(conn, export_dir, days_back=7):
    """Export recent daily lineups to SQL file."""
    cursor = conn.cursor()
    
    # Check if daily_lineups table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_lineups'")
    if not cursor.fetchone():
        print("⚠️  daily_lineups table not found, skipping")
        return None, set()
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT * FROM daily_lineups 
        WHERE date >= ? 
        ORDER BY date DESC
    """, (cutoff_date,))
    
    lineups = cursor.fetchall()
    
    if not lineups:
        print(f"No lineups found since {cutoff_date}")
        return None, set()
    
    # Get column names and find job_id column index
    cursor.execute("PRAGMA table_info(daily_lineups)")
    columns_info = cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    # Find job_id column index
    job_id_index = None
    for i, col in enumerate(columns):
        if col == 'job_id':
            job_id_index = i
            break
    
    # Collect unique job_ids
    job_ids = set()
    if job_id_index is not None:
        for row in lineups:
            if row[job_id_index]:
                job_ids.add(row[job_id_index])
    
    # Generate SQL file
    sql_file = export_dir / f'lineups_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Recent lineups export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Lineups since: {cutoff_date}\n")
        f.write(f"-- Count: {len(lineups)}\n\n")
        
        for row in lineups:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(str(val))
            
            f.write(f"REPLACE INTO daily_lineups ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
    
    print(f"✅ Exported {len(lineups)} lineups to {sql_file}")
    return sql_file, job_ids

def main():
    """Main sync process."""
    print("🚀 Starting production sync process...\n")
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    db_path = project_root / 'database' / 'league_analytics.db'
    export_dir = project_root / 'cloudflare-production' / 'sql' / 'incremental'
    
    # Create export directory if it doesn't exist
    export_dir.mkdir(parents=True, exist_ok=True)
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return 1
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    
    try:
        # Export recent data
        print("📤 Exporting recent data...\n")
        
        # Collect all job_ids that need to be exported
        all_job_ids = set()
        
        # Export transactions
        transaction_file = export_recent_transactions(conn, export_dir)
        
        # Export lineups and get their job_ids
        lineup_file, lineup_job_ids = export_recent_lineups(conn, export_dir)
        all_job_ids.update(lineup_job_ids)
        
        # Export job_log entries for foreign key dependencies
        job_log_file = None
        if all_job_ids:
            print(f"\n📋 Found {len(all_job_ids)} unique job_ids to export")
            job_log_file = export_job_logs(conn, export_dir, all_job_ids)
        
        if not transaction_file and not lineup_file:
            print("\n⚠️  No recent data to sync")
            return 0
        
        print("\n" + "="*60)
        print("📋 NEXT STEPS TO COMPLETE SYNC:")
        print("="*60)
        print("\n1. Navigate to cloudflare-production directory:")
        print("   cd cloudflare-production\n")
        
        print("2. Import data to Cloudflare D1 IN THIS ORDER:")
        
        # IMPORTANT: Import job_logs first to satisfy foreign key constraints
        if job_log_file:
            relative_path = job_log_file.relative_to(project_root / 'cloudflare-production')
            print(f"   npx wrangler d1 execute gkl-fantasy --file=./{relative_path} --remote")
        
        if transaction_file:
            relative_path = transaction_file.relative_to(project_root / 'cloudflare-production')
            print(f"   npx wrangler d1 execute gkl-fantasy --file=./{relative_path} --remote")
        
        if lineup_file:
            relative_path = lineup_file.relative_to(project_root / 'cloudflare-production')
            print(f"   npx wrangler d1 execute gkl-fantasy --file=./{relative_path} --remote")
        
        print("\n⚠️  IMPORTANT: Import job_logs FIRST to avoid foreign key errors!")
        
        print("\n3. Verify the production API:")
        print("   curl https://gkl-fantasy-api.services-403.workers.dev/transactions?limit=1")
        print("   curl https://gkl-fantasy-api.services-403.workers.dev/lineups/dates")
        
        print("\n4. Check the production website:")
        print("   https://goldenknightlounge.com")
        
        print("\n✅ Export complete! Follow the steps above to sync to production.")
        
    finally:
        conn.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())