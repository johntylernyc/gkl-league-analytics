#!/usr/bin/env python3
"""
Player ID Mapping System

Maps Yahoo Fantasy player IDs to MLB/pybaseball identifiers.
Critical component for linking fantasy roster data with MLB statistics.

Key Features:
- Fuzzy name matching for player identification
- Multiple ID source support (MLB, Fangraphs, Baseball Reference)
- Confidence scoring for mapping quality
- Manual override capabilities
- Validation and verification tracking
"""

import sys
import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.config import get_config_for_environment
from player_stats.pybaseball_integration import PyBaseballIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PlayerMapping:
    """Represents a player ID mapping with all associated data."""
    yahoo_player_id: str
    yahoo_player_name: str
    mlb_player_id: Optional[str] = None
    fangraphs_id: Optional[str] = None
    bbref_id: Optional[str] = None
    standardized_name: str = ""
    team_code: Optional[str] = None
    position_codes: Optional[str] = None
    birth_year: Optional[int] = None
    confidence_score: float = 0.0
    mapping_method: str = "pending"
    manual_override: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_active: bool = True
    last_validated: Optional[date] = None
    validation_status: str = "pending"
    notes: Optional[str] = None


class PlayerIdMapper:
    """
    Manages player ID mappings between Yahoo Fantasy and MLB data sources.
    
    Provides fuzzy matching, confidence scoring, and mapping validation
    to ensure accurate linkage between fantasy and real baseball data.
    """
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the player ID mapper.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.db_path = self.config['database_path']
        self.mapping_table = self.config['player_mapping_table']
        
        # Initialize pybaseball integration
        self.pybaseball = PyBaseballIntegration(environment)
        
        logger.info(f"Initialized PlayerIdMapper for {environment} environment")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Mapping table: {self.mapping_table}")
        
    def standardize_name(self, name: str) -> str:
        """
        Standardize a player name for matching purposes.
        
        Args:
            name: Raw player name
            
        Returns:
            Standardized name for consistent matching
        """
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove common suffixes
        suffixes = [' jr.', ' jr', ' sr.', ' sr', ' ii', ' iii', ' iv']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
                break
        
        # Remove periods and special characters
        name = re.sub(r'[^\w\s-]', '', name)
        
        # Normalize whitespace
        name = ' '.join(name.split())
        
        return name
    
    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two player names.
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity score from 0.0 to 1.0
        """
        std_name1 = self.standardize_name(name1)
        std_name2 = self.standardize_name(name2)
        
        if not std_name1 or not std_name2:
            return 0.0
        
        # Exact match
        if std_name1 == std_name2:
            return 1.0
        
        # Split into parts for flexible matching
        parts1 = std_name1.split()
        parts2 = std_name2.split()
        
        if not parts1 or not parts2:
            return 0.0
        
        # Check for common patterns
        # Last name + first initial match
        if len(parts1) >= 2 and len(parts2) >= 2:
            if (parts1[-1] == parts2[-1] and  # Same last name
                parts1[0][0] == parts2[0][0]):  # Same first initial
                return 0.8
        
        # Simple edit distance approach for similar names
        # This is a basic implementation - could be enhanced with Levenshtein distance
        common_chars = set(std_name1) & set(std_name2)
        total_chars = set(std_name1) | set(std_name2)
        
        if total_chars:
            char_similarity = len(common_chars) / len(total_chars)
            return char_similarity * 0.6  # Lower confidence for character-based matching
        
        return 0.0
    
    def get_existing_mapping(self, yahoo_player_id: str) -> Optional[PlayerMapping]:
        """
        Get existing mapping for a Yahoo player ID.
        
        Args:
            yahoo_player_id: Yahoo Fantasy player ID
            
        Returns:
            PlayerMapping if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT yahoo_player_id, yahoo_player_name, mlb_player_id, 
                       fangraphs_id, bbref_id, standardized_name, team_code,
                       position_codes, birth_year, confidence_score, mapping_method,
                       manual_override, verified_by, verified_at, is_active,
                       last_validated, validation_status, notes
                FROM {self.mapping_table}
                WHERE yahoo_player_id = ? AND is_active = TRUE
            """, (yahoo_player_id,))
            
            row = cursor.fetchone()
            if row:
                return PlayerMapping(
                    yahoo_player_id=row[0],
                    yahoo_player_name=row[1],
                    mlb_player_id=row[2],
                    fangraphs_id=row[3],
                    bbref_id=row[4],
                    standardized_name=row[5],
                    team_code=row[6],
                    position_codes=row[7],
                    birth_year=row[8],
                    confidence_score=row[9],
                    mapping_method=row[10],
                    manual_override=bool(row[11]),
                    verified_by=row[12],
                    verified_at=datetime.fromisoformat(row[13]) if row[13] else None,
                    is_active=bool(row[14]),
                    last_validated=date.fromisoformat(row[15]) if row[15] else None,
                    validation_status=row[16],
                    notes=row[17]
                )
            
            return None
            
        finally:
            conn.close()
    
    def save_mapping(self, mapping: PlayerMapping) -> bool:
        """
        Save or update a player mapping.
        
        Args:
            mapping: PlayerMapping to save
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if mapping already exists
            existing = self.get_existing_mapping(mapping.yahoo_player_id)
            
            if existing:
                # Update existing mapping
                cursor.execute(f"""
                    UPDATE {self.mapping_table}
                    SET yahoo_player_name = ?, mlb_player_id = ?, fangraphs_id = ?,
                        bbref_id = ?, standardized_name = ?, team_code = ?,
                        position_codes = ?, birth_year = ?, confidence_score = ?,
                        mapping_method = ?, manual_override = ?, verified_by = ?,
                        verified_at = ?, is_active = ?, last_validated = ?,
                        validation_status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE yahoo_player_id = ?
                """, (
                    mapping.yahoo_player_name, mapping.mlb_player_id, mapping.fangraphs_id,
                    mapping.bbref_id, mapping.standardized_name, mapping.team_code,
                    mapping.position_codes, mapping.birth_year, mapping.confidence_score,
                    mapping.mapping_method, mapping.manual_override, mapping.verified_by,
                    mapping.verified_at.isoformat() if mapping.verified_at else None,
                    mapping.is_active, mapping.last_validated.isoformat() if mapping.last_validated else None,
                    mapping.validation_status, mapping.notes, mapping.yahoo_player_id
                ))
                logger.info(f"Updated mapping for Yahoo player {mapping.yahoo_player_id}")
            else:
                # Insert new mapping
                cursor.execute(f"""
                    INSERT INTO {self.mapping_table} (
                        yahoo_player_id, yahoo_player_name, mlb_player_id, fangraphs_id,
                        bbref_id, standardized_name, team_code, position_codes, birth_year,
                        confidence_score, mapping_method, manual_override, verified_by,
                        verified_at, is_active, last_validated, validation_status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mapping.yahoo_player_id, mapping.yahoo_player_name, mapping.mlb_player_id,
                    mapping.fangraphs_id, mapping.bbref_id, mapping.standardized_name,
                    mapping.team_code, mapping.position_codes, mapping.birth_year,
                    mapping.confidence_score, mapping.mapping_method, mapping.manual_override,
                    mapping.verified_by, mapping.verified_at.isoformat() if mapping.verified_at else None,
                    mapping.is_active, mapping.last_validated.isoformat() if mapping.last_validated else None,
                    mapping.validation_status, mapping.notes
                ))
                logger.info(f"Created new mapping for Yahoo player {mapping.yahoo_player_id}")
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to save mapping for {mapping.yahoo_player_id}: {e}")
            return False
            
        finally:
            conn.close()
    
    def find_candidates_by_name(self, yahoo_name: str, team_code: str = None) -> List[Dict[str, Any]]:
        """
        Find potential MLB player candidates by name.
        
        Args:
            yahoo_name: Yahoo Fantasy player name
            team_code: Optional team code to narrow search
            
        Returns:
            List of candidate players with similarity scores
        """
        logger.debug(f"Looking up candidates for: {yahoo_name} (team: {team_code})")
        
        # Parse name into parts
        name_parts = yahoo_name.strip().split()
        if not name_parts:
            return []
        
        # Try different name combinations
        candidates = []
        
        if len(name_parts) >= 2:
            # Try first name + last name
            first_name = name_parts[0]
            last_name = name_parts[-1]  # Take the last part as last name
            
            try:
                players = self.pybaseball.lookup_player_ids(last_name, first_name)
                candidates.extend(players)
            except Exception as e:
                logger.warning(f"Error looking up {first_name} {last_name}: {e}")
        
        # If we have middle names/initials, try without them
        if len(name_parts) > 2:
            first_name = name_parts[0]
            last_name = name_parts[-1]
            
            try:
                players = self.pybaseball.lookup_player_ids(last_name, first_name)
                candidates.extend(players)
            except Exception as e:
                logger.warning(f"Error looking up {first_name} {last_name} (simplified): {e}")
        
        # Try last name only if first+last didn't work
        if not candidates and len(name_parts) >= 1:
            last_name = name_parts[-1]
            
            try:
                players = self.pybaseball.lookup_player_ids(last_name)
                candidates.extend(players)
            except Exception as e:
                logger.warning(f"Error looking up {last_name} (last name only): {e}")
        
        # Remove duplicates based on MLB ID
        seen_ids = set()
        unique_candidates = []
        for candidate in candidates:
            mlb_id = candidate.get('mlb_id')
            if mlb_id and mlb_id not in seen_ids:
                seen_ids.add(mlb_id)
                unique_candidates.append(candidate)
        
        logger.debug(f"Found {len(unique_candidates)} unique candidates for {yahoo_name}")
        return unique_candidates
    
    def create_automatic_mapping(self, yahoo_player_id: str, yahoo_name: str, 
                                team_code: str = None) -> Optional[PlayerMapping]:
        """
        Attempt to create an automatic mapping for a Yahoo player.
        
        Args:
            yahoo_player_id: Yahoo Fantasy player ID
            yahoo_name: Yahoo Fantasy player name
            team_code: Optional team code
            
        Returns:
            PlayerMapping if successful, None otherwise
        """
        logger.info(f"Attempting automatic mapping for {yahoo_name} ({yahoo_player_id})")
        
        # Check if mapping already exists
        existing = self.get_existing_mapping(yahoo_player_id)
        if existing:
            logger.info(f"Mapping already exists for {yahoo_player_id}")
            return existing
        
        # Find candidates using name matching
        candidates = self.find_candidates_by_name(yahoo_name, team_code)
        
        if not candidates:
            logger.warning(f"No candidates found for {yahoo_name}")
            # Create a pending mapping for manual review
            mapping = PlayerMapping(
                yahoo_player_id=yahoo_player_id,
                yahoo_player_name=yahoo_name,
                standardized_name=self.standardize_name(yahoo_name),
                team_code=team_code,
                confidence_score=0.0,
                mapping_method="manual",  # Changed from "pending" to "manual"
                validation_status="needs_review",
                notes=f"No automatic matches found for '{yahoo_name}'"
            )
            
            if self.save_mapping(mapping):
                return mapping
            return None
        
        # Evaluate candidates and pick the best match
        best_candidate = None
        best_score = 0.0
        
        for candidate in candidates:
            similarity = self.calculate_name_similarity(yahoo_name, candidate.get('name', ''))
            
            # Boost score if team matches
            if team_code and candidate.get('team') == team_code:
                similarity += 0.1
            
            if similarity > best_score:
                best_score = similarity
                best_candidate = candidate
        
        if best_candidate and best_score >= 0.7:  # High confidence threshold
            mapping = PlayerMapping(
                yahoo_player_id=yahoo_player_id,
                yahoo_player_name=yahoo_name,
                mlb_player_id=best_candidate.get('mlb_id'),
                fangraphs_id=best_candidate.get('fangraphs_id'),
                bbref_id=best_candidate.get('bbref_id'),
                standardized_name=self.standardize_name(yahoo_name),
                team_code=team_code or best_candidate.get('team'),
                position_codes=best_candidate.get('positions'),
                birth_year=best_candidate.get('birth_year'),
                confidence_score=best_score,
                mapping_method="exact" if best_score >= 0.95 else "fuzzy",
                validation_status="valid" if best_score >= 0.9 else "needs_review",
                notes=f"Auto-matched to {best_candidate.get('name')} with {best_score:.2f} confidence"
            )
            
            if self.save_mapping(mapping):
                logger.info(f"Created automatic mapping: {yahoo_name} -> {best_candidate.get('name')} ({best_score:.2f})")
                return mapping
        
        # If no good automatic match, create a pending mapping
        mapping = PlayerMapping(
            yahoo_player_id=yahoo_player_id,
            yahoo_player_name=yahoo_name,
            standardized_name=self.standardize_name(yahoo_name),
            team_code=team_code,
            confidence_score=best_score,
            mapping_method="fuzzy" if best_score > 0 else "manual",  # Changed from "pending" to "manual"
            validation_status="needs_review",
            notes=f"Best match: {best_candidate.get('name') if best_candidate else 'none'} ({best_score:.2f})"
        )
        
        if self.save_mapping(mapping):
            return mapping
        
        return None
    
    def bulk_map_players(self, players: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create mappings for multiple players in bulk.
        
        Args:
            players: List of dicts with 'yahoo_player_id', 'yahoo_name', and optional 'team_code'
            
        Returns:
            Dictionary with mapping results and statistics
        """
        logger.info(f"Starting bulk mapping for {len(players)} players")
        
        results = {
            'total_players': len(players),
            'successful_mappings': 0,
            'failed_mappings': 0,
            'existing_mappings': 0,
            'needs_review': 0,
            'mappings': []
        }
        
        for player in players:
            yahoo_id = player.get('yahoo_player_id')
            yahoo_name = player.get('yahoo_name')
            team_code = player.get('team_code')
            
            if not yahoo_id or not yahoo_name:
                logger.warning(f"Skipping player with missing data: {player}")
                results['failed_mappings'] += 1
                continue
            
            try:
                mapping = self.create_automatic_mapping(yahoo_id, yahoo_name, team_code)
                
                if mapping:
                    results['mappings'].append({
                        'yahoo_player_id': yahoo_id,
                        'yahoo_name': yahoo_name,
                        'confidence_score': mapping.confidence_score,
                        'mapping_method': mapping.mapping_method,
                        'validation_status': mapping.validation_status
                    })
                    
                    if mapping.validation_status == 'needs_review':
                        results['needs_review'] += 1
                    else:
                        results['successful_mappings'] += 1
                else:
                    results['failed_mappings'] += 1
                    
            except Exception as e:
                logger.error(f"Error mapping player {yahoo_name} ({yahoo_id}): {e}")
                results['failed_mappings'] += 1
        
        logger.info(f"Bulk mapping completed: {results['successful_mappings']} successful, "
                   f"{results['needs_review']} need review, {results['failed_mappings']} failed")
        
        return results
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current mapping state.
        
        Returns:
            Dictionary with mapping statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total mappings
            cursor.execute(f"SELECT COUNT(*) FROM {self.mapping_table} WHERE is_active = TRUE")
            stats['total_mappings'] = cursor.fetchone()[0]
            
            # By validation status
            cursor.execute(f"""
                SELECT validation_status, COUNT(*) 
                FROM {self.mapping_table} 
                WHERE is_active = TRUE 
                GROUP BY validation_status
            """)
            stats['by_status'] = dict(cursor.fetchall())
            
            # By mapping method
            cursor.execute(f"""
                SELECT mapping_method, COUNT(*) 
                FROM {self.mapping_table} 
                WHERE is_active = TRUE 
                GROUP BY mapping_method
            """)
            stats['by_method'] = dict(cursor.fetchall())
            
            # Confidence distribution
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN confidence_score >= 0.9 THEN 'high'
                        WHEN confidence_score >= 0.7 THEN 'medium'
                        WHEN confidence_score >= 0.5 THEN 'low'
                        ELSE 'very_low'
                    END as confidence_level,
                    COUNT(*)
                FROM {self.mapping_table}
                WHERE is_active = TRUE
                GROUP BY confidence_level
            """)
            stats['by_confidence'] = dict(cursor.fetchall())
            
            # Manual overrides
            cursor.execute(f"""
                SELECT COUNT(*) FROM {self.mapping_table} 
                WHERE is_active = TRUE AND manual_override = TRUE
            """)
            stats['manual_overrides'] = cursor.fetchone()[0]
            
            return stats
            
        finally:
            conn.close()


def main():
    """Command-line interface for player ID mapping operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Player ID Mapping Management")
    parser.add_argument("action", choices=["map", "stats", "validate"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--player-id", help="Yahoo player ID for single mapping")
    parser.add_argument("--player-name", help="Yahoo player name for single mapping")
    parser.add_argument("--team-code", help="Team code for single mapping")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    mapper = PlayerIdMapper(environment=args.env)
    
    if args.action == "map":
        if args.player_id and args.player_name:
            print(f"Creating mapping for {args.player_name} ({args.player_id})...")
            
            mapping = mapper.create_automatic_mapping(
                args.player_id, 
                args.player_name, 
                args.team_code
            )
            
            if mapping:
                print(f"Mapping created:")
                print(f"  Confidence: {mapping.confidence_score:.2f}")
                print(f"  Method: {mapping.mapping_method}")
                print(f"  Status: {mapping.validation_status}")
                if mapping.notes:
                    print(f"  Notes: {mapping.notes}")
            else:
                print("Failed to create mapping")
        else:
            print("ERROR: --player-id and --player-name are required for mapping")
    
    elif args.action == "stats":
        print(f"Player ID mapping statistics for {args.env} environment:")
        print("-" * 60)
        
        stats = mapper.get_mapping_statistics()
        
        print(f"Total mappings: {stats.get('total_mappings', 0)}")
        print(f"Manual overrides: {stats.get('manual_overrides', 0)}")
        
        print("\nBy validation status:")
        for status, count in stats.get('by_status', {}).items():
            print(f"  {status}: {count}")
        
        print("\nBy mapping method:")
        for method, count in stats.get('by_method', {}).items():
            print(f"  {method}: {count}")
        
        print("\nBy confidence level:")
        for level, count in stats.get('by_confidence', {}).items():
            print(f"  {level}: {count}")


if __name__ == "__main__":
    main()