#!/usr/bin/env python3
"""
Analyze what stats we have and what we need for AVG, OBP, SLG, OPS calculations
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


def check_available_stats():
    """Check what stats Yahoo provides for daily data"""
    
    # Get access token
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
    all_stat_ids = set()
    sample_player = None
    
    for player in root.findall('.//fantasy:player', ns):
        name_elem = player.find('.//fantasy:name/fantasy:full', ns)
        if name_elem is not None:
            player_name = name_elem.text
            
            # Get player stats
            player_stats = player.find('.//fantasy:player_stats', ns)
            if player_stats is not None:
                stats_container = player_stats.find('.//fantasy:stats', ns)
                if stats_container is not None:
                    stats = stats_container.findall('.//fantasy:stat', ns)
                    
                    # Look for a player with many stats
                    if len(stats) > 10 and not sample_player:
                        sample_player = (player_name, stats)
                    
                    # Collect all stat IDs
                    for stat in stats:
                        stat_id = stat.find('fantasy:stat_id', ns)
                        if stat_id is not None:
                            all_stat_ids.add(stat_id.text)
    
    print("="*80)
    print("AVAILABLE DAILY STAT IDS FROM YAHOO API")
    print("="*80)
    
    if sample_player:
        player_name, stats = sample_player
        print(f"\nSample Player: {player_name}")
        print("Stats provided:")
        
        for stat in stats:
            stat_id = stat.find('fantasy:stat_id', ns)
            value = stat.find('fantasy:value', ns)
            if stat_id is not None and value is not None:
                print(f"  Stat ID {stat_id.text}: {value.text}")
    
    print(f"\nAll unique stat IDs found: {sorted(all_stat_ids)}")
    
    # Check what batting stats we need
    print("\n" + "="*80)
    print("STATS NEEDED FOR CALCULATIONS")
    print("="*80)
    
    print("\nFor AVG (Batting Average):")
    print("  - Hits (H) - Stat ID 8 ✓")
    print("  - At Bats (AB) - Stat ID 60 (H/AB format) ✓")
    
    print("\nFor OBP (On-Base Percentage):")
    print("  Formula: (H + BB + HBP) / (AB + BB + HBP + SF)")
    print("  - Hits (H) - Stat ID 8 ✓")
    print("  - Walks (BB) - Stat ID 18 ?")
    print("  - Hit By Pitch (HBP) - Need to find stat ID")
    print("  - At Bats (AB) - Stat ID 60 ✓")
    print("  - Sacrifice Flies (SF) - Need to find stat ID")
    
    print("\nFor SLG (Slugging Percentage):")
    print("  Formula: (1B + 2*2B + 3*3B + 4*HR) / AB")
    print("  - Singles (1B) - Calculate as (H - 2B - 3B - HR)")
    print("  - Doubles (2B) - Stat ID 10 ?")
    print("  - Triples (3B) - Stat ID 11 ?")
    print("  - Home Runs (HR) - Stat ID 12 ✓")
    print("  - At Bats (AB) - Stat ID 60 ✓")
    
    print("\nFor OPS (On-Base Plus Slugging):")
    print("  Formula: OBP + SLG")
    print("  - Requires all stats from OBP and SLG above")


def check_database_schema():
    """Check what columns we have in our database"""
    config = get_config_for_environment('test')
    conn = sqlite3.connect(config['database_path'])
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("DATABASE SCHEMA CHECK")
    print("="*80)
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({config['gkl_player_stats_table']})")
    columns = cursor.fetchall()
    
    batting_columns = []
    for col in columns:
        if 'batting_' in col[1]:
            batting_columns.append(col[1])
    
    print("\nBatting columns in database:")
    for col in sorted(batting_columns):
        print(f"  - {col}")
    
    # Check if we have the calculated fields
    print("\nCalculated fields status:")
    print(f"  - batting_obp: {'✓' if 'batting_obp' in batting_columns else '✗ MISSING'}")
    print(f"  - batting_slg: {'✓' if 'batting_slg' in batting_columns else '✗ MISSING'}")
    print(f"  - batting_ops: {'✓' if 'batting_ops' in batting_columns else '✗ MISSING'}")
    
    # Check what raw stats we have
    print("\nRaw stats for calculations:")
    required_stats = [
        'batting_at_bats',
        'batting_hits', 
        'batting_doubles',
        'batting_triples',
        'batting_home_runs',
        'batting_walks',
        'batting_hit_by_pitch',
        'batting_sacrifice_flies'
    ]
    
    for stat in required_stats:
        status = '✓' if stat in batting_columns else '✗ MISSING'
        print(f"  - {stat}: {status}")
    
    conn.close()


def test_stat_calculations():
    """Test if we can calculate stats from what we have"""
    config = get_config_for_environment('test')
    conn = sqlite3.connect(config['database_path'])
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("TESTING STAT CALCULATIONS WITH CURRENT DATA")
    print("="*80)
    
    # Try to calculate stats for a player
    cursor.execute(f"""
        SELECT 
            player_name,
            date,
            batting_at_bats,
            batting_hits,
            batting_doubles,
            batting_triples,
            batting_home_runs,
            batting_walks,
            batting_strikeouts,
            batting_avg
        FROM {config['gkl_player_stats_table']}
        WHERE date = '2025-08-05'
          AND batting_at_bats > 0
        ORDER BY batting_hits DESC
        LIMIT 5
    """)
    
    print("\nSample calculations:")
    for row in cursor.fetchall():
        name, date, ab, h, d2b, d3b, hr, bb, k, avg = row
        
        print(f"\n{name} on {date}:")
        print(f"  AB={ab}, H={h}, 2B={d2b or 0}, 3B={d3b or 0}, HR={hr}, BB={bb or 0}")
        
        # Calculate what we can
        if ab > 0:
            calc_avg = h / ab
            print(f"  AVG: {calc_avg:.3f} (stored: {avg:.3f})")
            
            # Try to calculate SLG
            singles = h - (d2b or 0) - (d3b or 0) - hr
            total_bases = singles + 2*(d2b or 0) + 3*(d3b or 0) + 4*hr
            slg = total_bases / ab
            print(f"  SLG: {slg:.3f} (1B={singles}, TB={total_bases})")
            
            # OBP - limited without HBP and SF
            if bb is not None:
                # Simplified OBP without HBP and SF
                obp = (h + bb) / (ab + bb)
                print(f"  OBP: {obp:.3f} (simplified - missing HBP, SF)")
            else:
                print("  OBP: Cannot calculate - missing BB")
        
    conn.close()


def main():
    """Main function"""
    print("Analyzing Stats for AVG, OBP, SLG, OPS Calculations")
    print("="*80)
    
    # Check what Yahoo provides
    check_available_stats()
    
    # Check our database schema
    check_database_schema()
    
    # Test calculations
    test_stat_calculations()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print("\n1. We need to find and map these Yahoo stat IDs:")
    print("   - Hit By Pitch (HBP)")
    print("   - Sacrifice Flies (SF)")
    print("   - Verify we're getting Walks (BB) - stat ID 18")
    print("\n2. Database schema needs these columns:")
    print("   - batting_hit_by_pitch")
    print("   - batting_sacrifice_flies")
    print("\n3. After collecting raw stats, calculate and store:")
    print("   - batting_obp = (H + BB + HBP) / (AB + BB + HBP + SF)")
    print("   - batting_slg = (1B + 2*2B + 3*3B + 4*HR) / AB")
    print("   - batting_ops = OBP + SLG")


if __name__ == "__main__":
    main()