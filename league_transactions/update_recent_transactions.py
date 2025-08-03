#!/usr/bin/env python
"""
Update Recent Transactions Script

This script performs incremental updates to collect new transaction data
since the last update. It identifies the most recent transaction date in
the database and fetches only new transactions from the Yahoo API.

Usage:
    python update_recent_transactions.py [--environment production|test] [--max-days 30]

Examples:
    # Update production database with default 30-day lookback
    python update_recent_transactions.py --environment production

    # Update test database with 7-day lookback  
    python update_recent_transactions.py --environment test --max-days 7

    # Quick update (default to production, 30 days)
    python update_recent_transactions.py
"""

import sys
import os
import argparse
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from league_transactions.backfill_transactions_optimized import (
    run_incremental_update,
    get_latest_transaction_date,
    get_date_range_for_update,
    init_database
)
from common.season_manager import get_league_key
import datetime

def main():
    """Main function for incremental transaction updates"""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Update transaction database with recent Yahoo API data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--environment', '-e',
        choices=['production', 'test'],
        default='production',
        help='Database environment to update (default: production)'
    )
    
    parser.add_argument(
        '--max-days', '-d',
        type=int,
        default=30,
        help='Maximum days to look back from today (default: 30)'
    )
    
    parser.add_argument(
        '--league-key', '-l',
        type=str,
        help='League key to update (default: current season league)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=== Transaction Incremental Update ===")
    print(f"Environment: {args.environment}")
    print(f"Max days back: {args.max_days}")
    
    # Get league key  
    if args.league_key:
        league_key = args.league_key
    else:
        # Default to current year's league
        current_year = datetime.datetime.now().year
        league_key = get_league_key(current_year)
    print(f"League key: {league_key}")
    
    # Show current database status
    try:
        latest_date = get_latest_transaction_date(args.environment, league_key)
        if latest_date:
            print(f"Latest transaction in database: {latest_date}")
        else:
            print("No transactions found in database")
            
        # Show what date range would be updated
        start_date, end_date = get_date_range_for_update(
            args.environment, league_key, args.max_days
        )
        
        if start_date and end_date:
            print(f"Update range: {start_date} to {end_date}")
        else:
            print("Database is already up to date")
            return
            
    except Exception as e:
        print(f"Error checking database status: {e}")
        return
    
    # Dry run mode
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print("No changes will be made to the database")
        print(f"Would update transactions from {start_date} to {end_date}")
        return
    
    # Confirm before proceeding
    print(f"\nReady to update {args.environment} database")
    print(f"Will fetch transactions from {start_date} to {end_date}")
    
    if args.environment == 'production':
        response = input("Continue with production update? (y/N): ")
        if response.lower() != 'y':
            print("Update cancelled")
            return
    
    # Run the incremental update
    print("\n=== Starting Incremental Update ===")
    
    try:
        result = run_incremental_update(
            environment=args.environment,
            league_key=league_key,
            max_days_back=args.max_days
        )
        
        # Display results
        print(f"\n=== Update Complete ===")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Transactions added: {result['transactions_added']}")
        
        if 'date_range' in result:
            print(f"Date range: {result['date_range']}")
            
        # Show final database status
        final_latest = get_latest_transaction_date(args.environment, league_key)
        if final_latest:
            print(f"Latest transaction now: {final_latest}")
            
    except Exception as e:
        print(f"\nUpdate failed: {e}")
        logging.error(f"Incremental update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()