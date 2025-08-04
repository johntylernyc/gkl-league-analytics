"""
Data Quality Validation Module for Daily Lineups

This module provides comprehensive data quality checks for lineup data
to ensure completeness, accuracy, and consistency before database insertion.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LineupDataQualityChecker:
    """Validates lineup data quality and completeness."""
    
    # Valid fantasy positions
    VALID_POSITIONS = {
        'C', '1B', '2B', '3B', 'SS', 'MI', 'CI', 'OF', 'UTIL',  # Batting positions
        'SP', 'RP', 'P',  # Pitching positions
        'BN', 'IL', 'IL10', 'IL60', 'NA'  # Bench/Reserve positions
    }
    
    # Valid player status values
    VALID_STATUS = {
        'healthy', 'DTD', 'D7', 'D10', 'D15', 'D60', 'IL', 'IL10', 'IL60', 'NA', 'SUSP'
    }
    
    # Required fields for lineup records
    REQUIRED_FIELDS = [
        'date', 'team_key', 'player_id', 'player_name', 'job_id'
    ]
    
    # Optional but important fields
    IMPORTANT_FIELDS = [
        'selected_position', 'position_type', 'player_status', 
        'eligible_positions', 'player_team', 'season'
    ]
    
    def __init__(self):
        """Initialize the quality checker."""
        self.validation_stats = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'warnings': 0,
            'field_errors': {},
            'position_errors': 0,
            'date_errors': 0,
            'duplicate_warnings': 0
        }
    
    def validate_lineup(self, lineup: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single lineup record.
        
        Args:
            lineup: Lineup dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in lineup or not lineup[field]:
                errors.append(f"Missing required field: {field}")
                self.validation_stats['field_errors'][field] = \
                    self.validation_stats['field_errors'].get(field, 0) + 1
        
        # Validate date format and range
        if 'date' in lineup and lineup['date']:
            date_error = self.validate_date(lineup['date'])
            if date_error:
                errors.append(date_error)
                self.validation_stats['date_errors'] += 1
        
        # Validate position if present
        if 'selected_position' in lineup and lineup['selected_position']:
            if lineup['selected_position'] not in self.VALID_POSITIONS:
                warnings.append(f"Invalid position: {lineup['selected_position']}")
                self.validation_stats['position_errors'] += 1
        
        # Validate player status
        if 'player_status' in lineup and lineup['player_status']:
            if lineup['player_status'] not in self.VALID_STATUS:
                warnings.append(f"Unknown player status: {lineup['player_status']}")
        
        # Validate eligible positions
        if 'eligible_positions' in lineup and lineup['eligible_positions']:
            positions = lineup['eligible_positions'].split(',') if isinstance(lineup['eligible_positions'], str) else []
            invalid_positions = [p for p in positions if p and p not in self.VALID_POSITIONS]
            if invalid_positions:
                warnings.append(f"Invalid eligible positions: {invalid_positions}")
        
        # Check for logical consistency
        if lineup.get('selected_position') and lineup.get('eligible_positions'):
            eligible = lineup['eligible_positions'].split(',') if isinstance(lineup['eligible_positions'], str) else []
            if lineup['selected_position'] not in ['BN', 'IL', 'IL10', 'IL60', 'NA']:
                if lineup['selected_position'] not in eligible:
                    warnings.append(f"Selected position {lineup['selected_position']} not in eligible positions")
        
        # Check team key format
        if 'team_key' in lineup and lineup['team_key']:
            if not self.validate_team_key(lineup['team_key']):
                errors.append(f"Invalid team key format: {lineup['team_key']}")
        
        # Check player ID format
        if 'player_id' in lineup and lineup['player_id']:
            if not str(lineup['player_id']).isdigit():
                warnings.append(f"Player ID should be numeric: {lineup['player_id']}")
        
        # Log warnings but don't invalidate
        for warning in warnings:
            logger.debug(f"Validation warning: {warning}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_date(self, date_str: str) -> Optional[str]:
        """
        Validate date format and range.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        try:
            # Parse date
            lineup_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if date is in the future
            if lineup_date > date.today():
                return f"Date is in the future: {date_str}"
            
            # Check if date is too old (before 2008 when Yahoo Fantasy started)
            if lineup_date.year < 2008:
                return f"Date is before Yahoo Fantasy era: {date_str}"
            
            return None
            
        except ValueError:
            return f"Invalid date format (expected YYYY-MM-DD): {date_str}"
    
    def validate_team_key(self, team_key: str) -> bool:
        """
        Validate team key format.
        
        Args:
            team_key: Team key to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Yahoo team key format: {game_code}.l.{league_id}.t.{team_id}
        # Example: mlb.l.6966.t.1
        parts = team_key.split('.')
        
        if len(parts) != 5:
            return False
        
        if parts[1] != 'l' or parts[3] != 't':
            return False
        
        # Check if league and team IDs are numeric
        try:
            int(parts[2])  # league_id
            int(parts[4])  # team_id
        except ValueError:
            return False
        
        return True
    
    def validate_batch(self, lineups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of lineup records.
        
        Args:
            lineups: List of lineup dictionaries
            
        Returns:
            Validation statistics dictionary
        """
        # Reset stats
        self.validation_stats = {
            'total': len(lineups),
            'valid': 0,
            'invalid': 0,
            'warnings': 0,
            'field_errors': {},
            'position_errors': 0,
            'date_errors': 0,
            'duplicate_warnings': 0
        }
        
        # Track duplicates
        seen_keys = set()
        
        for lineup in lineups:
            # Check for duplicates
            key = (
                lineup.get('date'),
                lineup.get('team_key'),
                lineup.get('player_id'),
                lineup.get('selected_position')
            )
            
            if key in seen_keys:
                self.validation_stats['duplicate_warnings'] += 1
                logger.debug(f"Duplicate lineup entry: {key}")
            else:
                seen_keys.add(key)
            
            # Validate individual lineup
            is_valid, errors = self.validate_lineup(lineup)
            
            if is_valid:
                self.validation_stats['valid'] += 1
            else:
                self.validation_stats['invalid'] += 1
                for error in errors:
                    logger.debug(f"Validation error: {error}")
        
        return self.validation_stats
    
    def generate_report(self, stats: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            stats: Validation statistics (uses internal stats if None)
            
        Returns:
            Formatted report string
        """
        if stats is None:
            stats = self.validation_stats
        
        report = []
        report.append("=" * 60)
        report.append("LINEUP DATA QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"Total Records: {stats['total']}")
        report.append(f"Valid Records: {stats['valid']} ({stats['valid']/max(stats['total'],1)*100:.1f}%)")
        report.append(f"Invalid Records: {stats['invalid']} ({stats['invalid']/max(stats['total'],1)*100:.1f}%)")
        
        if stats['duplicate_warnings'] > 0:
            report.append(f"Duplicate Warnings: {stats['duplicate_warnings']}")
        
        if stats['field_errors']:
            report.append("\nField Errors:")
            for field, count in sorted(stats['field_errors'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  - {field}: {count} errors")
        
        if stats['position_errors'] > 0:
            report.append(f"\nPosition Errors: {stats['position_errors']}")
        
        if stats['date_errors'] > 0:
            report.append(f"Date Errors: {stats['date_errors']}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def check_data_completeness(self, lineups: List[Dict[str, Any]], 
                               expected_teams: int = 12,
                               expected_players_per_team: int = 26) -> Dict[str, Any]:
        """
        Check if lineup data is complete for a given date.
        
        Args:
            lineups: List of lineup records for a specific date
            expected_teams: Expected number of teams
            expected_players_per_team: Expected roster size
            
        Returns:
            Completeness statistics
        """
        completeness = {
            'date': None,
            'teams_found': 0,
            'teams_missing': [],
            'total_players': len(lineups),
            'expected_players': expected_teams * expected_players_per_team,
            'completeness_pct': 0.0,
            'teams_with_incomplete_rosters': []
        }
        
        if not lineups:
            return completeness
        
        # Get date from first record
        completeness['date'] = lineups[0].get('date')
        
        # Count players per team
        team_counts = {}
        for lineup in lineups:
            team_key = lineup.get('team_key')
            if team_key:
                team_counts[team_key] = team_counts.get(team_key, 0) + 1
        
        completeness['teams_found'] = len(team_counts)
        
        # Check for incomplete rosters
        for team_key, count in team_counts.items():
            if count < expected_players_per_team:
                completeness['teams_with_incomplete_rosters'].append({
                    'team': team_key,
                    'players': count,
                    'missing': expected_players_per_team - count
                })
        
        # Calculate completeness percentage
        completeness['completeness_pct'] = (
            completeness['total_players'] / completeness['expected_players'] * 100
            if completeness['expected_players'] > 0 else 0
        )
        
        return completeness
    
    def validate_season_coverage(self, season: int, dates_with_data: List[str]) -> Dict[str, Any]:
        """
        Check season coverage completeness.
        
        Args:
            season: Season year
            dates_with_data: List of dates that have lineup data
            
        Returns:
            Coverage statistics
        """
        from data_pipeline.metadata.league_keys import SEASON_DATES
        
        coverage = {
            'season': season,
            'total_days_with_data': len(dates_with_data),
            'missing_dates': [],
            'coverage_pct': 0.0,
            'gaps': []
        }
        
        # Get season date range
        season_info = SEASON_DATES.get(season)
        if not season_info:
            coverage['error'] = f"No season dates found for {season}"
            return coverage
        
        start_date = datetime.strptime(season_info['start'], '%Y-%m-%d').date()
        end_date = datetime.strptime(season_info['end'], '%Y-%m-%d').date()
        today = date.today()
        
        # Adjust end date if season is current
        if end_date > today:
            end_date = today
        
        # Calculate expected days
        total_days = (end_date - start_date).days + 1
        coverage['expected_days'] = total_days
        
        # Convert dates_with_data to set for faster lookup
        data_dates = set(dates_with_data)
        
        # Find missing dates and gaps
        current = start_date
        gap_start = None
        
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            
            if date_str not in data_dates:
                coverage['missing_dates'].append(date_str)
                if gap_start is None:
                    gap_start = current
            else:
                if gap_start is not None:
                    gap_end = current - timedelta(days=1)
                    coverage['gaps'].append({
                        'start': str(gap_start),
                        'end': str(gap_end),
                        'days': (gap_end - gap_start).days + 1
                    })
                    gap_start = None
            
            current += timedelta(days=1)
        
        # Handle gap at the end
        if gap_start is not None:
            coverage['gaps'].append({
                'start': str(gap_start),
                'end': str(end_date),
                'days': (end_date - gap_start).days + 1
            })
        
        # Calculate coverage percentage
        coverage['coverage_pct'] = (
            coverage['total_days_with_data'] / total_days * 100
            if total_days > 0 else 0
        )
        
        return coverage


# Convenience function for quick validation
def validate_lineup_data(lineups: List[Dict[str, Any]], verbose: bool = False) -> bool:
    """
    Quick validation function for lineup data.
    
    Args:
        lineups: List of lineup dictionaries
        verbose: Whether to print the report
        
    Returns:
        True if all records are valid, False otherwise
    """
    checker = LineupDataQualityChecker()
    stats = checker.validate_batch(lineups)
    
    if verbose:
        print(checker.generate_report(stats))
    
    return stats['invalid'] == 0