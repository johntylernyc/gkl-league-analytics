#!/usr/bin/env python
"""
Cloudflare D1 Database Connection Module

This module provides a direct connection to Cloudflare D1 databases using the D1 HTTP API.
It's designed for use in GitHub Actions and other environments where direct D1 access is needed,
eliminating the need for local SQLite databases and sync operations.

Features:
    - Direct HTTP API connection to D1
    - Automatic retry with exponential backoff
    - Batch operations for performance (up to 100 statements)
    - Environment variable configuration
    - D1-specific error handling and limitations
    - Foreign key constraint management

Usage:
    from data_pipeline.common.d1_connection import D1Connection
    
    # Initialize connection
    d1 = D1Connection()
    
    # Execute single query
    result = d1.execute("SELECT COUNT(*) FROM job_log")
    
    # Execute batch operations
    statements = [
        ("INSERT INTO job_log (job_id, job_type) VALUES (?, ?)", ["job1", "test"]),
        ("INSERT INTO job_log (job_id, job_type) VALUES (?, ?)", ["job2", "test"])
    ]
    d1.execute_batch(statements)
"""

import os
import time
import logging
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple, Union

import requests

logger = logging.getLogger(__name__)


class D1ConnectionError(Exception):
    """Custom exception for D1 connection errors."""
    pass


class D1QueryError(Exception):
    """Custom exception for D1 query errors."""
    pass


def retry_d1_operation(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Decorator to retry D1 operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for backoff delay
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, D1QueryError) as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"D1 operation failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"D1 operation failed (attempt {attempt + 1}/{max_attempts}), "
                                 f"retrying in {wait_time:.1f}s: {str(e)}")
                    time.sleep(wait_time)
            
        return wrapper
    return decorator


class D1Connection:
    """
    Direct connection to Cloudflare D1 database using HTTP API.
    
    This class provides methods to interact with D1 databases directly,
    without requiring local SQLite or Wrangler CLI dependencies.
    """
    
    # D1 API limits
    MAX_BATCH_SIZE = 100
    MAX_RESPONSE_SIZE_MB = 1
    REQUEST_TIMEOUT = 30
    RATE_LIMIT_RPM = 1000
    
    def __init__(self, account_id: Optional[str] = None, database_id: Optional[str] = None, 
                 api_token: Optional[str] = None):
        """
        Initialize D1 connection.
        
        Args:
            account_id: Cloudflare account ID (defaults to env var)
            database_id: D1 database ID (defaults to env var)
            api_token: Cloudflare API token (defaults to env var)
        """
        self.account_id = account_id or os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        self.database_id = database_id or os.environ.get('D1_DATABASE_ID')
        self.api_token = api_token or os.environ.get('CLOUDFLARE_API_TOKEN')
        
        if not all([self.account_id, self.database_id, self.api_token]):
            missing = []
            if not self.account_id:
                missing.append('CLOUDFLARE_ACCOUNT_ID')
            if not self.database_id:
                missing.append('D1_DATABASE_ID')
            if not self.api_token:
                missing.append('CLOUDFLARE_API_TOKEN')
            
            raise D1ConnectionError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Initialized D1 connection to database {self.database_id}")
    
    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """
        Make HTTP request to D1 API.
        
        Args:
            endpoint: API endpoint (e.g., '/query', '/batch')
            data: Request payload
            
        Returns:
            API response data
            
        Raises:
            D1QueryError: If query fails
            D1ConnectionError: If connection fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=self.REQUEST_TIMEOUT
            )
            
            if not response.ok:
                error_msg = f"D1 API request failed (HTTP {response.status_code}): {response.text}"
                logger.error(error_msg)
                
                if response.status_code >= 500:
                    # Server errors - retry
                    raise D1ConnectionError(error_msg)
                else:
                    # Client errors - don't retry
                    raise D1QueryError(error_msg)
            
            result = response.json()
            
            # Check for API-level errors
            if not result.get('success', True):
                errors = result.get('errors', [])
                error_msg = f"D1 API returned errors: {errors}"
                logger.error(error_msg)
                raise D1QueryError(error_msg)
            
            return result
            
        except requests.exceptions.Timeout:
            raise D1ConnectionError(f"D1 request timed out after {self.REQUEST_TIMEOUT}s")
        except requests.exceptions.ConnectionError as e:
            raise D1ConnectionError(f"Failed to connect to D1 API: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise D1ConnectionError(f"D1 request failed: {str(e)}")
    
    @retry_d1_operation()
    def execute(self, query: str, params: Optional[List[Any]] = None) -> Dict:
        """
        Execute a single SQL query against D1.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query result dictionary with meta information
        """
        data = {
            "sql": query,
            "params": params or []
        }
        
        logger.debug(f"Executing D1 query: {query[:100]}{'...' if len(query) > 100 else ''}")
        
        result = self._make_request("/query", data)
        
        # D1 returns result as a list with one item for single queries
        result_data = result.get('result', [])
        if isinstance(result_data, list) and len(result_data) > 0:
            query_result = result_data[0]
            # Flatten meta information to top level for easier access
            meta = query_result.get('meta', {})
            return {
                'results': query_result.get('results', []),
                'success': query_result.get('success', True),
                'changes': meta.get('changes', 0),
                'last_row_id': meta.get('last_row_id'),
                'rows_read': meta.get('rows_read', 0),
                'rows_written': meta.get('rows_written', 0)
            }
        else:
            # Fallback for unexpected response format
            return {
                'results': [],
                'success': False,
                'changes': 0,
                'rows_read': 0,
                'rows_written': 0
            }
    
    @retry_d1_operation()
    def execute_batch(self, statements: List[Tuple[str, List[Any]]]) -> List[Dict]:
        """
        Execute multiple SQL statements in batches.
        
        D1 supports up to 100 statements per batch. This method automatically
        chunks larger lists into multiple batch requests.
        
        Args:
            statements: List of (query, params) tuples
            
        Returns:
            List of result dictionaries
        """
        if not statements:
            return []
        
        all_results = []
        
        # Process in chunks of MAX_BATCH_SIZE
        for i in range(0, len(statements), self.MAX_BATCH_SIZE):
            batch = statements[i:i + self.MAX_BATCH_SIZE]
            
            # Convert to D1 batch format
            batch_statements = []
            for query, params in batch:
                batch_statements.append({
                    "sql": query,
                    "params": params or []
                })
            
            data = {"statements": batch_statements}
            
            logger.debug(f"Executing D1 batch: {len(batch)} statements")
            
            result = self._make_request("/batch", data)
            
            # Process batch results - D1 batch returns list of results
            batch_results = result.get('result', [])
            for batch_result in batch_results:
                # Flatten meta information similar to single query
                meta = batch_result.get('meta', {})
                processed_result = {
                    'results': batch_result.get('results', []),
                    'success': batch_result.get('success', True),
                    'changes': meta.get('changes', 0),
                    'last_row_id': meta.get('last_row_id'),
                    'rows_read': meta.get('rows_read', 0),
                    'rows_written': meta.get('rows_written', 0)
                }
                all_results.append(processed_result)
        
        return all_results
    
    def ensure_job_exists(self, job_id: str, job_type: str, environment: str = 'production',
                         league_key: Optional[str] = None, date_range_start: Optional[str] = None,
                         date_range_end: Optional[str] = None, metadata: Optional[str] = None) -> bool:
        """
        Ensure a job_log entry exists for the given job_id.
        
        This is critical for maintaining foreign key integrity in D1.
        Uses INSERT OR IGNORE to handle duplicates gracefully.
        
        Args:
            job_id: Unique job identifier
            job_type: Type of job
            environment: Environment ('production' or 'test')
            league_key: Yahoo league key
            date_range_start: Start date for data collection
            date_range_end: End date for data collection
            metadata: Additional job metadata
            
        Returns:
            True if job was created, False if it already existed
        """
        query = """
            INSERT OR IGNORE INTO job_log (
                job_id, job_type, environment, status, 
                date_range_start, date_range_end, league_key, metadata,
                start_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = [
            job_id, job_type, environment, 'running',
            date_range_start, date_range_end, league_key, metadata
        ]
        
        result = self.execute(query, params)
        
        # Check if row was inserted (changes > 0) or already existed (changes = 0)
        changes = result.get('changes', 0)
        if changes > 0:
            logger.info(f"Created job_log entry for job_id: {job_id}")
            return True
        else:
            logger.debug(f"Job_log entry already exists for job_id: {job_id}")
            return False
    
    def update_job_status(self, job_id: str, status: str, records_processed: Optional[int] = None,
                         records_inserted: Optional[int] = None, error_message: Optional[str] = None) -> bool:
        """
        Update job status in job_log.
        
        Args:
            job_id: Job identifier
            status: New status ('completed', 'failed', etc.)
            records_processed: Number of records processed
            records_inserted: Number of records inserted
            error_message: Error message if status is 'failed'
            
        Returns:
            True if job was updated
        """
        update_parts = ['status = ?', 'end_time = CURRENT_TIMESTAMP']
        params = [status]
        
        if records_processed is not None:
            update_parts.append('records_processed = ?')
            params.append(records_processed)
        
        if records_inserted is not None:
            update_parts.append('records_inserted = ?') 
            params.append(records_inserted)
        
        if error_message:
            update_parts.append('error_message = ?')
            params.append(error_message)
        
        params.append(job_id)
        
        query = f"UPDATE job_log SET {', '.join(update_parts)} WHERE job_id = ?"
        
        result = self.execute(query, params)
        
        changes = result.get('changes', 0)
        if changes > 0:
            logger.info(f"Updated job {job_id} status to {status}")
            return True
        else:
            logger.warning(f"No job found with job_id: {job_id}")
            return False
    
    def insert_transactions(self, transactions: List[Dict], job_id: str) -> Tuple[int, int]:
        """
        Insert transaction records using batch operations.
        
        Args:
            transactions: List of transaction dictionaries
            job_id: Job identifier for foreign key
            
        Returns:
            Tuple of (inserted_count, error_count)
        """
        if not transactions:
            return 0, 0
        
        # Prepare batch statements
        statements = []
        for trans in transactions:
            query = """
                INSERT OR REPLACE INTO transactions (
                    date, league_key, transaction_id, transaction_type,
                    player_id, player_name, player_position, player_team,
                    movement_type, destination_team_key, destination_team_name,
                    source_team_key, source_team_name, job_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = [
                trans['date'], trans['league_key'], trans['transaction_id'],
                trans['transaction_type'], trans['player_id'], trans['player_name'], 
                trans['player_position'], trans['player_team'], trans['movement_type'],
                trans['destination_team_key'], trans['destination_team_name'],
                trans['source_team_key'], trans['source_team_name'], job_id
            ]
            
            statements.append((query, params))
        
        # Execute batch
        results = self.execute_batch(statements)
        
        # Count successful inserts
        inserted_count = 0
        error_count = 0
        
        for result in results:
            if result.get('success', True):
                inserted_count += result.get('changes', 0)
            else:
                error_count += 1
                logger.error(f"Transaction insert failed: {result.get('error')}")
        
        logger.info(f"Inserted {inserted_count} transactions, {error_count} errors")
        return inserted_count, error_count
    
    def insert_lineups(self, lineups: List[Dict], job_id: str) -> Tuple[int, int]:
        """
        Insert lineup records using batch operations.
        
        Args:
            lineups: List of lineup dictionaries
            job_id: Job identifier for foreign key
            
        Returns:
            Tuple of (inserted_count, error_count)
        """
        if not lineups:
            return 0, 0
        
        # Prepare batch statements
        statements = []
        for lineup in lineups:
            query = """
                INSERT OR REPLACE INTO daily_lineups (
                    job_id, season, date, team_key, team_name,
                    player_id, player_name, selected_position, position_type,
                    player_status, eligible_positions, player_team
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = [
                job_id, lineup['season'], lineup['date'], lineup['team_key'],
                lineup['team_name'], lineup['player_id'], lineup['player_name'],
                lineup['selected_position'], lineup['position_type'],
                lineup['player_status'], lineup['eligible_positions'], lineup['player_team']
            ]
            
            statements.append((query, params))
        
        # Execute batch
        results = self.execute_batch(statements)
        
        # Count successful inserts
        inserted_count = 0
        error_count = 0
        
        for result in results:
            if result.get('success', True):
                inserted_count += result.get('changes', 0)
            else:
                error_count += 1
                logger.error(f"Lineup insert failed: {result.get('error')}")
        
        logger.info(f"Inserted {inserted_count} lineup records, {error_count} errors")
        return inserted_count, error_count
    
    def test_connection(self) -> bool:
        """
        Test D1 connection and basic functionality.
        
        Returns:
            True if connection is working
        """
        try:
            # Test basic query
            result = self.execute("SELECT 1 as test")
            
            if result and len(result.get('results', [])) > 0:
                logger.info("D1 connection test successful")
                return True
            else:
                logger.error("D1 connection test failed: no results")
                return False
                
        except Exception as e:
            logger.error(f"D1 connection test failed: {str(e)}")
            return False
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        Get information about a table structure.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Table information or None if table doesn't exist
        """
        try:
            result = self.execute(f"PRAGMA table_info({table_name})")
            return result
        except D1QueryError:
            return None


def create_d1_connection() -> D1Connection:
    """
    Factory function to create a D1 connection with environment variable validation.
    
    Returns:
        Configured D1Connection instance
    """
    return D1Connection()


def is_d1_available() -> bool:
    """
    Check if D1 credentials are available in environment variables.
    
    Returns:
        True if all required D1 environment variables are set
    """
    required_vars = ['CLOUDFLARE_ACCOUNT_ID', 'D1_DATABASE_ID', 'CLOUDFLARE_API_TOKEN']
    return all(os.environ.get(var) for var in required_vars)


if __name__ == '__main__':
    # Test script when run directly
    if is_d1_available():
        print("Testing D1 connection...")
        try:
            d1 = create_d1_connection()
            if d1.test_connection():
                print("✅ D1 connection successful")
            else:
                print("❌ D1 connection failed")
        except Exception as e:
            print(f"❌ D1 connection error: {e}")
    else:
        print("❌ D1 environment variables not configured")
        print("Required: CLOUDFLARE_ACCOUNT_ID, D1_DATABASE_ID, CLOUDFLARE_API_TOKEN")