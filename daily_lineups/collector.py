"""
Daily Lineups Collector Module
Handles data collection from Yahoo Fantasy API for daily roster/lineup data.
"""

import requests
import xml.etree.ElementTree as ET
import sqlite3
import json
import logging
import time
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from auth.config import BASE_FANTASY_URL
from daily_lineups.config import (
    API_DELAY_SECONDS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    REQUEST_TIMEOUT,
    BATCH_SIZE,
    get_lineup_table_name,
    get_database_path,
    get_league_key,
    get_season_dates
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyLineupsCollector:
    """Collects daily lineup data from Yahoo Fantasy API."""
    
    def __init__(self, token_manager=None, environment="production"):
        """
        Initialize the collector.
        
        Args:
            token_manager: TokenManager instance for OAuth2 authentication
            environment: 'production' or 'test' for table selection
        """
        self.token_manager = token_manager
        self.environment = environment
        self.table_name = get_lineup_table_name(environment)
        self.db_path = get_database_path(environment)
        self.access_token = None
        self.token_expiry = None
        
        # Statistics tracking
        self.stats = {
            "requests_made": 0,
            "requests_failed": 0,
            "records_processed": 0,
            "records_inserted": 0
        }
    
    def _ensure_token(self):
        """Ensure we have a valid access token."""
        if self.token_manager:
            # Use TokenManager if available
            self.access_token = self.token_manager.get_valid_token()
        else:
            # Fallback to reading from tokens.json
            token_path = Path(__file__).parent.parent / "auth" / "tokens.json"
            if token_path.exists():
                with open(token_path, 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get('access_token')
            else:
                raise ValueError("No token manager provided and tokens.json not found")
        
        if not self.access_token:
            raise ValueError("Unable to obtain access token")
    
    def _make_api_request(self, url: str, retries: int = MAX_RETRIES) -> str:
        """
        Make an API request with retry logic.
        
        Args:
            url: The API endpoint URL
            retries: Number of retry attempts
            
        Returns:
            Response text from the API
        """
        self._ensure_token()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/xml"
        }
        
        for attempt in range(retries):
            try:
                self.stats["requests_made"] += 1
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 401:
                    # Token expired, refresh and retry
                    logger.warning("Token expired, refreshing...")
                    self.access_token = None
                    self._ensure_token()
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    continue
                
                response.raise_for_status()
                return response.text
                
            except requests.exceptions.RequestException as e:
                self.stats["requests_failed"] += 1
                wait_time = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                
                if attempt < retries - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed to fetch data after {retries} attempts")
    
    def fetch_league_teams(self, league_key: str) -> List[Tuple[str, str]]:
        """
        Fetch all teams in a league.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            List of (team_key, team_name) tuples
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/teams"
        logger.info(f"Fetching teams for league {league_key}")
        
        xml_text = self._make_api_request(url)
        
        # Remove namespace for easier parsing
        xml_text = re.sub(r' xmlns="[^"]+"', '', xml_text, count=1)
        root = ET.fromstring(xml_text)
        
        teams = []
        for team in root.findall(".//team"):
            team_key = team.findtext("team_key")
            team_name = team.findtext("name")
            if team_key and team_name:
                teams.append((team_key, team_name))
                logger.debug(f"Found team: {team_name} ({team_key})")
        
        logger.info(f"Found {len(teams)} teams")
        return teams
    
    def fetch_team_roster(self, team_key: str, date_str: str) -> List[Dict]:
        """
        Fetch roster for a specific team on a specific date.
        
        Args:
            team_key: Yahoo team key
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            List of player dictionaries with lineup information
        """
        url = f"{BASE_FANTASY_URL}/team/{team_key}/roster;date={date_str}"
        logger.debug(f"Fetching roster for {team_key} on {date_str}")
        
        xml_text = self._make_api_request(url)
        
        # Remove namespace for easier parsing
        xml_text = re.sub(r' xmlns="[^"]+"', '', xml_text, count=1)
        root = ET.fromstring(xml_text)
        
        players = []
        for player in root.findall(".//player"):
            player_data = {
                "player_id": player.findtext("player_id"),
                "player_name": player.findtext("name/full"),
                "selected_position": player.findtext(".//selected_position/position"),
                "position_type": None,  # Will be determined from selected_position
                "eligible_positions": [],
                "player_status": "healthy",  # Default
                "player_team": None  # MLB team
            }
            
            # Get eligible positions
            for position in player.findall(".//eligible_positions/position"):
                pos_text = position.text
                if pos_text:
                    player_data["eligible_positions"].append(pos_text)
            
            # Join eligible positions
            player_data["eligible_positions"] = ",".join(player_data["eligible_positions"])
            
            # Determine position type
            selected_pos = player_data["selected_position"]
            if selected_pos in ["BN", "IL", "IL10", "IL60", "NA"]:
                player_data["position_type"] = "B"  # Bench
            elif selected_pos in ["SP", "RP", "P"]:
                player_data["position_type"] = "P"  # Pitcher
            else:
                player_data["position_type"] = "B"  # Batter (default)
            
            # Get player status
            status = player.findtext("status")
            if status:
                player_data["player_status"] = status
            
            # Get MLB team
            editorial_team = player.findtext("editorial_team_abbr")
            if editorial_team:
                player_data["player_team"] = editorial_team
            
            if player_data["player_id"] and player_data["player_name"]:
                players.append(player_data)
                self.stats["records_processed"] += 1
        
        logger.debug(f"Found {len(players)} players for {team_key}")
        return players
    
    def collect_date_range(self, start_date: str, end_date: str, league_key: str = None, job_id: str = None):
        """
        Collect lineup data for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            league_key: Yahoo league key (optional, will use current season if not provided)
            job_id: Job ID for tracking (optional)
        """
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Get league key if not provided
        if not league_key:
            season = start.year
            league_key = get_league_key(season)
            if not league_key:
                raise ValueError(f"No league key configured for season {season}")
        
        # Extract season from league key or use year
        season = start.year
        
        # Generate job_id if not provided
        if not job_id:
            from uuid import uuid4
            job_id = f"lineup_collection_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        
        logger.info(f"Starting collection for {start_date} to {end_date}")
        logger.info(f"League: {league_key}, Environment: {self.environment}, Job: {job_id}")
        
        # Create job log entry
        self._create_job_log(job_id, league_key, start_date, end_date)
        
        try:
            # Fetch teams once
            teams = self.fetch_league_teams(league_key)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Process each date
            current_date = start
            batch_data = []
            
            while current_date <= end:
                date_str = current_date.strftime("%Y-%m-%d")
                logger.info(f"Processing {date_str}")
                
                # Fetch roster for each team
                for team_key, team_name in teams:
                    try:
                        # Add delay between requests
                        time.sleep(API_DELAY_SECONDS)
                        
                        # Fetch roster
                        players = self.fetch_team_roster(team_key, date_str)
                        
                        # Prepare batch insert data
                        for player in players:
                            batch_data.append((
                                job_id,
                                season,
                                date_str,
                                team_key,
                                team_name,
                                player["player_id"],
                                player["player_name"],
                                player["selected_position"],
                                player["position_type"],
                                player["player_status"],
                                player["eligible_positions"],
                                player["player_team"]
                            ))
                        
                        # Insert in batches
                        if len(batch_data) >= BATCH_SIZE:
                            self._insert_batch(cursor, batch_data)
                            conn.commit()
                            batch_data = []
                            
                    except Exception as e:
                        logger.error(f"Error processing {team_name} on {date_str}: {e}")
                        continue
                
                # Move to next date
                current_date += timedelta(days=1)
            
            # Insert remaining data
            if batch_data:
                self._insert_batch(cursor, batch_data)
                conn.commit()
            
            # Update job log
            self._update_job_log(job_id, "completed", self.stats["records_processed"], self.stats["records_inserted"])
            
            logger.info(f"Collection completed: {self.stats}")
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            self._update_job_log(job_id, "failed", error_message=str(e))
            raise
            
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _insert_batch(self, cursor, batch_data):
        """Insert a batch of lineup data."""
        try:
            cursor.executemany(f"""
                INSERT OR REPLACE INTO {self.table_name} (
                    job_id, season, date, team_key, team_name,
                    player_id, player_name, selected_position, position_type,
                    player_status, eligible_positions, player_team
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            
            self.stats["records_inserted"] += len(batch_data)
            logger.debug(f"Inserted batch of {len(batch_data)} records")
            
        except sqlite3.Error as e:
            logger.error(f"Database error inserting batch: {e}")
            raise
    
    def _create_job_log(self, job_id, league_key, start_date, end_date):
        """Create job log entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                date_range_start, date_range_end, league_key,
                start_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            "lineup_collection",
            self.environment,
            "running",
            start_date,
            end_date,
            league_key,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_job_log(self, job_id, status, records_processed=None, records_inserted=None, error_message=None):
        """Update job log entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE job_log
            SET status = ?,
                records_processed = ?,
                records_inserted = ?,
                error_message = ?,
                end_time = ?
            WHERE job_id = ?
        """, (
            status,
            records_processed,
            records_inserted,
            error_message,
            datetime.now().isoformat(),
            job_id
        ))
        
        conn.commit()
        conn.close()


def main():
    """Command line interface for the collector."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect daily lineup data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--league", help="League key (optional)")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (production/test)")
    
    args = parser.parse_args()
    
    # Initialize collector
    collector = DailyLineupsCollector(environment=args.env)
    
    # Run collection
    collector.collect_date_range(
        start_date=args.start,
        end_date=args.end,
        league_key=args.league
    )


if __name__ == "__main__":
    main()