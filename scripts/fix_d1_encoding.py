#!/usr/bin/env python3
"""
Fix character encoding issues in CloudFlare D1.
Generate UPDATE statements to fix corrupted player names.
"""

import sqlite3
from pathlib import Path

def generate_fix_statements():
    """Generate SQL statements to fix encoding issues in D1."""
    
    # Connect to local database (which has correct encoding)
    conn = sqlite3.connect('database/league_analytics.db')
    cursor = conn.cursor()
    
    # Get all unique player names with accented characters
    cursor.execute("""
        SELECT DISTINCT player_name 
        FROM transactions 
        WHERE player_name LIKE '%é%'
           OR player_name LIKE '%á%'
           OR player_name LIKE '%í%'
           OR player_name LIKE '%ó%'
           OR player_name LIKE '%ú%'
           OR player_name LIKE '%ñ%'
           OR player_name LIKE '%ü%'
        ORDER BY player_name
    """)
    
    transaction_names = cursor.fetchall()
    
    # Generate fix SQL
    output_file = Path('database/d1_export/fix_encoding.sql')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Fix character encoding issues in CloudFlare D1\n")
        f.write("-- Generated from local database with correct UTF-8 encoding\n\n")
        
        f.write("-- Fix transactions table\n")
        for (name,) in transaction_names:
            # The corrupted version has the replacement character
            corrupted = name.replace('é', '�').replace('á', '�').replace('í', '�')
            corrupted = corrupted.replace('ó', '�').replace('ú', '�').replace('ñ', '�')
            corrupted = corrupted.replace('ü', '�')
            
            # Escape single quotes for SQL
            clean_name = name.replace("'", "''")
            corrupted_name = corrupted.replace("'", "''")
            
            f.write(f"UPDATE transactions SET player_name = '{clean_name}' WHERE player_name = '{corrupted_name}';\n")
        
        f.write("\n-- Fix daily_lineups table\n")
        
        # Get names from daily_lineups
        cursor.execute("""
            SELECT DISTINCT player_name 
            FROM daily_lineups 
            WHERE player_name LIKE '%é%'
               OR player_name LIKE '%á%'
               OR player_name LIKE '%í%'
               OR player_name LIKE '%ó%'
               OR player_name LIKE '%ú%'
               OR player_name LIKE '%ñ%'
               OR player_name LIKE '%ü%'
            ORDER BY player_name
        """)
        
        lineup_names = cursor.fetchall()
        
        for (name,) in lineup_names:
            corrupted = name.replace('é', '�').replace('á', '�').replace('í', '�')
            corrupted = corrupted.replace('ó', '�').replace('ú', '�').replace('ñ', '�')
            corrupted = corrupted.replace('ü', '�')
            
            clean_name = name.replace("'", "''")
            corrupted_name = corrupted.replace("'", "''")
            
            f.write(f"UPDATE daily_lineups SET player_name = '{clean_name}' WHERE player_name = '{corrupted_name}';\n")
        
        f.write("\n-- Fix daily_gkl_player_stats table\n")
        
        # Get names from player stats
        cursor.execute("""
            SELECT DISTINCT player_name 
            FROM daily_gkl_player_stats 
            WHERE player_name LIKE '%é%'
               OR player_name LIKE '%á%'
               OR player_name LIKE '%í%'
               OR player_name LIKE '%ó%'
               OR player_name LIKE '%ú%'
               OR player_name LIKE '%ñ%'
               OR player_name LIKE '%ü%'
            ORDER BY player_name
            LIMIT 500
        """)
        
        stats_names = cursor.fetchall()
        
        for (name,) in stats_names:
            corrupted = name.replace('é', '�').replace('á', '�').replace('í', '�')
            corrupted = corrupted.replace('ó', '�').replace('ú', '�').replace('ñ', '�')
            corrupted = corrupted.replace('ü', '�')
            
            clean_name = name.replace("'", "''")
            corrupted_name = corrupted.replace("'", "''")
            
            f.write(f"UPDATE daily_gkl_player_stats SET player_name = '{clean_name}' WHERE player_name = '{corrupted_name}';\n")
    
    conn.close()
    
    print(f"Generated fix statements in: {output_file}")
    print(f"  - {len(transaction_names)} players in transactions")
    print(f"  - {len(lineup_names)} players in daily_lineups")
    print(f"  - {len(stats_names)} players in daily_gkl_player_stats")
    
    return output_file

if __name__ == "__main__":
    generate_fix_statements()