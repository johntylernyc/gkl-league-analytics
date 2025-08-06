#!/usr/bin/env python3
"""
Check what stats we have and what we need for AVG, OBP, SLG, OPS calculations
"""

import sys
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import sqlite3

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.token_manager import YahooTokenManager
from data_pipeline.player_stats.config import get_config_for_environment

LEAGUE_KEY = '458.l.6966'  # 2025 season


def get_all_stat_ids():
    """Get all available stat IDs from Yahoo"""
    
    token_manager = YahooTokenManager()
    access_token = token_manager.get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml'
    }
    
    # Get stat categories to understand all available stats
    url = "https://fantasysports.yahooapis.com/fantasy/v2/game/mlb/stat_categories"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        print("ALL AVAILABLE YAHOO STAT IDS:")
        print("="*80)
        
        batting_stats = {}
        
        for stat in root.findall('.//fantasy:stat', ns):
            stat_id = stat.find('.//fantasy:stat_id', ns)
            name = stat.find('.//fantasy:name', ns)
            display_name = stat.find('.//fantasy:display_name', ns)
            position_type = stat.find('.//fantasy:position_type', ns)
            
            if stat_id is not None and name is not None:
                # Focus on batting stats
                if position_type is not None and position_type.text == 'B':
                    batting_stats[stat_id.text] = {
                        'name': name.text,
                        'display': display_name.text if display_name is not None else name.text
                    }
        
        # Print batting stats sorted by ID
        for stat_id in sorted(batting_stats.keys(), key=int):
            stat = batting_stats[stat_id]
            print(f"  ID {stat_id}: {stat['name']} ({stat['display']})")
        
        return batting_stats


def check_daily_stats():
    """Check what stats are actually provided in daily data"""
    
    token_manager = YahooTokenManager()
    access_token = token_manager.get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/xml'
    }
    
    # Get a team's roster for yesterday
    yesterday = '2025-08-05'
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{LEAGUE_KEY}.t.1/roster;date={yesterday}/players/stats;type=date;date={yesterday}"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return set()
    
    root = ET.fromstring(response.content)
    ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
    
    # Collect all stat IDs that appear in daily data
    daily_stat_ids = set()
    
    for player in root.findall('.//fantasy:player', ns):
        player_stats = player.find('.//fantasy:player_stats', ns)
        if player_stats is not None:
            stats_container = player_stats.find('.//fantasy:stats', ns)
            if stats_container is not None:
                for stat in stats_container.findall('.//fantasy:stat', ns):
                    stat_id = stat.find('fantasy:stat_id', ns)
                    if stat_id is not None:
                        daily_stat_ids.add(stat_id.text)
    
    return daily_stat_ids


def analyze_stat_gaps():
    """Analyze what stats we need vs what we have"""
    
    # Get all available stats
    all_stats = get_all_stat_ids()
    
    # Get stats provided in daily data
    daily_stats = check_daily_stats()
    
    print("\n\nDAILY STATS PROVIDED BY YAHOO:")
    print("="*80)
    print("Stats in daily data:", sorted(daily_stats, key=int))
    
    # Check specific stats we need
    print("\n\nSTAT AVAILABILITY FOR CALCULATIONS:")
    print("="*80)
    
    required_stats = {
        # For AVG
        '8': 'Hits (H) - REQUIRED for AVG',
        '60': 'H/AB - Provides At Bats - REQUIRED for AVG',
        
        # For OBP
        '18': 'Walks (BB) - REQUIRED for OBP',
        '19': 'Hit By Pitch (HBP) - REQUIRED for OBP',
        '90': 'Sacrifice Flies (SF) - REQUIRED for OBP',
        
        # For SLG
        '10': 'Doubles (2B) - REQUIRED for SLG',
        '11': 'Triples (3B) - REQUIRED for SLG',
        '12': 'Home Runs (HR) - REQUIRED for SLG',
        
        # Additional useful stats
        '21': 'Strikeouts (K)',
        '16': 'Stolen Bases (SB)',
        '17': 'Caught Stealing (CS)',
    }
    
    print("\nRequired stats status:")
    for stat_id, description in required_stats.items():
        in_catalog = stat_id in all_stats
        in_daily = stat_id in daily_stats
        
        if in_daily:
            status = "[PROVIDED IN DAILY]"
        elif in_catalog:
            status = "[EXISTS but NOT in daily]"
        else:
            status = "[NOT FOUND]"
            
        print(f"  {stat_id}: {description} {status}")
        
        if in_catalog and stat_id in all_stats:
            print(f"      Yahoo name: {all_stats[stat_id]['name']}")


def check_database_columns():
    """Check what columns exist in our database"""
    config = get_config_for_environment('test')
    conn = sqlite3.connect(config['database_path'])
    cursor = conn.cursor()
    
    print("\n\nDATABASE SCHEMA CHECK:")
    print("="*80)
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({config['gkl_player_stats_table']})")
    columns = cursor.fetchall()
    
    batting_columns = []
    for col in columns:
        if 'batting_' in col[1]:
            batting_columns.append(col[1])
    
    print("Batting columns in database:")
    for col in sorted(batting_columns):
        print(f"  - {col}")
    
    # Check required columns
    print("\nMissing columns for calculations:")
    required = [
        'batting_hit_by_pitch',
        'batting_sacrifice_flies', 
        'batting_caught_stealing',
        'batting_obp',
        'batting_slg',
        'batting_ops'
    ]
    
    for col in required:
        if col not in batting_columns:
            print(f"  - {col} [MISSING]")
    
    conn.close()


def show_calculation_formulas():
    """Show the formulas we need to implement"""
    
    print("\n\nSTAT CALCULATION FORMULAS:")
    print("="*80)
    
    print("\n1. AVG (Batting Average):")
    print("   Formula: H / AB")
    print("   We have: H (stat 8), AB (from stat 60)")
    print("   Status: CAN CALCULATE")
    
    print("\n2. OBP (On-Base Percentage):")
    print("   Formula: (H + BB + HBP) / (AB + BB + HBP + SF)")
    print("   We have: H, AB, possibly BB")
    print("   Missing: HBP (stat 19), SF (stat 90)")
    print("   Status: NEED MORE DATA")
    
    print("\n3. SLG (Slugging Percentage):")
    print("   Formula: Total Bases / AB")
    print("   Total Bases = 1B + 2*2B + 3*3B + 4*HR")
    print("   Singles (1B) = H - 2B - 3B - HR")
    print("   We need: H, 2B, 3B, HR, AB")
    print("   Status: CHECK IF 2B/3B PROVIDED")
    
    print("\n4. OPS (On-Base Plus Slugging):")
    print("   Formula: OBP + SLG")
    print("   Status: Depends on OBP and SLG")


def main():
    """Main function"""
    print("Analyzing Stats Requirements for AVG, OBP, SLG, OPS")
    print("="*80)
    
    # Get all stats and check what's available
    analyze_stat_gaps()
    
    # Check database schema
    check_database_columns()
    
    # Show formulas
    show_calculation_formulas()
    
    print("\n\nRECOMMENDATIONS:")
    print("="*80)
    print("1. Check if stats 18 (BB), 19 (HBP), 90 (SF) are in daily data")
    print("2. Add missing columns to database schema")
    print("3. Calculate OBP, SLG, OPS during data collection")
    print("4. Store calculated values for easy aggregation")


if __name__ == "__main__":
    main()