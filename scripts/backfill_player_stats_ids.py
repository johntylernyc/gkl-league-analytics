#!/usr/bin/env python3
"""
Backfill missing player IDs in daily_gkl_player_stats table
Date: 2025-08-13

This script updates existing player stats records with Yahoo, Baseball Reference,
and Fangraphs IDs by joining with the player_mapping table.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Check if we should use D1
USE_D1 = '--use-d1' in sys.argv

if USE_D1:
    from data_pipeline.common.d1_connection import D1Connection
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

def backfill_d1():
    """Backfill player IDs in D1 database."""
    try:
        conn = D1Connection()
        logger.info("Connected to D1 database")
        
        # First, check how many records need updating
        result = conn.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN yahoo_player_id IS NULL THEN 1 END) as missing_yahoo,
                   COUNT(CASE WHEN baseball_reference_id IS NULL THEN 1 END) as missing_bbref,
                   COUNT(CASE WHEN fangraphs_id IS NULL THEN 1 END) as missing_fg
            FROM daily_gkl_player_stats
        """)
        
        if result and result[0]:
            stats = result[0][0]
            logger.info(f"Current state:")
            logger.info(f"  Total records: {stats['total']}")
            logger.info(f"  Missing Yahoo IDs: {stats['missing_yahoo']}")
            logger.info(f"  Missing Baseball Reference IDs: {stats['missing_bbref']}")
            logger.info(f"  Missing Fangraphs IDs: {stats['missing_fg']}")
        
        # Update records by joining with player_mapping
        logger.info("\nUpdating player IDs from player_mapping table...")
        
        # Update in batches to avoid timeout
        batch_size = 100
        offset = 0
        total_updated = 0
        
        while True:
            # Get batch of records that need updating
            result = conn.execute(f"""
                SELECT DISTINCT mlb_player_id
                FROM daily_gkl_player_stats
                WHERE yahoo_player_id IS NULL 
                   OR baseball_reference_id IS NULL 
                   OR fangraphs_id IS NULL
                LIMIT {batch_size} OFFSET {offset}
            """)
            
            if not result or not result[0]:
                break
            
            mlb_ids = [row['mlb_player_id'] for row in result[0]]
            if not mlb_ids:
                break
            
            # Update each MLB ID
            for mlb_id in mlb_ids:
                # Get mapping data
                mapping_result = conn.execute("""
                    SELECT yahoo_player_id, baseball_reference_id, fangraphs_id
                    FROM player_mapping
                    WHERE mlb_player_id = ?
                """, [mlb_id])
                
                if mapping_result and mapping_result[0] and mapping_result[0][0]:
                    mapping = mapping_result[0][0]
                    
                    # Update daily_gkl_player_stats
                    update_result = conn.execute("""
                        UPDATE daily_gkl_player_stats
                        SET yahoo_player_id = ?,
                            baseball_reference_id = ?,
                            fangraphs_id = ?
                        WHERE mlb_player_id = ?
                    """, [
                        mapping['yahoo_player_id'],
                        mapping['baseball_reference_id'],
                        mapping['fangraphs_id'],
                        mlb_id
                    ])
                    
                    if update_result:
                        total_updated += 1
            
            logger.info(f"  Processed batch {offset // batch_size + 1}, total updated: {total_updated}")
            offset += batch_size
        
        # Check final state
        result = conn.execute("""
            SELECT COUNT(*) as total,
                   COUNT(yahoo_player_id) as with_yahoo,
                   COUNT(baseball_reference_id) as with_bbref,
                   COUNT(fangraphs_id) as with_fg
            FROM daily_gkl_player_stats
        """)
        
        if result and result[0]:
            stats = result[0][0]
            logger.info(f"\nFinal state:")
            logger.info(f"  Total records: {stats['total']}")
            logger.info(f"  With Yahoo IDs: {stats['with_yahoo']} ({stats['with_yahoo']*100//stats['total']}%)")
            logger.info(f"  With Baseball Reference IDs: {stats['with_bbref']} ({stats['with_bbref']*100//stats['total']}%)")
            logger.info(f"  With Fangraphs IDs: {stats['with_fg']} ({stats['with_fg']*100//stats['total']}%)")
        
        logger.info(f"\n[SUCCESS] Backfill completed! Updated {total_updated} players")
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to backfill D1: {e}")
        return False
    
    return True

def backfill_local():
    """Backfill player IDs in local SQLite database."""
    import sqlite3
    
    db_path = Path("R:/GitHub/gkl-league-analytics/database/league_analytics.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN yahoo_player_id IS NULL THEN 1 END) as missing_yahoo,
                   COUNT(CASE WHEN baseball_reference_id IS NULL THEN 1 END) as missing_bbref,
                   COUNT(CASE WHEN fangraphs_id IS NULL THEN 1 END) as missing_fg
            FROM daily_gkl_player_stats
        """)
        
        stats = cursor.fetchone()
        print(f"Current state:")
        print(f"  Total records: {stats[0]}")
        print(f"  Missing Yahoo IDs: {stats[1]}")
        print(f"  Missing Baseball Reference IDs: {stats[2]}")
        print(f"  Missing Fangraphs IDs: {stats[3]}")
        
        if stats[1] == 0 and stats[2] == 0 and stats[3] == 0:
            print("\nAll IDs are already populated!")
            return True
        
        # Update using JOIN
        print("\nUpdating player IDs from player_mapping table...")
        
        cursor.execute("""
            UPDATE daily_gkl_player_stats
            SET yahoo_player_id = (
                    SELECT yahoo_player_id FROM player_mapping 
                    WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
                ),
                baseball_reference_id = (
                    SELECT baseball_reference_id FROM player_mapping 
                    WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
                ),
                fangraphs_id = (
                    SELECT fangraphs_id FROM player_mapping 
                    WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
                )
            WHERE EXISTS (
                SELECT 1 FROM player_mapping 
                WHERE player_mapping.mlb_player_id = daily_gkl_player_stats.mlb_player_id
            )
        """)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        # Check final state
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(yahoo_player_id) as with_yahoo,
                   COUNT(baseball_reference_id) as with_bbref,
                   COUNT(fangraphs_id) as with_fg
            FROM daily_gkl_player_stats
        """)
        
        stats = cursor.fetchone()
        print(f"\nFinal state:")
        print(f"  Total records: {stats[0]}")
        print(f"  With Yahoo IDs: {stats[1]} ({stats[1]*100//stats[0] if stats[0] else 0}%)")
        print(f"  With Baseball Reference IDs: {stats[2]} ({stats[2]*100//stats[0] if stats[0] else 0}%)")
        print(f"  With Fangraphs IDs: {stats[3]} ({stats[3]*100//stats[0] if stats[0] else 0}%)")
        
        print(f"\n[SUCCESS] Backfill completed! Updated {rows_updated} records")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to backfill local database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if USE_D1:
        print("Backfilling D1 database...")
        success = backfill_d1()
    else:
        print("Backfilling local SQLite database...")
        success = backfill_local()
    
    sys.exit(0 if success else 1)