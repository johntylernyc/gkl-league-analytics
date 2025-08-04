#!/usr/bin/env python3
"""
Split large SQL files into chunks for Cloudflare D1 import
"""
import os
import sys

def split_sql_file(input_file, output_prefix, chunk_size=5000):
    """Split a SQL file into smaller chunks"""
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    num_chunks = (total_lines + chunk_size - 1) // chunk_size
    
    print(f"Splitting {input_file}:")
    print(f"  Total lines: {total_lines}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Number of chunks: {num_chunks}")
    
    # Create chunks
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, total_lines)
        
        chunk_file = f"chunks/{output_prefix}_chunk_{i+1:02d}.sql"
        
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.writelines(lines[start_idx:end_idx])
        
        print(f"  Created {chunk_file} ({end_idx - start_idx} lines)")
    
    return num_chunks

def main():
    # Change to sql directory
    os.chdir('../sql')
    
    # Ensure chunks directory exists
    if not os.path.exists('chunks'):
        os.makedirs('chunks')
    
    print("=" * 50)
    print("SQL File Splitter for Cloudflare D1")
    print("=" * 50)
    print()
    
    # Split daily_lineups
    if os.path.exists('data_daily_lineups.sql'):
        lineups_chunks = split_sql_file(
            'data_daily_lineups.sql', 
            'daily_lineups',
            chunk_size=5000
        )
        print(f"\n[OK] Split daily_lineups into {lineups_chunks} chunks")
    else:
        print("[WARNING] data_daily_lineups.sql not found")
    
    print()
    
    # Split daily_gkl_player_stats
    if os.path.exists('data_daily_gkl_player_stats.sql'):
        stats_chunks = split_sql_file(
            'data_daily_gkl_player_stats.sql',
            'player_stats',
            chunk_size=5000
        )
        print(f"\n[OK] Split player_stats into {stats_chunks} chunks")
    else:
        print("[WARNING] data_daily_gkl_player_stats.sql not found")
    
    print()
    print("=" * 50)
    print("Splitting complete!")
    print("Chunks are in the sql/chunks/ directory")
    print("Use import-chunks.bat to import them to D1")
    print("=" * 50)

if __name__ == "__main__":
    main()