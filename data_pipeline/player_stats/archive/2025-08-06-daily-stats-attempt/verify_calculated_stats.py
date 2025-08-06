#!/usr/bin/env python3
"""
Verify if Yahoo provides pre-calculated AVG, OBP, SLG in daily data
"""

import sys
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.token_manager import YahooTokenManager

LEAGUE_KEY = '458.l.6966'  # 2025 season


def check_calculated_stats():
    """Check if Yahoo provides calculated stats in daily data"""
    
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
        return
    
    root = ET.fromstring(response.content)
    ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
    
    # Find a player with good stats
    for player in root.findall('.//fantasy:player', ns):
        name_elem = player.find('.//fantasy:name/fantasy:full', ns)
        if name_elem is not None:
            player_name = name_elem.text
            
            # Look for Max Muncy or another player we know had good stats
            if 'Muncy' in player_name or 'Judge' in player_name or 'Betts' in player_name:
                print(f"\n{'='*80}")
                print(f"Player: {player_name}")
                print("="*80)
                
                player_stats = player.find('.//fantasy:player_stats', ns)
                if player_stats is not None:
                    stats_container = player_stats.find('.//fantasy:stats', ns)
                    if stats_container is not None:
                        
                        # Collect all stats
                        stats_dict = {}
                        for stat in stats_container.findall('.//fantasy:stat', ns):
                            stat_id = stat.find('fantasy:stat_id', ns)
                            value = stat.find('fantasy:value', ns)
                            if stat_id is not None and value is not None:
                                stats_dict[stat_id.text] = value.text
                        
                        # Display key stats
                        print("\nRaw counting stats:")
                        print(f"  Stat 60 (H/AB): {stats_dict.get('60', 'N/A')}")
                        print(f"  Stat 7 (R): {stats_dict.get('7', 'N/A')}")
                        print(f"  Stat 8 (H): {stats_dict.get('8', 'N/A')}")
                        print(f"  Stat 11 (3B): {stats_dict.get('11', 'N/A')}")
                        print(f"  Stat 12 (HR): {stats_dict.get('12', 'N/A')}")
                        print(f"  Stat 13 (RBI): {stats_dict.get('13', 'N/A')}")
                        
                        print("\nCalculated rate stats:")
                        print(f"  Stat 3 (AVG): {stats_dict.get('3', 'N/A')}")
                        print(f"  Stat 4 (OBP): {stats_dict.get('4', 'N/A')}")
                        print(f"  Stat 5 (SLG): {stats_dict.get('5', 'N/A')}")
                        
                        print("\nMissing raw components:")
                        print(f"  Stat 10 (2B): {stats_dict.get('10', 'NOT PROVIDED')}")
                        print(f"  Stat 18 (BB): {stats_dict.get('18', 'NOT PROVIDED')}")
                        print(f"  Stat 20 (HBP): {stats_dict.get('20', 'NOT PROVIDED')}")
                        print(f"  Stat 15 (SF): {stats_dict.get('15', 'NOT PROVIDED')}")
                        
                        # Check if we can verify calculations
                        if '60' in stats_dict and '/' in stats_dict['60']:
                            h_ab = stats_dict['60'].split('/')
                            if len(h_ab) == 2:
                                hits = int(h_ab[0])
                                at_bats = int(h_ab[1])
                                
                                if at_bats > 0:
                                    calc_avg = hits / at_bats
                                    yahoo_avg = float(stats_dict.get('3', '0'))
                                    
                                    print(f"\nVerification:")
                                    print(f"  Calculated AVG: {calc_avg:.3f}")
                                    print(f"  Yahoo AVG: {yahoo_avg:.3f}")
                                    print(f"  Match: {'YES' if abs(calc_avg - yahoo_avg) < 0.001 else 'NO'}")


def show_stat_mapping_needed():
    """Show what we need to map"""
    
    print("\n\n" + "="*80)
    print("STAT MAPPING UPDATES NEEDED")
    print("="*80)
    
    print("\nCurrent mapping in collect_daily_stats.py:")
    print("  - We're collecting the counting stats (H, R, RBI, HR, etc.)")
    print("  - We're NOT collecting the rate stats Yahoo provides (AVG, OBP, SLG)")
    print("  - We're missing some raw components (2B, BB, HBP, SF)")
    
    print("\nOptions:")
    print("\n1. Use Yahoo's calculated daily values (EASIEST):")
    print("   - Map stat ID 3 -> batting_avg")
    print("   - Map stat ID 4 -> batting_obp")  
    print("   - Map stat ID 5 -> batting_slg")
    print("   - Calculate OPS = OBP + SLG")
    print("   BUT: Can't accurately aggregate these across date ranges")
    
    print("\n2. Calculate from raw stats (MOST ACCURATE):")
    print("   - Need to check if stat IDs 10, 18, 20, 15 are actually in daily data")
    print("   - If not available, use simplified formulas:")
    print("     * AVG = H / AB (we have this)")
    print("     * SLG = (H - 3B - HR + 2*3B + 4*HR) / AB (missing 2B)")
    print("     * OBP = simplified without HBP and SF")
    print("     * OPS = OBP + SLG")


def main():
    """Main function"""
    print("Verifying Yahoo's Calculated Stats in Daily Data")
    print("="*80)
    
    check_calculated_stats()
    show_stat_mapping_needed()


if __name__ == "__main__":
    main()