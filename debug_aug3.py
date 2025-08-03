#!/usr/bin/env python
"""
Debug script to fetch August 3, 2025 transactions directly from Yahoo API
"""
import requests
import xml.etree.ElementTree as ET
import json
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import config
from league_transactions.backfill_transactions_optimized import TokenManager

# Initialize
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
BASE_FANTASY_URL = config.BASE_FANTASY_URL

def fetch_transactions_for_date(date_str, token_manager):
    """Fetch transactions for a specific date."""
    
    print(f"\n=== Fetching transactions for {date_str} ===")
    
    # Get access token
    access_token = token_manager.get_access_token()
    
    # Build URL
    league_key = "mlb.l.6966"
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
    
    print(f"URL: {url}")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml'
    }
    
    # Make request
    print(f"Making API request...")
    response = requests.get(url, headers=headers)
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        # Parse XML
        root = ET.fromstring(response.text)
        
        # Define namespace
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        # Find transactions
        transactions = root.findall('.//fantasy:transaction', ns)
        
        print(f"Found {len(transactions)} transactions")
        
        if len(transactions) > 0:
            print("\nTransaction details:")
            for i, transaction in enumerate(transactions[:5], 1):  # First 5
                trans_id = transaction.find('.//fantasy:transaction_id', ns)
                trans_type = transaction.find('.//fantasy:type', ns)
                timestamp = transaction.find('.//fantasy:timestamp', ns)
                
                print(f"\n{i}. Transaction ID: {trans_id.text if trans_id is not None else 'N/A'}")
                print(f"   Type: {trans_type.text if trans_type is not None else 'N/A'}")
                print(f"   Timestamp: {timestamp.text if timestamp is not None else 'N/A'}")
                
                # Get players
                players = transaction.findall('.//fantasy:player', ns)
                for player in players[:2]:  # First 2 players
                    player_name = player.find('.//fantasy:full', ns)
                    player_id = player.find('.//fantasy:player_id', ns)
                    trans_data = player.find('.//fantasy:transaction_data', ns)
                    
                    if trans_data is not None:
                        trans_type = trans_data.find('.//fantasy:type', ns)
                        source_team = trans_data.find('.//fantasy:source_team_name', ns)
                        dest_team = trans_data.find('.//fantasy:destination_team_name', ns)
                        
                        print(f"   Player: {player_name.text if player_name is not None else 'N/A'} ({player_id.text if player_id is not None else 'N/A'})")
                        print(f"     Type: {trans_type.text if trans_type is not None else 'N/A'}")
                        if source_team is not None:
                            print(f"     From: {source_team.text}")
                        if dest_team is not None:
                            print(f"     To: {dest_team.text}")
        else:
            print("\nNo transactions found for this date.")
            print("\nChecking raw XML response (first 500 chars):")
            print(response.text[:500])
            
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
    
    return response

def main():
    """Main execution."""
    print("=== Debug Script for August 3, 2025 Transactions ===")
    
    # Initialize token manager
    token_manager = TokenManager()
    
    # Test dates
    dates_to_check = [
        "2025-08-02",  # Known to have transactions
        "2025-08-03",  # Should have transactions
        "2025-08-04"   # Future date
    ]
    
    for date_str in dates_to_check:
        try:
            response = fetch_transactions_for_date(date_str, token_manager)
        except Exception as e:
            print(f"Error fetching {date_str}: {e}")
    
    print("\n=== Debug Complete ===")

if __name__ == "__main__":
    main()