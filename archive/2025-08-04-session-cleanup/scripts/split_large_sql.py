#!/usr/bin/env python3
"""
Split large SQL files into smaller chunks for CloudFlare D1 import.
"""

import sys
from pathlib import Path

def split_sql_file(input_file, max_lines=10000):
    """Split SQL file into smaller chunks."""
    
    input_path = Path(input_file)
    output_dir = input_path.parent
    base_name = input_path.stem
    
    print(f"Splitting {input_file} into chunks of {max_lines} lines...")
    
    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    # Find header lines (comments)
    header_lines = []
    data_lines = []
    
    for line in lines:
        if line.startswith('--') or line.strip() == '':
            if not data_lines:  # Still in header
                header_lines.append(line)
        else:
            data_lines.append(line)
    
    print(f"Total data lines: {len(data_lines)}")
    
    # Split into chunks
    chunk_num = 1
    for i in range(0, len(data_lines), max_lines):
        chunk_file = output_dir / f"{base_name}_chunk_{chunk_num:02d}.sql"
        
        with open(chunk_file, 'w', encoding='utf-8') as f:
            # Write header
            for line in header_lines:
                f.write(line)
            f.write(f"-- Chunk {chunk_num} of {(len(data_lines) + max_lines - 1) // max_lines}\n\n")
            
            # Write chunk data
            chunk = data_lines[i:i + max_lines]
            for line in chunk:
                f.write(line)
        
        print(f"  Created {chunk_file.name} with {len(chunk)} lines")
        chunk_num += 1
    
    print(f"Split complete. Created {chunk_num - 1} chunks.")
    return chunk_num - 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python split_large_sql.py <input_file> [max_lines]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    
    split_sql_file(input_file, max_lines)