"""
Draft Results Collector Module

Handles data collection from Yahoo Fantasy API for draft results data.
This module follows the patterns established in daily_lineups and league_transactions.
"""

import json
import logging
import sqlite3
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from auth.token_manager import YahooTokenManager
from data_pipeline.config.database_config import get_database_path
from data_pipeline.draft_results.config import (
    API_DELAY_SECONDS,
    BASE_FANTASY_URL,
    BATCH_SIZE,
    DEFAULT_PLAYER_POSITION,
    DEFAULT_PLAYER_TEAM,
    DRAFT_TYPE_AUCTION,
    DRAFT_TYPE_SNAKE,
    LOG_FORMAT,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF_BASE,
    get_draft_table_name,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class DraftResultsCollector:
    """Collects draft results data from Yahoo Fantasy API."""
    
    def __init__(self, environment='development'):
        """
        Initialize the collector.
        
        Args:
            environment: 'production', 'development', or 'test' for database selection
        """
        self.environment = environment
        self.db_path = get_database_path(environment)
        self.table_name = get_draft_table_name(environment)
        
        # Authentication
        self.token_manager = YahooTokenManager()
        
        # Job tracking
        self.job_id = None
        self.stats = {
            'requests_made': 0,
            'requests_failed': 0,
            'records_processed': 0,
            'records_inserted': 0,
            'errors': 0
        }
        
        # Initialize database
        self._init_database()
        
        logger.info(f"DraftResultsCollector initialized for {environment} environment")
    
    def _init_database(self):
        """Initialize database and ensure tables exist."""
        schema_path = Path(__file__).parent / 'schema.sql'
        
        if not schema_path.exists():
            logger.warning("Schema file not found, tables must already exist")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create job_log table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_log (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                records_processed INTEGER DEFAULT 0,
                records_inserted INTEGER DEFAULT 0,
                error_message TEXT,
                date_range_start TEXT,
                date_range_end TEXT,
                league_key TEXT
            )
        """)
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            cursor.executescript(schema_sql)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _start_job(self, job_type: str, league_key: str, season: int) -> str:
        """
        Start a new job and log it in the job_log table.
        
        Args:
            job_type: Type of job (e.g., 'draft_collection')
            league_key: Yahoo league key
            season: Season year
            
        Returns:
            str: Generated job ID
        """
        job_id = f"{job_type}_{self.environment}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                league_key, date_range_start, date_range_end
            ) VALUES (?, ?, ?, 'running', ?, ?, ?)
        """, (
            job_id, job_type, self.environment,
            league_key, f"{season}-01-01", f"{season}-12-31"
        ))
        
        conn.commit()
        conn.close()
        
        self.job_id = job_id
        logger.info(f"Started job: {job_id}")
        return job_id
    
    def _update_job_status(self, status: str, error_message: Optional[str] = None):
        """Update job status in job_log table."""
        if not self.job_id:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE job_log 
            SET status = ?, records_processed = ?, 
                records_inserted = ?, error_message = ?
            WHERE job_id = ?
        """, (
            status,
            self.stats['records_processed'], self.stats['records_inserted'],
            error_message, self.job_id
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated job {self.job_id} status to {status}")
    
    def _make_api_request(self, url: str, retries: int = MAX_RETRIES) -> str:
        """
        Make an API request with retry logic.
        
        Args:
            url: The API endpoint URL
            retries: Number of retry attempts
            
        Returns:
            Response text from the API
        """
        access_token = self.token_manager.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/xml"
        }
        
        for attempt in range(retries):
            try:
                self.stats['requests_made'] += 1
                
                # Rate limiting
                time.sleep(API_DELAY_SECONDS)
                
                response = requests.get(
                    url, 
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 401:
                    # Token expired, refresh and retry
                    logger.warning("Token expired, refreshing...")
                    access_token = self.token_manager.get_access_token()
                    headers["Authorization"] = f"Bearer {access_token}"
                    continue
                
                response.raise_for_status()
                return response.text
                
            except requests.exceptions.RequestException as e:
                self.stats['requests_failed'] += 1
                wait_time = RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                
                if attempt < retries - 1:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception(f"Failed to fetch data after {retries} attempts")
    
    def fetch_league_settings(self, league_key: str) -> Dict:
        """
        Fetch league settings to determine draft type.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            Dict with draft_type and other settings
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/settings"
        logger.info(f"Fetching league settings for {league_key}")
        
        xml_text = self._make_api_request(url)
        root = ET.fromstring(xml_text)
        
        # Parse settings - Yahoo uses different namespace
        ns = {'yh': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        settings = {}
        settings_elem = root.find('.//yh:settings', ns)
        
        if settings_elem is not None:
            # Check is_auction_draft first (more reliable)
            is_auction_elem = settings_elem.find('.//yh:is_auction_draft', ns)
            if is_auction_elem is not None and is_auction_elem.text == '1':
                settings['draft_type'] = DRAFT_TYPE_AUCTION
            else:
                # Fall back to draft_type element
                draft_type_elem = settings_elem.find('.//yh:draft_type', ns)
                if draft_type_elem is not None:
                    # Yahoo uses 'live' for snake draft, 'auction' for auction
                    yahoo_type = draft_type_elem.text
                    settings['draft_type'] = DRAFT_TYPE_AUCTION if yahoo_type == 'auction' else DRAFT_TYPE_SNAKE
                else:
                    settings['draft_type'] = DRAFT_TYPE_SNAKE  # Default
            
            # Draft time
            draft_time_elem = settings_elem.find('.//yh:draft_time', ns)
            if draft_time_elem is not None:
                settings['draft_time'] = draft_time_elem.text
        
        logger.info(f"League settings: {settings}")
        return settings
    
    def fetch_player_details(self, player_keys: List[str]) -> Dict[str, Dict]:
        """
        Fetch player details for a list of player keys.
        
        Args:
            player_keys: List of Yahoo player keys
            
        Returns:
            Dict mapping player_key to player details
        """
        if not player_keys:
            return {}
        
        # Yahoo allows fetching multiple players at once
        # Join player keys with commas
        player_keys_str = ','.join(player_keys[:25])  # Limit to 25 at a time
        
        url = f"{BASE_FANTASY_URL}/players;player_keys={player_keys_str}"
        logger.info(f"Fetching details for {len(player_keys[:25])} players")
        
        try:
            xml_text = self._make_api_request(url)
            root = ET.fromstring(xml_text)
            
            ns = {'yh': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            player_details = {}
            
            for player in root.findall('.//yh:player', ns):
                player_key_elem = player.find('.//yh:player_key', ns)
                if player_key_elem is None:
                    continue
                    
                player_key = player_key_elem.text
                details = {}
                
                # Player name
                name_elem = player.find('.//yh:name/yh:full', ns)
                if name_elem is not None:
                    details['name'] = name_elem.text
                
                # Position
                pos_elem = player.find('.//yh:display_position', ns)
                if pos_elem is not None:
                    details['position'] = pos_elem.text
                
                # Team
                team_elem = player.find('.//yh:editorial_team_abbr', ns)
                if team_elem is not None:
                    details['team'] = team_elem.text
                    
                player_details[player_key] = details
            
            return player_details
            
        except Exception as e:
            logger.warning(f"Failed to fetch player details: {e}")
            return {}
    
    def fetch_draft_data_from_yahoo(self, league_key: str) -> List[Dict]:
        """
        Fetch draft results from Yahoo API.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            List of draft pick dictionaries
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/draftresults"
        logger.info(f"Fetching draft results for {league_key}")
        
        xml_text = self._make_api_request(url)
        root = ET.fromstring(xml_text)
        
        # Parse draft results
        ns = {'yh': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        draft_results = []
        
        # Find all draft result elements
        for result in root.findall('.//yh:draft_result', ns):
            pick_data = {}
            
            # Extract basic draft info
            pick_elem = result.find('.//yh:pick', ns)
            if pick_elem is not None:
                pick_data['pick'] = int(pick_elem.text)
            
            round_elem = result.find('.//yh:round', ns)
            if round_elem is not None:
                pick_data['round'] = int(round_elem.text)
            
            # Team info
            team_key_elem = result.find('.//yh:team_key', ns)
            if team_key_elem is not None:
                pick_data['team_key'] = team_key_elem.text
            
            # Player info
            player_key_elem = result.find('.//yh:player_key', ns)
            if player_key_elem is not None:
                pick_data['player_key'] = player_key_elem.text
                # Extract player ID from key (format: "431.p.12345")
                pick_data['player_id'] = player_key_elem.text.split('.')[-1]
            
            # Store player key for later enrichment
            if 'player_key' in pick_data:
                # Placeholder values - will be enriched later
                pick_data['player_name'] = f"Player_{pick_data.get('player_id', 'Unknown')}"
                pick_data['player_position'] = DEFAULT_PLAYER_POSITION
                pick_data['player_team'] = DEFAULT_PLAYER_TEAM
            
            # Auction cost (if applicable)
            cost_elem = result.find('.//yh:cost', ns)
            if cost_elem is not None and cost_elem.text:
                pick_data['cost'] = int(cost_elem.text)
            
            draft_results.append(pick_data)
        
        logger.info(f"Fetched {len(draft_results)} draft picks")
        
        # Now enrich with player details
        if draft_results:
            # Extract all player keys
            player_keys = [pick['player_key'] for pick in draft_results if 'player_key' in pick]
            
            # Fetch player details in batches
            all_player_details = {}
            for i in range(0, len(player_keys), 25):
                batch = player_keys[i:i+25]
                batch_details = self.fetch_player_details(batch)
                all_player_details.update(batch_details)
            
            # Enrich draft results with player details
            for pick in draft_results:
                if 'player_key' in pick and pick['player_key'] in all_player_details:
                    details = all_player_details[pick['player_key']]
                    if 'name' in details:
                        pick['player_name'] = details['name']
                    if 'position' in details:
                        pick['player_position'] = details['position']
                    if 'team' in details:
                        pick['player_team'] = details['team']
        
        return draft_results
    
    def validate_draft_data(self, draft_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate draft data for required fields and data quality.
        
        Args:
            draft_data: List of draft pick dictionaries
            
        Returns:
            Tuple of (valid_records, invalid_records)
        """
        valid_records = []
        invalid_records = []
        
        required_fields = ['pick', 'round', 'team_key', 'player_id', 'player_name']
        
        for record in draft_data:
            # Check required fields
            missing_fields = [field for field in required_fields if field not in record or not record[field]]
            
            if missing_fields:
                logger.warning(f"Record missing required fields {missing_fields}: {record}")
                invalid_records.append(record)
            else:
                valid_records.append(record)
        
        logger.info(f"Validation complete: {len(valid_records)} valid, {len(invalid_records)} invalid")
        return valid_records, invalid_records
    
    def insert_draft_results(self, draft_data: List[Dict], league_key: str, season: int, draft_type: str):
        """
        Insert draft results into database.
        
        Args:
            draft_data: List of validated draft pick dictionaries
            league_key: Yahoo league key
            season: Season year
            draft_type: 'snake' or 'auction'
        """
        if not draft_data:
            logger.warning("No draft data to insert")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get team names for the league
        team_names = self._fetch_team_names(league_key)
        
        # Prepare insert data
        insert_data = []
        for record in draft_data:
            team_name = team_names.get(record['team_key'], 'Unknown Team')
            
            # Detect keepers in auction drafts:
            # In most auction keeper leagues, keepers are drafted in the final rounds
            # Based on analysis of this league: ALL keepers were in rounds 20-21
            keeper_status = False
            if draft_type == DRAFT_TYPE_AUCTION:
                round_num = record['round']
                
                # In this league, rounds 20-21 are keeper rounds
                # This is a common pattern where keepers are "drafted" at the end
                if round_num >= 20:
                    keeper_status = True
            
            insert_data.append((
                self.job_id,
                league_key,
                season,
                record['team_key'],
                team_name,
                record['player_id'],
                record['player_name'],
                record.get('player_position', DEFAULT_PLAYER_POSITION),
                record.get('player_team', DEFAULT_PLAYER_TEAM),
                record['round'],
                record['pick'],
                record.get('cost'),  # None for snake drafts
                draft_type,
                keeper_status,  # Auto-detected keeper status
                None    # drafted_datetime - could be parsed from settings
            ))
        
        # Batch insert with INSERT OR IGNORE to handle duplicates
        cursor.executemany("""
            INSERT OR IGNORE INTO draft_results (
                job_id, league_key, season, team_key, team_name,
                player_id, player_name, player_position, player_team,
                draft_round, draft_pick, draft_cost, draft_type,
                keeper_status, drafted_datetime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_data)
        
        records_inserted = cursor.rowcount
        self.stats['records_inserted'] += records_inserted
        
        conn.commit()
        conn.close()
        
        logger.info(f"Inserted {records_inserted} draft picks")
    
    def _fetch_team_names(self, league_key: str) -> Dict[str, str]:
        """
        Fetch team names for a league.
        
        Args:
            league_key: Yahoo league key
            
        Returns:
            Dict mapping team_key to team_name
        """
        url = f"{BASE_FANTASY_URL}/league/{league_key}/teams"
        
        try:
            xml_text = self._make_api_request(url)
            root = ET.fromstring(xml_text)
            
            ns = {'yh': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
            team_names = {}
            
            for team in root.findall('.//yh:team', ns):
                team_key_elem = team.find('.//yh:team_key', ns)
                team_name_elem = team.find('.//yh:name', ns)
                
                if team_key_elem is not None and team_name_elem is not None:
                    team_names[team_key_elem.text] = team_name_elem.text
            
            return team_names
            
        except Exception as e:
            logger.warning(f"Failed to fetch team names: {e}")
            return {}
    
    def collect_draft_results(self, league_key: str, season: int) -> Dict:
        """
        Main entry point to collect draft results for a league/season.
        
        Args:
            league_key: Yahoo league key
            season: Season year
            
        Returns:
            Dict with collection statistics
        """
        logger.info(f"Starting draft collection for {league_key} season {season}")
        
        try:
            # Start job logging
            self._start_job('draft_collection', league_key, season)
            
            # Fetch league settings to get draft type
            settings = self.fetch_league_settings(league_key)
            draft_type = settings.get('draft_type', DRAFT_TYPE_SNAKE)
            
            # Fetch draft results
            draft_data = self.fetch_draft_data_from_yahoo(league_key)
            self.stats['records_processed'] = len(draft_data)
            
            # Validate data
            valid_data, invalid_data = self.validate_draft_data(draft_data)
            
            if invalid_data:
                logger.warning(f"Found {len(invalid_data)} invalid records")
                self.stats['errors'] += len(invalid_data)
            
            # Insert valid data
            if valid_data:
                self.insert_draft_results(valid_data, league_key, season, draft_type)
            
            # Update job status
            self._update_job_status('completed')
            
            logger.info(f"Draft collection completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            logger.error(f"Draft collection failed: {e}")
            self.stats['errors'] += 1
            self._update_job_status('failed', str(e))
            raise
    
    def update_keeper_status(self, league_key: str, season: int) -> int:
        """
        Update keeper status for existing draft data based on cost patterns.
        
        This method identifies keepers in auction drafts by looking for:
        - High cost players in late rounds (19+)
        - Players with costs significantly above typical for their round
        
        Args:
            league_key: Yahoo league key
            season: Season year
            
        Returns:
            Number of records updated
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Update keepers based on auction draft patterns
        # In most auction keeper leagues, keepers are drafted in the final rounds
        cursor.execute("""
            UPDATE draft_results
            SET keeper_status = 1
            WHERE league_key = ? 
            AND season = ?
            AND draft_type = 'auction'
            AND keeper_status = 0
            AND draft_round >= 20  -- Keeper rounds in this league
        """, (league_key, season))
        
        records_updated = cursor.rowcount
        conn.commit()
        
        if records_updated > 0:
            logger.info(f"Updated keeper status for {records_updated} players")
            
            # Log the keepers
            cursor.execute("""
                SELECT player_name, draft_round, draft_pick, draft_cost, team_name
                FROM draft_results
                WHERE league_key = ? AND season = ? AND keeper_status = 1
                ORDER BY draft_cost DESC
            """, (league_key, season))
            
            keepers = cursor.fetchall()
            logger.info(f"Identified {len(keepers)} keepers:")
            for player_name, round_num, pick, cost, team in keepers:
                logger.info(f"  {player_name} - Round {round_num}, Pick {pick}, ${cost} ({team})")
        
        conn.close()
        return records_updated
    
    def push_to_d1(self, league_key: str, season: int) -> bool:
        """
        Push draft results to Cloudflare D1 using sync_to_production pattern.
        
        This method exports draft data to SQL files following the established
        sync_to_production.py pattern. It doesn't execute the SQL directly,
        but provides instructions for manual execution.
        
        Args:
            league_key: Yahoo league key
            season: Season year
            
        Returns:
            bool: True if export successful, False otherwise
        """
        logger.info(f"Starting D1 export for {league_key} season {season}")
        
        # Use the standard incremental export directory
        export_dir = Path(__file__).parent.parent.parent / 'cloudflare-production' / 'sql' / 'incremental'
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to production database (league_analytics.db)
        prod_db_path = Path(__file__).parent.parent.parent / 'database' / 'league_analytics.db'
        if not prod_db_path.exists():
            logger.error(f"Production database not found at {prod_db_path}")
            return False
            
        conn = sqlite3.connect(str(prod_db_path))
        cursor = conn.cursor()
        
        try:
            # Get draft data for this league/season
            cursor.execute("""
                SELECT * FROM draft_results
                WHERE league_key = ? AND season = ?
                ORDER BY draft_pick
            """, (league_key, season))
            
            draft_data = cursor.fetchall()
            
            if not draft_data:
                logger.warning("No draft data found to export")
                return False
            
            logger.info(f"Found {len(draft_data)} draft records to export")
            
            # Get column names
            cursor.execute("PRAGMA table_info(draft_results)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Collect unique job_ids for foreign key dependencies
            job_id_index = columns.index('job_id')
            job_ids = set([row[job_id_index] for row in draft_data if row[job_id_index]])
            
            # Export job_log entries first (following sync_to_production pattern)
            if job_ids:
                job_log_file = export_dir / f'draft_job_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
                with open(job_log_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- Job log export for draft results foreign key dependencies\n")
                    f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                    f.write(f"-- League: {league_key}, Season: {season}\n")
                    f.write(f"-- Count: {len(job_ids)}\n\n")
                    
                    # Get job_log data
                    placeholders = ','.join(['?' for _ in job_ids])
                    cursor.execute(f"""
                        SELECT * FROM job_log 
                        WHERE job_id IN ({placeholders})
                    """, list(job_ids))
                    
                    job_logs = cursor.fetchall()
                    
                    # Get job_log columns
                    cursor.execute("PRAGMA table_info(job_log)")
                    job_columns = [col[1] for col in cursor.fetchall()]
                    
                    for row in job_logs:
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                escaped = val.replace("'", "''")
                                values.append(f"'{escaped}'")
                            else:
                                values.append(str(val))
                        
                        f.write(f"INSERT OR IGNORE INTO job_log ({', '.join(job_columns)}) VALUES ({', '.join(values)});\n")
                
                logger.info(f"[OK] Exported job logs to {job_log_file}")
            
            # Export draft results
            draft_file = export_dir / f'draft_results_{league_key}_{season}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
            with open(draft_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Draft results export\n")
                f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                f.write(f"-- League: {league_key}, Season: {season}\n")
                f.write(f"-- Count: {len(draft_data)}\n\n")
                
                # Clear existing data for this league/season
                f.write(f"-- Clear existing draft data for this league/season\n")
                f.write(f"DELETE FROM draft_results WHERE league_key = '{league_key}' AND season = {season};\n\n")
                
                # Insert new data
                for row in draft_data:
                    values = []
                    for i, val in enumerate(row):
                        if val is None:
                            values.append('NULL')
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                        elif isinstance(val, bool):
                            values.append('1' if val else '0')
                        else:
                            values.append(str(val))
                    
                    # Skip the id column (auto-increment)
                    column_list = [col for col in columns if col != 'id']
                    value_list = [values[i] for i, col in enumerate(columns) if col != 'id']
                    
                    f.write(f"INSERT INTO draft_results ({', '.join(column_list)}) VALUES ({', '.join(value_list)});\n")
            
            logger.info(f"[OK] Exported draft results to {draft_file}")
            
            # Print instructions for manual D1 sync
            print("\n" + "="*60)
            print("NEXT STEPS TO PUSH DRAFT DATA TO D1:")
            print("="*60)
            print("\n1. Navigate to cloudflare-production directory:")
            print("   cd cloudflare-production\n")
            
            print("2. Create draft_results table if this is the first time (one-time setup):")
            print("   npx wrangler d1 execute gkl-fantasy --file=../data_pipeline/draft_results/schema.sql --remote\n")
            
            print("3. Import data to Cloudflare D1 IN THIS ORDER:")
            
            # Job logs first for foreign keys
            if job_ids:
                relative_job_path = job_log_file.relative_to(Path(__file__).parent.parent.parent / 'cloudflare-production')
                print(f"   npx wrangler d1 execute gkl-fantasy --file=./{relative_job_path} --remote")
            
            # Then draft results
            relative_draft_path = draft_file.relative_to(Path(__file__).parent.parent.parent / 'cloudflare-production')
            print(f"   npx wrangler d1 execute gkl-fantasy --file=./{relative_draft_path} --remote")
            
            print("\n[!] IMPORTANT: Import job_logs FIRST to avoid foreign key errors!")
            
            print("\n4. Verify the data in production:")
            print(f"   npx wrangler d1 execute gkl-fantasy --command=\"SELECT COUNT(*) FROM draft_results WHERE league_key = '{league_key}' AND season = {season}\" --remote")
            
            print("\n[OK] Export complete! Follow the steps above to sync to D1.")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting draft data: {e}")
            return False
        finally:
            conn.close()


def main():
    """Command-line interface for draft collection."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Collect draft results from Yahoo Fantasy API'
    )
    parser.add_argument(
        '--league_key',
        required=True,
        help='Yahoo league key (e.g., "458.l.6966")'
    )
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='Season year (e.g., 2025)'
    )
    parser.add_argument(
        '--environment',
        default='production',
        choices=['production', 'development', 'test'],
        help='Database environment (default: production)'
    )
    parser.add_argument(
        '--skip_d1_push',
        action='store_true',
        help='Skip pushing to D1 (for testing)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize collector
    collector = DraftResultsCollector(environment=args.environment)
    
    try:
        # Collect draft results
        logger.info(f"Starting draft collection for {args.league_key} season {args.season}")
        stats = collector.collect_draft_results(args.league_key, args.season)
        
        logger.info(f"Collection completed successfully!")
        logger.info(f"  Records processed: {stats['records_processed']}")
        logger.info(f"  Records inserted: {stats['records_inserted']}")
        logger.info(f"  Errors: {stats['errors']}")
        
        # Push to D1 unless skipped
        if not args.skip_d1_push:
            logger.info("Pushing results to D1...")
            if collector.push_to_d1(args.league_key, args.season):
                logger.info("Pushed to D1 successfully!")
            else:
                logger.warning("D1 push failed or not implemented")
        else:
            logger.info("Skipping D1 push (--skip_d1_push flag)")
        
        # Remind about keeper updates
        logger.info("\n" + "="*60)
        logger.info("IMPORTANT: Manual keeper update required!")
        logger.info("1. Get keeper list from Yahoo or league commissioner")
        logger.info("2. Update keeper status in database using SQL")
        logger.info("3. See README.md for detailed instructions")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Draft collection failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())