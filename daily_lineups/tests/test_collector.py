"""
Unit tests for the DailyLineupsCollector class.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import sqlite3
import tempfile
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from daily_lineups.collector import DailyLineupsCollector


class TestDailyLineupsCollector(unittest.TestCase):
    """Test cases for DailyLineupsCollector."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Initialize test database with schema
        self._init_test_db()
        
        # Create collector instance
        self.collector = DailyLineupsCollector(environment="test")
        self.collector.db_path = self.temp_db.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def _init_test_db(self):
        """Initialize test database with required schema."""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Create job_log table
        cursor.execute("""
            CREATE TABLE job_log (
                job_id TEXT PRIMARY KEY,
                job_type TEXT,
                environment TEXT,
                status TEXT,
                date_range_start TEXT,
                date_range_end TEXT,
                league_key TEXT,
                start_time TEXT,
                end_time TEXT,
                records_processed INTEGER,
                records_inserted INTEGER,
                error_message TEXT
            )
        """)
        
        # Create daily_lineups_test table
        cursor.execute("""
            CREATE TABLE daily_lineups_test (
                lineup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                season INTEGER,
                date TEXT,
                team_key TEXT,
                team_name TEXT,
                player_id TEXT,
                player_name TEXT,
                selected_position TEXT,
                position_type TEXT,
                player_status TEXT,
                eligible_positions TEXT,
                player_team TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    @patch('daily_lineups.collector.requests.get')
    def test_make_api_request_success(self, mock_get):
        """Test successful API request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<fantasy_content><team><name>Test Team</name></team></fantasy_content>"
        mock_get.return_value = mock_response
        
        # Set access token
        self.collector.access_token = "test_token"
        
        # Make request
        result = self.collector._make_api_request("http://test.url")
        
        # Assertions
        self.assertEqual(result, mock_response.text)
        self.assertEqual(self.collector.stats["requests_made"], 1)
        self.assertEqual(self.collector.stats["requests_failed"], 0)
        mock_get.assert_called_once()
    
    @patch('daily_lineups.collector.requests.get')
    def test_make_api_request_retry_on_failure(self, mock_get):
        """Test API request retry logic."""
        # Mock responses - fail twice, then succeed
        mock_get.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            Mock(status_code=200, text="<success/>")
        ]
        
        # Set access token
        self.collector.access_token = "test_token"
        
        # Make request with shorter retry delays
        with patch('daily_lineups.collector.time.sleep'):
            result = self.collector._make_api_request("http://test.url", retries=3)
        
        # Assertions
        self.assertEqual(result, "<success/>")
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(self.collector.stats["requests_made"], 3)
        self.assertEqual(self.collector.stats["requests_failed"], 2)
    
    @patch('daily_lineups.collector.requests.get')
    def test_fetch_league_teams(self, mock_get):
        """Test fetching league teams."""
        # Mock XML response
        xml_response = """
        <fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">
            <league>
                <teams>
                    <team>
                        <team_key>mlb.l.123.t.1</team_key>
                        <name>Team One</name>
                    </team>
                    <team>
                        <team_key>mlb.l.123.t.2</team_key>
                        <name>Team Two</name>
                    </team>
                </teams>
            </league>
        </fantasy_content>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        mock_get.return_value = mock_response
        
        # Set access token
        self.collector.access_token = "test_token"
        
        # Fetch teams
        teams = self.collector.fetch_league_teams("mlb.l.123")
        
        # Assertions
        self.assertEqual(len(teams), 2)
        self.assertEqual(teams[0], ("mlb.l.123.t.1", "Team One"))
        self.assertEqual(teams[1], ("mlb.l.123.t.2", "Team Two"))
    
    @patch('daily_lineups.collector.requests.get')
    def test_fetch_team_roster(self, mock_get):
        """Test fetching team roster."""
        # Mock XML response
        xml_response = """
        <fantasy_content xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng">
            <team>
                <roster>
                    <players>
                        <player>
                            <player_id>12345</player_id>
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
                        </player>
                        <player>
                            <player_id>67890</player_id>
                            <name>
                                <full>Shohei Ohtani</full>
                            </name>
                            <selected_position>
                                <position>BN</position>
                            </selected_position>
                            <eligible_positions>
                                <position>SP</position>
                                <position>UTIL</position>
                            </eligible_positions>
                            <status>DTD</status>
                            <editorial_team_abbr>LAD</editorial_team_abbr>
                        </player>
                    </players>
                </roster>
            </team>
        </fantasy_content>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = xml_response
        mock_get.return_value = mock_response
        
        # Set access token
        self.collector.access_token = "test_token"
        
        # Fetch roster
        players = self.collector.fetch_team_roster("mlb.l.123.t.1", "2025-06-15")
        
        # Assertions
        self.assertEqual(len(players), 2)
        
        # Check first player
        self.assertEqual(players[0]["player_id"], "12345")
        self.assertEqual(players[0]["player_name"], "Mike Trout")
        self.assertEqual(players[0]["selected_position"], "OF")
        self.assertEqual(players[0]["position_type"], "B")  # Batter
        self.assertEqual(players[0]["eligible_positions"], "OF,UTIL")
        self.assertEqual(players[0]["player_status"], "healthy")
        self.assertEqual(players[0]["player_team"], "LAA")
        
        # Check second player
        self.assertEqual(players[1]["player_id"], "67890")
        self.assertEqual(players[1]["player_name"], "Shohei Ohtani")
        self.assertEqual(players[1]["selected_position"], "BN")
        self.assertEqual(players[1]["position_type"], "B")  # Bench
        self.assertEqual(players[1]["player_status"], "DTD")
        self.assertEqual(players[1]["player_team"], "LAD")
    
    def test_insert_batch(self):
        """Test batch insertion of lineup data."""
        # Create test data
        batch_data = [
            ("job_123", 2025, "2025-06-15", "mlb.l.123.t.1", "Team One",
             "player_1", "Player One", "C", "B", "healthy", "C", "NYY"),
            ("job_123", 2025, "2025-06-15", "mlb.l.123.t.1", "Team One",
             "player_2", "Player Two", "1B", "B", "healthy", "1B", "BOS"),
        ]
        
        # Connect to test database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Insert batch
        self.collector._insert_batch(cursor, batch_data)
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM daily_lineups_test")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        # Verify data
        cursor.execute("SELECT player_name, selected_position FROM daily_lineups_test ORDER BY player_id")
        results = cursor.fetchall()
        self.assertEqual(results[0], ("Player One", "C"))
        self.assertEqual(results[1], ("Player Two", "1B"))
        
        # Check stats
        self.assertEqual(self.collector.stats["records_inserted"], 2)
        
        conn.close()
    
    def test_create_and_update_job_log(self):
        """Test job log creation and updates."""
        job_id = "test_job_123"
        
        # Create job log
        self.collector._create_job_log(
            job_id, "mlb.l.123", "2025-06-01", "2025-06-07"
        )
        
        # Verify creation
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT status, environment FROM job_log WHERE job_id = ?", (job_id,))
        result = cursor.fetchone()
        self.assertEqual(result[0], "running")
        self.assertEqual(result[1], "test")
        
        # Update job log
        self.collector._update_job_log(
            job_id, "completed", records_processed=100, records_inserted=95
        )
        
        # Verify update
        cursor.execute("""
            SELECT status, records_processed, records_inserted 
            FROM job_log WHERE job_id = ?
        """, (job_id,))
        result = cursor.fetchone()
        self.assertEqual(result[0], "completed")
        self.assertEqual(result[1], 100)
        self.assertEqual(result[2], 95)
        
        conn.close()
    
    @patch('daily_lineups.collector.DailyLineupsCollector.fetch_league_teams')
    @patch('daily_lineups.collector.DailyLineupsCollector.fetch_team_roster')
    def test_collect_date_range(self, mock_fetch_roster, mock_fetch_teams):
        """Test collecting lineup data for a date range."""
        # Mock teams
        mock_fetch_teams.return_value = [
            ("mlb.l.123.t.1", "Team One"),
            ("mlb.l.123.t.2", "Team Two")
        ]
        
        # Mock rosters
        mock_fetch_roster.return_value = [
            {
                "player_id": "player_1",
                "player_name": "Test Player",
                "selected_position": "OF",
                "position_type": "B",
                "player_status": "healthy",
                "eligible_positions": "OF",
                "player_team": "NYY"
            }
        ]
        
        # Set access token
        self.collector.access_token = "test_token"
        
        # Collect data with mocked sleep
        with patch('daily_lineups.collector.time.sleep'):
            self.collector.collect_date_range(
                "2025-06-01", "2025-06-02", "mlb.l.123"
            )
        
        # Verify data was collected
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check lineup data
        cursor.execute("SELECT COUNT(*) FROM daily_lineups_test")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 4)  # 2 teams × 2 dates × 1 player each
        
        # Check job log
        cursor.execute("SELECT status FROM job_log WHERE job_type = 'lineup_collection'")
        status = cursor.fetchone()[0]
        self.assertEqual(status, "completed")
        
        conn.close()


if __name__ == "__main__":
    unittest.main()