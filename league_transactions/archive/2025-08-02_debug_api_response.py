#!/usr/bin/env python3
"""
Debug script to examine Yahoo API response structure
"""

import requests
import xml.etree.ElementTree as ET
import json
import re
import base64
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import config

# === CONFIG ===
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
REDIRECT_URI = config.REDIRECT_URI
TOKEN_URL = config.TOKEN_URL
BASE_FANTASY_URL = config.BASE_FANTASY_URL

def get_access_token():
    """Get fresh access token"""
    tokens_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'auth', 'tokens.json'))
    with open(tokens_path) as f:
        tokens = json.load(f)
        refresh_token = tokens['refresh_token']
    
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'refresh_token',
        'redirect_uri': REDIRECT_URI,
        'refresh_token': refresh_token
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    tokens = response.json()
    return tokens['access_token']

def debug_api_response():
    """Fetch and examine API response structure"""
    
    league_key = "mlb.l.6966"
    date_str = "2025-07-25"  # Date we know has transactions
    
    access_token = get_access_token()
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={date_str}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/xml"
    }
    
    print(f"Fetching transactions for {date_str}...")
    print(f"URL: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.text)}")
    
    # Remove namespace for easier parsing
    xml_text = re.sub(' xmlns="[^"]+\"', '', response.text, count=1)
    
    # Save raw XML for inspection
    with open("debug_response.xml", "w", encoding='utf-8') as f:
        f.write(xml_text)
    print("Raw XML saved to debug_response.xml")
    
    # Parse and examine structure
    root = ET.fromstring(xml_text)
    
    print(f"\nRoot element: {root.tag}")
    print(f"Number of transactions: {len(root.findall('.//transaction'))}")
    
    # Examine first transaction in detail
    first_txn = root.find(".//transaction")
    if first_txn is not None:
        print(f"\n=== FIRST TRANSACTION STRUCTURE ===")
        print(f"Transaction ID: {first_txn.findtext('transaction_id')}")
        print(f"Type: {first_txn.findtext('type')}")
        
        # Show all child elements
        def print_element(elem, indent=0):
            spaces = "  " * indent
            if elem.text and elem.text.strip():
                print(f"{spaces}{elem.tag}: {elem.text.strip()}")
            else:
                print(f"{spaces}{elem.tag}:")
            for child in elem:
                print_element(child, indent + 1)
        
        print_element(first_txn)
        
        # Look specifically for team information
        players = first_txn.findall("players/player")
        print(f"\n=== PLAYERS IN TRANSACTION ===")
        for i, player in enumerate(players):
            print(f"\nPlayer {i+1}:")
            print(f"  Name: {player.findtext('name/full')}")
            print(f"  ID: {player.findtext('player_id')}")
            
            transaction_data = player.find("transaction_data")
            if transaction_data is not None:
                print(f"  Transaction data found:")
                print_element(transaction_data, indent=2)
            else:
                print(f"  No transaction_data found")

if __name__ == "__main__":
    debug_api_response()