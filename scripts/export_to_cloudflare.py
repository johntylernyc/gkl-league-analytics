"""
Export updated data from local SQLite to CloudFlare D1.
This script runs after GitHub Actions to sync data to the production website.
"""

import os
import sqlite3
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def export_recent_data():
    """Export recent data changes to SQL files for CloudFlare import."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    export_dir = Path(__file__).parent.parent / 'cloudflare-deployment' / 'sql' / 'incremental'
    export_dir.mkdir(exist_ok=True)
    
    if not db_path.exists():
        print("❌ Database not found")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("📤 Exporting recent data changes...")
    
    # Get data updated in the last job
    cursor.execute("""
        SELECT MAX(start_time) FROM job_log 
        WHERE status = 'completed' 
          AND job_type LIKE '%incremental%'
    """)
    
    last_job_time = cursor.fetchone()[0]
    if not last_job_time:
        print("ℹ️  No recent incremental jobs found")
        return False
    
    print(f"🕐 Exporting data from job: {last_job_time}")
    
    # Export recent transactions
    cursor.execute("""
        SELECT transaction_id, league_key, season, transaction_date,
               transaction_type, team_key, team_name, player_id, player_name,
               from_team_key, to_team_key
        FROM league_transactions
        WHERE created_at >= ?
        ORDER BY transaction_date, transaction_id
    """, (last_job_time,))
    
    transactions = cursor.fetchall()
    
    if transactions:
        print(f"📋 Found {len(transactions)} recent transactions")
        
        # Generate SQL for transactions
        sql_lines = []
        sql_lines.append("-- Recent transactions export")
        sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        sql_lines.append("")
        
        for txn in transactions:
            # Fix f-string syntax - can't use backslash in f-string
            escaped_values = []
            for v in txn:
                if v:
                    escaped_val = str(v).replace("'", "''")
                    escaped_values.append(f"'{escaped_val}'")
                else:
                    escaped_values.append('NULL')
            values = ', '.join(escaped_values)
            sql_lines.append(f"""
INSERT OR REPLACE INTO league_transactions 
(transaction_id, league_key, season, transaction_date, transaction_type, 
 team_key, team_name, player_id, player_name, from_team_key, to_team_key)
VALUES ({values});""")
        
        # Write transactions file
        txn_file = export_dir / 'recent_transactions.sql'
        with open(txn_file, 'w') as f:
            f.write('\n'.join(sql_lines))
        
        print(f"✅ Exported transactions to: {txn_file}")
    
    # Export recent lineup changes (last 3 days)
    cursor.execute("""
        SELECT job_id, season, date, team_key, team_name, 
               player_id, player_name, selected_position
        FROM daily_lineups
        WHERE date >= date('now', '-3 days')
        ORDER BY date, team_key, player_id
    """)
    
    lineups = cursor.fetchall()
    
    if lineups:
        print(f"📋 Found {len(lineups)} recent lineup entries")
        
        # Generate SQL for lineups
        sql_lines = []
        sql_lines.append("-- Recent lineups export")
        sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        sql_lines.append("")
        sql_lines.append("-- Clear recent lineup data")
        sql_lines.append("DELETE FROM daily_lineups WHERE date >= date('now', '-3 days');")
        sql_lines.append("")
        
        for lineup in lineups:
            # Fix f-string syntax - can't use backslash in f-string
            escaped_values = []
            for v in lineup:
                if v:
                    escaped_val = str(v).replace("'", "''")
                    escaped_values.append(f"'{escaped_val}'")
                else:
                    escaped_values.append('NULL')
            values = ', '.join(escaped_values)
            sql_lines.append(f"""
INSERT INTO daily_lineups 
(job_id, season, date, team_key, team_name, player_id, player_name, selected_position)
VALUES ({values});""")
        
        # Write lineups file
        lineup_file = export_dir / 'recent_lineups.sql'
        with open(lineup_file, 'w') as f:
            f.write('\n'.join(sql_lines))
        
        print(f"✅ Exported lineups to: {lineup_file}")
    
    # Export recent stats (last 7 days)
    cursor.execute("""
        SELECT yahoo_player_id, date, batting_hits, batting_runs, batting_rbis,
               batting_home_runs, batting_stolen_bases, has_batting_data, has_correction
        FROM daily_gkl_player_stats
        WHERE date >= date('now', '-7 days')
          AND has_batting_data = 1
        ORDER BY date, yahoo_player_id
    """)
    
    stats = cursor.fetchall()
    
    if stats:
        print(f"📋 Found {len(stats)} recent stats entries")
        
        # Generate SQL for stats
        sql_lines = []
        sql_lines.append("-- Recent stats export")
        sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        sql_lines.append("")
        sql_lines.append("-- Clear recent stats data")
        sql_lines.append("DELETE FROM daily_gkl_player_stats WHERE date >= date('now', '-7 days');")
        sql_lines.append("")
        
        for stat in stats:
            values = ', '.join([str(v) if v is not None else 'NULL' for v in stat])
            sql_lines.append(f"""
INSERT OR REPLACE INTO daily_gkl_player_stats 
(yahoo_player_id, date, batting_hits, batting_runs, batting_rbis, 
 batting_home_runs, batting_stolen_bases, has_batting_data, has_correction)
VALUES ({values});""")
        
        # Write stats file
        stats_file = export_dir / 'recent_stats.sql'
        with open(stats_file, 'w') as f:
            f.write('\n'.join(sql_lines))
        
        print(f"✅ Exported stats to: {stats_file}")
    
    conn.close()
    return True

def deploy_to_cloudflare():
    """Deploy the exported data to CloudFlare D1."""
    
    export_dir = Path(__file__).parent.parent / 'cloudflare-deployment' / 'sql' / 'incremental'
    
    print("🚀 Deploying to CloudFlare D1...")
    
    # Check if wrangler is available
    try:
        result = subprocess.run(['wrangler', '--version'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent / 'cloudflare-deployment')
        print(f"📦 Wrangler version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Wrangler CLI not found. Install with: npm install -g wrangler")
        return False
    
    # Execute SQL files
    sql_files = list(export_dir.glob('*.sql'))
    
    if not sql_files:
        print("ℹ️  No SQL files to deploy")
        return True
    
    # Get environment variables and ensure CloudFlare credentials are set
    env = os.environ.copy()
    
    # Debug: Check if CloudFlare credentials are available
    if 'CLOUDFLARE_API_TOKEN' in env:
        print(f"✅ CloudFlare API token found (length: {len(env['CLOUDFLARE_API_TOKEN'])})")
    else:
        print("⚠️  CloudFlare API token not found in environment")
    
    if 'CLOUDFLARE_ACCOUNT_ID' in env:
        print(f"✅ CloudFlare account ID found: {env['CLOUDFLARE_ACCOUNT_ID'][:8]}...")
    else:
        print("⚠️  CloudFlare account ID not found in environment")
    
    # Use the database name as configured in wrangler.toml
    database_name = 'gkl-fantasy'
    
    for sql_file in sql_files:
        print(f"📤 Executing: {sql_file.name}")
        
        # Build wrangler command with proper flags
        wrangler_cmd = [
            'wrangler', 'd1', 'execute', database_name,
            '--file', str(sql_file),
            '--remote',  # Execute on remote database
            '--env', 'production'  # Use production environment configuration
        ]
        
        print(f"🔧 Running command: {' '.join(wrangler_cmd)}")
        
        try:
            # Execute SQL file against D1 database using database name
            result = subprocess.run(
                wrangler_cmd,
                capture_output=True, 
                text=True, 
                cwd=Path(__file__).parent.parent / 'cloudflare-deployment',
                env=env)
            
            if result.returncode == 0:
                print(f"✅ {sql_file.name} executed successfully")
                # Remove the file after successful execution
                sql_file.unlink()
            else:
                print(f"❌ {sql_file.name} failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing {sql_file.name}: {e}")
            return False
    
    print("🎉 CloudFlare D1 deployment completed!")
    return True

def main():
    """Main export and deploy process."""
    print("=" * 60)
    print("CLOUDFLARE D1 DATA SYNC")
    print("=" * 60)
    
    try:
        # Step 1: Export recent data
        if not export_recent_data():
            print("ℹ️  No data to export")
            return
        
        # Step 2: Deploy to CloudFlare
        if deploy_to_cloudflare():
            print("✅ Data sync completed successfully!")
        else:
            print("❌ Data sync failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()