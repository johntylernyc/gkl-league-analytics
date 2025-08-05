#!/usr/bin/env python3
"""
Player Stats Data Quality Validation Module

Validates player statistics data for completeness, accuracy, and consistency.
Follows patterns established in daily_lineups and league_transactions modules.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PlayerStatsDataQualityChecker:
    """Validates player statistics data quality."""
    
    def __init__(self):
        self.validation_rules = {
            'required_fields': [
                'date', 'yahoo_player_id', 'player_name', 'team_code'
            ],
            'stat_bounds': {
                'batting_avg': (0.0, 1.0),
                'batting_obp': (0.0, 1.0),
                'batting_slg': (0.0, 5.0),
                'pitching_era': (0.0, 30.0),
                'pitching_whip': (0.0, 10.0)
            },
            'valid_positions': [
                'C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 
                'SP', 'RP', 'P', 'BN', 'IL', 'IL+', 'NA'
            ]
        }
    
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
    
    def check_player_mappings(self, conn) -> Dict[str, Any]:
        """Check player ID mapping quality."""
        cursor = conn.cursor()
        
        # Get mapping statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_mappings,
                COUNT(CASE WHEN confidence_score >= 0.9 THEN 1 END) as high_confidence,
                COUNT(CASE WHEN confidence_score < 0.7 THEN 1 END) as low_confidence,
                COUNT(CASE WHEN validation_status = 'failed' THEN 1 END) as failed_mappings,
                AVG(confidence_score) as avg_confidence
            FROM player_id_mapping
            WHERE is_active = TRUE
        """)
        
        result = cursor.fetchone()
        
        return {
            'total_mappings': result[0],
            'high_confidence': result[1],
            'low_confidence': result[2],
            'failed_mappings': result[3],
            'avg_confidence': result[4] or 0
        }
    
    def generate_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate human-readable validation report."""
        report = []
        report.append("=" * 60)
        report.append("PLAYER STATS DATA QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Records: {validation_results['total']}")
        report.append(f"Valid Records: {validation_results['valid']} "
                     f"({validation_results['valid']/validation_results['total']*100:.1f}%)")
        report.append(f"Invalid Records: {validation_results['invalid']}")
        report.append(f"Total Warnings: {validation_results['warnings']}")
        report.append("")
        
        # Error breakdown
        if validation_results['errors_by_type']:
            report.append("ERROR BREAKDOWN")
            report.append("-" * 20)
            for error_type, count in sorted(validation_results['errors_by_type'].items()):
                report.append(f"{error_type}: {count}")
            report.append("")
        
        # Sample errors
        if validation_results['sample_errors']:
            report.append("SAMPLE ERRORS")
            report.append("-" * 20)
            for i, sample in enumerate(validation_results['sample_errors'], 1):
                report.append(f"{i}. Player: {sample['player']} (Date: {sample['date']})")
                for error in sample['errors']:
                    report.append(f"   - {error}")
            report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)


# CLI interface
if __name__ == "__main__":
    import argparse
    import sqlite3
    from config import get_config_for_environment
    
    parser = argparse.ArgumentParser(description="Validate player stats data quality")
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'])
    parser.add_argument('--date', help='Validate specific date')
    parser.add_argument('--check-mappings', action='store_true',
                       help='Check player ID mapping quality')
    
    args = parser.parse_args()
    
    # Connect to database
    config = get_config_for_environment(args.environment)
    conn = sqlite3.connect(config['database_path'])
    
    checker = PlayerStatsDataQualityChecker()
    
    if args.check_mappings:
        mapping_stats = checker.check_player_mappings(conn)
        print("\nPLAYER ID MAPPING STATISTICS")
        print("-" * 30)
        for key, value in mapping_stats.items():
            print(f"{key}: {value}")
    
    # Validate recent stats
    query = "SELECT * FROM daily_gkl_player_stats"
    params = []
    
    if args.date:
        query += " WHERE date = ?"
        params.append(args.date)
    else:
        query += " WHERE date >= date('now', '-7 days')"
    
    query += " LIMIT 1000"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    # Convert to dict format
    columns = [desc[0] for desc in cursor.description]
    records = []
    for row in cursor.fetchall():
        records.append(dict(zip(columns, row)))
    
    if records:
        results = checker.validate_batch(records)
        print(checker.generate_report(results))
    else:
        print("No records found to validate")
    
    conn.close()