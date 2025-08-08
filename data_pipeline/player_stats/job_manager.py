#!/usr/bin/env python3
"""
Player Stats Job Manager

Manages job tracking, monitoring, and reporting for MLB player statistics
data collection operations. Integrates with the existing job logging
infrastructure to provide comprehensive visibility into collection status.

Key Features:
- Job status monitoring and reporting
- Performance metrics tracking
- Error analysis and reporting
- Collection progress visualization
- Integration with existing job_log system
"""

import sys
import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from data_pipeline.player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobSummary:
    """Summary information for a player stats job."""
    job_id: str
    job_type: str
    environment: str
    status: str
    date_range_start: Optional[str]
    date_range_end: Optional[str]
    records_processed: Optional[int]
    records_inserted: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    processing_time_seconds: Optional[float]
    
    @property
    def success_rate(self) -> Optional[float]:
        """Calculate success rate if data is available."""
        if self.records_processed and self.records_processed > 0:
            return (self.records_inserted or 0) / self.records_processed
        return None
    
    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully."""
        return self.status == JobStatus.COMPLETED.value


@dataclass
class CollectionMetrics:
    """Metrics for collection performance analysis."""
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    running_jobs: int = 0
    total_records_processed: int = 0
    total_records_inserted: int = 0
    average_processing_time: Optional[float] = None
    total_processing_time: Optional[float] = None
    success_rate: Optional[float] = None
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from base data."""
        if self.total_jobs > 0:
            self.success_rate = self.successful_jobs / self.total_jobs
        
        if self.total_records_processed > 0:
            self.overall_record_success_rate = self.total_records_inserted / self.total_records_processed


class PlayerStatsJobManager:
    """
    Manages job tracking and monitoring for player stats operations.
    
    Provides comprehensive job management capabilities including status
    monitoring, performance analysis, and integration with existing
    job logging infrastructure.
    """
    
    def __init__(self, environment: str = "production", use_d1: bool = False):
        """
        Initialize the job manager.
        
        Args:
            environment: 'production' or 'test'
            use_d1: If True, use Cloudflare D1 instead of SQLite
        """
        self.environment = environment
        self.use_d1 = use_d1
        self.config = get_config_for_environment(environment)
        
        # Database connection
        if use_d1:
            from data_pipeline.common.d1_connection import D1Connection
            self.d1_conn = D1Connection()
            self.conn = None
            logger.info("Using Cloudflare D1 for job logging")
        else:
            self.db_path = self.config['database_path']
            self.conn = None
            self.d1_conn = None
            logger.info(f"Using SQLite database: {self.db_path}")
        
        # Job types we manage
        self.managed_job_types = [
            "player_stats_collection",
            "player_stats_backfill", 
            "player_id_mapping_update",
            "player_stats_validation"
        ]
        
        logger.info(f"Initialized PlayerStatsJobManager for {environment} environment")
    
    def start_job(self, job_type: str, date_range_start: str, date_range_end: str,
                  league_key: str = None, metadata: Dict = None) -> str:
        """
        Start a new job and create job_log entry.
        
        Args:
            job_type: Type of job (e.g., 'stats_incremental', 'stats_backfill')
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            league_key: League key (optional for player stats)
            metadata: Additional metadata dict
            
        Returns:
            Generated job_id
        """
        import uuid
        job_id = str(uuid.uuid4())
        
        if self.use_d1:
            # Use D1 connection
            self.d1_conn.ensure_job_exists(
                job_id=job_id,
                job_type=job_type,
                environment=self.environment,
                league_key=league_key,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                metadata=json.dumps(metadata) if metadata else None
            )
            logger.info(f"Started job in D1: {job_id} ({job_type})")
        else:
            # Use SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO job_log (job_id, job_type, environment, status, 
                                        date_range_start, date_range_end, league_key, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (job_id, job_type, self.environment, 'running', 
                      date_range_start, date_range_end, league_key, 
                      json.dumps(metadata) if metadata else None))
                conn.commit()
                
                logger.info(f"Started job: {job_id} ({job_type})")
                
            finally:
                conn.close()
        
        return job_id
    
    def update_job(self, job_id: str, status: str, records_processed: int = None,
                   records_inserted: int = None, error_msg: str = None, 
                   metadata: Dict = None):
        """
        Update an existing job's status.
        
        Args:
            job_id: Job ID to update
            status: New status ('running', 'completed', 'failed')
            records_processed: Number of records processed
            records_inserted: Number of records inserted
            error_msg: Error message if failed
            metadata: Additional metadata to merge
        """
        if self.use_d1:
            # Use D1 connection
            self.d1_conn.update_job_status(
                job_id=job_id,
                status=status,
                records_processed=records_processed,
                records_inserted=records_inserted,
                error_message=error_msg
            )
            logger.info(f"Updated job in D1 {job_id}: {status}")
        else:
            # Use SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Get existing metadata
                cursor.execute('SELECT metadata FROM job_log WHERE job_id = ?', (job_id,))
                result = cursor.fetchone()
                existing_metadata = {}
                if result and result[0]:
                    try:
                        existing_metadata = json.loads(result[0])
                    except:
                        pass
                
                # Merge metadata
                if metadata:
                    existing_metadata.update(metadata)
                
                # Update job
                cursor.execute('''
                    UPDATE job_log 
                    SET status = ?,
                        records_processed = COALESCE(?, records_processed),
                        records_inserted = COALESCE(?, records_inserted),
                        error_message = COALESCE(?, error_message),
                        metadata = ?,
                        end_time = CASE WHEN ? IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE end_time END
                    WHERE job_id = ?
                ''', (status, records_processed, records_inserted, error_msg,
                      json.dumps(existing_metadata) if existing_metadata else None,
                      status, job_id))
                
                conn.commit()
                logger.info(f"Updated job {job_id}: {status}")
                
            finally:
                conn.close()
    
    def get_job_summary(self, job_id: str) -> Optional[JobSummary]:
        """
        Get detailed summary for a specific job.
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            JobSummary if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT job_id, job_type, environment, status, date_range_start,
                       date_range_end, records_processed, records_inserted,
                       error_message, created_at, end_time
                FROM job_log
                WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Calculate processing time if both timestamps available
            processing_time = None
            if row[9] and row[10]:  # created_at and updated_at
                created = datetime.fromisoformat(row[9])
                updated = datetime.fromisoformat(row[10])
                processing_time = (updated - created).total_seconds()
            
            return JobSummary(
                job_id=row[0],
                job_type=row[1],
                environment=row[2],
                status=row[3],
                date_range_start=row[4],
                date_range_end=row[5],
                records_processed=row[6],
                records_inserted=row[7],
                error_message=row[8],
                created_at=datetime.fromisoformat(row[9]),
                updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
                processing_time_seconds=processing_time
            )
            
        finally:
            conn.close()
    
    def get_recent_jobs(self, limit: int = 20, job_type: str = None) -> List[JobSummary]:
        """
        Get recent player stats jobs.
        
        Args:
            limit: Maximum number of jobs to return
            job_type: Filter by specific job type
            
        Returns:
            List of JobSummary objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build query with optional job type filter
            where_clause = "WHERE job_type IN ({})".format(
                ','.join('?' for _ in self.managed_job_types)
            )
            params = list(self.managed_job_types)
            
            if job_type:
                where_clause += " AND job_type = ?"
                params.append(job_type)
            
            cursor.execute(f"""
                SELECT job_id, job_type, environment, status, date_range_start,
                       date_range_end, records_processed, records_inserted,
                       error_message, created_at, end_time
                FROM job_log
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
            """, params + [limit])
            
            jobs = []
            for row in cursor.fetchall():
                # Calculate processing time if both timestamps available
                processing_time = None
                if row[9] and row[10]:  # created_at and updated_at
                    created = datetime.fromisoformat(row[9])
                    updated = datetime.fromisoformat(row[10])
                    processing_time = (updated - created).total_seconds()
                
                jobs.append(JobSummary(
                    job_id=row[0],
                    job_type=row[1],
                    environment=row[2],
                    status=row[3],
                    date_range_start=row[4],
                    date_range_end=row[5],
                    records_processed=row[6],
                    records_inserted=row[7],
                    error_message=row[8],
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    processing_time_seconds=processing_time
                ))
            
            return jobs
            
        finally:
            conn.close()
    
    def get_jobs_by_date_range(self, start_date: date, end_date: date) -> List[JobSummary]:
        """
        Get jobs that collected data for a specific date range.
        
        Args:
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            List of JobSummary objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT job_id, job_type, environment, status, date_range_start,
                       date_range_end, records_processed, records_inserted,
                       error_message, created_at, end_time
                FROM job_log
                WHERE job_type IN ({})
                AND (
                    (date_range_start <= ? AND date_range_end >= ?) OR
                    (date_range_start >= ? AND date_range_start <= ?) OR
                    (date_range_end >= ? AND date_range_end <= ?)
                )
                ORDER BY created_at DESC
            """.format(','.join('?' for _ in self.managed_job_types)), 
            self.managed_job_types + [
                start_date.isoformat(), start_date.isoformat(),
                start_date.isoformat(), end_date.isoformat(),
                start_date.isoformat(), end_date.isoformat()
            ])
            
            jobs = []
            for row in cursor.fetchall():
                # Calculate processing time if both timestamps available
                processing_time = None
                if row[9] and row[10]:  # created_at and updated_at
                    created = datetime.fromisoformat(row[9])
                    updated = datetime.fromisoformat(row[10])
                    processing_time = (updated - created).total_seconds()
                
                jobs.append(JobSummary(
                    job_id=row[0],
                    job_type=row[1],
                    environment=row[2],
                    status=row[3],
                    date_range_start=row[4],
                    date_range_end=row[5],
                    records_processed=row[6],
                    records_inserted=row[7],
                    error_message=row[8],
                    created_at=datetime.fromisoformat(row[9]),
                    updated_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    processing_time_seconds=processing_time
                ))
            
            return jobs
            
        finally:
            conn.close()
    
    def get_collection_metrics(self, days_back: int = 30) -> CollectionMetrics:
        """
        Get collection performance metrics for recent period.
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            CollectionMetrics with performance data
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get basic job counts
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM job_log
                WHERE job_type IN ({})
                AND created_at >= ?
                GROUP BY status
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [cutoff_date.isoformat()])
            
            status_counts = dict(cursor.fetchall())
            
            # Get record processing totals
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(records_processed), 0) as total_processed,
                    COALESCE(SUM(records_inserted), 0) as total_inserted,
                    COUNT(*) as total_jobs,
                    AVG(
                        CASE 
                            WHEN created_at IS NOT NULL AND updated_at IS NOT NULL 
                            THEN (julianday(updated_at) - julianday(created_at)) * 86400
                            ELSE NULL 
                        END
                    ) as avg_processing_time,
                    SUM(
                        CASE 
                            WHEN created_at IS NOT NULL AND updated_at IS NOT NULL 
                            THEN (julianday(updated_at) - julianday(created_at)) * 86400
                            ELSE 0 
                        END
                    ) as total_processing_time
                FROM job_log
                WHERE job_type IN ({})
                AND created_at >= ?
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [cutoff_date.isoformat()])
            
            row = cursor.fetchone()
            
            metrics = CollectionMetrics(
                total_jobs=status_counts.get('completed', 0) + status_counts.get('failed', 0) + status_counts.get('running', 0),
                successful_jobs=status_counts.get('completed', 0),
                failed_jobs=status_counts.get('failed', 0),
                running_jobs=status_counts.get('running', 0),
                total_records_processed=row[0] if row else 0,
                total_records_inserted=row[1] if row else 0,
                average_processing_time=row[3] if row else None,
                total_processing_time=row[4] if row else None
            )
            
            metrics.calculate_derived_metrics()
            return metrics
            
        finally:
            conn.close()
    
    def get_daily_collection_status(self, target_date: date) -> Dict[str, Any]:
        """
        Get collection status for a specific date.
        
        Args:
            target_date: Date to check collection status for
            
        Returns:
            Dictionary with collection status information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check for jobs that collected this date
            cursor.execute("""
                SELECT job_id, job_type, status, records_processed, records_inserted,
                       error_message, created_at, updated_at
                FROM job_log
                WHERE job_type IN ({})
                AND date_range_start <= ? AND date_range_end >= ?
                ORDER BY created_at DESC
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [target_date.isoformat(), target_date.isoformat()])
            
            jobs = cursor.fetchall()
            
            # Check for actual data in final table
            final_table = self.config['gkl_player_stats_table']
            cursor.execute(f"""
                SELECT COUNT(*) FROM {final_table}
                WHERE date = ?
            """, (target_date.isoformat(),))
            
            records_in_final = cursor.fetchone()[0]
            
            status = {
                'date': target_date.isoformat(),
                'has_collection_jobs': len(jobs) > 0,
                'has_final_data': records_in_final > 0,
                'records_in_final_table': records_in_final,
                'collection_jobs': [],
                'latest_job_status': None,
                'collection_complete': False
            }
            
            for job in jobs:
                job_info = {
                    'job_id': job[0],
                    'job_type': job[1], 
                    'status': job[2],
                    'records_processed': job[3],
                    'records_inserted': job[4],
                    'error_message': job[5],
                    'created_at': job[6],
                    'updated_at': job[7]
                }
                status['collection_jobs'].append(job_info)
            
            if jobs:
                status['latest_job_status'] = jobs[0][2]  # Most recent job status
                status['collection_complete'] = (jobs[0][2] == 'completed' and records_in_final > 0)
            
            return status
            
        finally:
            conn.close()
    
    def get_failed_jobs_analysis(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Analyze recent failed jobs for common patterns.
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with failure analysis
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get failed jobs
            cursor.execute("""
                SELECT job_id, job_type, error_message, date_range_start, created_at
                FROM job_log
                WHERE job_type IN ({})
                AND status = 'failed'
                AND created_at >= ?
                ORDER BY created_at DESC
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [cutoff_date.isoformat()])
            
            failed_jobs = cursor.fetchall()
            
            # Analyze error patterns
            error_patterns = {}
            job_type_failures = {}
            date_failures = {}
            
            for job in failed_jobs:
                job_id, job_type, error_msg, date_range, created_at = job
                
                # Count by job type
                job_type_failures[job_type] = job_type_failures.get(job_type, 0) + 1
                
                # Count by date
                if date_range:
                    date_failures[date_range] = date_failures.get(date_range, 0) + 1
                
                # Analyze error message patterns
                if error_msg:
                    # Simple pattern matching - look for common error types
                    error_key = "unknown"
                    if "timeout" in error_msg.lower():
                        error_key = "timeout"
                    elif "connection" in error_msg.lower():
                        error_key = "connection"
                    elif "permission" in error_msg.lower():
                        error_key = "permission"
                    elif "not found" in error_msg.lower():
                        error_key = "not_found"
                    elif "validation" in error_msg.lower():
                        error_key = "validation"
                    
                    error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
            
            analysis = {
                'period_days': days_back,
                'total_failed_jobs': len(failed_jobs),
                'error_patterns': error_patterns,
                'job_type_failures': job_type_failures,
                'date_failures': date_failures,
                'recent_failures': [
                    {
                        'job_id': job[0],
                        'job_type': job[1],
                        'error_message': job[2][:100] + "..." if job[2] and len(job[2]) > 100 else job[2],
                        'date_range': job[3],
                        'created_at': job[4]
                    }
                    for job in failed_jobs[:10]  # Most recent 10 failures
                ]
            }
            
            return analysis
            
        finally:
            conn.close()
    
    def cleanup_old_jobs(self, days_to_keep: int = 90) -> Dict[str, int]:
        """
        Clean up old job log entries to manage database size.
        
        Args:
            days_to_keep: Number of days of job history to retain
            
        Returns:
            Dictionary with cleanup results
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Count jobs to be deleted
            cursor.execute("""
                SELECT COUNT(*) FROM job_log
                WHERE job_type IN ({})
                AND created_at < ?
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [cutoff_date.isoformat()])
            
            jobs_to_delete = cursor.fetchone()[0]
            
            # Delete old jobs
            cursor.execute("""
                DELETE FROM job_log
                WHERE job_type IN ({})
                AND created_at < ?
            """.format(','.join('?' for _ in self.managed_job_types)),
            self.managed_job_types + [cutoff_date.isoformat()])
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old job log entries (older than {days_to_keep} days)")
            
            return {
                'jobs_identified_for_deletion': jobs_to_delete,
                'jobs_actually_deleted': deleted_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        finally:
            conn.close()


def main():
    """Command-line interface for job management operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Player Stats Job Management")
    parser.add_argument("action", choices=["status", "recent", "metrics", "failures", "cleanup"],
                       help="Action to perform")
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--job-id", help="Specific job ID for status check")
    parser.add_argument("--date", help="Date for collection status check (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=10,
                       help="Limit for recent jobs (default: 10)")
    parser.add_argument("--days", type=int, default=7,
                       help="Number of days for analysis (default: 7)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    manager = PlayerStatsJobManager(environment=args.env)
    
    if args.action == "status":
        if args.job_id:
            # Single job status
            print(f"Job status for {args.job_id}:")
            print("-" * 60)
            
            job = manager.get_job_summary(args.job_id)
            if job:
                print(f"Status: {job.status}")
                print(f"Type: {job.job_type}")
                print(f"Environment: {job.environment}")
                print(f"Date Range: {job.date_range_start} to {job.date_range_end}")
                print(f"Records: {job.records_inserted or 0}/{job.records_processed or 0}")
                if job.processing_time_seconds:
                    print(f"Processing Time: {job.processing_time_seconds:.1f}s")
                if job.error_message:
                    print(f"Error: {job.error_message}")
            else:
                print("Job not found")
                
        elif args.date:
            # Daily collection status
            try:
                target_date = date.fromisoformat(args.date)
            except ValueError:
                print("ERROR: Invalid date format. Use YYYY-MM-DD")
                return
            
            print(f"Collection status for {target_date}:")
            print("-" * 60)
            
            status = manager.get_daily_collection_status(target_date)
            print(f"Has collection jobs: {status['has_collection_jobs']}")
            print(f"Has final data: {status['has_final_data']}")
            print(f"Records in final table: {status['records_in_final_table']}")
            print(f"Collection complete: {status['collection_complete']}")
            
            if status['collection_jobs']:
                print(f"\nCollection jobs ({len(status['collection_jobs'])}):")
                for job in status['collection_jobs']:
                    print(f"  {job['job_id']}: {job['status']} ({job['job_type']})")
        else:
            print("ERROR: --job-id or --date required for status check")
    
    elif args.action == "recent":
        print(f"Recent player stats jobs ({args.limit}):")
        print("-" * 60)
        
        jobs = manager.get_recent_jobs(limit=args.limit)
        
        for job in jobs:
            status_icon = "✓" if job.is_successful else "✗" if job.status == "failed" else "⏳"
            print(f"{status_icon} {job.job_id} - {job.job_type}")
            print(f"   Status: {job.status} | Records: {job.records_inserted or 0}/{job.records_processed or 0}")
            print(f"   Date: {job.date_range_start} | Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}")
            if job.error_message:
                print(f"   Error: {job.error_message[:80]}...")
            print()
    
    elif args.action == "metrics":
        print(f"Collection metrics (last {args.days} days):")
        print("-" * 60)
        
        metrics = manager.get_collection_metrics(days_back=args.days)
        
        print(f"Total Jobs: {metrics.total_jobs}")
        print(f"Successful: {metrics.successful_jobs} ({metrics.success_rate:.1%} if metrics.success_rate else 'N/A')")
        print(f"Failed: {metrics.failed_jobs}")
        print(f"Running: {metrics.running_jobs}")
        print(f"Total Records: {metrics.total_records_inserted:,}/{metrics.total_records_processed:,}")
        if metrics.average_processing_time:
            print(f"Avg Processing Time: {metrics.average_processing_time:.1f}s")
    
    elif args.action == "failures":
        print(f"Failed jobs analysis (last {args.days} days):")
        print("-" * 60)
        
        analysis = manager.get_failed_jobs_analysis(days_back=args.days)
        
        print(f"Total Failed Jobs: {analysis['total_failed_jobs']}")
        
        if analysis['error_patterns']:
            print("\nError Patterns:")
            for pattern, count in analysis['error_patterns'].items():
                print(f"  {pattern}: {count}")
        
        if analysis['job_type_failures']:
            print("\nFailures by Job Type:")
            for job_type, count in analysis['job_type_failures'].items():
                print(f"  {job_type}: {count}")
        
        if analysis['recent_failures']:
            print(f"\nRecent Failures ({len(analysis['recent_failures'])}):")
            for failure in analysis['recent_failures']:
                print(f"  {failure['job_id']} - {failure['job_type']}")
                print(f"    Error: {failure['error_message']}")
                print()
    
    elif args.action == "cleanup":
        print(f"Cleaning up job logs older than {args.days} days...")
        print("-" * 60)
        
        results = manager.cleanup_old_jobs(days_to_keep=args.days)
        
        print(f"Jobs identified for deletion: {results['jobs_identified_for_deletion']}")
        print(f"Jobs actually deleted: {results['jobs_actually_deleted']}")
        print(f"Cutoff date: {results['cutoff_date']}")


if __name__ == "__main__":
    main()