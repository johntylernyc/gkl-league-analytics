#!/usr/bin/env python3
"""
Player Stats Repository

Data access layer for MLB player statistics with optimized queries,
aggregations, and filtering capabilities. Provides a clean interface
for accessing player statistics data across multiple time periods.

Key Features:
- Optimized queries for common access patterns
- Date range filtering and aggregation
- Player and team-based filtering
- Performance metrics and statistics
- Integration with player ID mapping
"""

import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
import pandas as pd

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PlayerStatsRecord:
    """Individual player statistics record."""
    yahoo_player_id: str
    player_name: str
    team_code: str
    date: date
    games_played: int
    has_batting_data: bool
    has_pitching_data: bool
    
    # Batting stats
    batting_at_bats: Optional[int] = None
    batting_runs: Optional[int] = None
    batting_hits: Optional[int] = None
    batting_doubles: Optional[int] = None
    batting_triples: Optional[int] = None
    batting_home_runs: Optional[int] = None
    batting_rbis: Optional[int] = None
    batting_stolen_bases: Optional[int] = None
    batting_walks: Optional[int] = None
    batting_strikeouts: Optional[int] = None
    batting_avg: Optional[float] = None
    batting_obp: Optional[float] = None
    batting_slg: Optional[float] = None
    batting_ops: Optional[float] = None
    
    # Pitching stats
    pitching_games_started: Optional[int] = None
    pitching_wins: Optional[int] = None
    pitching_losses: Optional[int] = None
    pitching_saves: Optional[int] = None
    pitching_holds: Optional[int] = None
    pitching_innings_pitched: Optional[float] = None
    pitching_hits_allowed: Optional[int] = None
    pitching_runs_allowed: Optional[int] = None
    pitching_earned_runs: Optional[int] = None
    pitching_walks_allowed: Optional[int] = None
    pitching_strikeouts: Optional[int] = None
    pitching_home_runs_allowed: Optional[int] = None
    pitching_era: Optional[float] = None
    pitching_whip: Optional[float] = None
    pitching_quality_starts: Optional[int] = None
    
    # Metadata
    confidence_score: Optional[float] = None
    validation_status: Optional[str] = None


@dataclass
class PlayerStatsAggregation:
    """Aggregated player statistics over a time period."""
    yahoo_player_id: str
    player_name: str
    team_code: str
    start_date: date
    end_date: date
    total_games: int
    
    # Batting aggregations
    total_at_bats: int = 0
    total_runs: int = 0
    total_hits: int = 0
    total_doubles: int = 0
    total_triples: int = 0
    total_home_runs: int = 0
    total_rbis: int = 0
    total_stolen_bases: int = 0
    total_walks: int = 0
    total_strikeouts: int = 0
    avg_batting_avg: Optional[float] = None
    avg_obp: Optional[float] = None
    avg_slg: Optional[float] = None
    avg_ops: Optional[float] = None
    
    # Pitching aggregations
    total_games_started: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_saves: int = 0
    total_holds: int = 0
    total_innings_pitched: float = 0.0
    total_hits_allowed: int = 0
    total_runs_allowed: int = 0
    total_earned_runs: int = 0
    total_walks_allowed: int = 0
    total_strikeouts_pitched: int = 0
    total_home_runs_allowed: int = 0
    avg_era: Optional[float] = None
    avg_whip: Optional[float] = None
    total_quality_starts: int = 0


class PlayerStatsRepository:
    """
    Data access layer for player statistics.
    
    Provides optimized queries and aggregations for player statistics
    data with support for filtering by date, player, team, and other criteria.
    """
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the repository.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.db_path = self.config['database_path']
        self.stats_table = self.config['gkl_player_stats_table']
        self.mapping_table = self.config['player_mapping_table']
        
        logger.info(f"Initialized PlayerStatsRepository for {environment} environment")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Stats table: {self.stats_table}")
    
    def get_player_stats(self, yahoo_player_id: str, start_date: date, 
                        end_date: date = None) -> List[PlayerStatsRecord]:
        """
        Get statistics for a specific player over a date range.
        
        Args:
            yahoo_player_id: Yahoo Fantasy player ID
            start_date: Start date for query
            end_date: End date for query (defaults to start_date)
            
        Returns:
            List of PlayerStatsRecord objects
        """
        if end_date is None:
            end_date = start_date
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT yahoo_player_id, player_name, team_code, date, games_played,
                       has_batting_data, has_pitching_data,
                       batting_at_bats, batting_runs, batting_hits, batting_doubles,
                       batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                       batting_walks, batting_strikeouts, batting_avg, batting_obp,
                       batting_slg, batting_ops,
                       pitching_games_started, pitching_wins, pitching_losses,
                       pitching_saves, pitching_holds, pitching_innings_pitched,
                       pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
                       pitching_walks_allowed, pitching_strikeouts, pitching_home_runs_allowed,
                       pitching_era, pitching_whip, pitching_quality_starts,
                       confidence_score, validation_status
                FROM {self.stats_table}
                WHERE yahoo_player_id = ? AND date BETWEEN ? AND ?
                ORDER BY date ASC
            """, (yahoo_player_id, start_date.isoformat(), end_date.isoformat()))
            
            records = []
            for row in cursor.fetchall():
                records.append(PlayerStatsRecord(
                    yahoo_player_id=row[0],
                    player_name=row[1],
                    team_code=row[2],
                    date=date.fromisoformat(row[3]),
                    games_played=row[4],
                    has_batting_data=bool(row[5]),
                    has_pitching_data=bool(row[6]),
                    batting_at_bats=row[7],
                    batting_runs=row[8],
                    batting_hits=row[9],
                    batting_doubles=row[10],
                    batting_triples=row[11],
                    batting_home_runs=row[12],
                    batting_rbis=row[13],
                    batting_stolen_bases=row[14],
                    batting_walks=row[15],
                    batting_strikeouts=row[16],
                    batting_avg=row[17],
                    batting_obp=row[18],
                    batting_slg=row[19],
                    batting_ops=row[20],
                    pitching_games_started=row[21],
                    pitching_wins=row[22],
                    pitching_losses=row[23],
                    pitching_saves=row[24],
                    pitching_holds=row[25],
                    pitching_innings_pitched=row[26],
                    pitching_hits_allowed=row[27],
                    pitching_runs_allowed=row[28],
                    pitching_earned_runs=row[29],
                    pitching_walks_allowed=row[30],
                    pitching_strikeouts=row[31],
                    pitching_home_runs_allowed=row[32],
                    pitching_era=row[33],
                    pitching_whip=row[34],
                    pitching_quality_starts=row[35],
                    confidence_score=row[36],
                    validation_status=row[37]
                ))
            
            return records
            
        finally:
            conn.close()
    
    def get_stats_for_date(self, target_date: date, 
                          player_ids: List[str] = None) -> List[PlayerStatsRecord]:
        """
        Get all player statistics for a specific date.
        
        Args:
            target_date: Date to query
            player_ids: Optional list of player IDs to filter by
            
        Returns:
            List of PlayerStatsRecord objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            base_query = f"""
                SELECT yahoo_player_id, player_name, team_code, date, games_played,
                       has_batting_data, has_pitching_data,
                       batting_at_bats, batting_runs, batting_hits, batting_doubles,
                       batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                       batting_walks, batting_strikeouts, batting_avg, batting_obp,
                       batting_slg, batting_ops,
                       pitching_games_started, pitching_wins, pitching_losses,
                       pitching_saves, pitching_holds, pitching_innings_pitched,
                       pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
                       pitching_walks_allowed, pitching_strikeouts, pitching_home_runs_allowed,
                       pitching_era, pitching_whip, pitching_quality_starts,
                       confidence_score, validation_status
                FROM {self.stats_table}
                WHERE date = ?
            """
            
            params = [target_date.isoformat()]
            
            if player_ids:
                placeholders = ','.join('?' for _ in player_ids)
                base_query += f" AND yahoo_player_id IN ({placeholders})"
                params.extend(player_ids)
            
            base_query += " ORDER BY player_name ASC"
            
            cursor.execute(base_query, params)
            
            records = []
            for row in cursor.fetchall():
                records.append(PlayerStatsRecord(
                    yahoo_player_id=row[0],
                    player_name=row[1],
                    team_code=row[2],
                    date=date.fromisoformat(row[3]),
                    games_played=row[4],
                    has_batting_data=bool(row[5]),
                    has_pitching_data=bool(row[6]),
                    batting_at_bats=row[7],
                    batting_runs=row[8],
                    batting_hits=row[9],
                    batting_doubles=row[10],
                    batting_triples=row[11],
                    batting_home_runs=row[12],
                    batting_rbis=row[13],
                    batting_stolen_bases=row[14],
                    batting_walks=row[15],
                    batting_strikeouts=row[16],
                    batting_avg=row[17],
                    batting_obp=row[18],
                    batting_slg=row[19],
                    batting_ops=row[20],
                    pitching_games_started=row[21],
                    pitching_wins=row[22],
                    pitching_losses=row[23],
                    pitching_saves=row[24],
                    pitching_holds=row[25],
                    pitching_innings_pitched=row[26],
                    pitching_hits_allowed=row[27],
                    pitching_runs_allowed=row[28],
                    pitching_earned_runs=row[29],
                    pitching_walks_allowed=row[30],
                    pitching_strikeouts=row[31],
                    pitching_home_runs_allowed=row[32],
                    pitching_era=row[33],
                    pitching_whip=row[34],
                    pitching_quality_starts=row[35],
                    confidence_score=row[36],
                    validation_status=row[37]
                ))
            
            return records
            
        finally:
            conn.close()
    
    def get_player_aggregation(self, yahoo_player_id: str, start_date: date, 
                             end_date: date) -> Optional[PlayerStatsAggregation]:
        """
        Get aggregated statistics for a player over a date range.
        
        Args:
            yahoo_player_id: Yahoo Fantasy player ID
            start_date: Start date for aggregation
            end_date: End date for aggregation
            
        Returns:
            PlayerStatsAggregation object or None if no data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT 
                    player_name, team_code,
                    COUNT(*) as total_games,
                    COALESCE(SUM(batting_at_bats), 0) as total_at_bats,
                    COALESCE(SUM(batting_runs), 0) as total_runs,
                    COALESCE(SUM(batting_hits), 0) as total_hits,
                    COALESCE(SUM(batting_doubles), 0) as total_doubles,
                    COALESCE(SUM(batting_triples), 0) as total_triples,
                    COALESCE(SUM(batting_home_runs), 0) as total_home_runs,
                    COALESCE(SUM(batting_rbis), 0) as total_rbis,
                    COALESCE(SUM(batting_stolen_bases), 0) as total_stolen_bases,
                    COALESCE(SUM(batting_walks), 0) as total_walks,
                    COALESCE(SUM(batting_strikeouts), 0) as total_strikeouts,
                    AVG(batting_avg) as avg_batting_avg,
                    AVG(batting_obp) as avg_obp,
                    AVG(batting_slg) as avg_slg,
                    AVG(batting_ops) as avg_ops,
                    COALESCE(SUM(pitching_games_started), 0) as total_games_started,
                    COALESCE(SUM(pitching_wins), 0) as total_wins,
                    COALESCE(SUM(pitching_losses), 0) as total_losses,
                    COALESCE(SUM(pitching_saves), 0) as total_saves,
                    COALESCE(SUM(pitching_holds), 0) as total_holds,
                    COALESCE(SUM(pitching_innings_pitched), 0.0) as total_innings_pitched,
                    COALESCE(SUM(pitching_hits_allowed), 0) as total_hits_allowed,
                    COALESCE(SUM(pitching_runs_allowed), 0) as total_runs_allowed,
                    COALESCE(SUM(pitching_earned_runs), 0) as total_earned_runs,
                    COALESCE(SUM(pitching_walks_allowed), 0) as total_walks_allowed,
                    COALESCE(SUM(pitching_strikeouts), 0) as total_strikeouts_pitched,
                    COALESCE(SUM(pitching_home_runs_allowed), 0) as total_home_runs_allowed,
                    AVG(pitching_era) as avg_era,
                    AVG(pitching_whip) as avg_whip,
                    COALESCE(SUM(pitching_quality_starts), 0) as total_quality_starts
                FROM {self.stats_table}
                WHERE yahoo_player_id = ? AND date BETWEEN ? AND ?
                GROUP BY yahoo_player_id, player_name, team_code
            """, (yahoo_player_id, start_date.isoformat(), end_date.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return PlayerStatsAggregation(
                yahoo_player_id=yahoo_player_id,
                player_name=row[0],
                team_code=row[1],
                start_date=start_date,
                end_date=end_date,
                total_games=row[2],
                total_at_bats=row[3],
                total_runs=row[4],
                total_hits=row[5],
                total_doubles=row[6],
                total_triples=row[7],
                total_home_runs=row[8],
                total_rbis=row[9],
                total_stolen_bases=row[10],
                total_walks=row[11],
                total_strikeouts=row[12],
                avg_batting_avg=row[13],
                avg_obp=row[14],
                avg_slg=row[15],
                avg_ops=row[16],
                total_games_started=row[17],
                total_wins=row[18],
                total_losses=row[19],
                total_saves=row[20],
                total_holds=row[21],
                total_innings_pitched=row[22],
                total_hits_allowed=row[23],
                total_runs_allowed=row[24],
                total_earned_runs=row[25],
                total_walks_allowed=row[26],
                total_strikeouts_pitched=row[27],
                total_home_runs_allowed=row[28],
                avg_era=row[29],
                avg_whip=row[30],
                total_quality_starts=row[31]
            )
            
        finally:
            conn.close()
    
    def get_team_stats_for_date(self, team_code: str, target_date: date) -> List[PlayerStatsRecord]:
        """
        Get all player statistics for a team on a specific date.
        
        Args:
            team_code: Team code to filter by
            target_date: Date to query
            
        Returns:
            List of PlayerStatsRecord objects for the team
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT yahoo_player_id, player_name, team_code, date, games_played,
                       has_batting_data, has_pitching_data,
                       batting_at_bats, batting_runs, batting_hits, batting_doubles,
                       batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                       batting_walks, batting_strikeouts, batting_avg, batting_obp,
                       batting_slg, batting_ops,
                       pitching_games_started, pitching_wins, pitching_losses,
                       pitching_saves, pitching_holds, pitching_innings_pitched,
                       pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
                       pitching_walks_allowed, pitching_strikeouts, pitching_home_runs_allowed,
                       pitching_era, pitching_whip, pitching_quality_starts,
                       confidence_score, validation_status
                FROM {self.stats_table}
                WHERE team_code = ? AND date = ?
                ORDER BY player_name ASC
            """, (team_code, target_date.isoformat()))
            
            records = []
            for row in cursor.fetchall():
                records.append(PlayerStatsRecord(
                    yahoo_player_id=row[0],
                    player_name=row[1],
                    team_code=row[2],
                    date=date.fromisoformat(row[3]),
                    games_played=row[4],
                    has_batting_data=bool(row[5]),
                    has_pitching_data=bool(row[6]),
                    batting_at_bats=row[7],
                    batting_runs=row[8],
                    batting_hits=row[9],
                    batting_doubles=row[10],
                    batting_triples=row[11],
                    batting_home_runs=row[12],
                    batting_rbis=row[13],
                    batting_stolen_bases=row[14],
                    batting_walks=row[15],
                    batting_strikeouts=row[16],
                    batting_avg=row[17],
                    batting_obp=row[18],
                    batting_slg=row[19],
                    batting_ops=row[20],
                    pitching_games_started=row[21],
                    pitching_wins=row[22],
                    pitching_losses=row[23],
                    pitching_saves=row[24],
                    pitching_holds=row[25],
                    pitching_innings_pitched=row[26],
                    pitching_hits_allowed=row[27],
                    pitching_runs_allowed=row[28],
                    pitching_earned_runs=row[29],
                    pitching_walks_allowed=row[30],
                    pitching_strikeouts=row[31],
                    pitching_home_runs_allowed=row[32],
                    pitching_era=row[33],
                    pitching_whip=row[34],
                    pitching_quality_starts=row[35],
                    confidence_score=row[36],
                    validation_status=row[37]
                ))
            
            return records
            
        finally:
            conn.close()
    
    def get_available_dates(self, start_date: date = None, 
                           end_date: date = None) -> List[date]:
        """
        Get list of dates that have statistics data available.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of dates with data available
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            base_query = f"SELECT DISTINCT date FROM {self.stats_table}"
            params = []
            
            where_clauses = []
            if start_date:
                where_clauses.append("date >= ?")
                params.append(start_date.isoformat())
            if end_date:
                where_clauses.append("date <= ?")
                params.append(end_date.isoformat())
            
            if where_clauses:
                base_query += " WHERE " + " AND ".join(where_clauses)
            
            base_query += " ORDER BY date ASC"
            
            cursor.execute(base_query, params)
            
            return [date.fromisoformat(row[0]) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def get_data_coverage_summary(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Get summary of data coverage over a date range.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with coverage statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get basic coverage stats
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT date) as dates_with_data,
                    COUNT(*) as total_player_records,
                    COUNT(DISTINCT yahoo_player_id) as unique_players,
                    COUNT(CASE WHEN has_batting_data THEN 1 END) as records_with_batting,
                    COUNT(CASE WHEN has_pitching_data THEN 1 END) as records_with_pitching,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    AVG(confidence_score) as avg_confidence_score
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            row = cursor.fetchone()
            
            # Calculate expected dates in range
            expected_dates = (end_date - start_date).days + 1
            
            # Get validation status breakdown
            cursor.execute(f"""
                SELECT validation_status, COUNT(*) 
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
                GROUP BY validation_status
            """, (start_date.isoformat(), end_date.isoformat()))
            
            validation_breakdown = dict(cursor.fetchall())
            
            # Get team coverage
            cursor.execute(f"""
                SELECT team_code, COUNT(DISTINCT date) as dates_covered
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
                GROUP BY team_code
                ORDER BY dates_covered DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            team_coverage = dict(cursor.fetchall())
            
            summary = {
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'expected_dates': expected_dates,
                    'dates_with_data': row[0] if row else 0,
                    'coverage_percentage': (row[0] / expected_dates * 100) if row and row[0] else 0.0
                },
                'records': {
                    'total_player_records': row[1] if row else 0,
                    'unique_players': row[2] if row else 0,
                    'records_with_batting': row[3] if row else 0,
                    'records_with_pitching': row[4] if row else 0,
                    'batting_coverage_pct': (row[3] / row[1] * 100) if row and row[1] else 0.0,
                    'pitching_coverage_pct': (row[4] / row[1] * 100) if row and row[1] else 0.0
                },
                'data_quality': {
                    'avg_confidence_score': row[7] if row and row[7] else 0.0,
                    'validation_breakdown': validation_breakdown
                },
                'team_coverage': team_coverage,
                'date_range_actual': {
                    'earliest_date': row[5] if row and row[5] else None,
                    'latest_date': row[6] if row and row[6] else None
                }
            }
            
            return summary
            
        finally:
            conn.close()
    
    def search_players_by_name(self, name_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for players by name with recent statistics.
        
        Args:
            name_query: Name search query (partial match)
            limit: Maximum results to return
            
        Returns:
            List of player records with recent stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get players matching name with their most recent stats
            cursor.execute(f"""
                SELECT DISTINCT 
                    s.yahoo_player_id,
                    s.player_name,
                    s.team_code,
                    MAX(s.date) as latest_date,
                    COUNT(s.date) as total_games_recorded
                FROM {self.stats_table} s
                WHERE s.player_name LIKE ?
                GROUP BY s.yahoo_player_id, s.player_name, s.team_code
                ORDER BY s.player_name ASC
                LIMIT ?
            """, (f"%{name_query}%", limit))
            
            players = []
            for row in cursor.fetchall():
                # Get recent performance for this player
                recent_stats = self.get_player_stats(
                    row[0], 
                    date.fromisoformat(row[3]) - timedelta(days=7),
                    date.fromisoformat(row[3])
                )
                
                players.append({
                    'yahoo_player_id': row[0],
                    'player_name': row[1],
                    'team_code': row[2],
                    'latest_date': row[3],
                    'total_games_recorded': row[4],
                    'recent_games': len(recent_stats)
                })
            
            return players
            
        finally:
            conn.close()
    
    def get_top_performers(self, stat_category: str, start_date: date, 
                          end_date: date, limit: int = 10, 
                          player_type: str = "batting") -> List[Dict[str, Any]]:
        """
        Get top performers in a specific statistical category.
        
        Args:
            stat_category: Statistical category to rank by
            start_date: Start date for period
            end_date: End date for period  
            limit: Number of top performers to return
            player_type: 'batting' or 'pitching'
            
        Returns:
            List of top performers with their stats
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Map stat categories to SQL columns
        batting_stats = {
            'home_runs': 'SUM(batting_home_runs)',
            'rbis': 'SUM(batting_rbis)',
            'runs': 'SUM(batting_runs)',
            'hits': 'SUM(batting_hits)',
            'stolen_bases': 'SUM(batting_stolen_bases)',
            'avg': 'AVG(batting_avg)',
            'ops': 'AVG(batting_ops)'
        }
        
        pitching_stats = {
            'wins': 'SUM(pitching_wins)',
            'saves': 'SUM(pitching_saves)',
            'strikeouts': 'SUM(pitching_strikeouts)',
            'innings': 'SUM(pitching_innings_pitched)',
            'era': 'AVG(pitching_era)',
            'whip': 'AVG(pitching_whip)',
            'quality_starts': 'SUM(pitching_quality_starts)'
        }
        
        try:
            if player_type == "batting" and stat_category in batting_stats:
                stat_sql = batting_stats[stat_category]
                filter_clause = "has_batting_data = 1"
            elif player_type == "pitching" and stat_category in pitching_stats:
                stat_sql = pitching_stats[stat_category]
                filter_clause = "has_pitching_data = 1"
            else:
                raise ValueError(f"Invalid stat category: {stat_category} for type: {player_type}")
            
            cursor.execute(f"""
                SELECT 
                    yahoo_player_id,
                    player_name,
                    team_code,
                    COUNT(*) as games,
                    {stat_sql} as stat_value
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
                AND {filter_clause}
                GROUP BY yahoo_player_id, player_name, team_code
                HAVING COUNT(*) >= 3  -- Minimum games requirement
                ORDER BY stat_value DESC
                LIMIT ?
            """, (start_date.isoformat(), end_date.isoformat(), limit))
            
            performers = []
            for row in cursor.fetchall():
                performers.append({
                    'yahoo_player_id': row[0],
                    'player_name': row[1],
                    'team_code': row[2],
                    'games': row[3],
                    'stat_category': stat_category,
                    'stat_value': row[4],
                    'player_type': player_type
                })
            
            return performers
            
        finally:
            conn.close()


def main():
    """Command-line interface for repository operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Player Stats Repository Operations")
    parser.add_argument("action", choices=["player", "date", "coverage", "search", "top"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--player-id", help="Yahoo player ID for player query")
    parser.add_argument("--date", help="Date for queries (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start date for range queries (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for range queries (YYYY-MM-DD)")
    parser.add_argument("--team", help="Team code for team queries")
    parser.add_argument("--query", help="Search query for player search")
    parser.add_argument("--stat", help="Stat category for top performers")
    parser.add_argument("--type", choices=["batting", "pitching"], default="batting",
                       help="Player type for top performers")
    parser.add_argument("--limit", type=int, default=10,
                       help="Limit for results (default: 10)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    repo = PlayerStatsRepository(environment=args.env)
    
    if args.action == "player":
        if not args.player_id or not args.date:
            print("ERROR: --player-id and --date are required for player query")
            return
        
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Player stats for {args.player_id} on {target_date}:")
        print("-" * 60)
        
        stats = repo.get_player_stats(args.player_id, target_date)
        
        if stats:
            for stat in stats:
                print(f"Player: {stat.player_name} ({stat.team_code})")
                print(f"Games: {stat.games_played}")
                if stat.has_batting_data:
                    print(f"Batting: {stat.batting_hits}/{stat.batting_at_bats} AVG:{stat.batting_avg:.3f}")
                if stat.has_pitching_data:
                    print(f"Pitching: {stat.pitching_innings_pitched}IP ERA:{stat.pitching_era:.2f}")
        else:
            print("No stats found")
    
    elif args.action == "date":
        if not args.date:
            print("ERROR: --date is required for date query")
            return
        
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"All player stats for {target_date}:")
        print("-" * 60)
        
        stats = repo.get_stats_for_date(target_date)
        
        print(f"Found {len(stats)} player records")
        for stat in stats[:args.limit]:
            print(f"{stat.player_name} ({stat.team_code}) - G:{stat.games_played}")
    
    elif args.action == "coverage":
        if not args.start_date or not args.end_date:
            print("ERROR: --start-date and --end-date are required for coverage analysis")
            return
        
        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Data coverage analysis: {start_date} to {end_date}")
        print("-" * 60)
        
        summary = repo.get_data_coverage_summary(start_date, end_date)
        
        print(f"Date Coverage: {summary['date_range']['dates_with_data']}/{summary['date_range']['expected_dates']} ({summary['date_range']['coverage_percentage']:.1f}%)")
        print(f"Total Records: {summary['records']['total_player_records']:,}")
        print(f"Unique Players: {summary['records']['unique_players']:,}")
        print(f"Avg Confidence: {summary['data_quality']['avg_confidence_score']:.3f}")
    
    elif args.action == "search":
        if not args.query:
            print("ERROR: --query is required for player search")
            return
        
        print(f"Searching players: '{args.query}'")
        print("-" * 60)
        
        players = repo.search_players_by_name(args.query, args.limit)
        
        for player in players:
            print(f"{player['player_name']} ({player['team_code']})")
            print(f"  Latest: {player['latest_date']} | Total Games: {player['total_games_recorded']}")
    
    elif args.action == "top":
        if not args.stat or not args.start_date or not args.end_date:
            print("ERROR: --stat, --start-date, and --end-date are required for top performers")
            return
        
        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Top {args.limit} {args.type} performers in {args.stat}:")
        print("-" * 60)
        
        try:
            performers = repo.get_top_performers(
                args.stat, start_date, end_date, args.limit, args.type
            )
            
            for i, performer in enumerate(performers, 1):
                print(f"{i}. {performer['player_name']} ({performer['team_code']})")
                print(f"   {performer['stat_category']}: {performer['stat_value']:.3f} ({performer['games']} games)")
                
        except ValueError as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()