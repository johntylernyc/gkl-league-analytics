"""
Unit tests for the LineupParser class.
"""

import unittest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from daily_lineups.parser import LineupParser, LineupDataEnricher


class TestLineupParser(unittest.TestCase):
    """Test cases for LineupParser."""
    
    def test_remove_namespace(self):
        """Test XML namespace removal."""
        xml_with_ns = '<fantasy_content xmlns="http://example.com"><data>test</data></fantasy_content>'
        result = LineupParser.remove_namespace(xml_with_ns)
        self.assertNotIn('xmlns=', result)
        self.assertIn('<fantasy_content>', result)
    
    def test_parse_teams_response(self):
        """Test parsing teams from XML response."""
        xml_text = """
        <fantasy_content>
            <league>
                <teams>
                    <team>
                        <team_key>mlb.l.123.t.1</team_key>
                        <name>Bash Brothers</name>
                    </team>
                    <team>
                        <team_key>mlb.l.123.t.2</team_key>
                        <name>Diamond Dynasty</name>
                    </team>
                </teams>
            </league>
        </fantasy_content>
        """
        
        teams = LineupParser.parse_teams_response(xml_text)
        
        self.assertEqual(len(teams), 2)
        self.assertEqual(teams[0], ("mlb.l.123.t.1", "Bash Brothers"))
        self.assertEqual(teams[1], ("mlb.l.123.t.2", "Diamond Dynasty"))
    
    def test_parse_roster_response(self):
        """Test parsing roster from XML response."""
        xml_text = """
        <fantasy_content>
            <team>
                <roster>
                    <players>
                        <player>
                            <player_id>12345</player_id>
                            <player_key>mlb.p.12345</player_key>
                            <name>
                                <full>Mike Trout</full>
                            </name>
                            <selected_position>
                                <position>OF</position>
                            </selected_position>
                            <eligible_positions>
                                <position>OF</position>
                                <position>UTIL</position>
                            </eligible_positions>
                            <status>healthy</status>
                            <editorial_team_abbr>LAA</editorial_team_abbr>
                            <uniform_number>27</uniform_number>
                        </player>
                        <player>
                            <player_id>67890</player_id>
                            <name>
                                <full>Freddie Freeman</full>
                            </name>
                            <selected_position>
                                <position>1B</position>
                            </selected_position>
                            <eligible_positions>
                                <position>1B</position>
                            </eligible_positions>
                            <status>DTD</status>
                            <editorial_team_abbr>LAD</editorial_team_abbr>
                        </player>
                    </players>
                </roster>
            </team>
        </fantasy_content>
        """
        
        players = LineupParser.parse_roster_response(xml_text)
        
        self.assertEqual(len(players), 2)
        
        # Check first player
        self.assertEqual(players[0]["player_id"], "12345")
        self.assertEqual(players[0]["player_name"], "Mike Trout")
        self.assertEqual(players[0]["selected_position"], "OF")
        self.assertEqual(players[0]["position_type"], "B")
        self.assertEqual(players[0]["eligible_positions"], "OF,UTIL")
        self.assertEqual(players[0]["player_status"], "healthy")
        self.assertEqual(players[0]["player_team"], "LAA")
        self.assertEqual(players[0]["uniform_number"], "27")
        
        # Check second player
        self.assertEqual(players[1]["player_id"], "67890")
        self.assertEqual(players[1]["player_name"], "Freddie Freeman")
        self.assertEqual(players[1]["selected_position"], "1B")
        self.assertEqual(players[1]["player_status"], "DTD")
    
    def test_determine_position_type(self):
        """Test position type determination."""
        # Batters
        self.assertEqual(LineupParser._determine_position_type("C"), "B")
        self.assertEqual(LineupParser._determine_position_type("1B"), "B")
        self.assertEqual(LineupParser._determine_position_type("OF"), "B")
        self.assertEqual(LineupParser._determine_position_type("UTIL"), "B")
        
        # Pitchers
        self.assertEqual(LineupParser._determine_position_type("SP"), "P")
        self.assertEqual(LineupParser._determine_position_type("RP"), "P")
        self.assertEqual(LineupParser._determine_position_type("P"), "P")
        
        # Bench/IL
        self.assertEqual(LineupParser._determine_position_type("BN"), "X")
        self.assertEqual(LineupParser._determine_position_type("IL"), "X")
        self.assertEqual(LineupParser._determine_position_type("IL10"), "X")
        
        # None/empty
        self.assertEqual(LineupParser._determine_position_type(None), "X")
        self.assertEqual(LineupParser._determine_position_type(""), "X")
    
    def test_validate_lineup_data(self):
        """Test lineup data validation."""
        lineup_data = [
            {
                "player_id": "123",
                "player_name": "  Valid Player  ",
                "selected_position": "OF"
            },
            {
                "player_id": "",  # Missing ID
                "player_name": "Invalid Player"
            },
            {
                "player_id": "456",
                "player_name": "Bad Position",
                "selected_position": "XYZ"  # Invalid position
            }
        ]
        
        valid_data, errors = LineupParser.validate_lineup_data(lineup_data)
        
        # Should have 2 valid players (one with trimmed name, one with position warning)
        self.assertEqual(len(valid_data), 2)
        self.assertEqual(valid_data[0]["player_name"], "Valid Player")  # Trimmed
        
        # Should have 2 errors
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("Missing fields" in e for e in errors))
        self.assertTrue(any("Invalid position XYZ" in e for e in errors))


class TestLineupDataEnricher(unittest.TestCase):
    """Test cases for LineupDataEnricher."""
    
    def test_add_derived_fields(self):
        """Test adding derived fields to player data."""
        player_data = {
            "player_id": "123",
            "player_name": "Test Player",
            "selected_position": "OF",
            "player_status": "healthy"
        }
        
        enriched = LineupDataEnricher.add_derived_fields(player_data)
        
        self.assertTrue(enriched["is_starting"])
        self.assertTrue(enriched["is_active"])
        self.assertEqual(enriched["position_category"], "batting")
        
        # Test bench player
        bench_player = {
            "selected_position": "BN",
            "player_status": "IL10"
        }
        
        enriched_bench = LineupDataEnricher.add_derived_fields(bench_player)
        
        self.assertFalse(enriched_bench["is_starting"])
        self.assertFalse(enriched_bench["is_active"])
        self.assertEqual(enriched_bench["position_category"], "bench")
    
    def test_calculate_lineup_stats(self):
        """Test calculating lineup statistics."""
        lineup_data = [
            {
                "selected_position": "C",
                "position_type": "B",
                "is_starting": True,
                "player_team": "NYY"
            },
            {
                "selected_position": "1B",
                "position_type": "B",
                "is_starting": True,
                "player_team": "BOS"
            },
            {
                "selected_position": "SP",
                "position_type": "P",
                "is_starting": True,
                "player_team": "NYY"
            },
            {
                "selected_position": "BN",
                "position_type": "B",
                "is_starting": False,
                "player_team": "LAD"
            },
            {
                "selected_position": "IL",
                "position_type": "B",
                "is_starting": False,
                "player_team": "LAD"
            }
        ]
        
        stats = LineupDataEnricher.calculate_lineup_stats(lineup_data)
        
        self.assertEqual(stats["total_players"], 5)
        self.assertEqual(stats["starting_batters"], 2)
        self.assertEqual(stats["starting_pitchers"], 1)
        self.assertEqual(stats["bench_players"], 1)
        self.assertEqual(stats["injured_players"], 1)
        self.assertEqual(stats["unique_positions"], 3)  # C, 1B, SP
        self.assertEqual(stats["unique_mlb_teams"], 3)  # NYY, BOS, LAD
        self.assertIn("C", stats["positions_filled"])
        self.assertIn("NYY", stats["mlb_teams_represented"])


if __name__ == "__main__":
    unittest.main()