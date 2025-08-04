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
    export_dir = Path(__file__).parent.parent / 'cloudflare-production' / 'sql' / 'incremental'
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
    
    # First, get all unique job_ids that will be referenced
    job_ids = set()
    
    # Get job_ids from transactions
    try:
        cursor.execute("""
            SELECT DISTINCT job_id FROM transactions 
            WHERE created_at >= ? AND job_id IS NOT NULL
        """, (last_job_time,))
        job_ids.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError as e:
        print(f"⚠️  Warning: Could not get job_ids from transactions: {e}")
    
    # Get job_ids from lineups
    try:
        cursor.execute("""
            SELECT DISTINCT job_id FROM daily_lineups 
            WHERE date >= date('now', '-3 days') AND job_id IS NOT NULL
        """)
        job_ids.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError as e:
        print(f"⚠️  Warning: Could not get job_ids from daily_lineups: {e}")
    
    # Get job_ids from stats
    try:
        cursor.execute("""
            SELECT DISTINCT job_id FROM daily_gkl_player_stats 
            WHERE date >= date('now', '-7 days') AND job_id IS NOT NULL
        """)
        job_ids.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError as e:
        print(f"⚠️  Warning: Could not get job_ids from daily_gkl_player_stats: {e}")
    
    if job_ids:
        print(f"📋 Found {len(job_ids)} job IDs to ensure exist in D1")
        
        # Generate SQL to ensure job_log entries exist (create minimal entries if needed)
        sql_lines = []
        sql_lines.append("-- Ensure job_log entries exist for foreign key constraints")
        sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
        sql_lines.append("")
        
        for job_id in job_ids:
            # Create a minimal job_log entry if it doesn't exist
            escaped_job_id = job_id.replace("'", "''")
            sql_lines.append(f"""
INSERT OR IGNORE INTO job_log 
(job_id, job_type, environment, status)
VALUES ('{escaped_job_id}', 'data_sync', 'production', 'completed');""")
        
        # Write job_log file
        job_file = export_dir / 'job_logs.sql'
        with open(job_file, 'w') as f:
            f.write('\n'.join(sql_lines))
        
        print(f"✅ Exported job logs to: {job_file}")
    
    # Export recent transactions
    cursor.execute("""
        SELECT transaction_id, league_key, transaction_date as date,
               transaction_type, player_id, player_name,
               team_name as player_team,
               CASE 
                   WHEN transaction_type = 'add' THEN 'add'
                   WHEN transaction_type = 'drop' THEN 'drop'
                   ELSE transaction_type
               END as movement_type,
               NULL as player_position,
               to_team_key as destination_team_key,
               team_name as destination_team_name,
               from_team_key as source_team_key,
               NULL as source_team_name,
               job_id
        FROM transactions
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
INSERT OR REPLACE INTO transactions 
(transaction_id, league_key, date, transaction_type, player_id, player_name,
 player_team, movement_type, player_position, destination_team_key, 
 destination_team_name, source_team_key, source_team_name, job_id)
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
    # Select all the columns that exist in the source table and map to D1 schema
    cursor.execute("""
        SELECT job_id, date, mlb_player_id, yahoo_player_id, 
               player_name, team_code, position_codes, 
               COALESCE(games_played, 1) as games_played,
               batting_plate_appearances,
               batting_at_bats,
               batting_runs, batting_hits, 
               batting_singles,
               batting_doubles,
               batting_triples,
               batting_home_runs, batting_rbis, batting_stolen_bases,
               batting_caught_stealing,
               batting_walks,
               batting_intentional_walks,
               batting_strikeouts,
               batting_hit_by_pitch,
               batting_sacrifice_hits,
               batting_sacrifice_flies,
               batting_ground_into_double_play,
               batting_total_bases,
               pitching_games_started,
               pitching_complete_games,
               pitching_shutouts,
               pitching_wins,
               pitching_losses,
               pitching_saves,
               pitching_blown_saves,
               pitching_holds,
               pitching_innings_pitched,
               pitching_batters_faced,
               pitching_hits_allowed,
               pitching_runs_allowed,
               pitching_earned_runs,
               pitching_home_runs_allowed,
               pitching_walks_allowed,
               pitching_intentional_walks_allowed,
               pitching_strikeouts,
               pitching_hit_batters,
               pitching_wild_pitches,
               pitching_balks,
               pitching_quality_starts,
               COALESCE(data_source, 'export') as data_source,
               COALESCE(confidence_score, 1.0) as confidence_score,
               has_batting_data,
               COALESCE(has_pitching_data, 0) as has_pitching_data,
               COALESCE(validation_status, 'valid') as validation_status,
               validation_notes
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
            # Properly escape and format values
            escaped_values = []
            for v in stat:
                if v is not None:
                    if isinstance(v, str):
                        escaped_val = str(v).replace("'", "''")
                        escaped_values.append(f"'{escaped_val}'")
                    else:
                        escaped_values.append(str(v))
                else:
                    escaped_values.append('NULL')
            values = ', '.join(escaped_values)
            
            sql_lines.append(f"""
INSERT OR REPLACE INTO daily_gkl_player_stats 
(job_id, date, mlb_player_id, yahoo_player_id, player_name, team_code, position_codes,
 games_played, batting_plate_appearances, batting_at_bats, batting_runs, batting_hits,
 batting_singles, batting_doubles, batting_triples, batting_home_runs, batting_rbis,
 batting_stolen_bases, batting_caught_stealing, batting_walks, batting_intentional_walks,
 batting_strikeouts, batting_hit_by_pitch, batting_sacrifice_hits, batting_sacrifice_flies,
 batting_ground_into_double_play, batting_total_bases, pitching_games_started,
 pitching_complete_games, pitching_shutouts, pitching_wins, pitching_losses,
 pitching_saves, pitching_blown_saves, pitching_holds, pitching_innings_pitched,
 pitching_batters_faced, pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
 pitching_home_runs_allowed, pitching_walks_allowed, pitching_intentional_walks_allowed,
 pitching_strikeouts, pitching_hit_batters, pitching_wild_pitches, pitching_balks,
 pitching_quality_starts, data_source, confidence_score, has_batting_data,
 has_pitching_data, validation_status, validation_notes)
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
    
    export_dir = Path(__file__).parent.parent / 'cloudflare-production' / 'sql' / 'incremental'
    
    print("🚀 Deploying to CloudFlare D1...")
    
    # Check if wrangler is available
    try:
        result = subprocess.run(['wrangler', '--version'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent / 'cloudflare-production')
        print(f"📦 Wrangler version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Wrangler CLI not found. Install with: npm install -g wrangler")
        return False
    
    # Execute SQL files in the correct order (job_logs first for foreign key constraints)
    sql_files = list(export_dir.glob('*.sql'))
    
    if not sql_files:
        print("ℹ️  No SQL files to deploy")
        return True
    
    # Sort files to ensure job_logs.sql is executed first
    sql_files = sorted(sql_files, key=lambda x: (0 if x.name == 'job_logs.sql' else 1, x.name))
    
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
            '--remote'  # Execute on remote database
        ]
        
        print(f"🔧 Running command: {' '.join(wrangler_cmd)}")
        
        try:
            # Execute SQL file against D1 database using database name
            result = subprocess.run(
                wrangler_cmd,
                capture_output=True, 
                text=True, 
                cwd=Path(__file__).parent.parent / 'cloudflare-production',
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