#!/usr/bin/env python3
"""
Yahoo Player ID Matcher

Maps Yahoo Fantasy player IDs to MLB player IDs using fuzzy matching
and data from existing transactions and lineups.
"""

import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import re

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YahooIDMatcher:
    """Matches Yahoo player IDs to MLB IDs using fuzzy matching"""
    
    def __init__(self, environment='test'):
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.conn = sqlite3.connect(self.config['database_path'])
        
        # Also connect to production database for Yahoo data
        prod_config = get_config_for_environment('production')
        self.prod_conn = sqlite3.connect(prod_config['database_path'])
        
        # Cache for Yahoo players
        self.yahoo_players = None
        
        logger.info(f"Initialized YahooIDMatcher for {environment}")
    
    def build_yahoo_player_registry(self) -> List[Dict]:
        """
        Extract all Yahoo players from transactions and lineups.
        
        Returns:
            List of Yahoo player records with IDs and names
        """
        logger.info("Building Yahoo player registry from existing data...")
        
        # Use production database for Yahoo data since that's where transactions/lineups are
        cursor = self.prod_conn.cursor()
        
        # Get unique players from transactions
        cursor.execute("""
            SELECT DISTINCT 
                t.player_id,
                t.player_name,
                t.player_team,
                NULL as player_positions,
                COUNT(*) as transaction_count
            FROM transactions t
            WHERE t.player_id IS NOT NULL
            GROUP BY t.player_id, t.player_name
        """)
        
        transaction_players = {}
        for row in cursor.fetchall():
            player_id = row[0]
            # player_id is already the Yahoo ID (e.g., "12345")
            yahoo_id = None
            if player_id:
                try:
                    yahoo_id = int(player_id)
                except (ValueError, TypeError):
                    # Try extracting from key format if needed
                    if '.p.' in str(player_id):
                        yahoo_id = int(str(player_id).split('.p.')[-1])
            
            if yahoo_id:
                transaction_players[yahoo_id] = {
                    'yahoo_player_id': yahoo_id,
                    'player_name': row[1],
                    'team': row[2],
                    'positions': row[3],
                    'transaction_count': row[4]
                }
        
        logger.info(f"Found {len(transaction_players)} unique players from transactions")
        
        # Get unique players from lineups
        lineup_rows = self._execute_query("""
            SELECT DISTINCT
                dl.player_id,
                dl.player_name,
                NULL as player_team,
                NULL as eligible_positions,
                COUNT(*) as lineup_count
            FROM daily_lineups dl
            WHERE dl.player_id IS NOT NULL
            GROUP BY dl.player_id, dl.player_name
        """, use_prod=True)
        
        lineup_players = {}
        for row in lineup_rows:
            player_id = row[0]
            # player_id is already the Yahoo ID
            yahoo_id = None
            if player_id:
                try:
                    yahoo_id = int(player_id)
                except (ValueError, TypeError):
                    # Try extracting from key format if needed
                    if '.p.' in str(player_id):
                        yahoo_id = int(str(player_id).split('.p.')[-1])
            
            if yahoo_id:
                lineup_players[yahoo_id] = {
                    'yahoo_player_id': yahoo_id,
                    'player_name': row[1],
                    'team': row[2],
                    'positions': row[3],
                    'lineup_count': row[4]
                }
        
        logger.info(f"Found {len(lineup_players)} unique players from lineups")
        
        # Merge the two sources
        all_yahoo_players = {}
        
        # Add all transaction players
        for yahoo_id, player in transaction_players.items():
            all_yahoo_players[yahoo_id] = player
            all_yahoo_players[yahoo_id]['lineup_count'] = 0
        
        # Merge lineup players
        for yahoo_id, player in lineup_players.items():
            if yahoo_id in all_yahoo_players:
                # Update with lineup count
                all_yahoo_players[yahoo_id]['lineup_count'] = player['lineup_count']
                # Use most recent name if different
                if player['player_name'] != all_yahoo_players[yahoo_id]['player_name']:
                    logger.debug(f"Name mismatch for {yahoo_id}: {all_yahoo_players[yahoo_id]['player_name']} vs {player['player_name']}")
            else:
                all_yahoo_players[yahoo_id] = player
                all_yahoo_players[yahoo_id]['transaction_count'] = 0
        
        # Convert to list and sort by usage frequency
        yahoo_players = list(all_yahoo_players.values())
        yahoo_players.sort(key=lambda x: x.get('transaction_count', 0) + x.get('lineup_count', 0), reverse=True)
        
        logger.info(f"Total unique Yahoo players: {len(yahoo_players)}")
        
        # Cache for later use
        self.yahoo_players = yahoo_players
        
        return yahoo_players
    
    def normalize_name(self, name: str) -> str:
        """Normalize player name for matching"""
        # Remove common suffixes
        name = re.sub(r'\s+(Jr\.|Sr\.|III|II|IV)$', '', name, flags=re.IGNORECASE)
        # Remove periods
        name = name.replace('.', '')
        # Convert to lowercase
        name = name.lower()
        # Remove extra spaces
        name = ' '.join(name.split())
        return name
    
    def fuzzy_match_name(self, name1: str, name2: str) -> float:
        """
        Calculate fuzzy match score between two names.
        
        Returns:
            Score between 0 and 1 (1 = perfect match)
        """
        # First check if one name has Jr. and the other doesn't
        # This is a common case where MLB drops Jr. but Yahoo keeps it
        name1_has_jr = bool(re.search(r'\s+(Jr\.?|Sr\.?|III|II|IV)$', name1, flags=re.IGNORECASE))
        name2_has_jr = bool(re.search(r'\s+(Jr\.?|Sr\.?|III|II|IV)$', name2, flags=re.IGNORECASE))
        
        # If suffix status differs, normalize both for comparison
        if name1_has_jr != name2_has_jr:
            # Remove suffixes from both for comparison
            norm1 = self.normalize_name(name1)
            norm2 = self.normalize_name(name2)
            
            # If they match after removing suffixes, it's a perfect match
            if norm1 == norm2:
                return 1.0
        
        # Standard normalization and matching
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Use SequenceMatcher for fuzzy matching
        score = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost score if last names match
        parts1 = norm1.split()
        parts2 = norm2.split()
        if parts1 and parts2 and parts1[-1] == parts2[-1]:
            score = min(1.0, score * 1.2)
        
        return score
    
    def match_yahoo_to_mlb(self, threshold: float = 0.85) -> Dict[int, int]:
        """
        Match Yahoo player IDs to MLB IDs.
        
        Args:
            threshold: Minimum match score to accept (0-1)
            
        Returns:
            Dictionary mapping Yahoo ID to MLB ID
        """
        if self.yahoo_players is None:
            self.build_yahoo_player_registry()
        
        logger.info(f"Matching Yahoo players to MLB IDs (threshold: {threshold})...")
        
        cursor = self.conn.cursor()
        
        # Get all MLB players from mapping table
        cursor.execute("""
            SELECT mlb_id, player_name, first_name, last_name, team_code
            FROM player_mapping
            WHERE active = 1
        """)
        
        mlb_players = []
        for row in cursor.fetchall():
            mlb_players.append({
                'mlb_id': row[0],
                'full_name': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'team': row[4]
            })
        
        # Match each Yahoo player
        matches = {}
        unmatched = []
        
        for yahoo_player in self.yahoo_players:
            yahoo_id = yahoo_player['yahoo_player_id']
            yahoo_name = yahoo_player['player_name']
            yahoo_team = yahoo_player.get('team', '')
            
            best_match = None
            best_score = 0
            
            for mlb_player in mlb_players:
                # Calculate name match score
                score = self.fuzzy_match_name(yahoo_name, mlb_player['full_name'])
                
                # Boost score if teams match
                if yahoo_team and mlb_player['team'] and yahoo_team == mlb_player['team']:
                    score = min(1.0, score * 1.1)
                
                if score > best_score:
                    best_score = score
                    best_match = mlb_player
            
            if best_score >= threshold and best_match:
                matches[yahoo_id] = best_match['mlb_id']
                logger.debug(f"Matched: {yahoo_name} -> {best_match['full_name']} (score: {best_score:.3f})")
            else:
                unmatched.append({
                    'yahoo_id': yahoo_id,
                    'name': yahoo_name,
                    'best_score': best_score,
                    'best_match': best_match['full_name'] if best_match else None
                })
        
        logger.info(f"Matched {len(matches)} Yahoo players to MLB IDs")
        logger.info(f"Unmatched: {len(unmatched)} players")
        
        # Show some unmatched examples
        if unmatched:
            logger.info("Sample unmatched players:")
            for player in unmatched[:5]:
                logger.info(f"  - {player['name']} (best: {player['best_match']} @ {player['best_score']:.3f})")
        
        return matches
    
    def update_player_mappings(self, matches: Dict[int, int]) -> int:
        """
        Update player_mapping table with Yahoo IDs.
        
        Args:
            matches: Dictionary mapping Yahoo ID to MLB ID
            
        Returns:
            Number of records updated
        """
        logger.info(f"Updating player mappings with {len(matches)} Yahoo IDs...")
        
        updated = 0
        
        for yahoo_id, mlb_id in matches.items():
            result = self._execute_query("""
                UPDATE player_mapping
                SET yahoo_player_id = ?
                WHERE mlb_id = ?
            """, (yahoo_id, mlb_id))
            
            if not self.use_d1:  # SQLite has rowcount
                updated += 1 if result.rowcount > 0 else 0
            else:  # D1 doesn't support rowcount, assume success
                updated += 1
        
        self._commit()
        logger.info(f"Updated {updated} player mappings with Yahoo IDs")
        
        return updated
    
    def show_matching_stats(self):
        """Show statistics about the Yahoo ID matching"""
        cursor = self.conn.cursor()
        
        print("\n" + "="*80)
        print("YAHOO ID MATCHING STATISTICS")
        print("="*80)
        
        # Overall mapping stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_players,
                COUNT(yahoo_player_id) as yahoo_mapped,
                COUNT(baseball_reference_id) as bbref_mapped,
                COUNT(fangraphs_id) as fg_mapped
            FROM player_mapping
            WHERE active = 1
        """)
        
        stats = cursor.fetchone()
        print(f"\nActive Player Mappings:")
        print(f"  Total players: {stats[0]}")
        print(f"  Yahoo ID mapped: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"  Baseball Reference mapped: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
        print(f"  FanGraphs mapped: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
        
        # Sample mapped players
        cursor.execute("""
            SELECT player_name, yahoo_player_id, mlb_id
            FROM player_mapping
            WHERE yahoo_player_id IS NOT NULL
            ORDER BY player_name
            LIMIT 10
        """)
        
        print(f"\nSample Mapped Players:")
        print(f"{'Player':<30} {'Yahoo ID':<10} {'MLB ID':<10}")
        print("-" * 50)
        for row in cursor.fetchall():
            print(f"{row[0]:<30} {row[1]:<10} {row[2]:<10}")
        
        # Check stats table mappings
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT mlb_id) as total,
                COUNT(DISTINCT CASE WHEN yahoo_player_id IS NOT NULL THEN mlb_id END) as yahoo_mapped
            FROM daily_gkl_player_stats
            WHERE date = (SELECT MAX(date) FROM daily_gkl_player_stats)
        """)
        
        stats_mapping = cursor.fetchone()
        if stats_mapping and stats_mapping[0] > 0:
            print(f"\nStats Table Mapping (Latest Date):")
            print(f"  Players with stats: {stats_mapping[0]}")
            print(f"  Yahoo ID mapped: {stats_mapping[1]} ({stats_mapping[1]/stats_mapping[0]*100:.1f}%)")


def main():
    """Main function for testing Yahoo ID matching"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Match Yahoo player IDs to MLB IDs')
    parser.add_argument('--environment', default='test', choices=['test', 'production'])
    parser.add_argument('--threshold', type=float, default=0.85, 
                       help='Matching threshold (0-1, default 0.85)')
    parser.add_argument('--update', action='store_true',
                       help='Update player mappings with matches')
    
    args = parser.parse_args()
    
    matcher = YahooIDMatcher(environment=args.environment)
    
    # Build Yahoo player registry
    yahoo_players = matcher.build_yahoo_player_registry()
    print(f"Found {len(yahoo_players)} Yahoo players")
    
    # Match to MLB IDs
    matches = matcher.match_yahoo_to_mlb(threshold=args.threshold)
    print(f"Matched {len(matches)} players")
    
    # Update mappings if requested
    if args.update:
        updated = matcher.update_player_mappings(matches)
        print(f"Updated {updated} player mappings")
    
    # Show statistics
    matcher.show_matching_stats()


if __name__ == '__main__':
    main()