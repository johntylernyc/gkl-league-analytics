#!/usr/bin/env python3
"""
Debug API response to see raw transaction data structure
"""

import sys
import os
import requests
import xml.etree.ElementTree as ET
import re
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backfill_transactions_optimized import TokenManager, LEAGUE_KEYS, BASE_FANTASY_URL

def debug_single_transaction():
    print("="*80)
    print("API RESPONSE DEBUG - SINGLE TRANSACTION")
    print("="*80)
    
    # Initialize token manager
    token_manager = TokenManager()
    token_manager.initialize()
    
    league_key = LEAGUE_KEYS[2025]
    test_date = "2025-07-15"  # Use a middle date
    
    print(f"Requesting transactions for: {test_date}")
    print(f"League: {league_key}")
    print(f"URL: {BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={test_date}")
    
    access_token = token_manager.get_access_token()
    url = f"{BASE_FANTASY_URL}/league/{league_key}/transactions;types=add,drop,trade;date={test_date}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/xml"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        # Show raw XML (first 2000 characters)
        raw_xml = response.text
        print(f"\nRaw XML Response (first 2000 chars):")
        print("-" * 80)
        print(raw_xml[:2000])
        if len(raw_xml) > 2000:
            print("... (truncated)")
        print("-" * 80)
        
        # Parse and show structured data
        xml_text = re.sub(' xmlns=\\\"[^\\\"]+\\\"', '', response.text, count=1)
        root = ET.fromstring(xml_text)
        
        print(f"\nParsed XML Structure:")
        print("-" * 80)
        
        transactions = root.findall(".//transaction")
        print(f"Found {len(transactions)} transactions")
        
        if transactions:
            # Show detailed structure of first transaction
            first_txn = transactions[0]
            print(f"\nFIRST TRANSACTION DETAILED STRUCTURE:")
            print("=" * 60)
            
            def print_element(elem, indent=0):
                spaces = "  " * indent
                if elem.text and elem.text.strip():
                    print(f"{spaces}{elem.tag}: '{elem.text.strip()}'")
                else:
                    print(f"{spaces}{elem.tag}:")
                
                for child in elem:
                    print_element(child, indent + 1)
            
            print_element(first_txn)
            
            # Show all available date-related fields
            print(f"\nDATE-RELATED FIELDS IN FIRST TRANSACTION:")
            print("=" * 60)
            
            def find_date_fields(elem, path=""):
                results = []
                current_path = f"{path}/{elem.tag}" if path else elem.tag
                
                # Check if this element contains date-like data
                if elem.text and elem.text.strip():
                    text = elem.text.strip()
                    if any(keyword in elem.tag.lower() for keyword in ['date', 'time', 'timestamp']) or \
                       any(keyword in text for keyword in ['2025', '2024']) or \
                       '-' in text:
                        results.append((current_path, text))
                
                # Check attributes
                for attr_name, attr_value in elem.attrib.items():
                    if any(keyword in attr_name.lower() for keyword in ['date', 'time', 'timestamp']) or \
                       any(keyword in str(attr_value) for keyword in ['2025', '2024']):
                        results.append((f"{current_path}@{attr_name}", attr_value))
                
                # Recurse into children
                for child in elem:
                    results.extend(find_date_fields(child, current_path))
                
                return results
            
            date_fields = find_date_fields(first_txn)
            for field_path, value in date_fields:
                print(f"  {field_path}: '{value}'")
            
            # Show players in first transaction
            players = first_txn.findall(".//player")
            print(f"\nPLAYERS IN FIRST TRANSACTION ({len(players)} players):")
            print("=" * 60)
            
            for i, player in enumerate(players[:2]):  # Show first 2 players
                print(f"\nPlayer {i+1}:")
                print_element(player, 1)
        
        print(f"\n" + "="*80)
        print("DEBUG COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_single_transaction()