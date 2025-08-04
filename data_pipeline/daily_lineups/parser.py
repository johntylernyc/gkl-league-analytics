"""
XML Parser for Daily Lineups
Handles parsing of Yahoo Fantasy API XML responses for roster data.
"""

import xml.etree.ElementTree as ET
import re
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LineupParser:
    """Parse Yahoo Fantasy API XML responses for lineup data."""
    
    @staticmethod
    def remove_namespace(xml_text: str) -> str:
        """
        Remove XML namespace for easier parsing.
        
        Args:
            xml_text: Raw XML text with namespace
            
        Returns:
            XML text without namespace
        """
        return re.sub(r' xmlns="[^"]+"', '', xml_text, count=1)
    
    @staticmethod
    def parse_teams_response(xml_text: str) -> List[Tuple[str, str]]:
        """
        Parse teams from league teams API response.
        
        Args:
            xml_text: XML response from /league/{league_key}/teams endpoint
            
        Returns:
            List of (team_key, team_name) tuples
        """
        try:
            # Remove namespace
            xml_text = LineupParser.remove_namespace(xml_text)
            root = ET.fromstring(xml_text)
            
            teams = []
            for team in root.findall(".//team"):
                team_key = team.findtext("team_key")
                team_name = team.findtext("name")
                
                if team_key and team_name:
                    teams.append((team_key, team_name))
                    logger.debug(f"Parsed team: {team_name} ({team_key})")
            
            logger.info(f"Parsed {len(teams)} teams from response")
            return teams
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing teams response: {e}")
            raise
    
    @staticmethod
    def parse_roster_response(xml_text: str) -> List[Dict]:
        """
        Parse roster from team roster API response.
        
        Args:
            xml_text: XML response from /team/{team_key}/roster endpoint
            
        Returns:
            List of player dictionaries with lineup information
        """
        try:
            # Remove namespace
            xml_text = LineupParser.remove_namespace(xml_text)
            root = ET.fromstring(xml_text)
            
            players = []
            for player in root.findall(".//player"):
                player_data = LineupParser._parse_player_element(player)
                if player_data:
                    players.append(player_data)
            
            logger.debug(f"Parsed {len(players)} players from roster response")
            return players
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing roster response: {e}")
            raise
    
    @staticmethod
    def _parse_player_element(player_element: ET.Element) -> Optional[Dict]:
        """
        Parse individual player element.
        
        Args:
            player_element: XML Element for a player
            
        Returns:
            Dictionary with player data or None if invalid
        """
        try:
            # Basic player info
            player_data = {
                "player_id": player_element.findtext("player_id"),
                "player_name": player_element.findtext("name/full"),
                "player_key": player_element.findtext("player_key"),
                "uniform_number": player_element.findtext("uniform_number"),
                "selected_position": None,
                "position_type": None,
                "eligible_positions": [],
                "player_status": "healthy",
                "player_team": None,
                "image_url": None
            }
            
            # Selected position (lineup position for the day)
            selected_pos = player_element.findtext(".//selected_position/position")
            if selected_pos:
                player_data["selected_position"] = selected_pos
                player_data["position_type"] = LineupParser._determine_position_type(selected_pos)
            
            # Eligible positions
            for position in player_element.findall(".//eligible_positions/position"):
                pos_text = position.text
                if pos_text:
                    player_data["eligible_positions"].append(pos_text)
            
            # Join eligible positions as comma-separated string
            player_data["eligible_positions"] = ",".join(player_data["eligible_positions"])
            
            # Player status
            status = player_element.findtext("status")
            status_full = player_element.findtext("status_full")
            
            if status:
                player_data["player_status"] = status
            elif status_full:
                # Parse full status like "Injured List"
                if "Injured" in status_full or "IL" in status_full:
                    player_data["player_status"] = "IL"
                elif "Day-to-Day" in status_full or "DTD" in status_full:
                    player_data["player_status"] = "DTD"
                elif "Out" in status_full:
                    player_data["player_status"] = "O"
                else:
                    player_data["player_status"] = status_full
            
            # MLB team
            player_data["player_team"] = (
                player_element.findtext("editorial_team_abbr") or
                player_element.findtext("editorial_team_abbreviation")
            )
            
            # Image URL (optional)
            player_data["image_url"] = player_element.findtext("image_url")
            
            # Validate required fields
            if not player_data["player_id"] or not player_data["player_name"]:
                logger.warning(f"Skipping player with missing ID or name: {player_data}")
                return None
            
            return player_data
            
        except Exception as e:
            logger.error(f"Error parsing player element: {e}")
            return None
    
    @staticmethod
    def _determine_position_type(position: str) -> str:
        """
        Determine position type from position code.
        
        Args:
            position: Position code (e.g., "C", "SP", "BN")
            
        Returns:
            Position type: "B" (Batter), "P" (Pitcher), or "X" (Bench/IL)
        """
        if not position:
            return "X"
        
        # Bench/IL positions
        if position in ["BN", "IL", "IL10", "IL60", "NA"]:
            return "X"
        
        # Pitcher positions
        if position in ["SP", "RP", "P"]:
            return "P"
        
        # Everything else is a batter
        return "B"
    
    @staticmethod
    def parse_transaction_date(xml_text: str) -> Optional[str]:
        """
        Extract transaction date from XML response.
        
        Args:
            xml_text: XML response containing transaction data
            
        Returns:
            Date string in YYYY-MM-DD format or None
        """
        try:
            xml_text = LineupParser.remove_namespace(xml_text)
            root = ET.fromstring(xml_text)
            
            # Try different date fields
            date_str = (
                root.findtext(".//transaction_date") or
                root.findtext(".//date") or
                root.findtext(".//timestamp")
            )
            
            if date_str:
                # Parse various date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
                        return dt.strftime("%Y-%m-%d")
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing transaction date: {e}")
            return None
    
    @staticmethod
    def validate_lineup_data(lineup_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Validate and clean lineup data.
        
        Args:
            lineup_data: List of player dictionaries
            
        Returns:
            Tuple of (valid_data, validation_errors)
        """
        valid_data = []
        errors = []
        
        for i, player in enumerate(lineup_data):
            # Check required fields
            required_fields = ["player_id", "player_name"]
            missing_fields = [f for f in required_fields if not player.get(f)]
            
            if missing_fields:
                errors.append(f"Player {i}: Missing fields {missing_fields}")
                continue
            
            # Validate position if present
            if player.get("selected_position"):
                valid_positions = [
                    "C", "1B", "2B", "3B", "SS", "MI", "CI", "OF", "UTIL",
                    "SP", "RP", "P", "BN", "IL", "IL10", "IL60", "NA"
                ]
                if player["selected_position"] not in valid_positions:
                    errors.append(f"Player {player['player_name']}: Invalid position {player['selected_position']}")
            
            # Clean and standardize data
            player["player_name"] = player["player_name"].strip()
            player["player_id"] = str(player["player_id"]).strip()
            
            valid_data.append(player)
        
        if errors:
            logger.warning(f"Validation found {len(errors)} issues")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(f"  - {error}")
        
        return valid_data, errors


class LineupDataEnricher:
    """Enrich lineup data with additional information."""
    
    @staticmethod
    def add_derived_fields(player_data: Dict, team_info: Dict = None) -> Dict:
        """
        Add derived fields to player data.
        
        Args:
            player_data: Player dictionary
            team_info: Optional team information
            
        Returns:
            Enriched player dictionary
        """
        # Add is_starting flag
        player_data["is_starting"] = (
            player_data.get("selected_position") and
            player_data["selected_position"] not in ["BN", "IL", "IL10", "IL60", "NA"]
        )
        
        # Add is_active flag
        player_data["is_active"] = (
            player_data.get("player_status") in ["healthy", "DTD", None]
        )
        
        # Add position category
        position = player_data.get("selected_position", "")
        if position in ["C", "1B", "2B", "3B", "SS", "MI", "CI", "OF", "UTIL"]:
            player_data["position_category"] = "batting"
        elif position in ["SP", "RP", "P"]:
            player_data["position_category"] = "pitching"
        else:
            player_data["position_category"] = "bench"
        
        # Add team info if provided
        if team_info:
            player_data.update(team_info)
        
        return player_data
    
    @staticmethod
    def calculate_lineup_stats(lineup_data: List[Dict]) -> Dict:
        """
        Calculate statistics for a lineup.
        
        Args:
            lineup_data: List of player dictionaries
            
        Returns:
            Dictionary with lineup statistics
        """
        stats = {
            "total_players": len(lineup_data),
            "starting_batters": 0,
            "starting_pitchers": 0,
            "bench_players": 0,
            "injured_players": 0,
            "positions_filled": set(),
            "mlb_teams_represented": set()
        }
        
        for player in lineup_data:
            position = player.get("selected_position", "")
            
            # Count by position type
            if player.get("position_type") == "B" and player.get("is_starting"):
                stats["starting_batters"] += 1
            elif player.get("position_type") == "P" and player.get("is_starting"):
                stats["starting_pitchers"] += 1
            elif position in ["BN"]:
                stats["bench_players"] += 1
            elif position in ["IL", "IL10", "IL60"]:
                stats["injured_players"] += 1
            
            # Track positions filled
            if position and position not in ["BN", "IL", "IL10", "IL60", "NA"]:
                stats["positions_filled"].add(position)
            
            # Track MLB teams
            if player.get("player_team"):
                stats["mlb_teams_represented"].add(player["player_team"])
        
        # Convert sets to counts
        stats["unique_positions"] = len(stats["positions_filled"])
        stats["unique_mlb_teams"] = len(stats["mlb_teams_represented"])
        stats["positions_filled"] = list(stats["positions_filled"])
        stats["mlb_teams_represented"] = list(stats["mlb_teams_represented"])
        
        return stats