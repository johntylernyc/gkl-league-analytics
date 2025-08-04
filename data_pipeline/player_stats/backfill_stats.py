#!/usr/bin/env python3
"""
Historical Player Stats Backfill Script

Comprehensive script for backfilling historical MLB player statistics data.
Designed for bulk collection of historical data with robust error handling,
progress tracking, and recovery capabilities for interrupted operations.

Key Features:
- Season-based or custom date range backfilling
- Intelligent gap detection and targeted collection
- Progress tracking with resume capability
- Batch processing with configurable concurrency
- Comprehensive error handling and retry logic
- Integration with existing job logging system
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import time

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))

from player_stats.collector import PlayerStatsCollector
from player_stats.job_manager import PlayerStatsJobManager
from player_stats.repository import PlayerStatsRepository
from player_stats.data_validator import PlayerStatsValidator
from player_stats.config import get_config_for_environment

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackfillProgress:
    """Manages backfill progress tracking and persistence."""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.data = self._load_progress()
    
    def _load_progress(self) -> Dict[str, Any]:
        """Load progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load progress file: {e}")
        
        return {
            'session_id': None,
            'start_date': None,
            'end_date': None,
            'completed_dates': [],
            'failed_dates': [],
            'total_dates': 0,
            'created_at': None,
            'updated_at': None
        }
    
    def save_progress(self):
        """Save progress to file."""
        self.data['updated_at'] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def start_session(self, session_id: str, start_date: date, end_date: date, total_dates: int):
        """Start a new backfill session."""
        self.data.update({
            'session_id': session_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'completed_dates': [],
            'failed_dates': [],
            'total_dates': total_dates,
            'created_at': datetime.now().isoformat()
        })
        self.save_progress()
    
    def mark_completed(self, target_date: date):
        """Mark a date as completed."""
        date_str = target_date.isoformat()
        if date_str not in self.data['completed_dates']:
            self.data['completed_dates'].append(date_str)
        if date_str in self.data['failed_dates']:
            self.data['failed_dates'].remove(date_str)
        self.save_progress()
    
    def mark_failed(self, target_date: date):
        """Mark a date as failed."""
        date_str = target_date.isoformat()
        if date_str not in self.data['failed_dates']:
            self.data['failed_dates'].append(date_str)
        if date_str in self.data['completed_dates']:
            self.data['completed_dates'].remove(date_str)
        self.save_progress()
    
    def get_progress_stats(self) -> Dict[str, Any]:
        """Get progress statistics."""
        completed = len(self.data['completed_dates'])
        failed = len(self.data['failed_dates'])
        total = self.data['total_dates']
        
        return {
            'completed': completed,
            'failed': failed,
            'total': total,
            'remaining': total - completed - failed,
            'completion_rate': completed / total if total > 0 else 0.0,
            'failure_rate': failed / total if total > 0 else 0.0
        }
    
    def get_pending_dates(self, start_date: date, end_date: date) -> List[date]:
        """Get list of dates that still need to be processed."""
        completed_set = set(self.data['completed_dates'])
        
        pending = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.isoformat() not in completed_set:
                pending.append(current_date)
            current_date += timedelta(days=1)
        
        return pending


class PlayerStatsBackfiller:
    """
    Manages historical player statistics backfill operations.
    
    Provides comprehensive backfill capabilities with progress tracking,
    error handling, and recovery for interrupted operations.
    """
    
    def __init__(self, environment: str = "production", progress_dir: Optional[Path] = None):
        """
        Initialize the backfiller.
        
        Args:
            environment: 'production' or 'test'
            progress_dir: Directory for progress tracking files
        """
        self.environment = environment
        self.config = get_config_for_environment(environment)
        
        # Initialize components
        self.collector = PlayerStatsCollector(environment)
        self.job_manager = PlayerStatsJobManager(environment)
        self.repository = PlayerStatsRepository(environment)
        self.validator = PlayerStatsValidator(environment)
        
        # Progress tracking
        if progress_dir is None:
            progress_dir = Path(__file__).parent / "progress"
        progress_dir.mkdir(exist_ok=True)
        self.progress_dir = progress_dir
        
        logger.info(f"Initialized PlayerStatsBackfiller for {environment} environment")
        logger.info(f"Progress directory: {progress_dir}")
    
    def detect_data_gaps(self, start_date: date, end_date: date) -> List[date]:
        """
        Detect gaps in existing data coverage.
        
        Args:
            start_date: Start date for gap detection
            end_date: End date for gap detection
            
        Returns:
            List of dates with missing data
        """
        logger.info(f"Detecting data gaps from {start_date} to {end_date}")
        
        # Get dates with existing data
        existing_dates = set(self.repository.get_available_dates(start_date, end_date))
        
        # Generate all dates in range
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Find missing dates
        missing_dates = [d for d in all_dates if d not in existing_dates]
        
        logger.info(f"Found {len(missing_dates)} missing dates out of {len(all_dates)} total dates")
        return missing_dates
    
    def backfill_date_range(self, start_date: date, end_date: date,
                           max_workers: int = 2, resume: bool = True,
                           validate_after: bool = True, 
                           skip_existing: bool = True) -> Dict[str, Any]:
        """
        Backfill player statistics for a date range.
        
        Args:
            start_date: Start date for backfill
            end_date: End date for backfill
            max_workers: Maximum concurrent workers
            resume: Whether to resume from previous progress
            validate_after: Whether to validate data after collection
            skip_existing: Whether to skip dates with existing data
            
        Returns:
            Dictionary with backfill results
        """
        session_id = f"backfill_{start_date}_{end_date}_{int(time.time())}"
        logger.info(f"Starting backfill session: {session_id}")
        
        # Initialize progress tracking
        progress_file = self.progress_dir / f"{session_id}.json"
        progress = BackfillProgress(progress_file)
        
        # Determine dates to process
        if skip_existing:
            target_dates = self.detect_data_gaps(start_date, end_date)
        else:
            target_dates = []
            current_date = start_date
            while current_date <= end_date:
                target_dates.append(current_date)
                current_date += timedelta(days=1)
        
        if resume and progress.data['session_id']:
            logger.info(f"Resuming previous session: {progress.data['session_id']}")
            pending_dates = progress.get_pending_dates(start_date, end_date)
            target_dates = [d for d in target_dates if d in pending_dates]
        else:
            progress.start_session(session_id, start_date, end_date, len(target_dates))
        
        if not target_dates:
            logger.info("No dates to process - backfill complete or no gaps found")
            return {
                'session_id': session_id,
                'total_dates': 0,
                'successful_dates': 0,
                'failed_dates': 0,
                'skipped_dates': 0,
                'errors': []
            }
        
        logger.info(f"Processing {len(target_dates)} dates with {max_workers} workers")
        
        # Process dates in batches for better control
        batch_size = max_workers * 5  # Process in manageable batches
        successful_count = 0
        failed_count = 0
        errors = []
        
        for i in range(0, len(target_dates), batch_size):
            batch_dates = target_dates[i:i + batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_dates)} dates")
            
            # Use collector's range collection for this batch
            if len(batch_dates) == 1:
                # Single date collection
                try:
                    job_id = self.collector.collect_daily_stats(
                        batch_dates[0],
                        job_metadata=f"Backfill for {batch_dates[0]} (session: {session_id})"
                    )
                    progress.mark_completed(batch_dates[0])
                    successful_count += 1
                    logger.info(f"✓ Completed {batch_dates[0]} (job: {job_id})")
                    
                except Exception as e:
                    progress.mark_failed(batch_dates[0])
                    failed_count += 1
                    error_msg = f"Failed {batch_dates[0]}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            else:
                # Range collection for batch
                batch_start = min(batch_dates)
                batch_end = max(batch_dates)
                
                try:
                    results = self.collector.collect_date_range(
                        batch_start, batch_end, max_workers
                    )
                    
                    # Update progress based on results
                    for date_obj in batch_dates:
                        # Check if this date was successful by looking at job logs
                        daily_status = self.job_manager.get_daily_collection_status(date_obj)
                        if daily_status['collection_complete']:
                            progress.mark_completed(date_obj)
                            successful_count += 1
                        else:
                            progress.mark_failed(date_obj)
                            failed_count += 1
                    
                    # Add any errors from the batch
                    errors.extend(results.get('errors', []))
                    
                except Exception as e:
                    # Mark entire batch as failed
                    for date_obj in batch_dates:
                        progress.mark_failed(date_obj)
                        failed_count += 1
                    
                    error_msg = f"Batch failed {batch_start} to {batch_end}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Progress update
            stats = progress.get_progress_stats()
            logger.info(f"Progress: {stats['completed']}/{stats['total']} completed ({stats['completion_rate']:.1%})")
        
        # Final validation if requested
        validation_results = None
        if validate_after and successful_count > 0:
            logger.info("Running validation on backfilled data...")
            try:
                validation_report = self.validator.validate_date_range(start_date, end_date)
                validation_results = {
                    'total_records_validated': validation_report.total_records_validated,
                    'error_count': validation_report.error_count,
                    'warning_count': validation_report.warning_count,
                    'is_valid': validation_report.is_valid,
                    'quality_score': validation_report.summary_stats.get('quality_metrics', {}).get('overall_quality_score', 0.0)
                }
                
                if validation_report.is_valid:
                    logger.info(f"✓ Validation passed: {validation_report.total_records_validated} records")
                else:
                    logger.warning(f"⚠ Validation issues: {validation_report.error_count} errors, {validation_report.warning_count} warnings")
                    
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                validation_results = {'error': str(e)}
        
        # Final results
        results = {
            'session_id': session_id,
            'total_dates': len(target_dates),
            'successful_dates': successful_count,
            'failed_dates': failed_count,
            'skipped_dates': 0,  # We don't skip in this implementation
            'errors': errors[:10],  # Limit errors in return
            'validation': validation_results,
            'progress_file': str(progress_file)
        }
        
        success_rate = successful_count / len(target_dates) if target_dates else 1.0
        logger.info(f"Backfill completed: {successful_count}/{len(target_dates)} successful ({success_rate:.1%})")
        
        return results
    
    def backfill_season(self, year: int, max_workers: int = 2, 
                       validate_after: bool = True) -> Dict[str, Any]:
        """
        Backfill an entire MLB season.
        
        Args:
            year: Year to backfill
            max_workers: Maximum concurrent workers
            validate_after: Whether to validate after collection
            
        Returns:
            Dictionary with backfill results
        """
        # Define MLB season dates (approximate)
        season_start = date(year, 3, 15)  # Spring training / early season
        season_end = date(year, 11, 15)   # End of World Series
        
        logger.info(f"Starting {year} season backfill: {season_start} to {season_end}")
        
        return self.backfill_date_range(
            season_start, 
            season_end,
            max_workers=max_workers,
            validate_after=validate_after
        )
    
    def get_backfill_status(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get status of backfill operations.
        
        Args:
            session_id: Specific session ID to check (optional)
            
        Returns:
            Dictionary with status information
        """
        if session_id:
            progress_file = self.progress_dir / f"{session_id}.json"
            if progress_file.exists():
                progress = BackfillProgress(progress_file)
                return {
                    'session_id': session_id,
                    'progress': progress.get_progress_stats(),
                    'data': progress.data
                }
            else:
                return {'error': f'Session {session_id} not found'}
        else:
            # Return all sessions
            sessions = []
            for progress_file in self.progress_dir.glob("backfill_*.json"):
                try:
                    progress = BackfillProgress(progress_file)
                    sessions.append({
                        'session_id': progress.data.get('session_id'),
                        'start_date': progress.data.get('start_date'),
                        'end_date': progress.data.get('end_date'),
                        'progress': progress.get_progress_stats(),
                        'created_at': progress.data.get('created_at'),
                        'updated_at': progress.data.get('updated_at')
                    })
                except Exception as e:
                    logger.warning(f"Failed to load session from {progress_file}: {e}")
            
            return {'sessions': sessions}


def main():
    """Main entry point for the backfill script."""
    parser = argparse.ArgumentParser(
        description="Historical MLB Player Statistics Backfill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backfill entire 2025 season
  python backfill_stats.py --season 2025

  # Backfill specific date range
  python backfill_stats.py --start-date 2025-07-01 --end-date 2025-07-31

  # Resume previous backfill with more workers
  python backfill_stats.py --start-date 2025-07-01 --end-date 2025-07-31 --resume --workers 4

  # Check backfill status
  python backfill_stats.py --status

  # Backfill only data gaps (skip existing)
  python backfill_stats.py --season 2025 --skip-existing --no-validate
        """
    )
    
    # Date/season arguments
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--season", type=int, help="MLB season year to backfill")
    date_group.add_argument("--start-date", help="Start date for range backfill (YYYY-MM-DD)")
    
    parser.add_argument("--end-date", help="End date for range backfill (YYYY-MM-DD, required with --start-date)")
    
    # Behavior options
    parser.add_argument("--workers", type=int, default=2,
                       help="Maximum concurrent workers (default: 2)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from previous progress")
    parser.add_argument("--skip-existing", action="store_true",
                       help="Skip dates with existing data")
    parser.add_argument("--validate", action="store_true", default=True,
                       help="Run validation after backfill (default: enabled)")
    parser.add_argument("--no-validate", dest="validate", action="store_false",
                       help="Skip validation after backfill")
    
    # Environment and output
    parser.add_argument("--env", default="production", choices=["production", "test"],
                       help="Environment (default: production)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--log-file", help="Log to file in addition to console")
    
    # Status and management
    parser.add_argument("--status", action="store_true",
                       help="Show backfill status and exit")
    parser.add_argument("--session-id", help="Specific session ID for status check")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start_date and not args.end_date:
        parser.error("--end-date is required when using --start-date")
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setLevel(logging.DEBUG if args.verbose else logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
    
    logger.info(f"Player Stats Backfill Script - Environment: {args.env}")
    
    # Initialize backfiller
    try:
        backfiller = PlayerStatsBackfiller(environment=args.env)
    except Exception as e:
        logger.error(f"Failed to initialize backfiller: {e}")
        return 1
    
    # Handle status command
    if args.status:
        status = backfiller.get_backfill_status(args.session_id)
        
        if 'error' in status:
            print(f"Error: {status['error']}")
            return 1
        
        if 'sessions' in status:
            sessions = status['sessions']
            print(f"\nBackfill Sessions ({len(sessions)}):")
            print("-" * 80)
            for session in sessions:
                progress = session['progress']
                print(f"Session: {session['session_id']}")
                print(f"  Date Range: {session['start_date']} to {session['end_date']}")
                print(f"  Progress: {progress['completed']}/{progress['total']} ({progress['completion_rate']:.1%})")
                print(f"  Failed: {progress['failed']} ({progress['failure_rate']:.1%})")
                print(f"  Updated: {session['updated_at']}")
                print()
        else:
            # Single session status
            progress = status['progress']
            data = status['data']
            print(f"\nSession: {status['session_id']}")
            print("-" * 60)
            print(f"Date Range: {data['start_date']} to {data['end_date']}")
            print(f"Progress: {progress['completed']}/{progress['total']} ({progress['completion_rate']:.1%})")
            print(f"Failed: {progress['failed']} ({progress['failure_rate']:.1%})")
            print(f"Remaining: {progress['remaining']}")
            print(f"Created: {data['created_at']}")
            print(f"Updated: {data['updated_at']}")
        
        return 0
    
    # Execute backfill
    try:
        if args.season:
            logger.info(f"Starting season backfill for {args.season}")
            results = backfiller.backfill_season(
                args.season,
                max_workers=args.workers,
                validate_after=args.validate
            )
        else:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
            
            logger.info(f"Starting range backfill: {start_date} to {end_date}")
            results = backfiller.backfill_date_range(
                start_date,
                end_date,
                max_workers=args.workers,
                resume=args.resume,
                validate_after=args.validate,
                skip_existing=args.skip_existing
            )
        
        # Display results
        success_rate = results['successful_dates'] / results['total_dates'] if results['total_dates'] > 0 else 1.0
        
        print(f"\nBackfill Results:")
        print("-" * 60)
        print(f"Session ID: {results['session_id']}")
        print(f"Total Dates: {results['total_dates']}")
        print(f"Successful: {results['successful_dates']} ({success_rate:.1%})")
        print(f"Failed: {results['failed_dates']}")
        
        if 'validation' in results and results['validation']:
            val = results['validation']
            if 'error' not in val:
                print(f"Validation: {val['total_records_validated']} records, quality {val['quality_score']:.1%}")
            else:
                print(f"Validation Error: {val['error']}")
        
        if results['errors']:
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors'][:5]:
                print(f"  - {error}")
        
        print(f"\nProgress file: {results['progress_file']}")
        
        # Return appropriate exit code
        return 0 if results['failed_dates'] == 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("Backfill interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)