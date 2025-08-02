#!/usr/bin/env python
"""
Transaction Update Script for Yahoo Fantasy Baseball League
Safely updates transaction data without creating duplicates
"""

import argparse
import sqlite3
import datetime
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from existing backfill script
from backfill_transactions_optimized import (
    TokenManager,
    rate_limiter,
    fetch_transactions_for_date,
    start_job_log,
    update_job_log,
    LEAGUE_KEYS,
    SEASON_DATES,
    DB_FILE,
    MAX_WORKERS
)

# === CONFIGURATION ===
DEFAULT_ENVIRONMENT = 'production'
UPDATE_MODES = ['incremental', 'refresh', 'force']

# === DATABASE FUNCTIONS ===

def analyze_existing_data(start_date, end_date, environment='production'):
    """
    Analyze what transaction data already exists in the database
    
    Returns:
        dict: Analysis results including dates with data, transaction counts, etc.
    """
    table_name = f"transactions_{environment}"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Get daily transaction counts
        cursor.execute(f"""
            SELECT date, 
                   COUNT(DISTINCT transaction_id) as transaction_count,
                   COUNT(*) as row_count,
                   MIN(created_at) as first_inserted,
                   MAX(created_at) as last_updated
            FROM {table_name}
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """, (start_date, end_date))
        
        daily_data = {}
        for row in cursor.fetchall():
            daily_data[row[0]] = {
                'transaction_count': row[1],
                'row_count': row[2],
                'first_inserted': row[3],
                'last_updated': row[4]
            }
        
        # Get overall statistics
        cursor.execute(f"""
            SELECT COUNT(DISTINCT date) as days_with_data,
                   COUNT(DISTINCT transaction_id) as unique_transactions,
                   COUNT(*) as total_rows,
                   MIN(date) as earliest_date,
                   MAX(date) as latest_date
            FROM {table_name}
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        
        overall_stats = cursor.fetchone()
        
        return {
            'daily_data': daily_data,
            'days_with_data': overall_stats[0] or 0,
            'unique_transactions': overall_stats[1] or 0,
            'total_rows': overall_stats[2] or 0,
            'earliest_date': overall_stats[3],
            'latest_date': overall_stats[4],
            'environment': environment,
            'table': table_name
        }
        
    finally:
        conn.close()

def identify_missing_dates(start_date, end_date, existing_data):
    """
    Identify dates that have no transaction data
    
    Returns:
        list: List of date strings (YYYY-MM-DD) that need to be fetched
    """
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    
    missing_dates = []
    current = start
    
    while current <= end:
        date_str = current.isoformat()
        if date_str not in existing_data.get('daily_data', {}):
            missing_dates.append(date_str)
        current += datetime.timedelta(days=1)
    
    return missing_dates

def update_or_insert_transactions(transactions, environment='production', dry_run=False):
    """
    Update existing transactions or insert new ones using UPSERT logic
    
    Returns:
        dict: Statistics about the update operation
    """
    if not transactions:
        return {'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    
    table_name = f"transactions_{environment}"
    stats = {'new': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    
    if dry_run:
        print(f"[DRY RUN] Would process {len(transactions)} transactions")
        return {'new': 0, 'updated': 0, 'skipped': len(transactions), 'errors': 0}
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        for txn in transactions:
            # Check if record exists
            cursor.execute(f"""
                SELECT id FROM {table_name}
                WHERE transaction_id = ? AND player_id = ? AND movement_type = ?
            """, (txn['transaction_id'], txn['player_id'], txn['movement_type']))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET date = ?,
                        league_key = ?,
                        transaction_type = ?,
                        player_name = ?,
                        player_position = ?,
                        player_team = ?,
                        destination_team_key = ?,
                        destination_team_name = ?,
                        source_team_key = ?,
                        source_team_name = ?,
                        job_id = ?
                    WHERE transaction_id = ? AND player_id = ? AND movement_type = ?
                """, (
                    txn['date'], txn['league_key'], txn['transaction_type'],
                    txn['player_name'], txn['player_position'], txn['player_team'],
                    txn['destination_team_key'], txn['destination_team_name'],
                    txn['source_team_key'], txn['source_team_name'], txn['job_id'],
                    txn['transaction_id'], txn['player_id'], txn['movement_type']
                ))
                
                if cursor.rowcount > 0:
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Insert new record
                cursor.execute(f"""
                    INSERT INTO {table_name}
                    (date, league_key, transaction_id, transaction_type, player_id,
                     player_name, player_position, player_team, movement_type,
                     destination_team_key, destination_team_name, source_team_key, 
                     source_team_name, job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    txn['date'], txn['league_key'], txn['transaction_id'],
                    txn['transaction_type'], txn['player_id'], txn['player_name'],
                    txn['player_position'], txn['player_team'], txn['movement_type'],
                    txn['destination_team_key'], txn['destination_team_name'],
                    txn['source_team_key'], txn['source_team_name'], txn['job_id']
                ))
                stats['new'] += 1
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        stats['errors'] += 1
        conn.rollback()
    finally:
        conn.close()
    
    return stats

def generate_update_report(start_date, end_date, before_stats, after_stats, update_stats, duration):
    """Generate a comprehensive update report"""
    
    print("\n" + "="*60)
    print("UPDATE SUMMARY")
    print("="*60)
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Environment: {before_stats['environment']}")
    print(f"Duration: {duration:.2f} seconds")
    print()
    
    print("Update Statistics:")
    print(f"  New Transactions: {update_stats.get('total_new', 0)}")
    print(f"  Updated Transactions: {update_stats.get('total_updated', 0)}")
    print(f"  Skipped (No Changes): {update_stats.get('total_skipped', 0)}")
    print(f"  Errors: {update_stats.get('total_errors', 0)}")
    print()
    
    print("Database State:")
    print(f"  Before: {before_stats['total_rows']} rows, {before_stats['unique_transactions']} transactions")
    print(f"  After:  {after_stats['total_rows']} rows, {after_stats['unique_transactions']} transactions")
    print(f"  Net Change: +{after_stats['total_rows'] - before_stats['total_rows']} rows")
    print()
    
    if update_stats.get('missing_dates_filled'):
        print(f"Missing Dates Filled: {len(update_stats['missing_dates_filled'])}")
        for date in sorted(update_stats['missing_dates_filled'])[:10]:
            print(f"  - {date}")
        if len(update_stats['missing_dates_filled']) > 10:
            print(f"  ... and {len(update_stats['missing_dates_filled']) - 10} more")

# === MAIN UPDATE FUNCTION ===

def update_transactions(start_date, end_date, mode='incremental', environment='production', 
                        dry_run=False, league_key=None, year=None):
    """
    Main function to update transactions for a date range
    """
    print(f"\n{'='*60}")
    print(f"TRANSACTION UPDATE - {mode.upper()} MODE")
    print(f"{'='*60}")
    
    # Determine league key if not provided
    if not league_key:
        if not year:
            year = datetime.datetime.strptime(start_date, "%Y-%m-%d").year
        league_key = LEAGUE_KEYS.get(year)
        if not league_key:
            print(f"Error: No league key found for year {year}")
            return
    
    print(f"League: {league_key}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Mode: {mode}")
    print(f"Environment: {environment}")
    if dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")
    print()
    
    # Initialize token manager
    token_manager = TokenManager()
    
    # Analyze existing data
    print("Analyzing existing data...")
    before_stats = analyze_existing_data(start_date, end_date, environment)
    print(f"  Found {before_stats['days_with_data']} days with data")
    print(f"  Total transactions: {before_stats['unique_transactions']}")
    
    # Determine dates to fetch based on mode
    dates_to_fetch = []
    
    if mode == 'incremental':
        # Only fetch missing dates
        dates_to_fetch = identify_missing_dates(start_date, end_date, before_stats)
        print(f"  Missing dates to fetch: {len(dates_to_fetch)}")
    elif mode == 'refresh':
        # Fetch all dates but preserve existing data
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        current = start
        while current <= end:
            dates_to_fetch.append(current.isoformat())
            current += datetime.timedelta(days=1)
        print(f"  Refreshing all {len(dates_to_fetch)} dates")
    elif mode == 'force':
        # Similar to refresh but with more aggressive updates
        print("  [WARNING] Force mode will overwrite existing data")
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        current = start
        while current <= end:
            dates_to_fetch.append(current.isoformat())
            current += datetime.timedelta(days=1)
    
    if not dates_to_fetch:
        print("\nNo dates to fetch. Database is up to date!")
        return
    
    # Start job logging
    metadata = f"mode={mode}, dates={len(dates_to_fetch)}, dry_run={dry_run}"
    job_id = start_job_log(f"transaction_update_{mode}", environment, start_date, end_date, league_key, metadata)
    
    # Fetch and update transactions
    print(f"\nFetching transactions for {len(dates_to_fetch)} dates...")
    
    update_stats = defaultdict(int)
    update_stats['missing_dates_filled'] = []
    start_time = time.time()
    
    try:
        # Use concurrent fetching for better performance
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_date = {
                executor.submit(fetch_transactions_for_date, token_manager, league_key, date_str, job_id): date_str 
                for date_str in dates_to_fetch
            }
            
            for future in as_completed(future_to_date):
                date_str, transactions = future.result()
                
                if transactions:
                    # Update or insert transactions
                    stats = update_or_insert_transactions(transactions, environment, dry_run)
                    
                    # Aggregate statistics
                    update_stats['total_new'] += stats['new']
                    update_stats['total_updated'] += stats['updated']
                    update_stats['total_skipped'] += stats['skipped']
                    update_stats['total_errors'] += stats['errors']
                    
                    # Track if this was a missing date
                    if date_str not in before_stats['daily_data']:
                        update_stats['missing_dates_filled'].append(date_str)
                    
                    print(f"  {date_str}: {len(transactions)} transactions "
                          f"(new: {stats['new']}, updated: {stats['updated']}, "
                          f"skipped: {stats['skipped']})")
                else:
                    print(f"  {date_str}: no transactions")
        
        # Get after statistics
        after_stats = analyze_existing_data(start_date, end_date, environment)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Generate report
        generate_update_report(start_date, end_date, before_stats, after_stats, update_stats, duration)
        
        # Update job log
        update_job_log(job_id, 'completed', 
                      records_processed=update_stats['total_new'] + update_stats['total_updated'],
                      records_inserted=update_stats['total_new'])
        
    except Exception as e:
        print(f"\nError during update: {e}")
        update_job_log(job_id, 'failed', error_message=str(e))
        raise

# === COMMAND LINE INTERFACE ===

def main():
    parser = argparse.ArgumentParser(
        description='Update Yahoo Fantasy Baseball transaction data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update today's transactions
  python update_transactions.py --days 1
  
  # Update last week (incremental - only missing dates)
  python update_transactions.py --days 7 --mode incremental
  
  # Refresh specific date range
  python update_transactions.py --start 2025-07-01 --end 2025-07-31 --mode refresh
  
  # Dry run to see what would be updated
  python update_transactions.py --days 30 --dry-run
        """
    )
    
    # Date range options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--days', type=int, 
                           help='Number of days to update (from today backwards)')
    date_group.add_argument('--start', type=str,
                           help='Start date (YYYY-MM-DD)')
    
    parser.add_argument('--end', type=str,
                       help='End date (YYYY-MM-DD), defaults to today or start date')
    
    # Update options
    parser.add_argument('--mode', choices=UPDATE_MODES, default='incremental',
                       help='Update mode: incremental (default), refresh, or force')
    parser.add_argument('--environment', choices=['test', 'production'], 
                       default=DEFAULT_ENVIRONMENT,
                       help='Database environment to update')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be updated without making changes')
    
    # League options
    parser.add_argument('--league-key', type=str,
                       help='Override league key (default: auto-detect from year)')
    parser.add_argument('--year', type=int,
                       help='Year for league key lookup')
    
    args = parser.parse_args()
    
    # Determine date range
    if args.days:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=args.days - 1)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
    else:
        start_date_str = args.start
        if args.end:
            end_date_str = args.end
        else:
            # Default to start date if no end specified
            end_date_str = args.start
    
    # Run the update
    update_transactions(
        start_date_str,
        end_date_str,
        mode=args.mode,
        environment=args.environment,
        dry_run=args.dry_run,
        league_key=args.league_key,
        year=args.year
    )

if __name__ == "__main__":
    main()