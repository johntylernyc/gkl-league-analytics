#!/usr/bin/env python3
"""
Player ID Mapping Population

Populates the player_id_mapping table with comprehensive player identification
using PyBaseball's playerid_lookup function and analysis results.

Key Functions:
- Load mapping candidates from analysis
- Use PyBaseball to lookup FanGraphs, Baseball Reference, and other IDs
- Populate player_id_mapping table with complete player information
- Handle fuzzy matching and confidence scoring
"""

import sys
import sqlite3
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import time

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.pybaseball_integration import PyBaseballIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerMappingPopulator:
    """Populates comprehensive player ID mappings using PyBaseball data."""
    
    def __init__(self, environment: str = "production"):
        """Initialize the mapping populator."""
        self.environment = environment
        self.db_path = root_dir / "database" / "league_analytics.db"
        self.pybaseball = PyBaseballIntegration(environment)
        
        logger.info(f"Initialized PlayerMappingPopulator for {environment}")
    
    def load_mapping_candidates(self, csv_path: str = None) -> pd.DataFrame:
        """Load mapping candidates from analysis results."""
        if csv_path is None:
            csv_path = root_dir / "player_stats" / "mapping_candidates.csv"
        
        candidates = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(candidates)} mapping candidates")
        return candidates
    
    def parse_player_name(self, full_name: str) -> Tuple[str, str]:
        """Parse full name into first and last name components."""
        if not full_name or pd.isna(full_name):
            return "", ""
        
        name_parts = full_name.strip().split()
        if len(name_parts) < 2:
            return name_parts[0] if name_parts else "", ""
        
        # Handle names like "Jose Altuve Jr."
        if name_parts[-1].lower() in ['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv']:
            last_name = name_parts[-2]
            first_name = ' '.join(name_parts[:-2])
        else:
            last_name = name_parts[-1]
            first_name = ' '.join(name_parts[:-1])
        
        return first_name.strip(), last_name.strip()
    
    def lookup_player_ids(self, player_name: str, team_code: str = None) -> Dict:
        """Lookup comprehensive player IDs using PyBaseball."""
        first_name, last_name = self.parse_player_name(player_name)
        
        if not first_name or not last_name:
            logger.warning(f"Could not parse name: {player_name}")
            return {}
        
        try:
            # Use PyBaseball's playerid_lookup
            results = self.pybaseball.lookup_player_ids(last_name, first_name)
            
            if not results:
                logger.warning(f"No PyBaseball results for: {first_name} {last_name}")
                return {}
            
            # Filter by team if provided (to handle common names)
            if team_code and len(results) > 1:
                team_filtered = [r for r in results if r.get('mlb_id') and 
                                str(r.get('mlb_id')).endswith(team_code)]
                if team_filtered:
                    results = team_filtered
            
            # Return the best match (first result if multiple)
            best_match = results[0]
            
            return {
                'mlb_player_id': str(best_match.get('mlb_id', '')),
                'fangraphs_id': str(best_match.get('fg_id', '')),
                'bbref_id': str(best_match.get('bbref_id', '')),
                'birth_year': best_match.get('birth_year'),
                'confidence_score': 0.8 if len(results) == 1 else 0.6,
                'mapping_method': 'pybaseball_lookup'
            }
            
        except Exception as e:
            logger.error(f"Error looking up {first_name} {last_name}: {e}")
            return {}
    
    def create_mapping_table(self):
        """Create or ensure player_id_mapping table exists with proper schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_id_mapping (
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
        
        # Create indexes for efficient lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_yahoo_player_id ON player_id_mapping(yahoo_player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mlb_player_id ON player_id_mapping(mlb_player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fangraphs_id ON player_id_mapping(fangraphs_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bbref_id ON player_id_mapping(bbref_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_standardized_name ON player_id_mapping(standardized_name)')
        
        conn.commit()
        conn.close()
        logger.info("Created/verified player_id_mapping table and indexes")
    
    def insert_mapping_record(self, mapping_data: Dict):
        """Insert a single mapping record into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if mapping already exists
        if mapping_data.get('yahoo_player_id'):
            cursor.execute(
                'SELECT mapping_id FROM player_id_mapping WHERE yahoo_player_id = ?',
                (mapping_data['yahoo_player_id'],)
            )
            if cursor.fetchone():
                conn.close()
                return  # Skip if already exists
        
        cursor.execute('''
            INSERT INTO player_id_mapping (
                yahoo_player_id, yahoo_player_name, mlb_player_id, 
                fangraphs_id, bbref_id, standardized_name, team_code, 
                position_codes, birth_year, confidence_score, mapping_method,
                validation_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            mapping_data.get('yahoo_player_id'),
            mapping_data.get('yahoo_player_name'),
            mapping_data.get('mlb_player_id'),
            mapping_data.get('fangraphs_id', ''),
            mapping_data.get('bbref_id', ''),
            mapping_data.get('standardized_name'),
            mapping_data.get('team_code'),
            mapping_data.get('position_codes'),
            mapping_data.get('birth_year'),
            mapping_data.get('confidence_score', 0.0),
            mapping_data.get('mapping_method', 'pending'),
            'pending' if mapping_data.get('needs_validation') else 'validated',
            datetime.now(),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def populate_mappings(self):
        """Populate player mappings from analysis results and PyBaseball lookups."""
        logger.info("Starting player mapping population process")
        
        # Ensure table exists
        self.create_mapping_table()
        
        # Load candidates
        candidates = self.load_mapping_candidates()
        
        # Process each candidate type
        processed = 0
        skipped = 0
        errors = 0
        
        for _, candidate in candidates.iterrows():
            try:
                mapping_data = {
                    'yahoo_player_id': candidate.get('yahoo_player_id'),
                    'yahoo_player_name': candidate.get('yahoo_player_name'),
                    'mlb_player_id': candidate.get('mlb_player_id'),
                    'standardized_name': candidate.get('standardized_name'),
                    'team_code': candidate.get('team_code'),
                    'position_codes': candidate.get('position_codes'),
                    'confidence_score': candidate.get('confidence_score', 0.0),
                    'mapping_method': candidate.get('mapping_method'),
                    'needs_validation': candidate.get('needs_validation', True)
                }
                
                # For players needing PyBaseball lookup
                if candidate.get('mapping_method') == 'needs_pybaseball_lookup':
                    logger.info(f"Looking up PyBaseball data for: {candidate.get('yahoo_player_name')}")
                    
                    pybaseball_data = self.lookup_player_ids(
                        candidate.get('yahoo_player_name'),
                        candidate.get('team_code')
                    )
                    
                    if pybaseball_data:
                        mapping_data.update(pybaseball_data)
                        mapping_data['needs_validation'] = False
                        logger.info(f"Found PyBaseball data for: {candidate.get('yahoo_player_name')}")
                    else:
                        logger.warning(f"No PyBaseball data found for: {candidate.get('yahoo_player_name')}")
                    
                    # Rate limiting
                    time.sleep(1)
                
                # For exact matches, add FanGraphs/Baseball Reference IDs
                elif candidate.get('mapping_method') == 'exact_name_match':
                    if candidate.get('yahoo_player_name'):
                        logger.info(f"Enhancing exact match with external IDs: {candidate.get('yahoo_player_name')}")
                        
                        pybaseball_data = self.lookup_player_ids(
                            candidate.get('yahoo_player_name'),
                            candidate.get('team_code')
                        )
                        
                        if pybaseball_data:
                            mapping_data['fangraphs_id'] = pybaseball_data.get('fangraphs_id', '')
                            mapping_data['bbref_id'] = pybaseball_data.get('bbref_id', '')
                            mapping_data['birth_year'] = pybaseball_data.get('birth_year')
                        
                        # Rate limiting
                        time.sleep(1)
                
                # Insert the mapping
                self.insert_mapping_record(mapping_data)
                processed += 1
                
                if processed % 50 == 0:
                    logger.info(f"Processed {processed} mappings...")
                
            except Exception as e:
                logger.error(f"Error processing candidate {candidate.get('yahoo_player_name', 'Unknown')}: {e}")
                errors += 1
                continue
        
        logger.info(f"Mapping population complete: {processed} processed, {errors} errors")
        
        # Log final statistics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM player_id_mapping')
        total_mappings = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM player_id_mapping WHERE fangraphs_id IS NOT NULL AND fangraphs_id != ""')
        fangraphs_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM player_id_mapping WHERE bbref_id IS NOT NULL AND bbref_id != ""')
        bbref_count = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"Final mapping statistics:")
        logger.info(f"  Total mappings: {total_mappings}")
        logger.info(f"  With FanGraphs ID: {fangraphs_count}")
        logger.info(f"  With Baseball Reference ID: {bbref_count}")


def main():
    """Run the player mapping population process."""
    populator = PlayerMappingPopulator()
    populator.populate_mappings()


if __name__ == "__main__":
    main()