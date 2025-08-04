#!/usr/bin/env python3
"""
Fix character encoding issues in CloudFlare D1.
This version handles the specific corruption pattern where accented characters
were replaced with the UTF-8 replacement character sequence.
"""

import sqlite3
from pathlib import Path

# Mapping of correct names to their corrupted versions
# The corruption pattern is that accented characters became ï¿½ (UTF-8 bytes: EF BF BD)
NAME_FIXES = {
    'José': 'Jos�',
    'Jesús': 'Jes�s',
    'Martínez': 'Mart�nez',
    'García': 'Garc�a',
    'Rodríguez': 'Rodr�guez',
    'González': 'Gonz�lez',
    'Hernández': 'Hern�ndez',
    'López': 'L�pez',
    'Pérez': 'P�rez',
    'Sánchez': 'S�nchez',
    'Ramírez': 'Ram�rez',
    'Díaz': 'D�az',
    'Vásquez': 'V�squez',
    'Giménez': 'Gim�nez',
    'Báez': 'B�ez',
    'Pagán': 'Pag�n',
    'Brazobán': 'Brazob�n',
    'Narváez': 'Narv�ez',
    'Domínguez': 'Dom�nguez',
    'Acuña': 'Acu�a',
}

def generate_fix_statements():
    """Generate SQL statements to fix encoding issues in D1."""
    
    # Connect to local database (which has correct encoding)
    conn = sqlite3.connect('database/league_analytics.db')
    cursor = conn.cursor()
    
    # Get all unique player names with accented characters
    cursor.execute("""
        SELECT DISTINCT player_name 
        FROM (
            SELECT player_name FROM transactions
            UNION
            SELECT player_name FROM daily_lineups
            UNION
            SELECT player_name FROM daily_gkl_player_stats
        )
        WHERE player_name LIKE '%é%'
           OR player_name LIKE '%á%'
           OR player_name LIKE '%í%'
           OR player_name LIKE '%ó%'
           OR player_name LIKE '%ú%'
           OR player_name LIKE '%ñ%'
           OR player_name LIKE '%ü%'
           OR player_name LIKE '%É%'
           OR player_name LIKE '%Á%'
           OR player_name LIKE '%Í%'
           OR player_name LIKE '%Ó%'
           OR player_name LIKE '%Ú%'
           OR player_name LIKE '%Ñ%'
        ORDER BY player_name
    """)
    
    all_names = cursor.fetchall()
    
    # Build comprehensive replacement mapping
    replacements = {}
    
    for (name,) in all_names:
        # Create the corrupted version
        corrupted = name
        for correct, corrupt in NAME_FIXES.items():
            if correct in name:
                corrupted = corrupted.replace(correct, corrupt)
        
        # Also handle individual character replacements
        char_map = {
            'é': '�', 'á': '�', 'í': '�', 'ó': '�', 'ú': '�', 'ñ': '�', 'ü': '�',
            'É': '�', 'Á': '�', 'Í': '�', 'Ó': '�', 'Ú': '�', 'Ñ': '�'
        }
        
        for correct_char, corrupt_char in char_map.items():
            if correct_char in name:
                corrupted = corrupted.replace(correct_char, corrupt_char)
        
        if corrupted != name:
            replacements[name] = corrupted
    
    # Generate fix SQL
    output_file = Path('database/d1_export/fix_encoding_v2.sql')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Fix character encoding issues in CloudFlare D1\n")
        f.write("-- This handles the specific UTF-8 replacement character corruption\n\n")
        
        # Write updates for each table
        for table in ['transactions', 'daily_lineups', 'daily_gkl_player_stats']:
            f.write(f"\n-- Fix {table} table\n")
            
            for correct_name, corrupted_name in replacements.items():
                # Escape single quotes for SQL
                clean = correct_name.replace("'", "''")
                corrupt = corrupted_name.replace("'", "''")
                
                f.write(f"UPDATE {table} SET player_name = '{clean}' WHERE player_name = '{corrupt}';\n")
    
    conn.close()
    
    print(f"Generated fix statements in: {output_file}")
    print(f"Total unique names to fix: {len(replacements)}")
    print("\nExample fixes:")
    for i, (correct, corrupted) in enumerate(list(replacements.items())[:5]):
        print(f"  {corrupted} -> {correct}")
    
    return output_file

if __name__ == "__main__":
    generate_fix_statements()