#!/usr/bin/env python3
"""
Simple Player ID Mapping Population

A streamlined approach to populate player ID mappings focusing on the most 
critical mappings first (exact matches) without external API calls initially.
"""

import sys
import sqlite3
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mapping_table():
    """Create player_id_mapping table with correct schema."""
    db_path = root_dir / "database" / "league_analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing table to ensure clean schema
    cursor.execute('DROP TABLE IF EXISTS player_id_mapping')
    
    cursor.execute('''
        CREATE TABLE player_id_mapping (
            mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            yahoo_player_id TEXT,
            yahoo_player_name TEXT,
            mlb_player_id TEXT,
            fangraphs_id TEXT,
            bbref_id TEXT,
            standardized_name TEXT,
            team_code TEXT,
            position_codes TEXT,
            birth_year INTEGER,
            confidence_score REAL DEFAULT 0.0,
            mapping_method TEXT DEFAULT 'pending',
            manual_override BOOLEAN DEFAULT FALSE,
            verified_by TEXT,
            verified_at TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            last_validated DATE,
            validation_status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX idx_yahoo_player_id ON player_id_mapping(yahoo_player_id)')
    cursor.execute('CREATE INDEX idx_mlb_player_id ON player_id_mapping(mlb_player_id)')
    
    conn.commit()
    conn.close()
    logger.info("Created player_id_mapping table")


def populate_exact_matches():
    """Populate high-confidence exact name matches first."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    # Load candidates
    candidates = pd.read_csv(candidates_path)
    exact_matches = candidates[candidates['mapping_method'] == 'exact_name_match'].copy()
    
    logger.info(f"Processing {len(exact_matches)} exact matches")
    
    conn = sqlite3.connect(db_path)
    
    # Prepare data for bulk insert
    records = []
    for _, row in exact_matches.iterrows():
        records.append((
            row['yahoo_player_id'],
            row['yahoo_player_name'],
            str(row['mlb_player_id']) if pd.notna(row['mlb_player_id']) else None,
            '',  # fangraphs_id - to be filled later
            '',  # bbref_id - to be filled later
            row['standardized_name'],
            row['team_code'],
            row['position_codes'],
            None,  # birth_year
            row['confidence_score'],
            'exact_name_match',
            0,  # manual_override
            None,  # verified_by
            None,  # verified_at
            1,  # is_active
            None,  # last_validated
            'validated',
            None,  # notes
            datetime.now(),
            datetime.now()
        ))
    
    # Bulk insert
    conn.executemany('''
        INSERT INTO player_id_mapping (
            yahoo_player_id, yahoo_player_name, mlb_player_id, 
            fangraphs_id, bbref_id, standardized_name, team_code, 
            position_codes, birth_year, confidence_score, mapping_method,
            manual_override, verified_by, verified_at, is_active,
            last_validated, validation_status, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Inserted {len(records)} exact match mappings")


def populate_pending_lookups():
    """Add entries for players that need PyBaseball lookup."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    candidates = pd.read_csv(candidates_path)
    need_lookup = candidates[candidates['mapping_method'] == 'needs_pybaseball_lookup'].copy()
    
    logger.info(f"Processing {len(need_lookup)} players needing lookup")
    
    conn = sqlite3.connect(db_path)
    
    records = []
    for _, row in need_lookup.iterrows():
        records.append((
            row['yahoo_player_id'],
            row['yahoo_player_name'],
            None,  # mlb_player_id - to be filled by lookup
            '',    # fangraphs_id
            '',    # bbref_id
            row['standardized_name'],
            row['team_code'],
            row['position_codes'],
            None,  # birth_year
            0.0,   # confidence_score
            'needs_lookup',
            0,     # manual_override
            None,  # verified_by
            None,  # verified_at
            1,     # is_active
            None,  # last_validated
            'pending',
            'Needs PyBaseball lookup',
            datetime.now(),
            datetime.now()
        ))
    
    conn.executemany('''
        INSERT INTO player_id_mapping (
            yahoo_player_id, yahoo_player_name, mlb_player_id, 
            fangraphs_id, bbref_id, standardized_name, team_code, 
            position_codes, birth_year, confidence_score, mapping_method,
            manual_override, verified_by, verified_at, is_active,
            last_validated, validation_status, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Inserted {len(records)} pending lookup entries")


def add_stats_only_players():
    """Add MLB-only players (no Yahoo Fantasy equivalent)."""
    db_path = root_dir / "database" / "league_analytics.db"
    candidates_path = root_dir / "player_stats" / "mapping_candidates.csv"
    
    candidates = pd.read_csv(candidates_path)
    stats_only = candidates[candidates['mapping_method'] == 'stats_only_player'].copy()
    
    logger.info(f"Processing {len(stats_only)} stats-only players")
    
    conn = sqlite3.connect(db_path)
    
    records = []
    for _, row in stats_only.iterrows():
        records.append((
            None,  # yahoo_player_id
            None,  # yahoo_player_name
            str(row['mlb_player_id']),
            '',    # fangraphs_id
            '',    # bbref_id
            row['standardized_name'],
            row['team_code'],
            row['position_codes'],
            None,  # birth_year
            0.8,   # confidence_score - we have MLB ID
            'mlb_only',
            0,     # manual_override
            None,  # verified_by
            None,  # verified_at
            1,     # is_active
            None,  # last_validated
            'validated',
            'MLB player not in fantasy lineups',
            datetime.now(),
            datetime.now()
        ))
    
    # Process in smaller batches to avoid locks
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        conn.executemany('''
            INSERT INTO player_id_mapping (
                yahoo_player_id, yahoo_player_name, mlb_player_id, 
                fangraphs_id, bbref_id, standardized_name, team_code, 
                position_codes, birth_year, confidence_score, mapping_method,
                manual_override, verified_by, verified_at, is_active,
                last_validated, validation_status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch)
        conn.commit()
        total_inserted += len(batch)
        logger.info(f"Inserted batch: {total_inserted}/{len(records)}")
    
    conn.close()
    logger.info(f"Inserted {total_inserted} stats-only player entries")


def verify_mappings():
    """Verify the mapping results."""
    db_path = root_dir / "database" / "league_analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM player_id_mapping')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM player_id_mapping WHERE yahoo_player_id IS NOT NULL')
    with_yahoo = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM player_id_mapping WHERE mlb_player_id IS NOT NULL')
    with_mlb = cursor.fetchone()[0]
    
    cursor.execute('SELECT mapping_method, COUNT(*) FROM player_id_mapping GROUP BY mapping_method')
    methods = cursor.fetchall()
    
    conn.close()
    
    logger.info("=== MAPPING VERIFICATION ===")
    logger.info(f"Total mappings: {total}")
    logger.info(f"With Yahoo ID: {with_yahoo}")
    logger.info(f"With MLB ID: {with_mlb}")
    logger.info("By method:")
    for method, count in methods:
        logger.info(f"  {method}: {count}")


def main():
    """Run the simplified mapping population."""
    logger.info("Starting simplified player mapping population")
    
    create_mapping_table()
    populate_exact_matches()
    populate_pending_lookups()
    add_stats_only_players()
    verify_mappings()
    
    logger.info("Player mapping population complete!")


if __name__ == "__main__":
    main()