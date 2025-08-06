#!/usr/bin/env python3
"""
Collect daily (game-by-game) player stats from Yahoo Fantasy API - FIXED stat mappings
"""

import sys
import json
import sqlite3
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import logging
import time

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from auth.token_manager import YahooTokenManager
from data_pipeline.player_stats.config import get_config_for_environment
from data_pipeline.player_stats.job_manager import PlayerStatsJobManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LEAGUE_KEY = '458.l.6966'  # 2025 season

# CORRECTED Yahoo stat ID mappings for daily baseball stats
DAILY_STAT_ID_MAP = {
    # Batting stats
    '7': 'runs',          # R
    '8': 'hits',          # H  
    '10': 'doubles',      # 2B
    '11': 'triples',      # 3B
    '12': 'home_runs',    # HR
    '13': 'rbis',         # RBI
    '16': 'stolen_bases', # SB
    '18': 'walks',        # BB
    '21': 'strikeouts',   # K (batting)
    '60': 'at_bats_hits', # H/AB format (e.g., "4/6" means 4 hits in 6 at-bats)
    
    # Pitching stats
    '24': 'wins',         # W
    '25': 'losses',       # L
    '26': 'games',        # G (pitching)
    '27': 'games_started',# GS
    '28': 'complete_games',# CG
    '32': 'saves',        # SV
    '42': 'strikeouts_p', # K (pitching)
    '48': 'holds',        # HLD
    '50': 'innings_pitched', # IP
}


class DailyStatsCollector:
    """Collect daily player stats from Yahoo Fantasy API"""
    
    def __init__(self, environment='test'):
        self.environment = environment
        self.token_manager = YahooTokenManager()
        self.config = get_config_for_environment(environment)
        self.conn = sqlite3.connect(self.config['database_path'])
        self.job_manager = PlayerStatsJobManager(environment=environment)
        
    def fetch_all_teams(self):
        """Fetch all team keys in the league"""
        logger.info("Fetching all teams in league...")
        
        access_token = self.token_manager.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/xml'
        }
        
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{LEAGUE_KEY}/teams"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch teams: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        teams = []
        for team in root.findall('.//fantasy:team', ns):
            team_key = team.find('.//fantasy:team_key', ns)
            team_name = team.find('.//fantasy:name', ns)
            if team_key is not None:
                teams.append({
                    'team_key': team_key.text,
                    'team_name': team_name.text if team_name is not None else 'Unknown'
                })
        
        logger.info(f"Found {len(teams)} teams")
        return teams
    
    def fetch_team_stats_for_date(self, team_key, date_str):
        """Fetch all players and their stats for a team on a specific date"""
        access_token = self.token_manager.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/xml'
        }
        
        # Use the roster endpoint with date parameter
        url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;date={date_str}/players/stats;type=date;date={date_str}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch team {team_key} stats: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        ns = {'fantasy': 'http://fantasysports.yahooapis.com/fantasy/v2/base.rng'}
        
        players_data = []
        
        # Find all players
        for player in root.findall('.//fantasy:player', ns):
            player_data = self.parse_daily_player_data(player, ns, date_str)
            if player_data:
                players_data.append(player_data)
        
        return players_data
    
    def parse_daily_player_data(self, player_elem, ns, date_str):
        """Parse daily player data from XML element"""
        player_data = {
            'date': date_str,
            'yahoo_player_id': None,
            'name': None,
            'team_code': None,
            'position': None,
            'batting_stats': {},
            'pitching_stats': {},
            'games_played': 0
        }
        
        # Get player ID
        player_key = player_elem.find('.//fantasy:player_key', ns)
        if player_key is not None:
            player_data['yahoo_player_id'] = player_key.text.split('.')[-1]
        
        # Get player name
        name = player_elem.find('.//fantasy:name/fantasy:full', ns)
        if name is not None:
            player_data['name'] = name.text
        
        # Get team
        editorial_team = player_elem.find('.//fantasy:editorial_team_abbr', ns)
        if editorial_team is not None:
            player_data['team_code'] = editorial_team.text
        
        # Get positions
        positions = []
        for pos in player_elem.findall('.//fantasy:eligible_positions/fantasy:position', ns):
            if pos.text and pos.text not in ['BN', 'IL', 'IL+', 'NA']:
                positions.append(pos.text)
        player_data['position'] = ','.join(positions) if positions else 'UTIL'
        
        # Check if player is a pitcher
        is_pitcher = any(p in ['SP', 'RP', 'P'] for p in positions)
        
        # Get daily stats
        player_stats = player_elem.find('.//fantasy:player_stats', ns)
        if player_stats is not None:
            # Verify this is daily stats
            coverage_type = player_stats.find('.//fantasy:coverage_type', ns)
            if coverage_type is not None and coverage_type.text == 'date':
                stats_date = player_stats.find('.//fantasy:date', ns)
                if stats_date is not None and stats_date.text == date_str:
                    # Parse the stats
                    for stat in player_stats.findall('.//fantasy:stats/fantasy:stat', ns):
                        stat_id_elem = stat.find('fantasy:stat_id', ns)
                        value_elem = stat.find('fantasy:value', ns)
                        
                        if stat_id_elem is not None and value_elem is not None:
                            stat_id = stat_id_elem.text
                            value = value_elem.text
                            
                            if stat_id in DAILY_STAT_ID_MAP and value and value != '-':
                                stat_name = DAILY_STAT_ID_MAP[stat_id]
                                
                                # Special handling for H/AB format (stat ID 60)
                                if stat_id == '60' and '/' in value:
                                    parts = value.split('/')
                                    if len(parts) == 2:
                                        try:
                                            at_bats = int(parts[1])  # Second part is AB
                                            hits = int(parts[0])     # First part is H
                                            player_data['batting_stats']['at_bats'] = at_bats
                                            # Don't override hits if we already have it from stat ID 8
                                            if 'hits' not in player_data['batting_stats']:
                                                player_data['batting_stats']['hits'] = hits
                                            if at_bats > 0:
                                                player_data['games_played'] = 1
                                        except ValueError:
                                            pass
                                # Pitching stats
                                elif stat_name in ['wins', 'losses', 'games', 'games_started', 
                                                 'complete_games', 'saves', 'strikeouts_p', 
                                                 'holds', 'innings_pitched']:
                                    try:
                                        if stat_name == 'innings_pitched':
                                            # Handle innings like "6.0" or "6.2"
                                            player_data['pitching_stats'][stat_name] = float(value)
                                        else:
                                            player_data['pitching_stats'][stat_name] = int(value)
                                        
                                        if stat_name == 'games' and int(value) > 0:
                                            player_data['games_played'] = 1
                                    except ValueError:
                                        pass
                                # Batting stats
                                else:
                                    try:
                                        player_data['batting_stats'][stat_name] = int(value)
                                    except ValueError:
                                        pass
        
        return player_data
    
    def save_daily_stats(self, all_players_data, date_str):
        """Save daily stats to database"""
        cursor = self.conn.cursor()
        
        # Start a job
        job_id = self.job_manager.start_job(
            job_type='stats_daily_collection',
            date_range_start=date_str,
            date_range_end=date_str,
            league_key=LEAGUE_KEY,
            metadata={'source': 'yahoo_daily_api', 'player_count': len(all_players_data)}
        )
        
        records_inserted = 0
        players_with_stats = 0
        errors = []
        
        for player in all_players_data:
            # Skip if player didn't play
            if player['games_played'] == 0:
                continue
            
            players_with_stats += 1
            
            try:
                batting = player['batting_stats']
                pitching = player['pitching_stats']
                
                # Calculate batting average for the day
                batting_avg = 0.0
                if batting.get('at_bats', 0) > 0 and 'hits' in batting:
                    batting_avg = batting['hits'] / batting['at_bats']
                
                # Determine if player has data
                has_batting = len(batting) > 0
                has_pitching = len(pitching) > 0
                
                # Insert into player stats table
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {self.config['gkl_player_stats_table']} (
                        job_id, date, yahoo_player_id, player_name, team_code, position_codes,
                        games_played, has_batting_data, has_pitching_data,
                        batting_at_bats, batting_runs, batting_hits, batting_rbis,
                        batting_home_runs, batting_stolen_bases, batting_avg,
                        batting_doubles, batting_triples, batting_walks, batting_strikeouts,
                        pitching_games_started, pitching_wins, pitching_losses, pitching_saves,
                        pitching_innings_pitched, pitching_strikeouts,
                        created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """, (
                    job_id,
                    date_str,
                    player['yahoo_player_id'],
                    player['name'],
                    player['team_code'],
                    player['position'],
                    player['games_played'],
                    has_batting,
                    has_pitching,
                    batting.get('at_bats', 0),
                    batting.get('runs', 0),
                    batting.get('hits', 0),
                    batting.get('rbis', 0),
                    batting.get('home_runs', 0),
                    batting.get('stolen_bases', 0),
                    batting_avg,
                    batting.get('doubles', 0),
                    batting.get('triples', 0),
                    batting.get('walks', 0),
                    batting.get('strikeouts', 0),
                    pitching.get('games_started', 0),
                    pitching.get('wins', 0),
                    pitching.get('losses', 0),
                    pitching.get('saves', 0),
                    pitching.get('innings_pitched', 0.0),
                    pitching.get('strikeouts_p', 0)
                ))
                
                records_inserted += 1
                
            except Exception as e:
                error_msg = f"Error inserting {player['name']}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        self.conn.commit()
        
        # Update job status
        self.job_manager.update_job(
            job_id,
            'completed' if not errors else 'completed_with_errors',
            records_processed=players_with_stats,
            records_inserted=records_inserted,
            metadata={'errors': errors[:10]} if errors else None
        )
        
        logger.info(f"Date {date_str}: {players_with_stats} players had games, {records_inserted} records saved")
        
        return records_inserted, players_with_stats
    
    def collect_stats_for_date(self, date_str):
        """Collect stats for all teams on a specific date"""
        logger.info(f"Collecting stats for {date_str}...")
        
        # Get all teams
        teams = self.fetch_all_teams()
        if not teams:
            logger.error("No teams found")
            return 0, 0
        
        all_players_data = []
        
        # Fetch stats for each team
        for i, team in enumerate(teams):
            logger.debug(f"Fetching team {i+1}/{len(teams)}: {team['team_name']}")
            
            team_players = self.fetch_team_stats_for_date(team['team_key'], date_str)
            all_players_data.extend(team_players)
            
            # Small delay to avoid rate limiting
            if i < len(teams) - 1:
                time.sleep(0.2)
        
        logger.info(f"Collected data for {len(all_players_data)} total players")
        
        # Save to database
        return self.save_daily_stats(all_players_data, date_str)
    
    def show_daily_results(self, date_str):
        """Show sample of daily stats collected"""
        cursor = self.conn.cursor()
        
        print(f"\n{'='*120}")
        print(f"DAILY STATS FOR {date_str}")
        print(f"{'='*120}")
        
        # Show batting stats
        print("\nBATTING PERFORMANCES:")
        print(f"{'Player':<25} {'Team':<5} {'AB':<4} {'H':<3} {'R':<3} {'RBI':<4} {'2B':<3} {'3B':<3} {'HR':<3} {'BB':<3} {'K':<3} {'SB':<3} {'AVG':<6}")
        print("-" * 120)
        
        cursor.execute(f"""
            SELECT 
                player_name, team_code,
                batting_at_bats, batting_hits, batting_runs, batting_rbis,
                batting_doubles, batting_triples, batting_home_runs,
                batting_walks, batting_strikeouts, batting_stolen_bases,
                ROUND(batting_avg, 3)
            FROM {self.config['gkl_player_stats_table']}
            WHERE date = ? AND has_batting_data = 1 AND batting_at_bats > 0
            ORDER BY batting_hits DESC, batting_rbis DESC
            LIMIT 15
        """, (date_str,))
        
        for row in cursor.fetchall():
            name = row[0][:25].ljust(25)
            team = (row[1] or 'FA').ljust(5)
            ab = str(row[2]).rjust(4)
            h = str(row[3]).rjust(3)
            r = str(row[4]).rjust(3)
            rbi = str(row[5]).rjust(4)
            doubles = str(row[6]).rjust(3)
            triples = str(row[7]).rjust(3)
            hr = str(row[8]).rjust(3)
            bb = str(row[9]).rjust(3)
            k = str(row[10]).rjust(3)
            sb = str(row[11]).rjust(3)
            avg = f"{row[12]:.3f}".ljust(6)
            
            print(f"{name} {team} {ab} {h} {r} {rbi} {doubles} {triples} {hr} {bb} {k} {sb} {avg}")
        
        # Show pitching stats
        print("\n\nPITCHING PERFORMANCES:")
        print(f"{'Player':<25} {'Team':<5} {'W':<3} {'L':<3} {'SV':<3} {'IP':<5} {'K':<3}")
        print("-" * 60)
        
        cursor.execute(f"""
            SELECT 
                player_name, team_code,
                pitching_wins, pitching_losses, pitching_saves,
                pitching_innings_pitched, pitching_strikeouts
            FROM {self.config['gkl_player_stats_table']}
            WHERE date = ? AND has_pitching_data = 1
            ORDER BY pitching_wins DESC, pitching_strikeouts DESC
            LIMIT 10
        """, (date_str,))
        
        for row in cursor.fetchall():
            name = row[0][:25].ljust(25)
            team = (row[1] or 'FA').ljust(5)
            w = str(row[2]).rjust(3)
            l = str(row[3]).rjust(3)
            sv = str(row[4]).rjust(3)
            ip = f"{row[5]:.1f}".rjust(5)
            k = str(row[6]).rjust(3)
            
            print(f"{name} {team} {w} {l} {sv} {ip} {k}")
        
        # Summary stats
        cursor.execute(f"""
            SELECT 
                COUNT(DISTINCT yahoo_player_id) as total_players,
                SUM(CASE WHEN has_batting_data = 1 THEN 1 ELSE 0 END) as batters,
                SUM(CASE WHEN has_pitching_data = 1 THEN 1 ELSE 0 END) as pitchers,
                SUM(batting_hits) as total_hits,
                SUM(batting_home_runs) as total_hrs,
                SUM(pitching_strikeouts) as total_ks
            FROM {self.config['gkl_player_stats_table']}
            WHERE date = ?
        """, (date_str,))
        
        summary = cursor.fetchone()
        if summary:
            print(f"\n\nDAILY SUMMARY:")
            print(f"Total players with stats: {summary[0]}")
            print(f"Batters: {summary[1]}, Pitchers: {summary[2]}")
            print(f"Total hits: {summary[3]}, Total HRs: {summary[4]}, Total Ks: {summary[5]}")
    
    def run_collection(self, date_str=None, days_back=1):
        """Run the daily stats collection"""
        if date_str:
            dates = [date_str]
        else:
            # Collect for the last N days
            dates = []
            for i in range(days_back):
                date = datetime.now() - timedelta(days=i+1)
                dates.append(date.strftime('%Y-%m-%d'))
        
        logger.info(f"Starting daily stats collection for {len(dates)} date(s)")
        
        total_records = 0
        total_players = 0
        
        for date in sorted(dates):
            records, players = self.collect_stats_for_date(date)
            total_records += records
            total_players += players
            
            if records > 0:
                self.show_daily_results(date)
        
        print(f"\n{'='*120}")
        print("DAILY STATS COLLECTION COMPLETE")
        print(f"{'='*120}")
        print(f"Dates processed: {len(dates)}")
        print(f"Total players who played: {total_players}")
        print(f"Total records saved: {total_records}")
        print(f"\nThis data represents actual game-by-game performance")
        print("You can now aggregate stats across any date range!")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect daily stats from Yahoo API")
    parser.add_argument('--environment', default='test',
                       choices=['test', 'production'],
                       help='Environment to run in (default: test)')
    parser.add_argument('--date', help='Specific date to collect (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=1,
                       help='Number of days to look back (default: 1)')
    
    args = parser.parse_args()
    
    collector = DailyStatsCollector(environment=args.environment)
    collector.run_collection(args.date, args.days)


if __name__ == "__main__":
    main()