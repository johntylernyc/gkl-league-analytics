#!/usr/bin/env python
"""
Transaction Data Quality Check Module

This module provides comprehensive data quality validation for transaction records
to ensure completeness and integrity before and after database insertion.
"""

import logging
import sqlite3
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TransactionDataQualityChecker:
    """Validates transaction data completeness and quality"""
    
    # Required fields for all transactions
    REQUIRED_FIELDS = [
        'date',
        'league_key',
        'transaction_id',
        'transaction_type',
        'player_id',
        'player_name',
        'movement_type',
        'job_id'
    ]
    
    # Required fields for specific transaction types
    CONDITIONAL_FIELDS = {
        'add': ['destination_team_key', 'destination_team_name', 'player_position', 'player_team'],
        'drop': ['source_team_key', 'source_team_name', 'player_position', 'player_team'],
        'add/drop': ['destination_team_key', 'destination_team_name', 'source_team_key', 'source_team_name', 'player_position', 'player_team'],
        'trade': ['destination_team_key', 'destination_team_name', 'source_team_key', 'source_team_name', 'player_position', 'player_team']
    }
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_transaction(self, transaction: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a single transaction for completeness.
        
        Args:
            transaction: Transaction dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in transaction or not transaction[field]:
                issues.append(f"Missing required field: {field}")
        
        # Check conditional fields based on transaction type
        if 'transaction_type' in transaction:
            trans_type = transaction['transaction_type']
            if trans_type in self.CONDITIONAL_FIELDS:
                for field in self.CONDITIONAL_FIELDS[trans_type]:
                    if field not in transaction or not transaction[field]:
                        # Allow source fields to be empty for free agent adds
                        if not (field.startswith('source_') and trans_type in ['add', 'add/drop']):
                            issues.append(f"Missing {trans_type} field: {field}")
        
        # For add/drop transactions, ensure both movements are captured
        if transaction.get('transaction_type') == 'add/drop':
            if transaction.get('movement_type') not in ['add', 'drop', 'add/drop']:
                issues.append(f"Invalid movement_type for add/drop: {transaction.get('movement_type')}")
        
        # Validate date format
        if 'date' in transaction:
            try:
                datetime.strptime(transaction['date'], '%Y-%m-%d')
            except (ValueError, TypeError):
                issues.append(f"Invalid date format: {transaction.get('date')}")
        
        # Validate player_id is numeric
        if 'player_id' in transaction:
            try:
                int(transaction['player_id'])
            except (ValueError, TypeError):
                issues.append(f"Invalid player_id: {transaction.get('player_id')}")
        
        return len(issues) == 0, issues
    
    def validate_batch(self, transactions: List[Dict]) -> Dict:
        """
        Validate a batch of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Dictionary with validation results
        """
        valid_count = 0
        invalid_transactions = []
        
        for i, trans in enumerate(transactions):
            is_valid, issues = self.validate_transaction(trans)
            if is_valid:
                valid_count += 1
            else:
                invalid_transactions.append({
                    'index': i,
                    'transaction': trans,
                    'issues': issues
                })
        
        return {
            'total': len(transactions),
            'valid': valid_count,
            'invalid': len(invalid_transactions),
            'invalid_transactions': invalid_transactions,
            'validation_rate': (valid_count / len(transactions) * 100) if transactions else 0
        }
    
    def validate_database_records(self, db_path: str, job_id: Optional[str] = None, date_range: Optional[Tuple[str, str]] = None) -> Dict:
        """
        Validate transaction records in the database.
        
        Args:
            db_path: Path to the database
            job_id: Optional job_id to filter records
            date_range: Optional tuple of (start_date, end_date)
            
        Returns:
            Dictionary with validation results
        """
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        
        if date_range:
            query += " AND date BETWEEN ? AND ?"
            params.extend(date_range)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        transactions = [dict(row) for row in rows]
        
        # Validate
        results = self.validate_batch(transactions)
        
        # Add specific checks for add/drop completeness
        if job_id or date_range:
            # Check for add/drop transactions that might be missing counterparts
            cursor.execute("""
                SELECT date, player_name, transaction_type, movement_type, COUNT(*) as count
                FROM transactions
                WHERE transaction_type = 'add/drop'
                  AND (job_id = ? OR (date BETWEEN ? AND ?))
                GROUP BY date, player_name, transaction_type
                HAVING count = 1
            """, [job_id] + list(date_range) if date_range else [None, None])
            
            incomplete_add_drops = cursor.fetchall()
            if incomplete_add_drops:
                results['incomplete_add_drops'] = [dict(row) for row in incomplete_add_drops]
                results['warnings'] = f"Found {len(incomplete_add_drops)} add/drop transactions with only one movement recorded"
        
        conn.close()
        return results
    
    def generate_report(self, validation_results: Dict) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            validation_results: Results from validate_batch or validate_database_records
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("TRANSACTION DATA QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"Total Records: {validation_results['total']}")
        report.append(f"Valid Records: {validation_results['valid']}")
        report.append(f"Invalid Records: {validation_results['invalid']}")
        report.append(f"Validation Rate: {validation_results['validation_rate']:.2f}%")
        
        if validation_results['invalid'] > 0:
            report.append("\nINVALID TRANSACTIONS:")
            report.append("-" * 40)
            for invalid in validation_results['invalid_transactions'][:10]:  # Show first 10
                trans = invalid['transaction']
                report.append(f"\nTransaction {invalid['index']}:")
                report.append(f"  Player: {trans.get('player_name', 'UNKNOWN')}")
                report.append(f"  Type: {trans.get('transaction_type', 'UNKNOWN')}")
                report.append(f"  Date: {trans.get('date', 'UNKNOWN')}")
                report.append(f"  Issues:")
                for issue in invalid['issues']:
                    report.append(f"    - {issue}")
            
            if validation_results['invalid'] > 10:
                report.append(f"\n... and {validation_results['invalid'] - 10} more invalid transactions")
        
        if 'incomplete_add_drops' in validation_results:
            report.append("\nINCOMPLETE ADD/DROP TRANSACTIONS:")
            report.append("-" * 40)
            for trans in validation_results['incomplete_add_drops'][:5]:
                report.append(f"  {trans['date']}: {trans['player_name']} - only {trans['movement_type']} recorded")
        
        if 'warnings' in validation_results:
            report.append(f"\nWARNINGS: {validation_results['warnings']}")
        
        report.append("=" * 60)
        return "\n".join(report)


def check_transaction_quality(transactions: List[Dict]) -> bool:
    """
    Quick function to check transaction quality before insertion.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        True if all transactions are valid, False otherwise
    """
    checker = TransactionDataQualityChecker()
    results = checker.validate_batch(transactions)
    
    if results['invalid'] > 0:
        print(checker.generate_report(results))
        return False
    
    return True


def validate_job_transactions(db_path: str, job_id: str) -> Dict:
    """
    Validate all transactions for a specific job.
    
    Args:
        db_path: Path to the database
        job_id: Job ID to validate
        
    Returns:
        Validation results dictionary
    """
    checker = TransactionDataQualityChecker()
    results = checker.validate_database_records(db_path, job_id=job_id)
    print(checker.generate_report(results))
    return results


if __name__ == "__main__":
    import argparse
    import os
    import sys
    
    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    parser = argparse.ArgumentParser(description='Check transaction data quality')
    parser.add_argument('--db', default='../../database/league_analytics.db', help='Database path')
    parser.add_argument('--job-id', help='Check specific job ID')
    parser.add_argument('--date-start', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--date-end', help='End date (YYYY-MM-DD)')
    parser.add_argument('--last-n-days', type=int, help='Check last N days')
    
    args = parser.parse_args()
    
    # Determine date range
    date_range = None
    if args.date_start and args.date_end:
        date_range = (args.date_start, args.date_end)
    elif args.last_n_days:
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=args.last_n_days)
        date_range = (str(start_date), str(end_date))
    
    # Run validation
    checker = TransactionDataQualityChecker()
    results = checker.validate_database_records(args.db, job_id=args.job_id, date_range=date_range)
    print(checker.generate_report(results))