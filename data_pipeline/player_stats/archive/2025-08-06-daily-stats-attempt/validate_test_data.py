#!/usr/bin/env python3
"""
Validate test data for UAT - shows what the job imports look like
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from tabulate import tabulate

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment


def show_job_logs(conn, config):
    """Show recent job logs"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("RECENT JOB LOGS")
    print("="*80)
    
    cursor.execute("""
        SELECT job_id, job_type, environment, status, 
               date_range_start, date_range_end,
               records_processed, records_inserted,
               datetime(created_at, 'localtime') as created_at
        FROM job_log
        WHERE job_type LIKE '%stats%'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    headers = ['Job ID (first 8)', 'Type', 'Env', 'Status', 'Start', 'End', 
               'Processed', 'Inserted', 'Created']
    rows = []
    
    for row in cursor.fetchall():
        job_id, job_type, env, status, start_date, end_date, processed, inserted, created = row
        rows.append([
            job_id[:8] + '...',
            job_type,
            env,
            status,
            start_date or 'N/A',
            end_date or 'N/A',
            processed or 0,
            inserted or 0,
            created
        ])
    
    if rows:
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    else:
        print("No job logs found for stats operations")


def show_player_stats(conn, config, date=None):
    """Show player stats for a specific date or latest"""
    cursor = conn.cursor()
    player_stats_table = config['gkl_player_stats_table']
    
    if not date:
        # Get latest date
        cursor.execute(f"SELECT MAX(date) FROM {player_stats_table}")
        date = cursor.fetchone()[0]
    
    print(f"\n{'='*80}")
    print(f"PLAYER STATS FOR {date}")
    print(f"{'='*80}")
    
    cursor.execute(f"""
        SELECT 
            ps.player_name,
            ps.team_code,
            ps.position_codes,
            ps.batting_at_bats as AB,
            ps.batting_hits as H,
            ps.batting_runs as R,
            ps.batting_rbis as RBI,
            ps.batting_home_runs as HR,
            ps.batting_stolen_bases as SB,
            ps.batting_avg as AVG,
            ps.job_id
        FROM {player_stats_table} ps
        WHERE ps.date = ?
        ORDER BY ps.batting_hits DESC, ps.batting_rbis DESC
    """, (date,))
    
    headers = ['Player', 'Team', 'Pos', 'AB', 'H', 'R', 'RBI', 'HR', 'SB', 'AVG', 'Job ID (first 8)']
    rows = []
    
    for row in cursor.fetchall():
        data = list(row)
        # Format job_id
        if data[-1]:
            data[-1] = data[-1][:8] + '...'
        # Format AVG
        if data[-2] is not None:
            data[-2] = f"{data[-2]:.3f}"
        rows.append(data)
    
    if rows:
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        print(f"\nTotal players with stats: {len(rows)}")
    else:
        print(f"No player stats found for {date}")


def show_player_mappings(conn, config):
    """Show player ID mappings"""
    cursor = conn.cursor()
    player_mapping_table = config['player_mapping_table']
    
    print(f"\n{'='*80}")
    print("PLAYER ID MAPPINGS")
    print(f"{'='*80}")
    
    cursor.execute(f"""
        SELECT 
            yahoo_player_id,
            yahoo_player_name,
            team_code,
            position_codes,
            confidence_score,
            mapping_method,
            validation_status
        FROM {player_mapping_table}
        WHERE is_active = 1
        ORDER BY yahoo_player_name
    """)
    
    headers = ['Yahoo ID', 'Player Name', 'Team', 'Positions', 'Confidence', 'Method', 'Status']
    rows = cursor.fetchall()
    
    if rows:
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        print(f"\nTotal active mappings: {len(rows)}")
    else:
        print("No player mappings found")


def show_date_summary(conn, config):
    """Show summary of available dates and record counts"""
    cursor = conn.cursor()
    player_stats_table = config['gkl_player_stats_table']
    
    print(f"\n{'='*80}")
    print("DATE SUMMARY")
    print(f"{'='*80}")
    
    cursor.execute(f"""
        SELECT 
            date,
            COUNT(*) as player_count,
            SUM(batting_hits) as total_hits,
            SUM(batting_runs) as total_runs,
            SUM(batting_rbis) as total_rbis,
            SUM(batting_home_runs) as total_hrs
        FROM {player_stats_table}
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """)
    
    headers = ['Date', 'Players', 'Total Hits', 'Total Runs', 'Total RBIs', 'Total HRs']
    rows = cursor.fetchall()
    
    if rows:
        print(tabulate(rows, headers=headers, tablefmt='grid'))
    else:
        print("No stats data found")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate test data for UAT")
    parser.add_argument('--date', help='Show stats for specific date (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Show all validation data')
    
    args = parser.parse_args()
    
    # Get test config
    config = get_config_for_environment('test')
    db_path = config['database_path']
    
    print(f"Validating test database: {db_path}")
    print(f"Stats table: {config['gkl_player_stats_table']}")
    print(f"Mapping table: {config['player_mapping_table']}")
    
    conn = sqlite3.connect(db_path)
    
    # Always show job logs
    show_job_logs(conn, config)
    
    # Show date summary
    show_date_summary(conn, config)
    
    # Show player stats for specific date or latest
    show_player_stats(conn, config, args.date)
    
    # Optionally show all data
    if args.all:
        show_player_mappings(conn, config)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print("UAT VALIDATION COMPLETE")
    print(f"{'='*80}")
    print("\nNext steps for UAT approval:")
    print("1. Review the job logs to verify job tracking is working")
    print("2. Check player stats data matches expected format")
    print("3. Verify dates align with stat correction window logic")
    print("4. Test with production data when ready")


if __name__ == "__main__":
    main()