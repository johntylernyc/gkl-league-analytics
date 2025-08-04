# SQL Chunk Files

## Purpose
These files contain chunked SQL data for CloudFlare D1 database import. They were generated from the main database and split into smaller files for CloudFlare's import limits.

## Files
- `daily_lineups_chunk_*.sql` - Daily lineup data split into chunks
- `player_stats_chunk_*.sql` - Player statistics data split into chunks

## Generation
These files can be regenerated using:
```bash
cd scripts
python split_sql_files.py
```

## Size
Total size: ~150MB
Individual chunk size: ~2-3MB each

## Import
Use the import scripts in the parent `scripts/` directory to import these chunks to CloudFlare D1.

Note: These files are tracked in git due to the complexity of regenerating them, but they are large. Consider using Git LFS if the repository size becomes an issue.