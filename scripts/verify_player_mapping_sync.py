#!/usr/bin/env python3
"""
Verify Player Mapping Sync

Quick script to verify that player mappings are properly synced to D1
and that player stats are being enriched with Yahoo IDs.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.common.d1_connection import D1Connection

def verify_sync():
    """Verify player mapping sync and stats enrichment."""
    
    d1 = D1Connection()
    
    print("=" * 60)
    print("PLAYER MAPPING SYNC VERIFICATION")
    print("=" * 60)
    
    # Check player_mapping table
    result = d1.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT mlb_id) as unique_mlb,
               COUNT(DISTINCT mlb_player_id) as unique_mlb_player,
               COUNT(yahoo_player_id) as with_yahoo,
               COUNT(baseball_reference_id) as with_bbref,
               COUNT(fangraphs_id) as with_fg
        FROM player_mapping
    """)
    
    if result and 'results' in result and result['results']:
        stats = result['results'][0]
        print(f"\nPlayer Mapping Table:")
        print(f"  Total mappings: {stats['total']}")
        print(f"  Unique MLB IDs: {stats['unique_mlb']}")
        print(f"  Unique MLB Player IDs: {stats['unique_mlb_player']}")
        print(f"  With Yahoo IDs: {stats['with_yahoo']}")
        print(f"  With Baseball Reference: {stats['with_bbref']}")
        print(f"  With FanGraphs: {stats['with_fg']}")
    
    # Check for specific players that were having issues
    print(f"\nSample Player Checks:")
    
    test_players = [
        829272,  # Player that was missing before
        545361,  # Mike Trout
        660271,  # Shohei Ohtani
    ]
    
    for mlb_id in test_players:
        result = d1.execute("""
            SELECT player_name, yahoo_player_id, baseball_reference_id, fangraphs_id
            FROM player_mapping
            WHERE mlb_player_id = ? OR mlb_id = ?
        """, [mlb_id, mlb_id])
        
        if result and 'results' in result and result['results']:
            player = result['results'][0]
            print(f"  {player['player_name']} (MLB: {mlb_id})")
            print(f"    Yahoo: {player['yahoo_player_id']}")
            print(f"    BBRef: {player['baseball_reference_id']}")
            print(f"    FanGraphs: {player['fangraphs_id']}")
    
    # Check daily_gkl_player_stats enrichment
    print(f"\nPlayer Stats Enrichment Check:")
    
    result = d1.execute("""
        SELECT 
            date,
            COUNT(*) as total_records,
            COUNT(yahoo_player_id) as with_yahoo,
            COUNT(CASE WHEN baseball_reference_id = 'baseball_reference_id' THEN 1 END) as bad_bbref,
            COUNT(CASE WHEN fangraphs_id = 'fangraphs_id' THEN 1 END) as bad_fg
        FROM daily_gkl_player_stats
        WHERE date >= date('now', '-7 days')
        GROUP BY date
        ORDER BY date DESC
        LIMIT 7
    """)
    
    if result and 'results' in result and result['results']:
        print(f"\n  Recent daily stats (last 7 days):")
        print(f"  {'Date':<12} {'Total':<8} {'w/Yahoo':<10} {'Bad BBRef':<12} {'Bad FG':<10}")
        print(f"  {'-'*52}")
        for row in result['results']:
            print(f"  {row['date']:<12} {row['total_records']:<8} {row['with_yahoo']:<10} {row['bad_bbref']:<12} {row['bad_fg']:<10}")
    
    # Check most recent stats
    result = d1.execute("""
        SELECT 
            player_name,
            yahoo_player_id,
            baseball_reference_id,
            fangraphs_id
        FROM daily_gkl_player_stats
        WHERE date = (SELECT MAX(date) FROM daily_gkl_player_stats)
        LIMIT 5
    """)
    
    if result and 'results' in result and result['results']:
        print(f"\n  Sample of most recent player stats:")
        for row in result['results']:
            print(f"    {row['player_name']}")
            print(f"      Yahoo: {row['yahoo_player_id']}")
            print(f"      BBRef: {row['baseball_reference_id']}")
            print(f"      FG: {row['fangraphs_id']}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    verify_sync()