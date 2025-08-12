#!/usr/bin/env python3
"""
Sync Player Mappings to D1

Syncs player_mapping table from local SQLite database to Cloudflare D1.
This enables player ID enrichment in production when collecting stats.

Usage:
    python sync_player_mappings_to_d1.py [--environment production|test]
"""

import sys
import sqlite3
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.common.d1_connection import D1Connection
from data_pipeline.player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_player_mapping_table_d1(d1_conn: D1Connection):
    """Create player_mapping table in D1 if it doesn't exist"""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS player_mapping (
        player_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
        mlb_id INTEGER,
        yahoo_player_id TEXT,
        baseball_reference_id TEXT,
        fangraphs_id TEXT,
        player_name TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        team_code TEXT,
        active BOOLEAN DEFAULT 1,
        last_verified TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    try:
        d1_conn.execute(schema_sql)
        logger.info("Ensured player_mapping table exists in D1")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb ON player_mapping(mlb_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id)",
            "CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(player_name)",
            "CREATE INDEX IF NOT EXISTS idx_player_mapping_active ON player_mapping(active)"
        ]
        
        for index_sql in indexes:
            d1_conn.execute(index_sql)
        
        logger.info("Created indexes on player_mapping table")
        
    except Exception as e:
        logger.error(f"Error creating player_mapping table: {e}")
        raise


def get_player_mappings_from_sqlite(db_path: str) -> List[Dict]:
    """Fetch all player mappings from local SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                mlb_id,
                yahoo_player_id,
                baseball_reference_id,
                fangraphs_id,
                player_name,
                first_name,
                last_name,
                team_code,
                active,
                last_verified,
                created_at,
                updated_at
            FROM player_mapping
            WHERE active = 1
            ORDER BY player_name
        """)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        mappings = []
        for row in rows:
            mapping = dict(zip(columns, row))
            mappings.append(mapping)
        
        logger.info(f"Found {len(mappings)} active player mappings in SQLite")
        return mappings
        
    finally:
        conn.close()


def sync_mappings_to_d1(d1_conn: D1Connection, mappings: List[Dict]):
    """Sync player mappings to D1 database"""
    
    # Clear existing mappings (we'll do a full replace)
    try:
        result = d1_conn.execute("DELETE FROM player_mapping")
        logger.info(f"Cleared {result.get('changes', 0)} existing mappings from D1")
    except Exception as e:
        logger.warning(f"Error clearing existing mappings (may not exist): {e}")
    
    # Insert mappings individually to avoid SQL variable limits
    # D1 has strict limits on SQL variables per query
    total_inserted = 0
    errors = 0
    
    logger.info(f"Starting to sync {len(mappings)} player mappings individually...")
    
    for idx, mapping in enumerate(mappings):
        # Use REPLACE to handle any duplicates
        insert_sql = """
            REPLACE INTO player_mapping (
                mlb_id, yahoo_player_id, baseball_reference_id, fangraphs_id,
                player_name, first_name, last_name, team_code,
                active, last_verified, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = [
            mapping.get('mlb_id'),
            mapping.get('yahoo_player_id'),
            mapping.get('baseball_reference_id'),
            mapping.get('fangraphs_id'),
            mapping.get('player_name'),
            mapping.get('first_name'),
            mapping.get('last_name'),
            mapping.get('team_code'),
            mapping.get('active', 1),
            mapping.get('last_verified'),
            mapping.get('created_at'),
            mapping.get('updated_at')
        ]
        
        try:
            result = d1_conn.execute(insert_sql, values)
            total_inserted += 1
            
            # Log progress every 100 records
            if (idx + 1) % 100 == 0:
                logger.info(f"Progress: {idx + 1}/{len(mappings)} mappings synced")
                
        except Exception as e:
            errors += 1
            logger.error(f"Error inserting mapping for {mapping.get('player_name')} (MLB ID {mapping.get('mlb_id')}): {e}")
            # Continue with next record
            if errors > 50:  # Stop if too many errors
                logger.error("Too many errors, stopping sync")
                break
    
    logger.info(f"Successfully synced {total_inserted} player mappings to D1 ({errors} errors)")
    
    # Verify the sync
    result = d1_conn.execute("SELECT COUNT(*) as count FROM player_mapping")
    count = result.get('results', [[0]])[0][0] if result.get('results') else 0
    logger.info(f"Verification: D1 now has {count} player mappings")


def main():
    parser = argparse.ArgumentParser(
        description='Sync player mappings from SQLite to D1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--environment',
        choices=['production', 'test'],
        default='production',
        help='Database environment to sync from (default: production)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be synced without actually syncing'
    )
    
    args = parser.parse_args()
    
    # Get configuration
    config = get_config_for_environment(args.environment)
    db_path = config['database_path']
    
    logger.info(f"Syncing player mappings from {args.environment} SQLite to D1")
    logger.info(f"Source database: {db_path}")
    
    # Fetch mappings from SQLite
    mappings = get_player_mappings_from_sqlite(db_path)
    
    if not mappings:
        logger.warning("No player mappings found in SQLite database")
        return
    
    # Show sample of what will be synced
    logger.info("\nSample of mappings to sync:")
    for mapping in mappings[:5]:
        logger.info(f"  {mapping['player_name']} (MLB: {mapping['mlb_id']}, Yahoo: {mapping['yahoo_player_id']})")
    
    if args.dry_run:
        logger.info(f"\nDry run mode - would sync {len(mappings)} mappings to D1")
        return
    
    # Initialize D1 connection
    try:
        d1_conn = D1Connection()
    except Exception as e:
        logger.error(f"Failed to initialize D1 connection: {e}")
        logger.error("Make sure D1 environment variables are set:")
        logger.error("  CLOUDFLARE_ACCOUNT_ID, D1_DATABASE_ID, CLOUDFLARE_API_TOKEN")
        return
    
    # Create table if needed (with mlb_player_id column)
    create_player_mapping_table_d1(d1_conn)
    
    # Add mlb_player_id column if missing (for backward compatibility)
    try:
        d1_conn.execute("ALTER TABLE player_mapping ADD COLUMN mlb_player_id INTEGER")
        logger.info("Added mlb_player_id column to player_mapping table")
    except Exception as e:
        # Column likely already exists
        pass
    
    # Update mlb_player_id to match mlb_id if needed
    try:
        d1_conn.execute("UPDATE player_mapping SET mlb_player_id = mlb_id WHERE mlb_player_id IS NULL")
        logger.info("Updated mlb_player_id values from mlb_id")
    except Exception as e:
        logger.debug(f"Could not update mlb_player_id: {e}")
    
    # Sync mappings
    sync_mappings_to_d1(d1_conn, mappings)
    
    logger.info("\nSync complete!")


if __name__ == "__main__":
    main()