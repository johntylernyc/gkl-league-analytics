#!/usr/bin/env python3
"""
Validate test data for UAT - shows what the job imports look like
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment


def format_table(headers, rows, widths=None):
    """Simple table formatter without dependencies"""
    if not widths:
        widths = [max(len(str(h)), max(len(str(row[i]) if row[i] is not None else 'N/A') 
                      for row in rows) if rows else 0) 
                  for i, h in enumerate(headers)]
    
    # Print header
    header_line = ' | '.join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print('-' * len(header_line))
    
    # Print rows
    for row in rows:
        formatted_row = []
        for i, (val, w) in enumerate(zip(row, widths)):
            if val is None:
                formatted_row.append('N/A'.ljust(w))
            else:
                formatted_row.append(str(val).ljust(w))
        print(' | '.join(formatted_row))


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
        format_table(headers, rows)
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
            ps.batting_avg as AVG
        FROM {player_stats_table} ps
        WHERE ps.date = ?
        ORDER BY ps.batting_hits DESC, ps.batting_rbis DESC
    """, (date,))
    
    headers = ['Player', 'Team', 'Pos', 'AB', 'H', 'R', 'RBI', 'HR', 'SB', 'AVG']
    rows = []
    
    for row in cursor.fetchall():
        data = list(row)
        # Format AVG
        if data[-1] is not None:
            data[-1] = f"{data[-1]:.3f}"
        rows.append(data)
    
    if rows:
        format_table(headers, rows)
        print(f"\nTotal players with stats: {len(rows)}")
    else:
        print(f"No player stats found for {date}")


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
        format_table(headers, rows)
    else:
        print("No stats data found")


def show_sample_job_data(conn, config):
    """Show what a typical job import looks like"""
    cursor = conn.cursor()
    player_stats_table = config['gkl_player_stats_table']
    
    print(f"\n{'='*80}")
    print("SAMPLE JOB IMPORT DATA")
    print(f"{'='*80}")
    
    # Get a recent job
    cursor.execute("""
        SELECT job_id, job_type, date_range_start, records_processed
        FROM job_log
        WHERE job_type LIKE '%stats%' AND status = 'completed'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    job_info = cursor.fetchone()
    if not job_info:
        print("No completed jobs found")
        return
    
    job_id, job_type, date_start, records = job_info
    print(f"Job: {job_id[:8]}... ({job_type})")
    print(f"Date: {date_start}, Records: {records}")
    print("\nSample records from this job:")
    
    # Show sample records
    cursor.execute(f"""
        SELECT 
            player_name,
            batting_at_bats,
            batting_hits,
            batting_runs,
            batting_rbis,
            batting_home_runs
        FROM {player_stats_table}
        WHERE job_id = ?
        LIMIT 5
    """, (job_id,))
    
    headers = ['Player', 'AB', 'H', 'R', 'RBI', 'HR']
    rows = cursor.fetchall()
    
    if rows:
        format_table(headers, rows)
    else:
        print("No records found for this job")


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
    
    # Show sample job data
    show_sample_job_data(conn, config)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print("UAT VALIDATION COMPLETE")
    print(f"{'='*80}")
    print("\nNext steps for UAT approval:")
    print("1. Review the job logs to verify job tracking is working")
    print("2. Check player stats data matches expected format")
    print("3. Verify dates align with stat correction window logic")
    print("4. Test with production data when ready")
    print("\nTo approve and move forward:")
    print("- Run: python update_stats.py --environment production")
    print("- Test D1 integration: python update_stats.py --use-d1")


if __name__ == "__main__":
    main()