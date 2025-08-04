#!/usr/bin/env python3
"""
Player Stats Data Validator

Comprehensive data quality validation system for MLB player statistics.
Performs range validation, completeness checks, consistency verification,
and anomaly detection to ensure high-quality data integrity.

Key Features:
- Statistical range validation (batting averages, ERAs, etc.)
- Data completeness verification
- Cross-field consistency checks
- Anomaly detection and reporting
- Integration with existing validation infrastructure
"""

import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics

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


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a data validation issue."""
    severity: ValidationSeverity
    category: str
    description: str
    field_name: Optional[str] = None
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    date: Optional[str] = None
    actual_value: Optional[Any] = None
    expected_range: Optional[Tuple[Any, Any]] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    validation_date: datetime
    date_range_start: date
    date_range_end: date
    total_records_validated: int
    issues: List[ValidationIssue]
    summary_stats: Dict[str, Any]
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len([i for i in self.issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]])
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len([i for i in self.issues if i.severity == ValidationSeverity.WARNING])
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return self.error_count == 0


class PlayerStatsValidator:
    """
    Comprehensive data quality validator for player statistics.
    
    Performs multi-layered validation including range checks, completeness
    verification, consistency validation, and anomaly detection to ensure
    high-quality data integrity across all player statistics.
    """
    
    def __init__(self, environment: str = "production"):
        """
        Initialize the validator.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        self.db_path = self.config['database_path']
        self.stats_table = self.config['gkl_player_stats_table']
        self.validation_config = self.config['data_validation']
        
        logger.info(f"Initialized PlayerStatsValidator for {environment} environment")
        logger.info(f"Database: {self.db_path}")
        logger.info(f"Stats table: {self.stats_table}")
    
    def validate_date(self, target_date: date, 
                     enable_anomaly_detection: bool = True) -> ValidationReport:
        """
        Validate all player statistics for a specific date.
        
        Args:
            target_date: Date to validate
            enable_anomaly_detection: Whether to run anomaly detection
            
        Returns:
            ValidationReport with all issues found
        """
        logger.info(f"Starting validation for {target_date}")
        
        issues = []
        
        # Get all records for the date
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
                WHERE date = ?
            """, (target_date.isoformat(),))
            
            records = cursor.fetchall()
            total_records = len(records)
            
            logger.info(f"Validating {total_records} records for {target_date}")
            
            for record in records:
                # Validate each record
                record_issues = self._validate_single_record(record)
                issues.extend(record_issues)
            
            # Run anomaly detection if enabled
            if enable_anomaly_detection and records:
                anomaly_issues = self._detect_anomalies(records, target_date)
                issues.extend(anomaly_issues)
            
            # Generate summary statistics
            summary_stats = self._generate_summary_stats(records, issues)
            
            report = ValidationReport(
                validation_date=datetime.now(),
                date_range_start=target_date,
                date_range_end=target_date,
                total_records_validated=total_records,
                issues=issues,
                summary_stats=summary_stats
            )
            
            logger.info(f"Validation completed: {len(issues)} issues found ({report.error_count} errors, {report.warning_count} warnings)")
            return report
            
        finally:
            conn.close()
    
    def validate_date_range(self, start_date: date, end_date: date,
                           enable_anomaly_detection: bool = True) -> ValidationReport:
        """
        Validate player statistics over a date range.
        
        Args:
            start_date: Start date for validation
            end_date: End date for validation
            enable_anomaly_detection: Whether to run anomaly detection
            
        Returns:
            ValidationReport with all issues found
        """
        logger.info(f"Starting validation for date range: {start_date} to {end_date}")
        
        all_issues = []
        total_records = 0
        
        # Validate each date in the range
        current_date = start_date
        while current_date <= end_date:
            daily_report = self.validate_date(current_date, enable_anomaly_detection=False)
            all_issues.extend(daily_report.issues)
            total_records += daily_report.total_records_validated
            current_date += timedelta(days=1)
        
        # Run cross-date anomaly detection if enabled
        if enable_anomaly_detection:
            range_anomalies = self._detect_range_anomalies(start_date, end_date)
            all_issues.extend(range_anomalies)
        
        # Generate summary for the entire range
        summary_stats = self._generate_range_summary(start_date, end_date, all_issues)
        
        report = ValidationReport(
            validation_date=datetime.now(),
            date_range_start=start_date,
            date_range_end=end_date,
            total_records_validated=total_records,
            issues=all_issues,
            summary_stats=summary_stats
        )
        
        logger.info(f"Range validation completed: {len(all_issues)} issues found ({report.error_count} errors, {report.warning_count} warnings)")
        return report
    
    def _validate_single_record(self, record: Tuple) -> List[ValidationIssue]:
        """Validate a single player stats record."""
        issues = []
        
        # Extract record fields
        (yahoo_player_id, player_name, team_code, date_str, games_played,
         has_batting_data, has_pitching_data,
         batting_at_bats, batting_runs, batting_hits, batting_doubles,
         batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
         batting_walks, batting_strikeouts, batting_avg, batting_obp,
         batting_slg, batting_ops,
         pitching_games_started, pitching_wins, pitching_losses,
         pitching_saves, pitching_holds, pitching_innings_pitched,
         pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
         pitching_walks_allowed, pitching_strikeouts_p, pitching_home_runs_allowed,
         pitching_era, pitching_whip, pitching_quality_starts,
         confidence_score, validation_status) = record
        
        # Basic required field validation
        if not yahoo_player_id:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="missing_data",
                description="Missing Yahoo player ID",
                player_name=player_name,
                date=date_str
            ))
        
        if not player_name:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="missing_data",
                description="Missing player name",
                player_id=yahoo_player_id,
                date=date_str
            ))
        
        if not team_code:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="missing_data",
                description="Missing team code",
                player_id=yahoo_player_id,
                player_name=player_name,
                date=date_str
            ))
        
        # Games played validation
        if games_played < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="Negative games played",
                field_name="games_played",
                player_id=yahoo_player_id,
                player_name=player_name,
                date=date_str,
                actual_value=games_played,
                expected_range=(0, 10)
            ))
        elif games_played > 10:  # Reasonable maximum
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="unusual_value",
                description="Unusually high games played",
                field_name="games_played",
                player_id=yahoo_player_id,
                player_name=player_name,
                date=date_str,
                actual_value=games_played,
                expected_range=(0, 10)
            ))
        
        # Batting statistics validation
        if has_batting_data:
            batting_issues = self._validate_batting_stats(
                yahoo_player_id, player_name, date_str,
                batting_at_bats, batting_runs, batting_hits, batting_doubles,
                batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                batting_walks, batting_strikeouts, batting_avg, batting_obp,
                batting_slg, batting_ops
            )
            issues.extend(batting_issues)
        
        # Pitching statistics validation
        if has_pitching_data:
            pitching_issues = self._validate_pitching_stats(
                yahoo_player_id, player_name, date_str,
                pitching_games_started, pitching_wins, pitching_losses,
                pitching_saves, pitching_holds, pitching_innings_pitched,
                pitching_hits_allowed, pitching_runs_allowed, pitching_earned_runs,
                pitching_walks_allowed, pitching_strikeouts_p, pitching_home_runs_allowed,
                pitching_era, pitching_whip, pitching_quality_starts
            )
            issues.extend(pitching_issues)
        
        # Data consistency validation
        if not has_batting_data and not has_pitching_data:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data_consistency",
                description="Player has neither batting nor pitching data",
                player_id=yahoo_player_id,
                player_name=player_name,
                date=date_str
            ))
        
        # Confidence score validation
        if confidence_score is not None:
            if confidence_score < 0.0 or confidence_score > 1.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_range",
                    description="Confidence score out of range",
                    field_name="confidence_score",
                    player_id=yahoo_player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=confidence_score,
                    expected_range=(0.0, 1.0)
                ))
            elif confidence_score < 0.5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="low_confidence",
                    description="Low confidence score for player mapping",
                    field_name="confidence_score",
                    player_id=yahoo_player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=confidence_score
                ))
        
        return issues
    
    def _validate_batting_stats(self, player_id: str, player_name: str, date_str: str,
                               at_bats, runs, hits, doubles, triples, home_runs, 
                               rbis, stolen_bases, walks, strikeouts, 
                               avg, obp, slg, ops) -> List[ValidationIssue]:
        """Validate batting statistics for logical consistency."""
        issues = []
        
        # Basic range validations
        if at_bats is not None and at_bats < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="Negative at-bats",
                field_name="batting_at_bats",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                actual_value=at_bats
            ))
        
        if hits is not None and hits < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="Negative hits",
                field_name="batting_hits",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                actual_value=hits
            ))
        
        # Logical consistency checks
        if at_bats is not None and hits is not None and hits > at_bats:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data_consistency",
                description="Hits cannot exceed at-bats",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                context={"hits": hits, "at_bats": at_bats}
            ))
        
        if hits is not None and doubles is not None and triples is not None and home_runs is not None:
            extra_base_hits = (doubles or 0) + (triples or 0) + (home_runs or 0)
            if extra_base_hits > hits:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="data_consistency",
                    description="Extra base hits cannot exceed total hits",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    context={"hits": hits, "extra_base_hits": extra_base_hits}
                ))
        
        # Statistical range validations
        if avg is not None:
            if avg < 0.0 or avg > 1.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_range",
                    description="Batting average out of valid range",
                    field_name="batting_avg",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=avg,
                    expected_range=(0.0, 1.0)
                ))
        
        if obp is not None and (obp < 0.0 or obp > 1.0):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="On-base percentage out of valid range",
                field_name="batting_obp",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                actual_value=obp,
                expected_range=(0.0, 1.0)
            ))
        
        if slg is not None and (slg < 0.0 or slg > 5.0):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="Slugging percentage out of reasonable range",
                field_name="batting_slg",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                actual_value=slg,
                expected_range=(0.0, 5.0)
            ))
        
        # Consistency between calculated stats
        if obp is not None and avg is not None and obp < avg:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="data_consistency",
                description="On-base percentage should not be less than batting average",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                context={"obp": obp, "avg": avg}
            ))
        
        return issues
    
    def _validate_pitching_stats(self, player_id: str, player_name: str, date_str: str,
                                games_started, wins, losses, saves, holds,
                                innings_pitched, hits_allowed, runs_allowed, earned_runs,
                                walks_allowed, strikeouts, home_runs_allowed,
                                era, whip, quality_starts) -> List[ValidationIssue]:
        """Validate pitching statistics for logical consistency."""
        issues = []
        
        # Basic range validations
        if innings_pitched is not None and innings_pitched < 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="invalid_range",
                description="Negative innings pitched",
                field_name="pitching_innings_pitched",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                actual_value=innings_pitched
            ))
        
        if earned_runs is not None and runs_allowed is not None and earned_runs > runs_allowed:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="data_consistency",
                description="Earned runs cannot exceed total runs allowed",
                player_id=player_id,
                player_name=player_name,
                date=date_str,
                context={"earned_runs": earned_runs, "runs_allowed": runs_allowed}
            ))
        
        # ERA validation
        if era is not None:
            if era < 0.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_range",
                    description="Negative ERA",
                    field_name="pitching_era",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=era
                ))
            elif era > self.validation_config['max_era']:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="unusual_value",
                    description="Extremely high ERA",
                    field_name="pitching_era",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=era,
                    expected_range=(0.0, self.validation_config['max_era'])
                ))
        
        # WHIP validation
        if whip is not None:
            if whip < 0.0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_range",
                    description="Negative WHIP",
                    field_name="pitching_whip",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=whip
                ))
            elif whip > self.validation_config['max_whip']:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="unusual_value",
                    description="Extremely high WHIP",
                    field_name="pitching_whip",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    actual_value=whip,
                    expected_range=(0.0, self.validation_config['max_whip'])
                ))
        
        # Quality starts validation
        if quality_starts is not None and games_started is not None:
            if quality_starts > games_started:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="data_consistency",
                    description="Quality starts cannot exceed games started",
                    player_id=player_id,
                    player_name=player_name,
                    date=date_str,
                    context={"quality_starts": quality_starts, "games_started": games_started}
                ))
        
        return issues
    
    def _detect_anomalies(self, records: List[Tuple], target_date: date) -> List[ValidationIssue]:
        """Detect statistical anomalies in the day's data."""
        issues = []
        
        # Extract values for anomaly detection
        home_runs = [r[14] for r in records if r[14] is not None and r[5]]  # batting_home_runs where has_batting_data
        rbis = [r[15] for r in records if r[15] is not None and r[5]]  # batting_rbis
        eras = [r[32] for r in records if r[32] is not None and r[6]]  # pitching_era where has_pitching_data
        
        # Detect extreme home run performances
        if home_runs:
            max_hrs = max(home_runs)
            if max_hrs > 4:  # More than 4 HRs in a game is extremely rare
                # Find the player(s) with this performance
                for record in records:
                    if record[14] == max_hrs:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="anomaly",
                            description=f"Unusual single-game home run performance: {max_hrs} HRs",
                            field_name="batting_home_runs",
                            player_id=record[0],
                            player_name=record[1],
                            date=target_date.isoformat(),
                            actual_value=max_hrs
                        ))
        
        # Detect extreme ERA performances (for games with significant innings)
        if eras:
            max_era = max(eras)
            if max_era > 30.0:  # Extremely high single-game ERA
                for record in records:
                    if record[32] == max_era and record[26] and record[26] > 1.0:  # innings_pitched > 1
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="anomaly",
                            description=f"Unusual single-game ERA: {max_era:.2f}",
                            field_name="pitching_era",
                            player_id=record[0],
                            player_name=record[1],
                            date=target_date.isoformat(),
                            actual_value=max_era
                        ))
        
        return issues
    
    def _detect_range_anomalies(self, start_date: date, end_date: date) -> List[ValidationIssue]:
        """Detect anomalies across a date range."""
        issues = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Look for players with impossible stat combinations over time
            cursor.execute(f"""
                SELECT yahoo_player_id, player_name,
                       SUM(batting_hits) as total_hits,
                       SUM(batting_at_bats) as total_at_bats,
                       AVG(batting_avg) as avg_batting_avg
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
                AND has_batting_data = 1
                AND batting_hits IS NOT NULL
                AND batting_at_bats IS NOT NULL
                AND batting_at_bats > 0
                GROUP BY yahoo_player_id, player_name
                HAVING COUNT(*) > 3  -- Multiple games
            """, (start_date.isoformat(), end_date.isoformat()))
            
            for row in cursor.fetchall():
                player_id, player_name, total_hits, total_at_bats, avg_batting_avg = row
                
                # Calculate actual average from totals
                if total_at_bats > 0:
                    calculated_avg = total_hits / total_at_bats
                    
                    # Compare with reported average (allowing for rounding differences)
                    if avg_batting_avg and abs(calculated_avg - avg_batting_avg) > 0.1:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            category="data_consistency",
                            description=f"Batting average inconsistency over date range",
                            player_id=player_id,
                            player_name=player_name,
                            context={
                                "calculated_avg": calculated_avg,
                                "reported_avg": avg_batting_avg,
                                "date_range": f"{start_date} to {end_date}"
                            }
                        ))
            
        finally:
            conn.close()
        
        return issues
    
    def _generate_summary_stats(self, records: List[Tuple], issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate summary statistics for validation report."""
        if not records:
            return {}
        
        summary = {
            'total_records': len(records),
            'records_with_batting': len([r for r in records if r[5]]),  # has_batting_data
            'records_with_pitching': len([r for r in records if r[6]]),  # has_pitching_data
            'unique_players': len(set(r[0] for r in records)),  # unique yahoo_player_ids
            'unique_teams': len(set(r[2] for r in records if r[2])),  # unique team_codes
            'issues_by_severity': {},
            'issues_by_category': {},
            'quality_metrics': {}
        }
        
        # Categorize issues
        for issue in issues:
            severity = issue.severity.value
            category = issue.category
            
            summary['issues_by_severity'][severity] = summary['issues_by_severity'].get(severity, 0) + 1
            summary['issues_by_category'][category] = summary['issues_by_category'].get(category, 0) + 1
        
        # Calculate quality metrics
        if summary['total_records'] > 0:
            summary['quality_metrics']['error_rate'] = len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) / summary['total_records']
            summary['quality_metrics']['warning_rate'] = len([i for i in issues if i.severity == ValidationSeverity.WARNING]) / summary['total_records']
            summary['quality_metrics']['overall_quality_score'] = max(0.0, 1.0 - summary['quality_metrics']['error_rate'] - (summary['quality_metrics']['warning_rate'] * 0.5))
        
        return summary
    
    def _generate_range_summary(self, start_date: date, end_date: date, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate summary statistics for date range validation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT date) as dates_with_data,
                    COUNT(DISTINCT yahoo_player_id) as unique_players,
                    COUNT(CASE WHEN has_batting_data THEN 1 END) as records_with_batting,
                    COUNT(CASE WHEN has_pitching_data THEN 1 END) as records_with_pitching,
                    AVG(confidence_score) as avg_confidence
                FROM {self.stats_table}
                WHERE date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            
            row = cursor.fetchone()
            
            summary = {
                'date_range': f"{start_date} to {end_date}",
                'total_records': row[0] if row else 0,
                'dates_with_data': row[1] if row else 0,
                'unique_players': row[2] if row else 0,
                'records_with_batting': row[3] if row else 0,
                'records_with_pitching': row[4] if row else 0,
                'avg_confidence': row[5] if row and row[5] else 0.0,
                'issues_by_severity': {},
                'issues_by_category': {},
                'quality_metrics': {}
            }
            
            # Categorize issues
            for issue in issues:
                severity = issue.severity.value
                category = issue.category
                
                summary['issues_by_severity'][severity] = summary['issues_by_severity'].get(severity, 0) + 1
                summary['issues_by_category'][category] = summary['issues_by_category'].get(category, 0) + 1
            
            # Calculate quality metrics
            if summary['total_records'] > 0:
                summary['quality_metrics']['error_rate'] = len([i for i in issues if i.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]) / summary['total_records']
                summary['quality_metrics']['warning_rate'] = len([i for i in issues if i.severity == ValidationSeverity.WARNING]) / summary['total_records']
                summary['quality_metrics']['overall_quality_score'] = max(0.0, 1.0 - summary['quality_metrics']['error_rate'] - (summary['quality_metrics']['warning_rate'] * 0.5))
            
            return summary
            
        finally:
            conn.close()


def main():
    """Command-line interface for data validation operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Player Stats Data Validation")
    parser.add_argument("action", choices=["validate", "range"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--date", help="Date for single validation (YYYY-MM-DD)")
    parser.add_argument("--start-date", help="Start date for range validation (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for range validation (YYYY-MM-DD)")
    parser.add_argument("--no-anomaly", action="store_true",
                       help="Disable anomaly detection")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--show-all", action="store_true",
                       help="Show all issues (not just summary)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = PlayerStatsValidator(environment=args.env)
    
    if args.action == "validate":
        if not args.date:
            print("ERROR: --date is required for single date validation")
            return
        
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Validating player stats for {target_date}...")
        print("-" * 60)
        
        report = validator.validate_date(target_date, enable_anomaly_detection=not args.no_anomaly)
        
        print(f"Validation {'PASSED' if report.is_valid else 'FAILED'}")
        print(f"Records validated: {report.total_records_validated}")
        print(f"Issues found: {len(report.issues)} ({report.error_count} errors, {report.warning_count} warnings)")
        
        if report.summary_stats.get('quality_metrics'):
            quality = report.summary_stats['quality_metrics']['overall_quality_score']
            print(f"Overall quality score: {quality:.1%}")
        
        if args.show_all and report.issues:
            print("\nIssues found:")
            for issue in report.issues:
                print(f"  {issue.severity.value.upper()}: {issue.description}")
                if issue.player_name:
                    print(f"    Player: {issue.player_name}")
                if issue.actual_value is not None:
                    print(f"    Value: {issue.actual_value}")
    
    elif args.action == "range":
        if not args.start_date or not args.end_date:
            print("ERROR: --start-date and --end-date are required for range validation")
            return
        
        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            return
        
        print(f"Validating player stats from {start_date} to {end_date}...")
        print("-" * 60)
        
        report = validator.validate_date_range(start_date, end_date, enable_anomaly_detection=not args.no_anomaly)
        
        print(f"Validation {'PASSED' if report.is_valid else 'FAILED'}")
        print(f"Records validated: {report.total_records_validated}")
        print(f"Issues found: {len(report.issues)} ({report.error_count} errors, {report.warning_count} warnings)")
        
        if report.summary_stats.get('quality_metrics'):
            quality = report.summary_stats['quality_metrics']['overall_quality_score']
            print(f"Overall quality score: {quality:.1%}")
        
        if report.summary_stats.get('issues_by_category'):
            print("\nIssues by category:")
            for category, count in report.summary_stats['issues_by_category'].items():
                print(f"  {category}: {count}")


if __name__ == "__main__":
    main()