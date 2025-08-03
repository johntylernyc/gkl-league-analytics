"""
Unit tests for the LineupJobManager class.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from daily_lineups.job_manager import LineupJobManager, LineupProgressTracker


class TestLineupJobManager(unittest.TestCase):
    """Test cases for LineupJobManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Create temporary checkpoint file
        self.temp_checkpoint = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.temp_checkpoint.close()
        
        # Initialize test database
        self._init_test_db()
        
        # Create job manager
        self.manager = LineupJobManager(environment='test')
        self.manager.db_path = self.temp_db.name
        self.manager.checkpoint_file = Path(self.temp_checkpoint.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary files
        for file_path in [self.temp_db.name, self.temp_checkpoint.name]:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    def _init_test_db(self):
        """Initialize test database with required schema."""
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE job_log (
                job_id TEXT PRIMARY KEY,
                job_type TEXT,
                environment TEXT,
                status TEXT,
                date_range_start TEXT,
                date_range_end TEXT,
                league_key TEXT,
                start_time TEXT,
                end_time TEXT,
                records_processed INTEGER,
                records_inserted INTEGER,
                error_message TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def test_start_job(self):
        """Test starting a new job."""
        job_id = self.manager.start_job(
            job_type='lineup_collection',
            date_range_start='2025-06-01',
            date_range_end='2025-06-07',
            league_key='mlb.l.123',
            metadata={'test': True}
        )
        
        # Verify job ID format
        self.assertIn('lineup_collection', job_id)
        self.assertIn('test', job_id)
        
        # Verify job log entry
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_log WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(job)
        self.assertEqual(job[1], 'lineup_collection')  # job_type
        self.assertEqual(job[2], 'test')  # environment
        self.assertEqual(job[3], 'running')  # status
        self.assertEqual(job[4], '2025-06-01')  # date_range_start
        self.assertEqual(job[5], '2025-06-07')  # date_range_end
        
        # Verify checkpoint created
        self.assertTrue(self.manager.checkpoint_file.exists())
        checkpoint = self.manager.load_checkpoint()
        self.assertEqual(checkpoint['job_id'], job_id)
        self.assertEqual(checkpoint['status'], 'running')
    
    def test_update_job(self):
        """Test updating job status."""
        # Start a job
        job_id = self.manager.start_job(
            job_type='lineup_collection',
            date_range_start='2025-06-01',
            date_range_end='2025-06-07',
            league_key='mlb.l.123'
        )
        
        # Update job
        self.manager.update_job(
            job_id,
            status='completed',
            records_processed=1000,
            records_inserted=950,
            progress_pct=100.0
        )
        
        # Verify update
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, records_processed, records_inserted, end_time, metadata
            FROM job_log WHERE job_id = ?
        """, (job_id,))
        result = cursor.fetchone()
        conn.close()
        
        self.assertEqual(result[0], 'completed')
        self.assertEqual(result[1], 1000)
        self.assertEqual(result[2], 950)
        self.assertIsNotNone(result[3])  # end_time should be set
        
        # Check progress in metadata
        metadata = json.loads(result[4]) if result[4] else {}
        self.assertEqual(metadata.get('progress_pct'), 100.0)
    
    def test_get_job_status(self):
        """Test retrieving job status."""
        # Start a job
        job_id = self.manager.start_job(
            job_type='lineup_backfill',
            date_range_start='2025-06-01',
            date_range_end='2025-06-30',
            league_key='mlb.l.456'
        )
        
        # Get status
        status = self.manager.get_job_status(job_id)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['job_id'], job_id)
        self.assertEqual(status['job_type'], 'lineup_backfill')
        self.assertEqual(status['status'], 'running')
        self.assertEqual(status['environment'], 'test')
        
        # Test non-existent job
        status = self.manager.get_job_status('fake_job_id')
        self.assertIsNone(status)
    
    def test_checkpoint_operations(self):
        """Test checkpoint save/load/update operations."""
        # Create checkpoint
        checkpoint_data = {
            'job_id': 'test_job_123',
            'status': 'running',
            'current_date': '2025-06-15',
            'teams_processed': ['team1', 'team2'],
            'dates_completed': ['2025-06-01', '2025-06-02']
        }
        
        self.manager._save_checkpoint(checkpoint_data)
        
        # Load checkpoint
        loaded = self.manager.load_checkpoint()
        self.assertEqual(loaded['job_id'], 'test_job_123')
        self.assertEqual(loaded['current_date'], '2025-06-15')
        self.assertIn('timestamp', loaded)
        
        # Update checkpoint
        self.manager.update_checkpoint(
            current_date='2025-06-16',
            dates_completed=['2025-06-01', '2025-06-02', '2025-06-03']
        )
        
        # Verify update
        updated = self.manager.load_checkpoint()
        self.assertEqual(updated['current_date'], '2025-06-16')
        self.assertEqual(len(updated['dates_completed']), 3)
        
        # Clear checkpoint
        self.manager.clear_checkpoint()
        self.assertFalse(self.manager.checkpoint_file.exists())
    
    def test_calculate_progress(self):
        """Test progress calculation."""
        # Test various progress scenarios
        progress = self.manager.calculate_progress('2025-06-01', '2025-06-01', '2025-06-10')
        self.assertEqual(progress, 0.0)
        
        progress = self.manager.calculate_progress('2025-06-05', '2025-06-01', '2025-06-10')
        self.assertEqual(progress, 40.0)
        
        progress = self.manager.calculate_progress('2025-06-10', '2025-06-01', '2025-06-10')
        self.assertEqual(progress, 90.0)
        
        # Test edge cases
        progress = self.manager.calculate_progress('2025-06-15', '2025-06-01', '2025-06-10')
        self.assertEqual(progress, 100.0)  # Capped at 100
    
    def test_get_recent_jobs(self):
        """Test retrieving recent jobs."""
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job_id = self.manager.start_job(
                job_type='lineup_collection',
                date_range_start=f'2025-06-0{i+1}',
                date_range_end=f'2025-06-0{i+2}',
                league_key='mlb.l.123'
            )
            job_ids.append(job_id)
        
        # Get recent jobs
        recent = self.manager.get_recent_jobs(limit=2)
        
        self.assertEqual(len(recent), 2)
        # Most recent should be first
        self.assertEqual(recent[0]['job_id'], job_ids[-1])
    
    def test_get_job_statistics(self):
        """Test aggregate job statistics."""
        # Create jobs with different statuses
        job1 = self.manager.start_job(
            job_type='lineup_collection',
            date_range_start='2025-06-01',
            date_range_end='2025-06-07',
            league_key='mlb.l.123'
        )
        self.manager.update_job(job1, 'completed', 1000, 950)
        
        job2 = self.manager.start_job(
            job_type='lineup_backfill',
            date_range_start='2025-06-08',
            date_range_end='2025-06-14',
            league_key='mlb.l.123'
        )
        self.manager.update_job(job2, 'failed', 500, 0, 'Test error')
        
        job3 = self.manager.start_job(
            job_type='lineup_collection',
            date_range_start='2025-06-15',
            date_range_end='2025-06-21',
            league_key='mlb.l.123'
        )
        # Leave job3 as running
        
        # Get statistics
        stats = self.manager.get_job_statistics()
        
        self.assertEqual(stats['total_jobs'], 3)
        self.assertEqual(stats['completed_jobs'], 1)
        self.assertEqual(stats['failed_jobs'], 1)
        self.assertEqual(stats['running_jobs'], 1)
        self.assertEqual(stats['total_records_processed'], 1500)
        self.assertEqual(stats['total_records_inserted'], 950)
        self.assertAlmostEqual(stats['success_rate'], 33.33, places=1)


class TestLineupProgressTracker(unittest.TestCase):
    """Test cases for LineupProgressTracker."""
    
    def test_progress_tracking(self):
        """Test progress tracking functionality."""
        tracker = LineupProgressTracker('test_job', total_items=100)
        
        # Initial state
        stats = tracker.get_stats()
        self.assertEqual(stats['processed'], 0)
        self.assertEqual(stats['total'], 100)
        self.assertEqual(stats['progress_pct'], 0.0)
        self.assertFalse(stats['is_complete'])
        
        # Update progress
        tracker.update(25)
        stats = tracker.get_stats()
        self.assertEqual(stats['processed'], 25)
        self.assertEqual(stats['progress_pct'], 25.0)
        
        # Update more
        tracker.update(50)
        stats = tracker.get_stats()
        self.assertEqual(stats['processed'], 75)
        self.assertEqual(stats['progress_pct'], 75.0)
        
        # Complete
        tracker.update(25)
        stats = tracker.get_stats()
        self.assertEqual(stats['processed'], 100)
        self.assertEqual(stats['progress_pct'], 100.0)
        self.assertTrue(stats['is_complete'])
    
    def test_rate_calculation(self):
        """Test rate and remaining time calculation."""
        tracker = LineupProgressTracker('test_job', total_items=100)
        
        # Simulate some processing with a small delay
        tracker.update(10)
        
        # Mock time to simulate elapsed time
        with patch('daily_lineups.job_manager.datetime') as mock_datetime:
            # Set elapsed time to 10 seconds
            mock_datetime.now.return_value = tracker.start_time + timedelta(seconds=10)
            
            stats = tracker.get_stats()
            
            # Should process 10 items in 10 seconds = 1 item/sec
            self.assertAlmostEqual(stats['rate_per_sec'], 1.0, places=1)
            # 90 items remaining at 1 item/sec = 90 seconds
            self.assertAlmostEqual(stats['remaining_seconds'], 90.0, places=0)


if __name__ == "__main__":
    unittest.main()