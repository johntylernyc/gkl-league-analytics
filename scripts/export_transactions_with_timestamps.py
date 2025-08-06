#!/usr/bin/env python3
"""
Export transactions with timestamps to Cloudflare D1.
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import json

def export_transactions_with_timestamps():
    """Export transactions with timestamp column to D1."""
    
    # Connect to database
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / 'cloudflare-production' / 'sql' / 'migrations'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # First, create the schema update file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    schema_file = output_dir / f'add_timestamp_column_{timestamp}.sql'
    
    with open(schema_file, 'w', encoding='utf-8') as f:
        f.write("-- Add timestamp column to transactions table\n")
        f.write("ALTER TABLE transactions ADD COLUMN timestamp INTEGER DEFAULT 0;\n")
        f.write("CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);\n")
    
    print(f"Created schema migration: {schema_file}")
    
    # Export all transactions with timestamps
    cursor.execute("""
        SELECT id, date, league_key, transaction_id, transaction_type, 
               player_id, player_name, player_team, movement_type, 
               created_at, player_position, destination_team_key, 
               destination_team_name, source_team_key, source_team_name, 
               job_id, timestamp
        FROM transactions
        WHERE timestamp > 0
        ORDER BY id DESC
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        # Create data update file
        data_file = output_dir / f'update_transaction_timestamps_{timestamp}.sql'
        
        with open(data_file, 'w', encoding='utf-8') as f:
            f.write("-- Update existing transactions with timestamps\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n")
            f.write(f"-- Count: {len(rows)}\n\n")
            
            # Write updates in batches
            batch_size = 100
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                for row in batch:
                    # Extract values
                    (id_, date, league_key, transaction_id, transaction_type,
                     player_id, player_name, player_team, movement_type,
                     created_at, player_position, destination_team_key,
                     destination_team_name, source_team_key, source_team_name,
                     job_id, timestamp) = row
                    
                    # Write UPDATE statement
                    f.write(f"UPDATE transactions SET timestamp = {timestamp} "
                           f"WHERE id = {id_};\n")
            
        print(f"Created timestamp updates: {data_file}")
        print(f"Total transactions with timestamps: {len(rows)}")
    
    conn.close()
    
    # Create deployment instructions
    instructions_file = output_dir / 'DEPLOYMENT_INSTRUCTIONS.md'
    with open(instructions_file, 'w') as f:
        f.write("# Transaction Timestamps Migration\n\n")
        f.write("## Steps to Deploy\n\n")
        f.write("1. First, add the timestamp column:\n")
        f.write(f"   ```bash\n")
        f.write(f"   npx wrangler d1 execute gkl-fantasy --file=./sql/migrations/add_timestamp_column_{timestamp}.sql --remote\n")
        f.write(f"   ```\n\n")
        f.write("2. Then update existing transactions with timestamps:\n")
        f.write(f"   ```bash\n")
        f.write(f"   npx wrangler d1 execute gkl-fantasy --file=./sql/migrations/update_transaction_timestamps_{timestamp}.sql --remote\n")
        f.write(f"   ```\n\n")
        f.write("3. Update the Workers API to include timestamp in responses\n\n")
        f.write("4. Deploy the updated Workers code\n\n")
        f.write("5. Test the frontend to verify relative timestamps are working\n")
    
    print(f"\nDeployment instructions: {instructions_file}")

if __name__ == '__main__':
    export_transactions_with_timestamps()