#!/usr/bin/env python3
"""
Monitor D1 Data Quality

This script monitors the data quality in Cloudflare D1 database,
checking for completeness, consistency, and recent updates.

Usage:
    python monitor_d1_data.py
    python monitor_d1_data.py --detailed
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.common.d1_connection import D1Connection


def check_data_quality():
    """Check overall data quality in D1."""
    d1 = D1Connection()
    
    print("="*60)
    print("D1 DATA QUALITY REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check each table
    tables = ['transactions', 'daily_lineups', 'daily_gkl_player_stats', 'player_mapping', 'job_log']
    
    for table in tables:
        print(f"\n## {table.upper()}")
        print("-"*40)
        
        # Get basic stats
        result = d1.execute(f"""
            SELECT 
                COUNT(*) as total_records
            FROM {table}
        """)
        
        if result and 'results' in result and result['results']:
            total = result['results'][0]['total_records']
            print(f"Total records: {total:,}")
            
            # Get date range for time-based tables
            if table in ['transactions', 'daily_lineups', 'daily_gkl_player_stats']:
                date_result = d1.execute(f"""
                    SELECT 
                        MIN(date) as earliest,
                        MAX(date) as latest,
                        COUNT(DISTINCT date) as unique_dates
                    FROM {table}
                """)
                
                if date_result and 'results' in date_result and date_result['results']:
                    stats = date_result['results'][0]
                    print(f"Date range: {stats['earliest']} to {stats['latest']}")
                    print(f"Unique dates: {stats['unique_dates']}")
                    
                    # Check for gaps
                    if stats['earliest'] and stats['latest']:
                        expected_days = (datetime.strptime(stats['latest'], '%Y-%m-%d') - 
                                       datetime.strptime(stats['earliest'], '%Y-%m-%d')).days + 1
                        missing_days = expected_days - stats['unique_dates']
                        if missing_days > 0:
                            print(f"WARNING: Missing days: {missing_days}")
                        else:
                            print(f"OK: No gaps in date range")
                    
                    # Check recent data
                    recent_result = d1.execute(f"""
                        SELECT date, COUNT(*) as count
                        FROM {table}
                        WHERE date >= date('now', '-7 days')
                        GROUP BY date
                        ORDER BY date DESC
                    """)
                    
                    if recent_result and 'results' in recent_result and recent_result['results']:
                        print(f"\nLast 7 days:")
                        for row in recent_result['results']:
                            print(f"  {row['date']}: {row['count']:,} records")
                    else:
                        print("WARNING: No data in last 7 days")
    
    # Check job status
    print("\n## JOB STATUS")
    print("-"*40)
    
    job_result = d1.execute("""
        SELECT 
            job_type,
            status,
            COUNT(*) as count
        FROM job_log
        WHERE start_time >= datetime('now', '-24 hours')
        GROUP BY job_type, status
        ORDER BY job_type, status
    """)
    
    if job_result and 'results' in job_result and job_result['results']:
        print("Last 24 hours:")
        for job in job_result['results']:
            status_icon = "OK" if job['status'] == 'completed' else "FAIL"
            print(f"  {status_icon} {job['job_type']}: {job['status']} ({job['count']} jobs)")
    
    # Check player mapping quality
    print("\n## PLAYER MAPPING QUALITY")
    print("-"*40)
    
    mapping_result = d1.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(mlb_player_id) as has_mlb_id,
            COUNT(yahoo_player_id) as has_yahoo_id
        FROM player_mapping
    """)
    
    if mapping_result and 'results' in mapping_result and mapping_result['results']:
        stats = mapping_result['results'][0]
        yahoo_pct = (stats['has_yahoo_id'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"Total mappings: {stats['total']:,}")
        print(f"With MLB ID: {stats['has_mlb_id']:,} (100%)")
        print(f"With Yahoo ID: {stats['has_yahoo_id']:,} ({yahoo_pct:.1f}%)")
        
        if yahoo_pct < 50:
            print("WARNING: Low Yahoo ID coverage - consider running Yahoo ID matcher")
    
    # Check data freshness
    print("\n## DATA FRESHNESS")
    print("-"*40)
    
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    for table in ['transactions', 'daily_lineups', 'daily_gkl_player_stats']:
        result = d1.execute(f"""
            SELECT MAX(date) as latest_date
            FROM {table}
        """)
        
        if result and 'results' in result and result['results']:
            latest = result['results'][0]['latest_date']
            if latest == today:
                print(f"OK: {table}: Up to date (today)")
            elif latest == yesterday:
                print(f"OK: {table}: Current (yesterday)")
            else:
                days_behind = (datetime.now() - datetime.strptime(latest, '%Y-%m-%d')).days if latest else 999
                print(f"WARNING: {table}: {days_behind} days behind (last: {latest})")


def check_detailed_stats():
    """Show detailed statistics."""
    d1 = D1Connection()
    
    print("\n## DETAILED PLAYER STATS ANALYSIS")
    print("-"*40)
    
    # Check player stats coverage
    result = d1.execute("""
        SELECT 
            COUNT(DISTINCT mlb_player_id) as unique_players,
            COUNT(DISTINCT date) as unique_dates,
            AVG(batting_hits) as avg_hits,
            AVG(pitching_strikeouts) as avg_k,
            SUM(CASE WHEN has_batting_data = 1 THEN 1 ELSE 0 END) as batting_records,
            SUM(CASE WHEN has_pitching_data = 1 THEN 1 ELSE 0 END) as pitching_records
        FROM daily_gkl_player_stats
    """)
    
    if result and 'results' in result and result['results']:
        stats = result['results'][0]
        print(f"Unique players tracked: {stats['unique_players']}")
        print(f"Unique dates: {stats['unique_dates']}")
        print(f"Records with batting data: {stats['batting_records']}")
        print(f"Records with pitching data: {stats['pitching_records']}")
        
        if stats['avg_hits']:
            print(f"Average hits per game: {stats['avg_hits']:.2f}")
        if stats['avg_k']:
            print(f"Average strikeouts (pitchers): {stats['avg_k']:.2f}")


def main():
    parser = argparse.ArgumentParser(
        description='Monitor D1 data quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed statistics')
    
    args = parser.parse_args()
    
    try:
        check_data_quality()
        
        if args.detailed:
            check_detailed_stats()
            
        print("\n" + "="*60)
        print("END OF REPORT")
        print("="*60)
        
    except Exception as e:
        print(f"\nERROR generating report: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()