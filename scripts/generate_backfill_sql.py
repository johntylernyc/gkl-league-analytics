#!/usr/bin/env python3
"""
Generate SQL to backfill missing player IDs in daily_gkl_player_stats
Date: 2025-08-13
"""

from datetime import datetime
from pathlib import Path

def generate_backfill_sql():
    """Generate SQL commands to backfill player IDs."""
    
    # Create output directory
    output_dir = Path("R:/GitHub/gkl-league-analytics/cloudflare-production/sql/migrations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"backfill_player_stats_ids_{timestamp}.sql"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"-- Backfill Player IDs in daily_gkl_player_stats\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- This updates existing records with Yahoo, Baseball Reference, and Fangraphs IDs\n\n")
        
        # Check current state
        f.write("-- Check current state\n")
        f.write("SELECT 'Before Update' as status,\n")
        f.write("       COUNT(*) as total_records,\n")
        f.write("       COUNT(yahoo_player_id) as with_yahoo,\n")
        f.write("       COUNT(baseball_reference_id) as with_bbref,\n")
        f.write("       COUNT(fangraphs_id) as with_fg\n")
        f.write("FROM daily_gkl_player_stats;\n\n")
        
        # Update statement using correlated subqueries
        f.write("-- Update player IDs from player_mapping table\n")
        f.write("UPDATE daily_gkl_player_stats\n")
        f.write("SET yahoo_player_id = (\n")
        f.write("        SELECT yahoo_player_id FROM player_mapping \n")
        f.write("        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id\n")
        f.write("    ),\n")
        f.write("    baseball_reference_id = (\n")
        f.write("        SELECT baseball_reference_id FROM player_mapping \n")
        f.write("        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id\n")
        f.write("    ),\n")
        f.write("    fangraphs_id = (\n")
        f.write("        SELECT fangraphs_id FROM player_mapping \n")
        f.write("        WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id\n")
        f.write("    )\n")
        f.write("WHERE EXISTS (\n")
        f.write("    SELECT 1 FROM player_mapping \n")
        f.write("    WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id\n")
        f.write(");\n\n")
        
        # Check final state
        f.write("-- Check final state\n")
        f.write("SELECT 'After Update' as status,\n")
        f.write("       COUNT(*) as total_records,\n")
        f.write("       COUNT(yahoo_player_id) as with_yahoo,\n")
        f.write("       COUNT(baseball_reference_id) as with_bbref,\n")
        f.write("       COUNT(fangraphs_id) as with_fg\n")
        f.write("FROM daily_gkl_player_stats;\n")
    
    print(f"[SUCCESS] SQL script generated!")
    print(f"   Output file: {output_file}")
    print(f"\nTo apply to D1, run:")
    print(f"   cd cloudflare-production")
    print(f"   npx wrangler d1 execute gkl-fantasy --file=./sql/migrations/backfill_player_stats_ids_{timestamp}.sql --remote")
    
    return output_file

if __name__ == "__main__":
    generate_backfill_sql()