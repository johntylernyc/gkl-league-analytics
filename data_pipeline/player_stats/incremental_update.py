"""
Incremental update for MLB stats with stat correction detection.
Handles retroactive stat corrections from official MLB sources.
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

# Import change tracking utilities
sys.path.append(str(parent_dir / 'scripts'))
from change_tracking import ChangeTracker, RefreshStrategy

# Constants
STAT_CORRECTION_WINDOW = 7  # Check for corrections within 7 days
DB_PATH = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
LEAGUE_KEY = 'mlb.l.6966'  # 2025 season


class PlayerStatsIncrementalUpdater:
    """Incremental updater for player stats with stat correction detection."""
    
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
        print("[DEBUG STATS] Attempting to import YahooTokenManager...")
        from auth.token_manager import YahooTokenManager
        print("[DEBUG STATS] Import successful, initializing token manager...")
        self.token_manager = YahooTokenManager()
        print("[DEBUG STATS] Token manager initialized successfully")
        self.job_id = None
        self.stats = {
            'new': 0,
            'updated': 0,
            'corrections': 0,
            'unchanged': 0,
            'checked': 0,
            'errors': 0
        }
    
        
    def start_job_log(self, date_range_start: str, date_range_end: str) -> str:
        """Start a job log entry."""
        cursor = self.conn.cursor()
        job_id = f"stats_incremental_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                date_range_start, date_range_end,
                start_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            job_id, 'stats_incremental', self.environment, 'running',
            date_range_start, date_range_end,
            json.dumps({'correction_window': STAT_CORRECTION_WINDOW})
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
            self.stats['new'] + self.stats['updated'] + self.stats['corrections'],
            error_message,
            json.dumps(self.stats),
            self.job_id
        ))
        self.conn.commit()
    
    def get_existing_stats_for_date(self, date: str) -> Dict[int, Dict]:
        """Get existing stats and hashes for a specific date."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT yahoo_player_id, content_hash, has_correction,
                   batting_hits, batting_runs, batting_rbis
            FROM daily_gkl_player_stats
            WHERE date = ?
              AND has_batting_data = 1
        """, (date,))
        
        existing = {}
        for row in cursor.fetchall():
            player_id, content_hash, has_correction, h, r, rbi = row
            existing[player_id] = {
                'content_hash': content_hash,
                'has_correction': has_correction,
                'stats': {
                    'h': h or 0,
                    'r': r or 0,
                    'rbi': rbi or 0
                }
            }
        
        return existing
    
    def simulate_stats_for_date(self, date: str) -> List[Dict]:
        """
        Fetch player stats for a specific date from Yahoo API.
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            List of player stats dictionaries
        """
        import requests
        import xml.etree.ElementTree as ET
        import re
        from datetime import datetime
        
        # Convert date to determine week number for MLB season
        # For simplicity, we'll fetch all players from the league and their stats
        
        try:
            # Get league players and their stats for the date
            url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{LEAGUE_KEY}/players/stats;type=date;date={date}"
            
            print(f"[DEBUG STATS] Getting access token for date {date}...")
            access_token = self.token_manager.get_access_token()
            print(f"[DEBUG STATS] Access token obtained (length: {len(access_token) if access_token else 0})")
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/xml'
            }
            
            print(f"[DEBUG STATS] Making API request to: {url}")
            response = requests.get(url, headers=headers)
            print(f"[DEBUG STATS] API response status: {response.status_code}")
            
            if response.status_code == 401:
                print(f"[DEBUG STATS] Got 401, attempting token refresh...")
                # Token might have expired, force refresh and retry
                self.token_manager.tokens['access_token'] = None  # Force refresh
                new_token = self.token_manager.get_access_token()
                print(f"[DEBUG STATS] New token obtained (length: {len(new_token) if new_token else 0})")
                headers['Authorization'] = f'Bearer {new_token}'
                response = requests.get(url, headers=headers)
                print(f"[DEBUG STATS] Retry response status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse XML response
                xml_text = re.sub(' xmlns="[^"]+"', '', response.text, count=1)
                root = ET.fromstring(xml_text)
                
                stats_list = []
                
                # Parse player stats
                for player in root.findall(".//player"):
                    player_id = player.findtext("player_id")
                    if not player_id:
                        continue
                        
                    # Extract player stats
                    stats_node = player.find("player_stats")
                    if stats_node is None:
                        continue
                    
                    # Parse individual stats
                    stats = {}
                    for stat in stats_node.findall(".//stat"):
                        stat_id = stat.findtext("stat_id")
                        stat_value = stat.findtext("value", "0")
                        
                        # Convert stat_id to stat name (using common MLB stat IDs)
                        stat_mappings = {
                            '0': 'games_played',
                            '1': 'at_bats', 
                            '2': 'runs',
                            '3': 'hits',
                            '4': 'singles',
                            '5': 'doubles',
                            '6': 'triples', 
                            '7': 'home_runs',
                            '8': 'rbis',
                            '9': 'stolen_bases',
                            '10': 'caught_stealing',
                            '11': 'walks',
                            '12': 'strikeouts'
                        }
                        
                        if stat_id in stat_mappings:
                            stats[stat_mappings[stat_id]] = int(stat_value) if stat_value.isdigit() else 0
                    
                    if stats:  # Only add if we got some stats
                        stats_list.append({
                            'player_id': player_id,
                            'date': date,
                            'stats': stats
                        })
                
                return stats_list
                
            elif response.status_code == 404:
                # No stats data for this date - this is normal
                return []
            else:
                print(f"[WARN] Failed to fetch stats for {date}: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[ERROR] Error fetching stats for {date}: {e}")
            self.stats['errors'] += 1
            
            # Fallback to getting existing stats from database for stat correction detection
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT yahoo_player_id, batting_hits, batting_runs, 
                       batting_rbis, batting_home_runs, batting_stolen_bases
                FROM daily_gkl_player_stats
                WHERE date = ?
                  AND has_batting_data = 1
                LIMIT 10
            """, (date,))
            
            stats_list = []
            for row in cursor.fetchall():
                player_id, h, r, rbi, hr, sb = row
                if player_id:  # Skip NULL player IDs
                    stats_list.append({
                        'player_id': player_id,
                        'date': date,
                        'stats': {
                            'hits': h or 0,
                            'runs': r or 0,
                            'rbis': rbi or 0,
                            'home_runs': hr or 0,
                            'stolen_bases': sb or 0
                        }
                    })
            
            return stats_list
    
    def detect_and_log_correction(
        self, player_id: int, date: str, 
        old_stats: Dict, new_stats: Dict, 
        old_hash: str, new_hash: str
    ):
        """Detect and log stat corrections."""
        cursor = self.conn.cursor()
        
        # Compare stats
        corrections = self.tracker.compare_stats(
            {'stats': old_stats},
            {'stats': new_stats}
        )
        
        if corrections:
            print(f"    [CORRECTION] Player {player_id}: {corrections}")
            
            # Log each correction
            for stat_name, correction in corrections.items():
                cursor.execute("""
                    INSERT INTO stat_corrections (
                        player_id, date, stat_category, stat_name,
                        old_value, new_value, difference,
                        correction_source, job_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    player_id, date, 'batting', stat_name,
                    str(correction['old']), str(correction['new']),
                    correction['difference'],
                    'incremental_update', self.job_id
                ))
            
            # Update the has_correction flag
            cursor.execute("""
                UPDATE daily_gkl_player_stats
                SET has_correction = 1,
                    content_hash = ?,
                    batting_hits = ?,
                    batting_runs = ?,
                    batting_rbis = ?
                WHERE date = ? AND yahoo_player_id = ?
            """, (
                new_hash,
                new_stats.get('h', 0),
                new_stats.get('r', 0),
                new_stats.get('rbi', 0),
                date, player_id
            ))
            
            self.stats['corrections'] += 1
    
    def process_player_stats(
        self, stats_data: Dict, existing_data: Dict
    ) -> Dict[str, int]:
        """Process stats for a single player."""
        result = {'new': 0, 'updated': 0, 'unchanged': 0, 'correction': 0}
        
        player_id = stats_data['player_id']
        date = stats_data['date']
        
        # Generate hash for new stats
        new_hash = self.tracker.generate_stats_hash(stats_data)
        
        if player_id not in existing_data:
            # New player stats
            result['new'] += 1
            
            # Insert new stats (simplified - in production would insert all fields)
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE daily_gkl_player_stats
                SET content_hash = ?
                WHERE date = ? AND yahoo_player_id = ?
            """, (new_hash, date, player_id))
            
        else:
            # Check for changes
            existing = existing_data[player_id]
            old_hash = existing['content_hash']
            
            if old_hash and old_hash != new_hash:
                # Stats have changed - likely a correction
                result['correction'] += 1
                self.detect_and_log_correction(
                    player_id, date,
                    existing['stats'], stats_data['stats'],
                    old_hash, new_hash
                )
            elif not old_hash:
                # No hash stored yet, update it
                result['updated'] += 1
                cursor = self.conn.cursor()
                cursor.execute("""
                    UPDATE daily_gkl_player_stats
                    SET content_hash = ?
                    WHERE date = ? AND yahoo_player_id = ?
                """, (new_hash, date, player_id))
            else:
                # No changes
                result['unchanged'] += 1
        
        return result
    
    def process_date(self, date: str) -> int:
        """Process stats for a specific date."""
        # Determine if we should check for corrections
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_old = (datetime.now() - date_obj).days
        check_corrections = days_old <= STAT_CORRECTION_WINDOW
        
        if check_corrections:
            print(f"\nProcessing stats for {date} (checking for corrections)...")
        else:
            print(f"\nProcessing stats for {date} (archive data)...")
            return 0  # Skip archive data
        
        # Get existing stats
        existing_data = self.get_existing_stats_for_date(date)
        
        # Fetch/simulate current stats
        current_stats = self.simulate_stats_for_date(date)
        
        if not current_stats:
            print(f"  No stats found for {date}")
            return 0
        
        processed = 0
        for stats_data in current_stats:
            result = self.process_player_stats(stats_data, existing_data)
            
            self.stats['new'] += result['new']
            self.stats['updated'] += result['updated']
            self.stats['unchanged'] += result['unchanged']
            self.stats['corrections'] += result['correction']
            self.stats['checked'] += 1
            processed += 1
        
        self.conn.commit()
        return processed
    
    def run(self, start_date: str = None, end_date: str = None):
        """
        Run incremental update for player stats.
        
        Args:
            start_date: Start date (default: 7 days ago)
            end_date: End date (default: today)
        """
        # Default date range
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            # Go back to correction window
            start_date = (datetime.now() - timedelta(days=STAT_CORRECTION_WINDOW)).strftime('%Y-%m-%d')
        
        print("\n" + "="*60)
        print("PLAYER STATS INCREMENTAL UPDATE")
        print("="*60)
        print(f"Date range: {start_date} to {end_date}")
        print(f"Environment: {self.environment}")
        print(f"Stat correction window: {STAT_CORRECTION_WINDOW} days")
        
        # Start job logging
        self.start_job_log(start_date, end_date)
        print(f"Job ID: {self.job_id}")
        
        try:
            # Process each date
            current = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                self.process_date(date_str)
                current += timedelta(days=1)
                
                # Rate limiting
                time.sleep(0.1)
            
            # Update job status
            self.update_job_log('completed')
            
            print("\n" + "="*60)
            print("UPDATE SUMMARY")
            print("="*60)
            print(f"Stats checked: {self.stats['checked']}")
            print(f"New stats: {self.stats['new']}")
            print(f"Updated stats: {self.stats['updated']}")
            print(f"Stat corrections: {self.stats['corrections']}")
            print(f"Unchanged stats: {self.stats['unchanged']}")
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
    
    parser = argparse.ArgumentParser(description="Incremental update for player stats")
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'],
                       help='Environment to run in')
    
    args = parser.parse_args()
    
    # Run the updater
    updater = PlayerStatsIncrementalUpdater(environment=args.environment)
    updater.run(args.start_date, args.end_date)


if __name__ == "__main__":
    main()