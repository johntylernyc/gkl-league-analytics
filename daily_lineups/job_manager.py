"""
Job Management Module for Daily Lineups
Handles job logging, checkpoint/resume, and progress tracking.
"""

import sqlite3
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from uuid import uuid4
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.config import (
    get_database_path,
    CHECKPOINT_FILE,
    STATE_FILE
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LineupJobManager:
    """Manages job lifecycle for lineup data collection."""
    
    def __init__(self, environment="production"):
        """
        Initialize job manager.
        
        Args:
            environment: 'production' or 'test'
        """
        self.environment = environment
        self.db_path = get_database_path(environment)
        self.checkpoint_file = CHECKPOINT_FILE
        self.state_file = STATE_FILE
        self.current_job_id = None
        self.job_metadata = {}
    
    def start_job(self, 
                  job_type: str,
                  date_range_start: str,
                  date_range_end: str,
                  league_key: str,
                  metadata: Dict = None) -> str:
        """
        Start a new job and create job log entry.
        
        Args:
            job_type: Type of job (e.g., 'lineup_collection', 'lineup_backfill')
            date_range_start: Start date (YYYY-MM-DD)
            date_range_end: End date (YYYY-MM-DD)
            league_key: Yahoo league key
            metadata: Additional job metadata
            
        Returns:
            job_id: Unique job identifier
        """
        # Generate unique job ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid4().hex[:8]
        job_id = f"{job_type}_{self.environment}_{timestamp}_{unique_id}"
        
        # Store metadata
        self.current_job_id = job_id
        self.job_metadata = metadata or {}
        
        # Create job log entry
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO job_log (
                    job_id, job_type, environment, status,
                    date_range_start, date_range_end, league_key,
                    start_time, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_type,
                self.environment,
                'running',
                date_range_start,
                date_range_end,
                league_key,
                datetime.now().isoformat(),
                json.dumps(self.job_metadata) if self.job_metadata else None
            ))
            
            conn.commit()
            logger.info(f"Started job: {job_id}")
            
            # Save initial checkpoint
            self._save_checkpoint({
                'job_id': job_id,
                'status': 'running',
                'start_date': date_range_start,
                'end_date': date_range_end,
                'current_date': date_range_start,
                'league_key': league_key,
                'teams_processed': [],
                'dates_completed': []
            })
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to start job: {e}")
            raise
        finally:
            conn.close()
    
    def update_job(self,
                   job_id: str,
                   status: str = None,
                   records_processed: int = None,
                   records_inserted: int = None,
                   error_message: str = None,
                   progress_pct: float = None) -> None:
        """
        Update job status and statistics.
        
        Args:
            job_id: Job identifier
            status: New status ('running', 'completed', 'failed', 'paused')
            records_processed: Number of records processed
            records_inserted: Number of records inserted
            error_message: Error message if failed
            progress_pct: Progress percentage (0-100)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            updates = []
            params = []
            
            if status:
                updates.append("status = ?")
                params.append(status)
            
            if records_processed is not None:
                updates.append("records_processed = ?")
                params.append(records_processed)
            
            if records_inserted is not None:
                updates.append("records_inserted = ?")
                params.append(records_inserted)
            
            if error_message:
                updates.append("error_message = ?")
                params.append(error_message)
            
            if progress_pct is not None:
                # Store progress in metadata
                cursor.execute("SELECT metadata FROM job_log WHERE job_id = ?", (job_id,))
                result = cursor.fetchone()
                metadata = json.loads(result[0]) if result and result[0] else {}
                metadata['progress_pct'] = progress_pct
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))
            
            if status in ['completed', 'failed']:
                updates.append("end_time = ?")
                params.append(datetime.now().isoformat())
            
            # Execute update
            if updates:
                query = f"UPDATE job_log SET {', '.join(updates)} WHERE job_id = ?"
                params.append(job_id)
                cursor.execute(query, params)
                conn.commit()
                
                logger.info(f"Updated job {job_id}: status={status}, progress={progress_pct}%")
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            raise
        finally:
            conn.close()
    
    def get_job_status(self, job_id: str) -> Dict:
        """
        Get current job status and statistics.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    job_id, job_type, environment, status,
                    date_range_start, date_range_end, league_key,
                    start_time, end_time,
                    records_processed, records_inserted,
                    error_message, metadata
                FROM job_log
                WHERE job_id = ?
            """, (job_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            # Parse metadata
            metadata = json.loads(result[12]) if result[12] else {}
            
            return {
                'job_id': result[0],
                'job_type': result[1],
                'environment': result[2],
                'status': result[3],
                'date_range_start': result[4],
                'date_range_end': result[5],
                'league_key': result[6],
                'start_time': result[7],
                'end_time': result[8],
                'records_processed': result[9],
                'records_inserted': result[10],
                'error_message': result[11],
                'metadata': metadata,
                'progress_pct': metadata.get('progress_pct', 0)
            }
            
        finally:
            conn.close()
    
    def _save_checkpoint(self, checkpoint_data: Dict) -> None:
        """
        Save checkpoint data to file.
        
        Args:
            checkpoint_data: Dictionary with checkpoint information
        """
        try:
            checkpoint_data['timestamp'] = datetime.now().isoformat()
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            logger.debug(f"Saved checkpoint: {checkpoint_data.get('current_date')}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict]:
        """
        Load checkpoint data from file.
        
        Returns:
            Checkpoint data or None if not found
        """
        if not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            
            logger.info(f"Loaded checkpoint for job: {checkpoint.get('job_id')}")
            return checkpoint
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def clear_checkpoint(self) -> None:
        """Clear checkpoint file."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("Cleared checkpoint file")
    
    def update_checkpoint(self,
                         current_date: str = None,
                         teams_processed: List[str] = None,
                         dates_completed: List[str] = None) -> None:
        """
        Update checkpoint with progress information.
        
        Args:
            current_date: Current processing date
            teams_processed: List of processed team keys
            dates_completed: List of completed dates
        """
        checkpoint = self.load_checkpoint()
        
        if not checkpoint:
            logger.warning("No checkpoint to update")
            return
        
        if current_date:
            checkpoint['current_date'] = current_date
        
        if teams_processed is not None:
            checkpoint['teams_processed'] = teams_processed
        
        if dates_completed is not None:
            checkpoint['dates_completed'] = dates_completed
        
        self._save_checkpoint(checkpoint)
    
    def calculate_progress(self, 
                          current_date: str,
                          start_date: str,
                          end_date: str) -> float:
        """
        Calculate job progress percentage.
        
        Args:
            current_date: Current processing date
            start_date: Job start date
            end_date: Job end date
            
        Returns:
            Progress percentage (0-100)
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            current = datetime.strptime(current_date, '%Y-%m-%d').date()
            
            total_days = (end - start).days + 1
            completed_days = (current - start).days
            
            if total_days <= 0:
                return 100.0
            
            progress = (completed_days / total_days) * 100
            return min(100.0, max(0.0, progress))
            
        except Exception as e:
            logger.error(f"Failed to calculate progress: {e}")
            return 0.0
    
    def get_recent_jobs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent jobs for this environment.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    job_id, job_type, status,
                    date_range_start, date_range_end,
                    start_time, end_time,
                    records_processed, records_inserted
                FROM job_log
                WHERE environment = ?
                    AND job_type LIKE 'lineup_%'
                ORDER BY start_time DESC
                LIMIT ?
            """, (self.environment, limit))
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'job_id': row[0],
                    'job_type': row[1],
                    'status': row[2],
                    'date_range_start': row[3],
                    'date_range_end': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'records_processed': row[7],
                    'records_inserted': row[8]
                })
            
            return jobs
            
        finally:
            conn.close()
    
    def get_job_statistics(self) -> Dict:
        """
        Get aggregate statistics for lineup jobs.
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Overall statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_jobs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_jobs,
                    SUM(records_processed) as total_records_processed,
                    SUM(records_inserted) as total_records_inserted
                FROM job_log
                WHERE environment = ?
                    AND job_type LIKE 'lineup_%'
            """, (self.environment,))
            
            stats = cursor.fetchone()
            
            # Calculate success rate
            total = stats[0] or 0
            completed = stats[1] or 0
            success_rate = (completed / total * 100) if total > 0 else 0
            
            return {
                'total_jobs': total,
                'completed_jobs': completed,
                'failed_jobs': stats[2] or 0,
                'running_jobs': stats[3] or 0,
                'success_rate': round(success_rate, 2),
                'total_records_processed': stats[4] or 0,
                'total_records_inserted': stats[5] or 0
            }
            
        finally:
            conn.close()


class LineupProgressTracker:
    """Track and report progress for lineup collection jobs."""
    
    def __init__(self, job_id: str, total_items: int):
        """
        Initialize progress tracker.
        
        Args:
            job_id: Job identifier
            total_items: Total items to process
        """
        self.job_id = job_id
        self.total_items = total_items
        self.processed_items = 0
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        self.update_frequency = 10  # Update every N items
    
    def update(self, items_processed: int = 1) -> None:
        """
        Update progress.
        
        Args:
            items_processed: Number of items processed
        """
        self.processed_items += items_processed
        
        # Only log updates at certain intervals
        if self.processed_items % self.update_frequency == 0 or \
           self.processed_items >= self.total_items:
            self._log_progress()
    
    def _log_progress(self) -> None:
        """Log current progress."""
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        # Calculate metrics
        progress_pct = (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0
        rate = self.processed_items / elapsed if elapsed > 0 else 0
        remaining = (self.total_items - self.processed_items) / rate if rate > 0 else 0
        
        # Log progress
        logger.info(
            f"Job {self.job_id}: {progress_pct:.1f}% complete "
            f"({self.processed_items}/{self.total_items} items, "
            f"{rate:.1f} items/sec, ~{remaining:.1f}s remaining)"
        )
        
        self.last_update_time = current_time
    
    def get_stats(self) -> Dict:
        """
        Get current progress statistics.
        
        Returns:
            Dictionary with progress metrics
        """
        current_time = datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        progress_pct = (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0
        rate = self.processed_items / elapsed if elapsed > 0 else 0
        remaining = (self.total_items - self.processed_items) / rate if rate > 0 else 0
        
        return {
            'job_id': self.job_id,
            'processed': self.processed_items,
            'total': self.total_items,
            'progress_pct': round(progress_pct, 2),
            'rate_per_sec': round(rate, 2),
            'elapsed_seconds': round(elapsed, 2),
            'remaining_seconds': round(remaining, 2),
            'is_complete': self.processed_items >= self.total_items
        }


def main():
    """Command line interface for job management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage lineup collection jobs")
    parser.add_argument('command', choices=['status', 'list', 'stats', 'resume'],
                       help="Command to execute")
    parser.add_argument('--job-id', help="Job ID for status command")
    parser.add_argument('--env', default='production', choices=['production', 'test'],
                       help="Environment")
    
    args = parser.parse_args()
    
    manager = LineupJobManager(environment=args.env)
    
    if args.command == 'status':
        if not args.job_id:
            print("Error: --job-id required for status command")
            return
        
        status = manager.get_job_status(args.job_id)
        if status:
            print(f"\nJob Status: {args.job_id}")
            print("-" * 50)
            for key, value in status.items():
                if key != 'metadata':
                    print(f"{key:20}: {value}")
        else:
            print(f"Job not found: {args.job_id}")
    
    elif args.command == 'list':
        jobs = manager.get_recent_jobs()
        print(f"\nRecent Jobs ({args.env})")
        print("-" * 80)
        print(f"{'Job ID':<50} {'Status':<12} {'Records':<10}")
        print("-" * 80)
        for job in jobs:
            print(f"{job['job_id']:<50} {job['status']:<12} {job.get('records_inserted', 0):<10}")
    
    elif args.command == 'stats':
        stats = manager.get_job_statistics()
        print(f"\nJob Statistics ({args.env})")
        print("-" * 40)
        for key, value in stats.items():
            print(f"{key:25}: {value}")
    
    elif args.command == 'resume':
        checkpoint = manager.load_checkpoint()
        if checkpoint:
            print(f"\nCheckpoint found for job: {checkpoint['job_id']}")
            print(f"Current date: {checkpoint.get('current_date')}")
            print(f"Dates completed: {len(checkpoint.get('dates_completed', []))}")
            print("\nUse collector with --resume flag to continue")
        else:
            print("No checkpoint found")


if __name__ == "__main__":
    main()