#!/usr/bin/env python
"""
Quick Transaction Update

Simple script to quickly update transaction database with recent data.
This is designed for daily/routine updates to keep the database current.

Usage:
    python quick_update.py              # Update production database
    python quick_update.py test         # Update test database
    python quick_update.py --help       # Show help
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from league_transactions.backfill_transactions_optimized import (
    run_incremental_update,
    get_latest_transaction_date
)
from common.season_manager import get_league_key
import datetime

def main():
    """Quick update with minimal interaction"""
    
    # Simple argument handling
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print(__doc__)
            return
        elif sys.argv[1] == 'test':
            environment = 'test'
        else:
            environment = 'production'
    else:
        environment = 'production'
    
    print(f"=== Quick Transaction Update ({environment}) ===")
    
    try:
        # Get league key
        current_year = datetime.datetime.now().year
        league_key = get_league_key(current_year)
        
        # Check current status
        latest_date = get_latest_transaction_date(environment, league_key)
        if latest_date:
            print(f"Latest transaction: {latest_date}")
        else:
            print("No existing transactions found")
        
        print("Updating with recent transactions...")
        
        # Run incremental update (7 days lookback for quick updates)
        result = run_incremental_update(
            environment=environment,
            league_key=league_key,
            max_days_back=7
        )
        
        # Show results
        if result['status'] == 'success':
            print(f"[SUCCESS] Added {result['transactions_added']} new transactions")
        elif result['status'] == 'up_to_date':
            print("[SUCCESS] Database is already up to date")
        elif result['status'] == 'no_new_data':
            print("[SUCCESS] No new transactions found")
        else:
            print(f"[ERROR] Update failed: {result['message']}")
            return
            
        # Show final status
        final_latest = get_latest_transaction_date(environment, league_key)
        if final_latest and final_latest != latest_date:
            print(f"Latest transaction now: {final_latest}")
        
    except Exception as e:
        print(f"[ERROR] Quick update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()