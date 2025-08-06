#!/usr/bin/env python3
"""
Update timestamps for existing transactions by re-fetching from Yahoo API.
"""
import argparse
import logging
import sqlite3
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

from auth.token_manager import YahooTokenManager
from data_pipeline.common.season_manager import get_league_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'


def fetch_transactions_for_date(token_manager: YahooTokenManager, league_key: str, date_str: str) -> Dict[str, int]:
    """
    Fetch transactions for a specific date and return mapping of transaction_id to timestamp.
    
    Returns:
        Dict mapping transaction_id to Unix timestamp
    """
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
    headers = {
        'Authorization': f'Bearer {token_manager.get_access_token()}',
        'Accept': 'application/xml'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.text)
        ns = {'y': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        timestamp_map = {}
        transaction_elements = root.findall('.//y:transaction', ns)
        
        for trans_elem in transaction_elements:
            trans_id_elem = trans_elem.find('.//y:transaction_id', ns)
            timestamp_elem = trans_elem.find('.//y:timestamp', ns)
            
            if trans_id_elem is not None and timestamp_elem is not None:
                trans_id = trans_id_elem.text
                if trans_id and timestamp_elem.text:
                    try:
                        timestamp = int(timestamp_elem.text)
                        timestamp_map[trans_id] = timestamp
                    except (ValueError, TypeError):
                        pass
        
        return timestamp_map
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching transactions for {date_str}: {e}")
        return {}


def update_timestamps_with_keys(db_path: str, start_date: datetime, end_date: datetime, api_league_key: str, db_league_key: str):
    """Update timestamps for existing transactions in the database."""
    
    token_manager = YahooTokenManager()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get distinct dates with missing timestamps
    cursor.execute("""
        SELECT DISTINCT date 
        FROM transactions 
        WHERE (timestamp IS NULL OR timestamp = 0)
        AND date >= ? AND date <= ?
        ORDER BY date
    """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    
    dates = [row[0] for row in cursor.fetchall()]
    
    if not dates:
        logger.info("No transactions with missing timestamps in date range")
        return
    
    logger.info(f"Found {len(dates)} dates with missing timestamps")
    
    total_updated = 0
    
    for date_str in dates:
        logger.info(f"Processing {date_str}...")
        
        # Fetch timestamps from API (use API league key)
        timestamp_map = fetch_transactions_for_date(token_manager, api_league_key, date_str)
        
        if not timestamp_map:
            logger.warning(f"No timestamps retrieved for {date_str}")
            continue
        
        # Update transactions with timestamps
        updated_this_date = 0
        
        # Update all transactions matching this transaction_id (may be multiple due to multiple players)
        for trans_id, timestamp in timestamp_map.items():
            # First check if we need to update (use DB league key)
            cursor.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE transaction_id = ? 
                AND league_key = ?
                AND (timestamp = 0 OR timestamp IS NULL)
            """, (trans_id, db_league_key))
            
            count = cursor.fetchone()[0]
            if count > 0:
                # Do the update
                cursor.execute("""
                    UPDATE transactions 
                    SET timestamp = ?
                    WHERE transaction_id = ? 
                    AND league_key = ?
                """, (timestamp, trans_id, db_league_key))
                
                if cursor.rowcount > 0:
                    updated_this_date += cursor.rowcount
                    total_updated += cursor.rowcount
        
        conn.commit()
        logger.info(f"Updated {updated_this_date} transactions for {date_str}")
        
        # Small delay to respect rate limits
        import time
        time.sleep(0.5)
    
    conn.close()
    logger.info(f"Total transactions updated: {total_updated}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Update timestamps for existing transactions'
    )
    
    parser.add_argument('--start', type=str, required=True,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--environment', choices=['production', 'test'], 
                       default='production',
                       help='Database environment (default: production)')
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start, '%Y-%m-%d')
    end_date = datetime.strptime(args.end, '%Y-%m-%d')
    
    # Get database path
    if args.environment == 'production':
        db_path = 'database/league_analytics.db'
    else:
        db_path = 'database/league_analytics_test.db'
    
    db_path = str(Path(__file__).parent.parent / db_path)
    
    # Get league key from API
    api_league_key = get_league_key(start_date.year)
    if not api_league_key:
        logger.error(f"No league key found for {start_date.year}")
        return
    
    # The database uses mlb.l.6966 format while API uses 458.l.6966
    # Extract the league ID part
    league_id = api_league_key.split('.', 1)[1]  # Gets "l.6966"
    db_league_key = f"mlb.{league_id}"
    
    logger.info(f"Updating timestamps from {args.start} to {args.end}")
    logger.info(f"Database: {db_path}")
    logger.info(f"API League: {api_league_key}")
    logger.info(f"DB League: {db_league_key}")
    
    # Pass both league keys to the update function
    update_timestamps_with_keys(db_path, start_date, end_date, api_league_key, db_league_key)


if __name__ == '__main__':
    main()