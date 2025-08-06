#!/usr/bin/env python3
"""
Yahoo Player Search Module

Searches Yahoo Fantasy API for player IDs to backfill missing mappings.
Uses the Yahoo API to find all available players and match them to MLB IDs.
"""

import sys
import sqlite3
import logging
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.token_manager import YahooTokenManager
from data_pipeline.player_stats.config import get_config_for_environment
from data_pipeline.player_stats.yahoo_id_matcher import YahooIDMatcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YahooPlayerSearch:
    """Search Yahoo Fantasy API for player IDs"""
    
    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    def __init__(self, environment='test', use_d1=False):
        self.environment = environment
        self.use_d1 = use_d1
        self.config = get_config_for_environment(environment)
        
        # Database connection
        if use_d1:
            from data_pipeline.common.d1_connection import D1Connection
            self.d1_conn = D1Connection()
            self.conn = None
            logger.info("Using Cloudflare D1 database")
        else:
            self.conn = sqlite3.connect(self.config['database_path'])
            self.d1_conn = None
            logger.info(f"Using SQLite database: {self.config['database_path']}")
        
        # Initialize token manager for Yahoo API
        self.token_manager = YahooTokenManager()
        
        # Yahoo league key for 2025
        self.league_key = "458.l.6966"
        
        # Rate limiting
        self.requests_made = 0
        self.last_request_time = None
        self.max_requests_per_second = 1
        
        logger.info(f"Initialized YahooPlayerSearch for {environment}")
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute query on appropriate database"""
        if self.use_d1:
            result = self.d1_conn.execute(query, params)
            return result.fetchall()
        else:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def _commit(self):
        """Commit transaction"""
        if not self.use_d1:  # D1 auto-commits
            self.conn.commit()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Yahoo API"""
        # Rate limiting
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < (1.0 / self.max_requests_per_second):
                time.sleep((1.0 / self.max_requests_per_second) - elapsed)
        
        # Get current access token
        access_token = self.token_manager.get_access_token()
        if not access_token:
            logger.error("Failed to get valid access token")
            return None
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params or {})
            response.raise_for_status()
            
            self.requests_made += 1
            self.last_request_time = time.time()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Yahoo API request failed: {e}")
            return None
    
    def search_player_by_name(self, player_name: str) -> Optional[Dict]:
        """
        Search for a player by name in Yahoo Fantasy.
        
        Args:
            player_name: Player's full name
            
        Returns:
            Player data from Yahoo or None if not found
        """
        # Yahoo player search endpoint
        endpoint = f"league/{self.league_key}/players;search={player_name}"
        
        response = self._make_request(endpoint, {'format': 'json'})
        
        if not response:
            return None
        
        try:
            # Navigate Yahoo's nested JSON structure
            players_data = response.get('fantasy_content', {}).get('league', [{}])[1].get('players', {})
            
            if not players_data or players_data.get('count', 0) == 0:
                return None
            
            # Get first matching player
            for key, value in players_data.items():
                if key.startswith('0') and 'player' in value:
                    player = value['player'][0]
                    return {
                        'yahoo_player_id': int(player[1]['player_id']),
                        'name': player[2]['name']['full'],
                        'team': player[6].get('editorial_team_abbr'),
                        'positions': [p['position'] for p in player[9].get('eligible_positions', [])]
                    }
            
            return None
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing Yahoo response for {player_name}: {e}")
            return None
    
    def get_all_available_players(self, position: str = None, start: int = 0, count: int = 25) -> List[Dict]:
        """
        Get all available players from Yahoo league.
        
        Args:
            position: Filter by position (optional)
            start: Starting index for pagination
            count: Number of players to fetch (max 25)
            
        Returns:
            List of player data
        """
        # Build endpoint
        endpoint = f"league/{self.league_key}/players"
        
        params = {
            'format': 'json',
            'start': start,
            'count': min(count, 25)  # Yahoo limits to 25 per request
        }
        
        if position:
            endpoint += f";position={position}"
        
        response = self._make_request(endpoint, params)
        
        if not response:
            return []
        
        try:
            players_data = response.get('fantasy_content', {}).get('league', [{}])[1].get('players', {})
            
            if not players_data:
                return []
            
            players = []
            for key, value in players_data.items():
                if key != 'count' and 'player' in value:
                    player_info = value['player'][0]
                    players.append({
                        'yahoo_player_id': int(player_info[1]['player_id']),
                        'name': player_info[2]['name']['full'],
                        'team': player_info[6].get('editorial_team_abbr'),
                        'positions': [p['position'] for p in player_info[9].get('eligible_positions', [])]
                    })
            
            return players
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing Yahoo players response: {e}")
            return []
    
    def fetch_all_mlb_players(self, max_players: int = 2000) -> List[Dict]:
        """
        Fetch all MLB players from Yahoo Fantasy.
        
        Args:
            max_players: Maximum number of players to fetch
            
        Returns:
            List of all Yahoo MLB players
        """
        logger.info(f"Fetching all MLB players from Yahoo (expecting ~1,828, max: {max_players})...")
        
        all_players = []
        positions = ['C', '1B', '2B', '3B', 'SS', 'OF', 'Util', 'SP', 'RP', 'P']
        
        for position in positions:
            logger.info(f"Fetching {position} players...")
            start = 0
            
            while start < max_players:
                players = self.get_all_available_players(position=position, start=start, count=25)
                
                if not players:
                    break
                
                # Deduplicate by Yahoo ID
                for player in players:
                    if not any(p['yahoo_player_id'] == player['yahoo_player_id'] for p in all_players):
                        all_players.append(player)
                
                logger.debug(f"  Fetched {len(players)} {position} players (total: {len(all_players)})")
                start += 25
                
                # Rate limiting
                time.sleep(0.5)
        
        logger.info(f"Fetched {len(all_players)} unique MLB players from Yahoo")
        return all_players
    
    def backfill_missing_yahoo_ids(self) -> Dict[str, int]:
        """
        Search Yahoo API for all MLB players missing Yahoo IDs.
        
        Returns:
            Statistics about the backfill process
        """
        cursor = self.conn.cursor()
        
        # Get players missing Yahoo IDs
        cursor.execute("""
            SELECT mlb_id, player_name, team_code
            FROM player_mapping
            WHERE yahoo_player_id IS NULL
            AND active = 1
            ORDER BY player_name
        """)
        
        missing_players = cursor.fetchall()
        logger.info(f"Found {len(missing_players)} active players missing Yahoo IDs")
        
        # Search for each player
        found = 0
        not_found = []
        
        for mlb_id, player_name, team in missing_players[:50]:  # Limit to 50 for testing
            logger.debug(f"Searching for {player_name}...")
            
            yahoo_player = self.search_player_by_name(player_name)
            
            if yahoo_player:
                # Update player mapping
                self._execute_query("""
                    UPDATE player_mapping
                    SET yahoo_player_id = ?
                    WHERE mlb_id = ?
                """, (yahoo_player['yahoo_player_id'], mlb_id))
                
                found += 1
                logger.info(f"Found: {player_name} -> Yahoo ID {yahoo_player['yahoo_player_id']}")
            else:
                not_found.append(player_name)
                logger.debug(f"Not found: {player_name}")
            
            # Rate limiting
            time.sleep(0.5)
        
        self._commit()
        
        # Show results
        logger.info(f"\nBackfill Results:")
        logger.info(f"  Searched: {min(50, len(missing_players))} players")
        logger.info(f"  Found: {found} players")
        logger.info(f"  Not found: {len(not_found)} players")
        
        if not_found:
            logger.info("\nPlayers not found in Yahoo:")
            for name in not_found[:10]:
                logger.info(f"  - {name}")
        
        return {
            'searched': min(50, len(missing_players)),
            'found': found,
            'not_found': len(not_found),
            'remaining': max(0, len(missing_players) - 50)
        }
    
    def bulk_import_yahoo_players(self) -> int:
        """
        Import all Yahoo players and match to MLB IDs.
        
        Returns:
            Number of new Yahoo IDs added
        """
        # Fetch all Yahoo players
        yahoo_players = self.fetch_all_mlb_players(max_players=1000)
        
        if not yahoo_players:
            logger.error("No players fetched from Yahoo")
            return 0
        
        # Initialize matcher
        matcher = YahooIDMatcher(environment=self.environment)
        
        # Match Yahoo players to MLB IDs
        matched = 0
        
        for yahoo_player in yahoo_players:
            # Try to find MLB player by name
            results = self._execute_query("""
                SELECT mlb_id
                FROM player_mapping
                WHERE player_name = ?
                AND yahoo_player_id IS NULL
                LIMIT 1
            """, (yahoo_player['name'],))
            
            if results:
                mlb_id = results[0][0]
                self._execute_query("""
                    UPDATE player_mapping
                    SET yahoo_player_id = ?
                    WHERE mlb_id = ?
                """, (yahoo_player['yahoo_player_id'], mlb_id))
                matched += 1
            else:
                # Try fuzzy matching
                cursor.execute("""
                    SELECT mlb_id, player_name
                    FROM player_mapping
                    WHERE yahoo_player_id IS NULL
                    AND active = 1
                """)
                
                best_match = None
                best_score = 0
                
                for mlb_id, mlb_name in cursor.fetchall():
                    score = matcher.fuzzy_match_name(yahoo_player['name'], mlb_name)
                    if score > best_score and score >= 0.85:
                        best_score = score
                        best_match = mlb_id
                
                if best_match:
                    cursor.execute("""
                        UPDATE player_mapping
                        SET yahoo_player_id = ?
                        WHERE mlb_id = ?
                    """, (yahoo_player['yahoo_player_id'], best_match))
                    matched += 1
        
        self.conn.commit()
        
        logger.info(f"Matched {matched} Yahoo players to MLB IDs")
        return matched
    
    def show_coverage_stats(self):
        """Show Yahoo ID coverage statistics"""
        
        print("\n" + "="*80)
        print("YAHOO ID COVERAGE STATISTICS")
        print("="*80)
        
        # Overall stats
        stats_result = self._execute_query("""
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo,
                COUNT(CASE WHEN yahoo_player_id IS NULL THEN 1 END) as without_yahoo
            FROM player_mapping
            WHERE active = 1
        """)
        
        stats = stats_result[0] if stats_result else (0, 0, 0)
        coverage_pct = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
        
        print(f"\nActive MLB Players:")
        print(f"  Total: {stats[0]}")
        print(f"  With Yahoo ID: {stats[1]} ({coverage_pct:.1f}%)")
        print(f"  Missing Yahoo ID: {stats[2]}")
        
        # Sample missing players
        missing = self._execute_query("""
            SELECT player_name, team_code
            FROM player_mapping
            WHERE yahoo_player_id IS NULL
            AND active = 1
            ORDER BY player_name
            LIMIT 10
        """)
        if missing:
            print(f"\nSample Players Missing Yahoo ID:")
            for name, team in missing:
                team_str = f"({team})" if team else ""
                print(f"  - {name} {team_str}")
        
        print(f"\nAPI Requests Made: {self.requests_made}")


def main():
    """Main function for testing Yahoo player search"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Search Yahoo Fantasy for player IDs')
    parser.add_argument('--action', choices=['search', 'backfill', 'bulk', 'stats'],
                       default='stats', help='Action to perform')
    parser.add_argument('--name', help='Player name to search for')
    parser.add_argument('--environment', default='test', choices=['test', 'production'])
    
    args = parser.parse_args()
    
    searcher = YahooPlayerSearch(environment=args.environment)
    
    if args.action == 'search':
        if not args.name:
            print("ERROR: --name required for search")
            return
        
        print(f"Searching Yahoo for: {args.name}")
        result = searcher.search_player_by_name(args.name)
        
        if result:
            print(f"\nFound player:")
            print(f"  Yahoo ID: {result['yahoo_player_id']}")
            print(f"  Name: {result['name']}")
            print(f"  Team: {result['team']}")
            print(f"  Positions: {', '.join(result['positions'])}")
        else:
            print(f"Player not found: {args.name}")
    
    elif args.action == 'backfill':
        print("Starting Yahoo ID backfill...")
        stats = searcher.backfill_missing_yahoo_ids()
        print(f"\nBackfill complete:")
        print(f"  Found: {stats['found']} players")
        print(f"  Not found: {stats['not_found']} players")
        print(f"  Remaining: {stats['remaining']} players")
    
    elif args.action == 'bulk':
        print("Starting bulk Yahoo player import...")
        matched = searcher.bulk_import_yahoo_players()
        print(f"\nBulk import complete: {matched} players matched")
    
    searcher.show_coverage_stats()


if __name__ == '__main__':
    main()