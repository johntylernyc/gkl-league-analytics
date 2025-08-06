#!/usr/bin/env python3
"""
Player Stats Data Quality Check Script

Comprehensive validation of MLB player statistics data quality.
Checks for completeness, accuracy, consistency, and anomalies.

Usage:
    # Check test database
    python data_quality_check.py
    
    # Check production database
    python data_quality_check.py --environment production
    
    # Check specific date range
    python data_quality_check.py --start 2024-08-01 --end 2024-08-05
    
    # Check D1 database
    python data_quality_check.py --use-d1
    
    # Generate detailed report
    python data_quality_check.py --detailed
    
    # Export issues to CSV
    python data_quality_check.py --export issues.csv
"""

import sys
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional, Any
import csv

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlayerStatsDataQualityChecker:
    """Comprehensive data quality validation for player statistics"""
    
    def __init__(self, environment='test', use_d1=False):
        """
        Initialize data quality checker.
        
        Args:
            environment: 'test' or 'production' for local databases
            use_d1: If True, check Cloudflare D1
        """
        self.environment = environment
        self.use_d1 = use_d1
        
        # Connect to database
        if use_d1:
            from data_pipeline.common.d1_connection import D1Connection
            self.d1_conn = D1Connection()
            self.conn = None
        else:
            config = get_config_for_environment(environment)
            self.conn = sqlite3.connect(config['database_path'])
        
        # Validation thresholds
        self.thresholds = {
            'min_players_per_day': 200,  # Expect at least 200 players per day
            'max_players_per_day': 400,  # No more than 400 players per day
            'min_yahoo_coverage': 0.50,  # At least 50% should have Yahoo IDs
            'max_batting_avg': 1.000,    # No batting average above 1.000
            'max_era': 50.00,            # ERA above 50 is suspicious
            'max_home_runs_per_game': 5, # More than 5 HRs in a game is rare
        }
        
        # Legacy validation rules for compatibility
        self.validation_rules = {
            'required_fields': [
                'date', 'player_name', 'mlb_id'
            ],
            'stat_bounds': {
                'batting_avg': (0.0, 1.0),
                'batting_obp': (0.0, 1.0),
                'batting_slg': (0.0, 5.0),
                'pitching_era': (0.0, 30.0),
                'pitching_whip': (0.0, 10.0)
            }
        }
        
        logger.info(f"Initialized checker for {environment} {'with D1' if use_d1 else 'with SQLite'}")
    
    def execute_query(self, query: str, params: tuple = ()) -> List:
        """Execute query on appropriate database"""
        if self.use_d1:
            return self.d1_conn.execute(query, params).fetchall()
        else:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def validate_single(self, stat_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single player stat record.
        
        Returns:
            Dict with keys: is_valid, errors, warnings
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.validation_rules['required_fields']:
            if field not in stat_record or stat_record[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate stat bounds
        for stat_name, (min_val, max_val) in self.validation_rules['stat_bounds'].items():
            if stat_name in stat_record and stat_record[stat_name] is not None:
                value = stat_record[stat_name]
                if not (min_val <= value <= max_val):
                    errors.append(f"{stat_name} out of bounds: {value} (expected {min_val}-{max_val})")
        
        # Validate player ID mapping
        if 'yahoo_player_id' in stat_record and not stat_record.get('mapping_confidence'):
            warnings.append("No player ID mapping confidence score")
        
        # Check data consistency
        if stat_record.get('games_played', 0) == 0:
            if any(stat_record.get(f'batting_{stat}', 0) > 0 for stat in ['hits', 'runs', 'rbis']):
                errors.append("Player has batting stats but games_played is 0")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_batch(self, stat_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of player stat records."""
        results = {
            'total': len(stat_records),
            'valid': 0,
            'invalid': 0,
            'warnings': 0,
            'errors_by_type': {},
            'sample_errors': []
        }
        
        for record in stat_records:
            validation = self.validate_single(record)
            
            if validation['is_valid']:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                
                # Track error types
                for error in validation['errors']:
                    error_type = error.split(':')[0]
                    results['errors_by_type'][error_type] = \
                        results['errors_by_type'].get(error_type, 0) + 1
                
                # Keep sample of errors
                if len(results['sample_errors']) < 5:
                    results['sample_errors'].append({
                        'player': record.get('player_name', 'Unknown'),
                        'date': record.get('date', 'Unknown'),
                        'errors': validation['errors']
                    })
            
            if validation['warnings']:
                results['warnings'] += len(validation['warnings'])
        
        return results
    
    def check_data_completeness(self, start_date: str = None, end_date: str = None) -> Dict:
        """
        Check data completeness.
        
        Returns:
            Dictionary with completeness metrics
        """
        logger.info("Checking data completeness...")
        
        # Date range filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE date >= ?"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE date <= ?"
            params = [end_date]
        
        # Check daily coverage
        query = f"""
            SELECT 
                date,
                COUNT(DISTINCT mlb_id) as player_count,
                COUNT(DISTINCT CASE WHEN yahoo_player_id IS NOT NULL THEN mlb_id END) as yahoo_count,
                COUNT(DISTINCT CASE WHEN has_batting_data = 1 THEN mlb_id END) as batters,
                COUNT(DISTINCT CASE WHEN has_pitching_data = 1 THEN mlb_id END) as pitchers
            FROM daily_gkl_player_stats
            {date_filter}
            GROUP BY date
            ORDER BY date DESC
        """
        
        daily_stats = self.execute_query(query, tuple(params))
        
        issues = []
        for row in daily_stats:
            date_str, players, yahoo, batters, pitchers = row
            
            # Check player count
            if players < self.thresholds['min_players_per_day']:
                issues.append({
                    'date': date_str,
                    'type': 'low_player_count',
                    'message': f"Only {players} players on {date_str} (expected >= {self.thresholds['min_players_per_day']})"
                })
            elif players > self.thresholds['max_players_per_day']:
                issues.append({
                    'date': date_str,
                    'type': 'high_player_count',
                    'message': f"{players} players on {date_str} (expected <= {self.thresholds['max_players_per_day']})"
                })
            
            # Check Yahoo coverage
            yahoo_pct = yahoo / players if players > 0 else 0
            if yahoo_pct < self.thresholds['min_yahoo_coverage']:
                issues.append({
                    'date': date_str,
                    'type': 'low_yahoo_coverage',
                    'message': f"Only {yahoo_pct:.1%} Yahoo coverage on {date_str}"
                })
        
        # Check for missing dates
        if daily_stats:
            all_dates = [row[0] for row in daily_stats]
            first_date = datetime.strptime(min(all_dates), '%Y-%m-%d').date()
            last_date = datetime.strptime(max(all_dates), '%Y-%m-%d').date()
            
            expected_dates = []
            current = first_date
            while current <= last_date:
                expected_dates.append(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
            
            missing_dates = set(expected_dates) - set(all_dates)
            for date_str in missing_dates:
                issues.append({
                    'date': date_str,
                    'type': 'missing_date',
                    'message': f"No data for {date_str}"
                })
        
        return {
            'total_days': len(daily_stats),
            'issues': issues,
            'daily_stats': daily_stats[:10]  # First 10 for summary
        }
    
    def check_stat_validity(self) -> Dict:
        """
        Check for invalid or suspicious statistics.
        
        Returns:
            Dictionary with validity issues
        """
        logger.info("Checking stat validity...")
        
        issues = []
        
        # Check batting averages
        query = """
            SELECT date, player_name, batting_avg, batting_hits, batting_at_bats
            FROM daily_gkl_player_stats
            WHERE batting_avg > ? AND batting_at_bats > 0
        """
        
        invalid_avg = self.execute_query(query, (self.thresholds['max_batting_avg'],))
        for row in invalid_avg:
            issues.append({
                'type': 'invalid_batting_avg',
                'player': row[1],
                'date': row[0],
                'message': f"{row[1]} has AVG of {row[2]:.3f} ({row[3]}H/{row[4]}AB) on {row[0]}"
            })
        
        # Check ERAs
        query = """
            SELECT date, player_name, pitching_era, pitching_earned_runs, pitching_innings_pitched
            FROM daily_gkl_player_stats
            WHERE pitching_era > ? AND pitching_innings_pitched > 0
        """
        
        high_era = self.execute_query(query, (self.thresholds['max_era'],))
        for row in high_era:
            issues.append({
                'type': 'suspicious_era',
                'player': row[1],
                'date': row[0],
                'message': f"{row[1]} has ERA of {row[2]:.2f} ({row[3]}ER/{row[4]}IP) on {row[0]}"
            })
        
        # Check home runs
        query = """
            SELECT date, player_name, batting_home_runs
            FROM daily_gkl_player_stats
            WHERE batting_home_runs > ?
        """
        
        high_hr = self.execute_query(query, (self.thresholds['max_home_runs_per_game'],))
        for row in high_hr:
            issues.append({
                'type': 'suspicious_home_runs',
                'player': row[1],
                'date': row[0],
                'message': f"{row[1]} hit {row[2]} home runs on {row[0]}"
            })
        
        # Check for negative values
        query = """
            SELECT date, player_name, 'negative_stat' as issue
            FROM daily_gkl_player_stats
            WHERE batting_hits < 0 OR batting_runs < 0 OR batting_rbis < 0
               OR pitching_wins < 0 OR pitching_strikeouts < 0
        """
        
        negative_stats = self.execute_query(query)
        for row in negative_stats:
            issues.append({
                'type': 'negative_value',
                'player': row[1],
                'date': row[0],
                'message': f"{row[1]} has negative stat values on {row[0]}"
            })
        
        return {
            'total_issues': len(issues),
            'issues': issues
        }
    
    def check_id_mappings(self) -> Dict:
        """
        Check player ID mapping completeness.
        
        Returns:
            Dictionary with mapping statistics
        """
        logger.info("Checking ID mappings...")
        
        # Overall mapping stats
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo,
                COUNT(baseball_reference_id) as with_bbref,
                COUNT(fangraphs_id) as with_fg
            FROM player_mapping
            WHERE active = 1
        """
        
        mapping_stats = self.execute_query(query)[0]
        
        # Players in stats without mappings
        query = """
            SELECT COUNT(DISTINCT ds.mlb_id)
            FROM daily_gkl_player_stats ds
            LEFT JOIN player_mapping pm ON ds.mlb_id = pm.mlb_id
            WHERE pm.mlb_id IS NULL
        """
        
        unmapped = self.execute_query(query)[0][0]
        
        # Yahoo ID coverage in daily stats
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(yahoo_player_id) as with_yahoo
            FROM daily_gkl_player_stats
        """
        
        stats_coverage = self.execute_query(query)[0]
        
        return {
            'total_players': mapping_stats[0],
            'yahoo_mapped': mapping_stats[1],
            'yahoo_pct': mapping_stats[1] / mapping_stats[0] * 100 if mapping_stats[0] > 0 else 0,
            'bbref_mapped': mapping_stats[2],
            'bbref_pct': mapping_stats[2] / mapping_stats[0] * 100 if mapping_stats[0] > 0 else 0,
            'fg_mapped': mapping_stats[3],
            'fg_pct': mapping_stats[3] / mapping_stats[0] * 100 if mapping_stats[0] > 0 else 0,
            'unmapped_in_stats': unmapped,
            'stats_yahoo_coverage': stats_coverage[1] / stats_coverage[0] * 100 if stats_coverage[0] > 0 else 0
        }
    
    def check_data_freshness(self) -> Dict:
        """
        Check how current the data is.
        
        Returns:
            Dictionary with freshness metrics
        """
        logger.info("Checking data freshness...")
        
        # Get latest date
        query = "SELECT MAX(date) FROM daily_gkl_player_stats"
        latest = self.execute_query(query)[0][0]
        
        if latest:
            latest_date = datetime.strptime(latest, '%Y-%m-%d').date()
            days_behind = (date.today() - latest_date).days
        else:
            latest_date = None
            days_behind = None
        
        # Get date range
        query = """
            SELECT 
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(DISTINCT date) as total_days
            FROM daily_gkl_player_stats
        """
        
        range_stats = self.execute_query(query)[0]
        
        return {
            'latest_date': latest,
            'days_behind': days_behind,
            'is_current': days_behind <= 2 if days_behind is not None else False,
            'first_date': range_stats[0],
            'last_date': range_stats[1],
            'total_days': range_stats[2]
        }
    
    def generate_report(self, start_date: str = None, end_date: str = None, 
                       detailed: bool = False) -> Dict:
        """
        Generate comprehensive data quality report.
        
        Args:
            start_date: Start date for checks
            end_date: End date for checks
            detailed: Include detailed issue listings
            
        Returns:
            Complete quality report
        """
        logger.info("Generating data quality report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment,
            'database': 'D1' if self.use_d1 else 'SQLite',
            'completeness': self.check_data_completeness(start_date, end_date),
            'validity': self.check_stat_validity(),
            'mappings': self.check_id_mappings(),
            'freshness': self.check_data_freshness()
        }
        
        # Calculate overall health score
        score = 100.0
        
        # Deduct for completeness issues
        completeness_issues = len(report['completeness']['issues'])
        score -= min(20, completeness_issues * 2)
        
        # Deduct for validity issues
        validity_issues = report['validity']['total_issues']
        score -= min(30, validity_issues * 3)
        
        # Deduct for mapping coverage
        yahoo_pct = report['mappings']['yahoo_pct']
        if yahoo_pct < 70:
            score -= (70 - yahoo_pct) * 0.3
        
        # Deduct for staleness
        days_behind = report['freshness']['days_behind']
        if days_behind and days_behind > 2:
            score -= min(20, days_behind * 2)
        
        report['health_score'] = max(0, score)
        report['health_grade'] = self._get_health_grade(score)
        
        if not detailed:
            # Remove detailed issue lists for summary report
            report['completeness'].pop('issues', None)
            report['validity'].pop('issues', None)
        
        return report
    
    def _get_health_grade(self, score: float) -> str:
        """Convert health score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def export_issues(self, filepath: str, report: Dict):
        """Export issues to CSV file"""
        logger.info(f"Exporting issues to {filepath}")
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Type', 'Date', 'Player', 'Message'])
            
            # Completeness issues
            for issue in report['completeness'].get('issues', []):
                writer.writerow([
                    'Completeness',
                    issue['type'],
                    issue.get('date', ''),
                    '',
                    issue['message']
                ])
            
            # Validity issues
            for issue in report['validity'].get('issues', []):
                writer.writerow([
                    'Validity',
                    issue['type'],
                    issue.get('date', ''),
                    issue.get('player', ''),
                    issue['message']
                ])
        
        logger.info(f"Exported issues to {filepath}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Check player statistics data quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Database options
    parser.add_argument('--environment', default='test',
                       choices=['test', 'production'],
                       help='Database environment (default: test)')
    parser.add_argument('--use-d1', action='store_true',
                       help='Check Cloudflare D1 database')
    
    # Date range options
    parser.add_argument('--start', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', help='End date (YYYY-MM-DD)')
    
    # Output options
    parser.add_argument('--detailed', action='store_true',
                       help='Include detailed issue listings')
    parser.add_argument('--export', help='Export issues to CSV file')
    
    args = parser.parse_args()
    
    # Initialize checker
    checker = PlayerStatsDataQualityChecker(
        environment=args.environment,
        use_d1=args.use_d1
    )
    
    # Generate report
    report = checker.generate_report(
        start_date=args.start,
        end_date=args.end,
        detailed=args.detailed
    )
    
    # Display report
    print("\n" + "="*60)
    print("PLAYER STATS DATA QUALITY REPORT")
    print("="*60)
    print(f"Environment: {report['environment']}")
    print(f"Database: {report['database']}")
    print(f"Report Time: {report['timestamp'][:19]}")
    
    print(f"\nOVERALL HEALTH: {report['health_score']:.1f}/100 (Grade: {report['health_grade']})")
    
    print(f"\nDATA FRESHNESS:")
    print(f"  Latest Date: {report['freshness']['latest_date']}")
    print(f"  Days Behind: {report['freshness']['days_behind']}")
    print(f"  Total Days: {report['freshness']['total_days']}")
    
    print(f"\nID MAPPING COVERAGE:")
    print(f"  Yahoo: {report['mappings']['yahoo_pct']:.1f}%")
    print(f"  Baseball Reference: {report['mappings']['bbref_pct']:.1f}%")
    print(f"  FanGraphs: {report['mappings']['fg_pct']:.1f}%")
    
    print(f"\nDATA COMPLETENESS:")
    print(f"  Days Analyzed: {report['completeness']['total_days']}")
    print(f"  Issues Found: {len(report['completeness'].get('issues', []))}")
    
    print(f"\nDATA VALIDITY:")
    print(f"  Issues Found: {report['validity']['total_issues']}")
    
    if args.detailed and report['completeness'].get('issues'):
        print("\nCOMPLETENESS ISSUES:")
        for issue in report['completeness']['issues'][:10]:
            print(f"  - {issue['message']}")
    
    if args.detailed and report['validity'].get('issues'):
        print("\nVALIDITY ISSUES:")
        for issue in report['validity']['issues'][:10]:
            print(f"  - {issue['message']}")
    
    # Export if requested
    if args.export:
        checker.export_issues(args.export, report)
        print(f"\nIssues exported to: {args.export}")


if __name__ == '__main__':
    main()