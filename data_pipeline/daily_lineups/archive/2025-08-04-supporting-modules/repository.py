"""
Data Access Layer for Daily Lineups
Provides high-level interface for querying and analyzing lineup data.
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.config import (
    get_database_path,
    get_lineup_table_name,
    SEASON_DATES,
    LEAGUE_KEYS
)


class LineupRepository:
    """Repository for accessing and analyzing lineup data."""
    
    def __init__(self, environment="production"):
        """
        Initialize the repository.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.db_path = get_database_path(environment)
        self.table_name = get_lineup_table_name(environment)
        self.positions_table = f"{self.table_name}_positions"
    
    def _execute_query(self, query: str, params: Tuple = ()) -> List[Tuple]:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def get_lineup_by_date(self, date_str: str, team_key: str = None) -> List[Dict]:
        """
        Get lineup(s) for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            team_key: Optional team filter
            
        Returns:
            List of lineup records
        """
        query = f"""
            SELECT 
                lineup_id,
                job_id,
                season,
                date,
                team_key,
                team_name,
                player_id,
                player_name,
                selected_position,
                position_type,
                player_status,
                eligible_positions,
                player_team
            FROM {self.table_name}
            WHERE date = ?
        """
        params = [date_str]
        
        if team_key:
            query += " AND team_key = ?"
            params.append(team_key)
        
        query += " ORDER BY team_name, position_type DESC, selected_position"
        
        results = self._execute_query(query, tuple(params))
        return [dict(row) for row in results]
    
    def get_player_usage(self, 
                        player_id: str,
                        start_date: str = None,
                        end_date: str = None) -> Dict:
        """
        Get usage statistics for a specific player.
        
        Args:
            player_id: Player ID
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Player usage statistics
        """
        # Default to current season if dates not provided
        if not start_date or not end_date:
            current_year = datetime.now().year
            season_dates = SEASON_DATES.get(current_year)
            if season_dates:
                start_date = start_date or season_dates[0]
                end_date = end_date or min(season_dates[1], date.today().strftime("%Y-%m-%d"))
        
        # Get overall usage
        query = f"""
            SELECT 
                player_name,
                COUNT(DISTINCT date) as days_active,
                COUNT(DISTINCT team_key) as teams_owned,
                SUM(CASE WHEN position_type = 'B' THEN 1 ELSE 0 END) as starts_batting,
                SUM(CASE WHEN position_type = 'P' THEN 1 ELSE 0 END) as starts_pitching,
                SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched,
                SUM(CASE WHEN selected_position LIKE 'IL%' THEN 1 ELSE 0 END) as injured
            FROM {self.table_name}
            WHERE player_id = ?
            AND date BETWEEN ? AND ?
        """
        
        result = self._execute_query(query, (player_id, start_date, end_date))
        
        if not result or not result[0]['days_active']:
            return None
        
        usage = dict(result[0])
        
        # Get position breakdown
        pos_query = f"""
            SELECT 
                selected_position,
                COUNT(*) as count
            FROM {self.table_name}
            WHERE player_id = ?
            AND date BETWEEN ? AND ?
            AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')
            GROUP BY selected_position
            ORDER BY count DESC
        """
        
        positions = self._execute_query(pos_query, (player_id, start_date, end_date))
        usage['positions'] = {row['selected_position']: row['count'] for row in positions}
        
        # Get team history
        team_query = f"""
            SELECT 
                team_key,
                team_name,
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(*) as days
            FROM {self.table_name}
            WHERE player_id = ?
            AND date BETWEEN ? AND ?
            GROUP BY team_key, team_name
            ORDER BY first_date
        """
        
        teams = self._execute_query(team_query, (player_id, start_date, end_date))
        usage['team_history'] = [dict(row) for row in teams]
        
        return usage
    
    def get_team_patterns(self, 
                         team_key: str,
                         start_date: str = None,
                         end_date: str = None) -> Dict:
        """
        Analyze lineup patterns for a team.
        
        Args:
            team_key: Team key
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Team pattern analysis
        """
        # Default dates
        if not start_date or not end_date:
            current_year = datetime.now().year
            season_dates = SEASON_DATES.get(current_year)
            if season_dates:
                start_date = start_date or season_dates[0]
                end_date = end_date or min(season_dates[1], date.today().strftime("%Y-%m-%d"))
        
        patterns = {
            "team_key": team_key,
            "date_range": f"{start_date} to {end_date}"
        }
        
        # Get team name
        name_query = f"""
            SELECT DISTINCT team_name 
            FROM {self.table_name}
            WHERE team_key = ?
            LIMIT 1
        """
        result = self._execute_query(name_query, (team_key,))
        patterns["team_name"] = result[0]['team_name'] if result else "Unknown"
        
        # Most used players
        players_query = f"""
            SELECT 
                player_id,
                player_name,
                COUNT(*) as days_rostered,
                SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') 
                    THEN 1 ELSE 0 END) as starts,
                ROUND(
                    100.0 * SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') 
                        THEN 1 ELSE 0 END) / COUNT(*), 1
                ) as start_pct
            FROM {self.table_name}
            WHERE team_key = ?
            AND date BETWEEN ? AND ?
            GROUP BY player_id, player_name
            ORDER BY starts DESC
            LIMIT 20
        """
        
        players = self._execute_query(players_query, (team_key, start_date, end_date))
        patterns["top_players"] = [dict(row) for row in players]
        
        # Position usage patterns
        position_query = f"""
            SELECT 
                selected_position,
                COUNT(DISTINCT date) as days_used,
                COUNT(DISTINCT player_id) as unique_players
            FROM {self.table_name}
            WHERE team_key = ?
            AND date BETWEEN ? AND ?
            AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')
            GROUP BY selected_position
            ORDER BY days_used DESC
        """
        
        positions = self._execute_query(position_query, (team_key, start_date, end_date))
        patterns["position_usage"] = [dict(row) for row in positions]
        
        # Bench usage
        bench_query = f"""
            SELECT 
                AVG(bench_count) as avg_bench,
                MAX(bench_count) as max_bench,
                MIN(bench_count) as min_bench
            FROM (
                SELECT 
                    date,
                    SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as bench_count
                FROM {self.table_name}
                WHERE team_key = ?
                AND date BETWEEN ? AND ?
                GROUP BY date
            )
        """
        
        bench = self._execute_query(bench_query, (team_key, start_date, end_date))
        patterns["bench_usage"] = dict(bench[0]) if bench else {}
        
        return patterns
    
    def find_lineup_changes(self, 
                           team_key: str,
                           date1: str,
                           date2: str) -> Dict:
        """
        Find lineup changes between two dates.
        
        Args:
            team_key: Team key
            date1: First date
            date2: Second date
            
        Returns:
            Dictionary of lineup changes
        """
        # Get lineups for both dates
        lineup1 = {row['player_id']: row for row in 
                  self.get_lineup_by_date(date1, team_key)}
        lineup2 = {row['player_id']: row for row in 
                  self.get_lineup_by_date(date2, team_key)}
        
        changes = {
            "date1": date1,
            "date2": date2,
            "team_key": team_key,
            "added": [],
            "dropped": [],
            "position_changes": [],
            "status_changes": []
        }
        
        # Find added/dropped players
        players1 = set(lineup1.keys())
        players2 = set(lineup2.keys())
        
        for player_id in players2 - players1:
            changes["added"].append({
                "player_id": player_id,
                "player_name": lineup2[player_id]["player_name"],
                "position": lineup2[player_id]["selected_position"]
            })
        
        for player_id in players1 - players2:
            changes["dropped"].append({
                "player_id": player_id,
                "player_name": lineup1[player_id]["player_name"],
                "position": lineup1[player_id]["selected_position"]
            })
        
        # Find position/status changes
        for player_id in players1 & players2:
            p1 = lineup1[player_id]
            p2 = lineup2[player_id]
            
            if p1["selected_position"] != p2["selected_position"]:
                changes["position_changes"].append({
                    "player_id": player_id,
                    "player_name": p1["player_name"],
                    "from_position": p1["selected_position"],
                    "to_position": p2["selected_position"]
                })
            
            if p1.get("player_status") != p2.get("player_status"):
                changes["status_changes"].append({
                    "player_id": player_id,
                    "player_name": p1["player_name"],
                    "from_status": p1.get("player_status"),
                    "to_status": p2.get("player_status")
                })
        
        return changes
    
    def get_daily_summary(self, date_str: str) -> Dict:
        """
        Get summary statistics for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Summary statistics
        """
        # Overall stats
        stats_query = f"""
            SELECT 
                COUNT(DISTINCT team_key) as teams,
                COUNT(DISTINCT player_id) as unique_players,
                COUNT(*) as total_positions,
                SUM(CASE WHEN position_type = 'B' THEN 1 ELSE 0 END) as batters,
                SUM(CASE WHEN position_type = 'P' THEN 1 ELSE 0 END) as pitchers,
                SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched,
                SUM(CASE WHEN selected_position LIKE 'IL%' THEN 1 ELSE 0 END) as injured
            FROM {self.table_name}
            WHERE date = ?
        """
        
        stats = self._execute_query(stats_query, (date_str,))
        summary = dict(stats[0]) if stats else {}
        summary["date"] = date_str
        
        # Most started players
        top_players_query = f"""
            SELECT 
                player_id,
                player_name,
                COUNT(*) as times_started
            FROM {self.table_name}
            WHERE date = ?
            AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')
            GROUP BY player_id, player_name
            HAVING COUNT(*) > 1
            ORDER BY times_started DESC
            LIMIT 10
        """
        
        top_players = self._execute_query(top_players_query, (date_str,))
        summary["most_started"] = [dict(row) for row in top_players]
        
        # Position distribution
        pos_dist_query = f"""
            SELECT 
                selected_position,
                COUNT(*) as count
            FROM {self.table_name}
            WHERE date = ?
            GROUP BY selected_position
            ORDER BY count DESC
        """
        
        positions = self._execute_query(pos_dist_query, (date_str,))
        summary["position_distribution"] = {row['selected_position']: row['count'] 
                                           for row in positions}
        
        return summary
    
    def search_players(self, 
                      search_term: str,
                      min_days: int = 1) -> List[Dict]:
        """
        Search for players by name.
        
        Args:
            search_term: Search term (partial name match)
            min_days: Minimum days rostered
            
        Returns:
            List of matching players
        """
        query = f"""
            SELECT 
                player_id,
                player_name,
                COUNT(DISTINCT date) as days_rostered,
                COUNT(DISTINCT team_key) as teams,
                MIN(date) as first_seen,
                MAX(date) as last_seen
            FROM {self.table_name}
            WHERE LOWER(player_name) LIKE LOWER(?)
            GROUP BY player_id, player_name
            HAVING COUNT(DISTINCT date) >= ?
            ORDER BY days_rostered DESC
            LIMIT 50
        """
        
        results = self._execute_query(query, (f"%{search_term}%", min_days))
        return [dict(row) for row in results]
    
    def get_position_eligibility(self, 
                                 player_id: str,
                                 date_str: str = None) -> List[str]:
        """
        Get position eligibility for a player.
        
        Args:
            player_id: Player ID
            date_str: Optional date (defaults to most recent)
            
        Returns:
            List of eligible positions
        """
        if date_str:
            query = f"""
                SELECT DISTINCT eligible_positions
                FROM {self.table_name}
                WHERE player_id = ?
                AND date = ?
                LIMIT 1
            """
            params = (player_id, date_str)
        else:
            query = f"""
                SELECT eligible_positions
                FROM {self.table_name}
                WHERE player_id = ?
                ORDER BY date DESC
                LIMIT 1
            """
            params = (player_id,)
        
        result = self._execute_query(query, params)
        
        if result and result[0]['eligible_positions']:
            positions = result[0]['eligible_positions']
            # Parse JSON if stored as string
            if isinstance(positions, str):
                try:
                    return json.loads(positions)
                except:
                    return positions.split(',')
            return positions
        
        return []
    
    def get_roster_turnover(self, 
                           team_key: str,
                           window_days: int = 7) -> List[Dict]:
        """
        Analyze roster turnover for a team.
        
        Args:
            team_key: Team key
            window_days: Window size in days
            
        Returns:
            List of turnover events
        """
        query = f"""
            WITH roster_windows AS (
                SELECT 
                    date,
                    GROUP_CONCAT(player_id) as roster
                FROM {self.table_name}
                WHERE team_key = ?
                GROUP BY date
            ),
            roster_changes AS (
                SELECT 
                    r1.date as date1,
                    r2.date as date2,
                    r1.roster as roster1,
                    r2.roster as roster2
                FROM roster_windows r1
                JOIN roster_windows r2 
                    ON r2.date = date(r1.date, '+{window_days} days')
            )
            SELECT * FROM roster_changes
            ORDER BY date1 DESC
            LIMIT 20
        """
        
        results = self._execute_query(query, (team_key,))
        
        turnovers = []
        for row in results:
            roster1 = set(row['roster1'].split(','))
            roster2 = set(row['roster2'].split(','))
            
            added = roster2 - roster1
            dropped = roster1 - roster2
            
            if added or dropped:
                turnovers.append({
                    "date_from": row['date1'],
                    "date_to": row['date2'],
                    "players_added": len(added),
                    "players_dropped": len(dropped),
                    "total_changes": len(added) + len(dropped)
                })
        
        return turnovers


def main():
    """Test the repository with sample queries."""
    
    repo = LineupRepository()
    
    # Test search
    print("Searching for players named 'Ohtani':")
    players = repo.search_players("Ohtani")
    for player in players:
        print(f"  {player['player_name']}: {player['days_rostered']} days")
    
    # Test daily summary
    print("\nSummary for 2025-08-01:")
    summary = repo.get_daily_summary("2025-08-01")
    if summary.get('teams'):
        print(f"  Teams: {summary['teams']}")
        print(f"  Players: {summary['unique_players']}")
        print(f"  Benched: {summary['benched']}")


if __name__ == "__main__":
    main()