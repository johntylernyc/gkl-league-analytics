#!/usr/bin/env python3
"""
Import SQL chunks to Cloudflare D1 database - Automated version
"""
import os
import subprocess
import time
from pathlib import Path

def import_chunk(chunk_file):
    """Import a single chunk file to D1"""
    cmd = [
        'wrangler', 'd1', 'execute', 'gkl-fantasy',
        '--file', chunk_file,
        '--remote'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    [TIMEOUT] Import timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"    [ERROR] {str(e)}")
        return False

def main():
    # Change to chunks directory
    chunks_dir = Path(__file__).parent.parent / 'sql' / 'chunks'
    os.chdir(chunks_dir)
    
    print("=" * 60)
    print("Cloudflare D1 Data Import - Automated")
    print("=" * 60)
    print()
    
    # Get all chunk files
    lineup_chunks = sorted(Path('.').glob('daily_lineups_chunk_*.sql'))
    stats_chunks = sorted(Path('.').glob('player_stats_chunk_*.sql'))
    
    total_chunks = len(lineup_chunks) + len(stats_chunks)
    print(f"Found {len(lineup_chunks)} lineup chunks")
    print(f"Found {len(stats_chunks)} player stats chunks")
    print(f"Total: {total_chunks} chunks to import")
    print()
    
    print("Starting automated import...")
    print()
    
    successful = 0
    failed = 0
    
    # Import daily lineups
    print("=" * 60)
    print("IMPORTING DAILY LINEUPS")
    print("=" * 60)
    
    for i, chunk in enumerate(lineup_chunks, 1):
        print(f"[{i}/{len(lineup_chunks)}] Importing {chunk.name}...", end=' ', flush=True)
        start_time = time.time()
        
        if import_chunk(str(chunk)):
            elapsed = time.time() - start_time
            print(f"[OK] ({elapsed:.1f}s)")
            successful += 1
        else:
            print(f"[FAILED]")
            failed += 1
        
        # Small delay between imports
        time.sleep(2)
    
    print()
    
    # Import player stats
    print("=" * 60)
    print("IMPORTING PLAYER STATS")
    print("=" * 60)
    
    for i, chunk in enumerate(stats_chunks, 1):
        print(f"[{i}/{len(stats_chunks)}] Importing {chunk.name}...", end=' ', flush=True)
        start_time = time.time()
        
        if import_chunk(str(chunk)):
            elapsed = time.time() - start_time
            print(f"[OK] ({elapsed:.1f}s)")
            successful += 1
        else:
            print(f"[FAILED]")
            failed += 1
        
        # Small delay between imports
        time.sleep(2)
    
    print()
    print("=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Successful imports: {successful}/{total_chunks}")
    print(f"Failed imports: {failed}/{total_chunks}")
    
    if failed > 0:
        print(f"[WARNING] {failed} chunks failed to import")
        print("You may need to re-run the import for failed chunks")
    
    print()
    
    # Verify counts
    print("Verifying database counts...")
    verify_cmd = [
        'wrangler', 'd1', 'execute', 'gkl-fantasy',
        '--command', 
        "SELECT 'transactions' as table_name, COUNT(*) as count FROM transactions " +
        "UNION ALL SELECT 'daily_lineups', COUNT(*) FROM daily_lineups " +
        "UNION ALL SELECT 'daily_gkl_player_stats', COUNT(*) FROM daily_gkl_player_stats " +
        "UNION ALL SELECT 'player_id_mapping', COUNT(*) FROM player_id_mapping " +
        "UNION ALL SELECT 'job_log', COUNT(*) FROM job_log",
        '--remote'
    ]
    
    try:
        result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # Parse the output to show counts nicely
            output = result.stdout
            if "results" in output:
                print("\nDatabase record counts:")
                # Simple parsing - just show the raw output for now
                lines = output.split('\n')
                for line in lines:
                    if '"count"' in line:
                        print(line.strip())
        else:
            print("Could not verify counts - command failed")
    except Exception as e:
        print(f"Could not verify counts: {e}")
    
    print()
    print("=" * 60)
    print("Import process complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()