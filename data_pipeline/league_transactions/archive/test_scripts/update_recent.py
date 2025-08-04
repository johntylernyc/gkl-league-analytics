"""
Quick script to update recent transactions
"""
import sys
import os
import datetime

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import main

if __name__ == "__main__":
    # Set environment variables for a small update
    os.environ['TRANSACTION_ENV'] = 'production'
    os.environ['TRANSACTION_SCENARIO'] = 'small'
    
    # Calculate date range for last 3 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=2)
    
    print(f"Updating transactions from {start_date} to {end_date}")
    print("="*60)
    
    # Override the dates in the config
    import backfill_transactions_optimized as backfill
    backfill.TEST_SCENARIOS['small'] = (start_date.isoformat(), end_date.isoformat())
    
    # Run the main function
    main()