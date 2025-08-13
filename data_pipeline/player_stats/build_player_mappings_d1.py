#!/usr/bin/env python3
"""
Build Comprehensive Player Mappings in D1

This script builds and maintains comprehensive player mappings directly in D1.
It combines data from multiple sources:
1. PyBaseball's Chadwick Registry (all MLB players)
2. Yahoo Fantasy league data (for Yahoo player IDs)
3. Fuzzy matching to connect the two

Unlike sync scripts, this NEVER deletes existing data. It only:
- Adds new players (INSERT OR IGNORE)
- Updates missing Yahoo IDs when found
- Preserves all manually added mappings

Usage:
    python build_player_mappings_d1.py --use-d1
    python build_player_mappings_d1.py --environment production --use-d1
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
import sqlite3

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

try:
    import pybaseball
except ImportError:
    print("PyBaseball not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pybaseball"])
    import pybaseball

from fuzzywuzzy import fuzz
from data_pipeline.common.d1_connection import D1Connection
from data_pipeline.player_stats.yahoo_id_matcher import YahooIDMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerMappingBuilder:
    """Builds comprehensive player mappings directly in D1"""
    
    def __init__(self, environment='production', use_d1=True):
        """
        Initialize the builder.
        
        Args:
            environment: Database environment
            use_d1: If True, write directly to D1
        """
        self.environment = environment
        self.use_d1 = use_d1
        
        if use_d1:
            self.d1_conn = D1Connection()
            logger.info("Using Cloudflare D1 database")
        else:
            raise ValueError("This script is designed for D1 only. Use --use-d1")
        
        # Initialize Yahoo matcher for getting Yahoo IDs
        self.yahoo_matcher = YahooIDMatcher(environment=environment)
        
    def ensure_table_exists(self):
        """Ensure player_mapping table exists in D1"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS player_mapping (
            player_mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mlb_id INTEGER,
            mlb_player_id INTEGER,
            yahoo_player_id TEXT,
            baseball_reference_id TEXT,
            fangraphs_id TEXT,
            player_name TEXT,
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
            self.d1_conn.execute(schema_sql)
            logger.info("Ensured player_mapping table exists")
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb ON player_mapping(mlb_id)",
                "CREATE INDEX IF NOT EXISTS idx_player_mapping_mlb_player ON player_mapping(mlb_player_id)",
                "CREATE INDEX IF NOT EXISTS idx_player_mapping_yahoo ON player_mapping(yahoo_player_id)",
                "CREATE INDEX IF NOT EXISTS idx_player_mapping_name ON player_mapping(player_name)"
            ]
            
            for index_sql in indexes:
                self.d1_conn.execute(index_sql)
                
        except Exception as e:
            logger.error(f"Error ensuring table exists: {e}")
            raise
    
    def get_existing_mlb_ids(self) -> Set[int]:
        """Get set of MLB IDs already in D1"""
        try:
            result = self.d1_conn.execute(
                "SELECT DISTINCT mlb_id FROM player_mapping WHERE mlb_id IS NOT NULL"
            )
            
            existing_ids = set()
            for row in result.get('results', []):
                if row and row[0]:
                    existing_ids.add(int(row[0]))
            
            logger.info(f"Found {len(existing_ids)} existing MLB IDs in D1")
            return existing_ids
            
        except Exception as e:
            logger.error(f"Error getting existing IDs: {e}")
            return set()
    
    def get_mlb_players_from_pybaseball(self) -> List[Dict]:
        """Get all MLB players from PyBaseball's Chadwick Registry"""
        logger.info("Fetching MLB players from PyBaseball...")
        
        try:
            # Get comprehensive player registry
            players = pybaseball.chadwick_register()
            
            # Filter to recent players (active since 2020)
            if 'mlb_played_last' in players.columns:
                recent_players = players[players['mlb_played_last'] >= 2020].copy()
            else:
                recent_players = players.copy()
            
            logger.info(f"Found {len(recent_players)} recent MLB players")
            
            # Convert to list of dicts
            player_list = []
            for _, player in recent_players.iterrows():
                player_dict = {
                    'mlb_id': player.get('key_mlbam'),
                    'baseball_reference_id': player.get('key_bbref'),
                    'fangraphs_id': player.get('key_fangraphs'),
                    'first_name': player.get('name_first', ''),
                    'last_name': player.get('name_last', ''),
                    'player_name': f"{player.get('name_first', '')} {player.get('name_last', '')}".strip(),
                    'active': 1 if player.get('mlb_played_last', 0) >= 2023 else 0
                }
                
                # Clean up None values
                for key in player_dict:
                    if player_dict[key] is None or (isinstance(player_dict[key], float) and pd.isna(player_dict[key])):
                        player_dict[key] = None
                
                player_list.append(player_dict)
            
            return player_list
            
        except Exception as e:
            logger.error(f"Error fetching MLB players: {e}")
            return []
    
    def get_yahoo_players_from_league(self) -> Dict[str, Dict]:
        """Get Yahoo players from league data"""
        logger.info("Building Yahoo player registry from league data...")
        
        try:
            # If using D1, get Yahoo players directly from D1
            if self.use_d1:
                return self.get_yahoo_players_from_d1()
            else:
                # Use the Yahoo matcher to build registry from local database
                self.yahoo_matcher.build_yahoo_player_registry()
                
                # Get the registry
                yahoo_players = {}
                for yahoo_id, player_info in self.yahoo_matcher.yahoo_registry.items():
                    yahoo_players[yahoo_id] = {
                        'yahoo_player_id': yahoo_id,
                        'player_name': player_info['name'],
                        'team': player_info.get('team'),
                        'positions': player_info.get('positions', [])
                    }
                
                logger.info(f"Found {len(yahoo_players)} Yahoo players from league data")
                return yahoo_players
            
        except Exception as e:
            logger.warning(f"Could not get Yahoo players from league: {e}")
            logger.info("Continuing without Yahoo player matching")
            return {}
    
    def get_yahoo_players_from_d1(self) -> Dict[str, Dict]:
        """Get Yahoo players directly from D1 transactions and lineups"""
        yahoo_players = {}
        
        try:
            # Get unique Yahoo players from transactions
            result = self.d1_conn.execute("""
                SELECT DISTINCT yahoo_player_id, player_name, player_team
                FROM transactions
                WHERE yahoo_player_id IS NOT NULL AND yahoo_player_id != ''
                UNION
                SELECT DISTINCT yahoo_player_id, player_name, player_team
                FROM daily_lineups
                WHERE yahoo_player_id IS NOT NULL AND yahoo_player_id != ''
            """)
            
            for row in result.get('results', []):
                if row and row[0]:
                    yahoo_players[row[0]] = {
                        'yahoo_player_id': row[0],
                        'player_name': row[1] if row[1] else '',
                        'team': row[2] if len(row) > 2 else None
                    }
            
            logger.info(f"Found {len(yahoo_players)} Yahoo players from D1")
            
        except Exception as e:
            logger.warning(f"Could not get Yahoo players from D1: {e}")
            
        return yahoo_players
    
    def match_and_merge_players(self, mlb_players: List[Dict], 
                               yahoo_players: Dict[str, Dict]) -> List[Dict]:
        """Match MLB players with Yahoo IDs using fuzzy matching"""
        logger.info("Matching MLB players with Yahoo IDs...")
        
        matched_count = 0
        
        for mlb_player in mlb_players:
            mlb_name = mlb_player['player_name'].lower().strip()
            
            # Try exact match first
            for yahoo_id, yahoo_info in yahoo_players.items():
                yahoo_name = yahoo_info['player_name'].lower().strip()
                
                if mlb_name == yahoo_name:
                    mlb_player['yahoo_player_id'] = yahoo_id
                    matched_count += 1
                    break
            
            # If no exact match, try fuzzy matching
            if not mlb_player.get('yahoo_player_id'):
                best_match = None
                best_score = 0
                
                for yahoo_id, yahoo_info in yahoo_players.items():
                    yahoo_name = yahoo_info['player_name'].lower().strip()
                    score = fuzz.ratio(mlb_name, yahoo_name)
                    
                    if score > best_score and score >= 85:  # 85% threshold
                        best_score = score
                        best_match = yahoo_id
                
                if best_match:
                    mlb_player['yahoo_player_id'] = best_match
                    matched_count += 1
        
        logger.info(f"Matched {matched_count} MLB players with Yahoo IDs")
        return mlb_players
    
    def insert_new_players(self, players: List[Dict]) -> int:
        """Insert new players into D1 (skips existing)"""
        inserted = 0
        errors = 0
        
        for player in players:
            try:
                # Use both mlb_id and mlb_player_id for compatibility
                mlb_id_value = player.get('mlb_id')
                
                sql = """
                    INSERT OR IGNORE INTO player_mapping (
                        mlb_id, mlb_player_id, yahoo_player_id, 
                        baseball_reference_id, fangraphs_id,
                        player_name, first_name, last_name, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = [
                    mlb_id_value,  # mlb_id
                    mlb_id_value,  # mlb_player_id (same value for compatibility)
                    player.get('yahoo_player_id'),
                    player.get('baseball_reference_id'),
                    player.get('fangraphs_id'),
                    player.get('player_name'),
                    player.get('first_name'),
                    player.get('last_name'),
                    player.get('active', 1)
                ]
                
                result = self.d1_conn.execute(sql, values)
                if result.get('changes', 0) > 0:
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"Error inserting player {player.get('player_name')}: {e}")
                errors += 1
        
        logger.info(f"Inserted {inserted} new players, {errors} errors")
        return inserted
    
    def update_yahoo_ids(self, players: List[Dict]) -> int:
        """Update Yahoo IDs for existing players that don't have them"""
        updated = 0
        
        for player in players:
            if not player.get('yahoo_player_id') or not player.get('mlb_id'):
                continue
            
            try:
                # Update where Yahoo ID is missing
                sql = """
                    UPDATE player_mapping 
                    SET yahoo_player_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE (mlb_id = ? OR mlb_player_id = ?)
                    AND yahoo_player_id IS NULL
                """
                
                result = self.d1_conn.execute(sql, [
                    player['yahoo_player_id'],
                    player['mlb_id'],
                    player['mlb_id']
                ])
                
                if result.get('changes', 0) > 0:
                    updated += 1
                    
            except Exception as e:
                logger.error(f"Error updating Yahoo ID for {player.get('player_name')}: {e}")
        
        if updated > 0:
            logger.info(f"Updated {updated} players with Yahoo IDs")
        
        return updated
    
    def build_mappings(self):
        """Main method to build comprehensive player mappings"""
        logger.info("Starting comprehensive player mapping build...")
        
        # Ensure table exists
        self.ensure_table_exists()
        
        # Get existing MLB IDs to avoid duplicates
        existing_ids = self.get_existing_mlb_ids()
        
        # Get all MLB players from PyBaseball
        mlb_players = self.get_mlb_players_from_pybaseball()
        
        # Filter out players we already have
        new_players = [
            p for p in mlb_players 
            if p.get('mlb_id') and int(p['mlb_id']) not in existing_ids
        ]
        logger.info(f"Found {len(new_players)} new MLB players to add")
        
        # Get Yahoo players from league data
        yahoo_players = self.get_yahoo_players_from_league()
        
        # Match and merge
        matched_players = self.match_and_merge_players(mlb_players, yahoo_players)
        
        # Insert new players
        if new_players:
            self.insert_new_players(new_players)
        
        # Update Yahoo IDs for all players (including existing)
        self.update_yahoo_ids(matched_players)
        
        # Show final stats
        self.show_stats()
    
    def show_stats(self):
        """Show statistics about player mappings in D1"""
        try:
            # Total players
            result = self.d1_conn.execute("SELECT COUNT(*) FROM player_mapping")
            total = result['results'][0][0] if result.get('results') else 0
            
            # Players with Yahoo IDs
            result = self.d1_conn.execute(
                "SELECT COUNT(*) FROM player_mapping WHERE yahoo_player_id IS NOT NULL"
            )
            with_yahoo = result['results'][0][0] if result.get('results') else 0
            
            # Active players
            result = self.d1_conn.execute(
                "SELECT COUNT(*) FROM player_mapping WHERE active = 1"
            )
            active = result['results'][0][0] if result.get('results') else 0
            
            logger.info("\n" + "="*60)
            logger.info("PLAYER MAPPING STATISTICS")
            logger.info("="*60)
            logger.info(f"Total players: {total}")
            logger.info(f"Active players: {active}")
            logger.info(f"Players with Yahoo IDs: {with_yahoo} ({with_yahoo*100/total:.1f}%)" if total > 0 else "No players")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Build comprehensive player mappings directly in D1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'],
                       help='Database environment (default: production)')
    parser.add_argument('--use-d1', action='store_true', required=True,
                       help='Write directly to Cloudflare D1 (required)')
    
    args = parser.parse_args()
    
    try:
        import pandas as pd
        global pd
    except ImportError:
        logger.info("Installing pandas...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas"])
        import pandas as pd
        global pd
    
    # Initialize builder
    builder = PlayerMappingBuilder(
        environment=args.environment,
        use_d1=args.use_d1
    )
    
    # Build mappings
    builder.build_mappings()


if __name__ == '__main__':
    main()