"""
Update transactions for the last few days
"""
import os
import sys

# Set to production mode and small scenario
os.environ['TRANSACTION_ENV'] = 'production'
os.environ['TRANSACTION_SCENARIO'] = 'small'

# Run the backfill script
sys.path.append('league_transactions')
import backfill_transactions_optimized

# The script runs on import