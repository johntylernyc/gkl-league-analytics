"""
Incremental update script for daily lineups with change detection.
Fetches new data and updates existing data that has changed.
"""

import sys
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Import with absolute path
sys.path.append(str(parent_dir / 'scripts'))
from change_tracking import ChangeTracker, RefreshStrategy

from auth.config import SEASON_DATES

# Constants
FORCE_REFRESH_DAYS = 3  # Always refresh recent data
DB_PATH = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
LEAGUE_KEY = 'mlb.l.6966'  # 2025 season


class DailyLineupIncrementalUpdater:
    """Incremental updater for daily lineups with change detection."""
    
    def __init__(self, environment='production'):
        """
        Initialize the updater.
        
        Args:
            environment: 'test' or 'production'
        """
        self.environment = environment
        self.conn = sqlite3.connect(str(DB_PATH))
        self.tracker = ChangeTracker()
        self.strategy = RefreshStrategy()
        # Use standardized token manager
        print("[DEBUG LINEUP] Attempting to import YahooTokenManager...")
        from auth.token_manager import YahooTokenManager
        print("[DEBUG LINEUP] Import successful, initializing token manager...")
        self.token_manager = YahooTokenManager()
        print("[DEBUG LINEUP] Token manager initialized successfully")
        self.job_id = None
        self.stats = {
            'new': 0,
            'updated': 0,
            'unchanged': 0,
            'checked': 0,
            'errors': 0
        }
        
    
    def start_job_log(self, date_range_start: str, date_range_end: str) -> str:
        """Start a job log entry."""
        cursor = self.conn.cursor()
        job_id = f"lineup_incremental_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                date_range_start, date_range_end, league_key,
                start_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            job_id, 'lineup_incremental', self.environment, 'running',
            date_range_start, date_range_end, LEAGUE_KEY,
            json.dumps({'update_type': 'incremental_with_changes'})
        ))
        self.conn.commit()
        
        self.job_id = job_id
        return job_id
    
    def update_job_log(self, status: str, error_message: str = None):
        """Update job log with final status."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE job_log
            SET status = ?,
                end_time = datetime('now'),
                records_processed = ?,
                records_inserted = ?,
                error_message = ?,
                metadata = ?
            WHERE job_id = ?
        """, (
            status,
            self.stats['checked'],
            self.stats['new'] + self.stats['updated'],
            error_message,
            json.dumps(self.stats),
            self.job_id
        ))
        self.conn.commit()
    
    def get_existing_lineup_metadata(
        self, start_date: str, end_date: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get existing lineup metadata from database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date, team_key, content_hash, last_fetched
            FROM daily_lineups_metadata
            WHERE date BETWEEN ? AND ?
            ORDER BY date, team_key
        """, (start_date, end_date))
        
        metadata = {}
        for row in cursor.fetchall():
            date, team_key, content_hash, last_fetched = row
            if date not in metadata:
                metadata[date] = {}
            metadata[date][team_key] = {
                'content_hash': content_hash,
                'last_fetched': datetime.fromisoformat(last_fetched) if last_fetched else None
            }
        
        return metadata
    
    def fetch_lineups_from_yahoo(self, date: str) -> List[Dict[str, Any]]:
        """
        Fetch lineups for a specific date from Yahoo API.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of lineup dictionaries
        """
        import requests
        import xml.etree.ElementTree as ET
        import re
        
        # Get all team keys from our league
        team_keys = [
            '458.l.6966.t.1', '458.l.6966.t.10', '458.l.6966.t.11', '458.l.6966.t.12',
            '458.l.6966.t.13', '458.l.6966.t.14', '458.l.6966.t.15', '458.l.6966.t.16', '458.l.6966.t.17'
        ]
        
        all_lineups = []
        
        for team_key in team_keys:
            try:
                # Yahoo API roster endpoint for specific date
                url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;date={date}"
                
                print(f"[DEBUG LINEUP] Getting access token for team {team_key}...")
                access_token = self.token_manager.get_access_token()
                print(f"[DEBUG LINEUP] Access token obtained (length: {len(access_token) if access_token else 0})")
                
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/xml'
                }
                
                print(f"[DEBUG LINEUP] Making API request to: {url}")
                response = requests.get(url, headers=headers)
                print(f"[DEBUG LINEUP] API response status: {response.status_code}")
                
                if response.status_code == 401:
                    print(f"[DEBUG LINEUP] Got 401, attempting token refresh...")
                    # Token might have expired, force refresh and retry
                    self.token_manager.tokens['access_token'] = None  # Force refresh
                    new_token = self.token_manager.get_access_token()
                    print(f"[DEBUG LINEUP] New token obtained (length: {len(new_token) if new_token else 0})")
                    headers['Authorization'] = f'Bearer {new_token}'
                    response = requests.get(url, headers=headers)
                    print(f"[DEBUG LINEUP] Retry response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Parse XML response
                    xml_text = re.sub(' xmlns="[^"]+"', '', response.text, count=1)
                    root = ET.fromstring(xml_text)
                    
                    # Extract team name
                    team_name = root.findtext(".//team/name", "Unknown Team")
                    
                    # Parse roster players
                    for player in root.findall(".//player"):
                        player_id = player.findtext("player_id")
                        name_full = player.findtext("name/full", "Unknown Player")
                        
                        # Get selected position
                        selected_position = player.findtext("selected_position/position", "BN")
                        position_type = "B" if selected_position == "BN" else "S"  # Bench or Starter
                        
                        # Get eligible positions
                        eligible_positions = []
                        for pos in player.findall(".//eligible_positions/position"):
                            eligible_positions.append(pos.text)
                        eligible_positions_str = ",".join(eligible_positions)
                        
                        # Get player status (if available)
                        player_status = player.findtext("status", "")
                        
                        # Get player team (MLB team)
                        player_team = player.findtext("editorial_team_abbr", "")
                        
                        lineup_data = {
                            'date': date,
                            'team_key': team_key,
                            'team_name': team_name,
                            'player_id': player_id,
                            'player_name': name_full,
                            'selected_position': selected_position,
                            'position_type': position_type,
                            'player_status': player_status,
                            'eligible_positions': eligible_positions_str,
                            'player_team': player_team
                        }
                        
                        all_lineups.append(lineup_data)
                        
                elif response.status_code == 404:
                    # No roster data for this date/team - this is normal
                    continue
                else:
                    print(f"[WARN] Failed to fetch lineup for team {team_key} on {date}: Status {response.status_code}")
                    
            except Exception as e:
                print(f"[ERROR] Error fetching lineup for team {team_key} on {date}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Group lineups by team
        lineups_by_team = {}
        for lineup_data in all_lineups:
            team_key = lineup_data['team_key']
            if team_key not in lineups_by_team:
                lineups_by_team[team_key] = {
                    'team_key': team_key,
                    'team_name': lineup_data['team_name'],
                    'date': date,
                    'players': []
                }
            
            lineups_by_team[team_key]['players'].append({
                'player_id': lineup_data['player_id'],
                'player_name': lineup_data['player_name'],
                'selected_position': lineup_data['selected_position'],
                'position_type': lineup_data['position_type'],
                'player_status': lineup_data['player_status'],
                'eligible_positions': lineup_data['eligible_positions'],
                'player_team': lineup_data['player_team']
            })
        
        return list(lineups_by_team.values())
    
    
    def get_existing_lineups_from_db(self, date: str) -> List[Dict[str, Any]]:
        """Get existing lineups from database for comparison."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT team_key
            FROM daily_lineups
            WHERE date = ?
        """, (date,))
        
        team_keys = [row[0] for row in cursor.fetchall()]
        lineups = []
        
        for team_key in team_keys:
            cursor.execute("""
                SELECT player_id, selected_position
                FROM daily_lineups
                WHERE date = ? AND team_key = ?
                ORDER BY player_id
            """, (date, team_key))
            
            players = []
            for row in cursor.fetchall():
                players.append({
                    'player_id': row[0],
                    'selected_position': row[1],
                    'status': 'active'
                })
            
            if players:
                lineups.append({
                    'date': date,
                    'team_key': team_key,
                    'players': players
                })
        
        return lineups
    
    def should_refresh_lineup(
        self, date: str, team_key: str, existing_metadata: Dict
    ) -> Tuple[bool, str]:
        """Determine if a lineup should be refreshed."""
        # Check if data exists
        if date not in existing_metadata:
            return True, "new_date"
        
        if team_key not in existing_metadata[date]:
            return True, "new_team"
        
        # Check if within force refresh window
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_old = (datetime.now() - date_obj).days
        
        if days_old <= FORCE_REFRESH_DAYS:
            return True, "recent_data"
        
        # Check if fetched before last scheduled update
        last_fetched = existing_metadata[date][team_key]['last_fetched']
        if last_fetched:
            last_scheduled = self.strategy.get_last_scheduled_update()
            if last_fetched < last_scheduled:
                return True, "stale_data"
        
        return False, "up_to_date"
    
    def update_lineup_with_change_detection(
        self, lineup: Dict[str, Any], existing_metadata: Dict
    ) -> Dict[str, int]:
        """Update lineup data with change detection."""
        stats = {'new': 0, 'updated': 0, 'unchanged': 0}
        cursor = self.conn.cursor()
        
        date = lineup['date']
        team_key = lineup['team_key']
        
        # Generate content hash
        content_hash = self.tracker.generate_lineup_hash(lineup)
        
        # Check if lineup exists and has changed
        existing_hash = None
        if date in existing_metadata and team_key in existing_metadata[date]:
            existing_hash = existing_metadata[date][team_key]['content_hash']
        
        if not existing_hash:
            # New lineup
            stats['new'] += 1
            print(f"  [NEW] {team_key} on {date}")
            
            # Insert lineup data
            for player in lineup['players']:
                # Extract season from date (year)
                season = int(date.split('-')[0])
                
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_lineups (
                        job_id, season, date, team_key, team_name,
                        player_id, player_name, selected_position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.job_id, season, date, team_key, 
                    team_key,  # Use team_key as team_name for now
                    str(player['player_id']), 
                    f"Player_{player['player_id']}",  # Placeholder name
                    player['selected_position']
                ))
            
            # Insert metadata
            cursor.execute("""
                INSERT OR REPLACE INTO daily_lineups_metadata (
                    date, team_key, content_hash, last_fetched, job_id
                ) VALUES (?, ?, ?, datetime('now'), ?)
            """, (date, team_key, content_hash, self.job_id))
            
        elif existing_hash != content_hash:
            # Lineup has changed
            stats['updated'] += 1
            print(f"  [UPDATED] {team_key} on {date}")
            
            # Get the old lineup for comparison
            old_lineup = {
                'date': date,
                'team_key': team_key,
                'players': []
            }
            
            cursor.execute("""
                SELECT player_id, selected_position
                FROM daily_lineups
                WHERE date = ? AND team_key = ?
            """, (date, team_key))
            
            for row in cursor.fetchall():
                old_lineup['players'].append({
                    'player_id': row[0],
                    'selected_position': row[1]
                })
            
            # Get detailed changes
            changes = self.tracker.compare_lineups(old_lineup, lineup)
            
            # Log the change
            cursor.execute("""
                INSERT INTO lineup_changes (
                    date, team_key, old_hash, new_hash,
                    change_type, players_added, players_removed,
                    position_changes, job_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date, team_key, existing_hash, content_hash,
                'modified', 
                json.dumps(changes['players_added']),
                json.dumps(changes['players_removed']),
                json.dumps(changes['position_changes']),
                self.job_id
            ))
            
            # Delete existing lineup entries
            cursor.execute("""
                DELETE FROM daily_lineups
                WHERE date = ? AND team_key = ?
            """, (date, team_key))
            
            # Insert updated lineup data
            for player in lineup['players']:
                # Extract season from date (year)
                season = int(date.split('-')[0])
                
                cursor.execute("""
                    INSERT INTO daily_lineups (
                        job_id, season, date, team_key, team_name,
                        player_id, player_name, selected_position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.job_id, season, date, team_key,
                    team_key,  # Use team_key as team_name for now
                    str(player['player_id']),
                    f"Player_{player['player_id']}",  # Placeholder name
                    player['selected_position']
                ))
            
            # Update metadata
            cursor.execute("""
                UPDATE daily_lineups_metadata
                SET content_hash = ?, last_fetched = datetime('now'), job_id = ?
                WHERE date = ? AND team_key = ?
            """, (content_hash, self.job_id, date, team_key))
            
        else:
            # No changes
            stats['unchanged'] += 1
            
            # Still update last_fetched timestamp
            cursor.execute("""
                UPDATE daily_lineups_metadata
                SET last_fetched = datetime('now')
                WHERE date = ? AND team_key = ?
            """, (date, team_key))
        
        self.conn.commit()
        return stats
    
    def process_date(self, date: str, existing_metadata: Dict) -> int:
        """Process lineups for a specific date."""
        print(f"\nProcessing lineups for {date}...")
        
        # Fetch current lineups from Yahoo API
        lineups = self.fetch_lineups_from_yahoo(date)
        
        if not lineups:
            print(f"  No lineups found for {date}")
            return 0
        
        processed = 0
        for lineup in lineups:
            team_key = lineup['team_key']
            
            # Check if should refresh
            should_refresh, reason = self.should_refresh_lineup(
                date, team_key, existing_metadata
            )
            
            if should_refresh:
                print(f"  Refreshing {team_key}: {reason}")
                stats = self.update_lineup_with_change_detection(
                    lineup, existing_metadata
                )
                
                self.stats['new'] += stats['new']
                self.stats['updated'] += stats['updated']
                self.stats['unchanged'] += stats['unchanged']
                processed += 1
            
            self.stats['checked'] += 1
        
        return processed
    
    def run(self, start_date: str = None, end_date: str = None):
        """
        Run incremental update for daily lineups.
        
        Args:
            start_date: Start date (default: 3 days ago)
            end_date: End date (default: today)
        """
        # Default date range
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=FORCE_REFRESH_DAYS)).strftime('%Y-%m-%d')
        
        print("\n" + "="*60)
        print("DAILY LINEUPS INCREMENTAL UPDATE")
        print("="*60)
        print(f"Date range: {start_date} to {end_date}")
        print(f"Environment: {self.environment}")
        print(f"Force refresh window: {FORCE_REFRESH_DAYS} days")
        
        # Start job logging
        self.start_job_log(start_date, end_date)
        print(f"Job ID: {self.job_id}")
        
        try:
            # Get existing metadata
            print("\nLoading existing metadata...")
            existing_metadata = self.get_existing_lineup_metadata(start_date, end_date)
            print(f"Found metadata for {len(existing_metadata)} dates")
            
            # Process each date
            current = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                self.process_date(date_str, existing_metadata)
                current += timedelta(days=1)
                
                # Rate limiting
                time.sleep(0.1)  # Small delay between dates
            
            # Update job status
            self.update_job_log('completed')
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            print(f"Lineups checked: {self.stats['checked']}")
            print(f"New lineups: {self.stats['new']}")
            print(f"Updated lineups: {self.stats['updated']}")
            print(f"Unchanged lineups: {self.stats['unchanged']}")
            print(f"Errors: {self.stats['errors']}")
            print("="*60)
            
        except Exception as e:
            print(f"\n[ERROR] Update failed: {e}")
            import traceback
            traceback.print_exc()
            self.update_job_log('failed', str(e))
            raise
        finally:
            self.conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Incremental update for daily lineups")
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'],
                       help='Environment to run in')
    parser.add_argument('--force-refresh', action='store_true',
                       help='Force refresh all data regardless of age')
    
    args = parser.parse_args()
    
    # Run the updater
    updater = DailyLineupIncrementalUpdater(environment=args.environment)
    updater.run(args.start_date, args.end_date)


if __name__ == "__main__":
    main()