#!/usr/bin/env python3
"""
Fix player stats chunks to use INSERT OR REPLACE instead of INSERT.
"""

from pathlib import Path

def fix_chunks():
    """Fix chunks to use INSERT OR REPLACE."""
    
    chunk_dir = Path('database/d1_export')
    
    # Process chunks 4-6
    for chunk_num in range(4, 7):
        chunk_file = chunk_dir / f'05_daily_gkl_player_stats_chunk_{chunk_num:02d}.sql'
        
        if chunk_file.exists():
            print(f"Fixing {chunk_file.name}...")
            
            with open(chunk_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Replace INSERT INTO with INSERT OR REPLACE INTO
            content = content.replace('INSERT INTO daily_gkl_player_stats', 'INSERT OR REPLACE INTO daily_gkl_player_stats')
            
            # Write back
            fixed_file = chunk_dir / f'05_daily_gkl_player_stats_chunk_{chunk_num:02d}_fixed.sql'
            with open(fixed_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  Created {fixed_file.name}")

if __name__ == "__main__":
    fix_chunks()