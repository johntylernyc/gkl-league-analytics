"""
Monitor the progress of lineup data collection.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.job_manager import LineupJobManager
from daily_lineups.config import SEASON_DATES

def monitor_progress():
    """Monitor the current collection progress."""
    
    # Connect to database
    conn = sqlite3.connect('database/league_analytics.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("DAILY LINEUPS COLLECTION MONITOR")
    print("=" * 70)
    print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get latest job
    cursor.execute("""
        SELECT job_id, status, date_range_start, date_range_end,
               start_time, end_time, records_processed, records_inserted
        FROM job_log
        WHERE job_type = 'lineup_collection'
        ORDER BY start_time DESC
        LIMIT 1
    """)
    job = cursor.fetchone()
    
    if not job:
        print("No lineup collection jobs found.")
        return
    
    job_id, status, start_date, end_date, start_time, end_time, records_proc, records_ins = job
    
    print(f"Latest Job: {job_id}")
    print(f"Status: {status.upper()}")
    print(f"Target Range: {start_date} to {end_date}")
    print()
    
    # Calculate total days in range
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    total_days = (end_dt - start_dt).days + 1
    
    # Get current progress
    cursor.execute("""
        SELECT MIN(date), MAX(date), COUNT(DISTINCT date) as days_done,
               COUNT(DISTINCT team_key) as teams,
               COUNT(DISTINCT player_id) as players,
               COUNT(*) as total_records
        FROM daily_lineups
        WHERE date BETWEEN ? AND ?
    """, (start_date, end_date))
    
    progress = cursor.fetchone()
    
    if progress[0]:
        print("COLLECTION PROGRESS")
        print("-" * 40)
        print(f"Date Range Collected: {progress[0]} to {progress[1]}")
        print(f"Days Completed: {progress[2]}/{total_days} ({progress[2]/total_days*100:.1f}%)")
        print(f"Teams: {progress[3]}")
        print(f"Unique Players: {progress[4]:,}")
        print(f"Total Records: {progress[5]:,}")
        print()
        
        # Show progress bar
        progress_pct = progress[2] / total_days
        bar_width = 50
        filled = int(bar_width * progress_pct)
        bar = '#' * filled + '-' * (bar_width - filled)
        print(f"Progress: [{bar}] {progress_pct*100:.1f}%")
        print()
        
        # Calculate timing
        if status == 'running':
            start_time_dt = datetime.fromisoformat(start_time)
            elapsed = datetime.now() - start_time_dt
            elapsed_minutes = elapsed.total_seconds() / 60
            
            if progress[2] > 0:
                rate = elapsed_minutes / progress[2]  # minutes per day
                remaining_days = total_days - progress[2]
                eta_minutes = remaining_days * rate
                eta_time = datetime.now() + timedelta(minutes=eta_minutes)
                
                print("TIMING")
                print("-" * 40)
                print(f"Elapsed Time: {int(elapsed_minutes)} minutes")
                print(f"Processing Rate: {rate:.1f} minutes per day")
                print(f"Estimated Time Remaining: {int(eta_minutes)} minutes")
                print(f"Estimated Completion: {eta_time.strftime('%Y-%m-%d %H:%M')}")
        
        elif status == 'completed':
            print("COMPLETED")
            print("-" * 40)
            start_time_dt = datetime.fromisoformat(start_time)
            end_time_dt = datetime.fromisoformat(end_time) if end_time else datetime.now()
            total_time = end_time_dt - start_time_dt
            print(f"Total Time: {int(total_time.total_seconds() / 60)} minutes")
            print(f"Records Processed: {records_proc:,}")
            print(f"Records Inserted: {records_ins:,}")
    
    else:
        print("No data collected yet for this job.")
    
    # Check for checkpoint
    print()
    print("CHECKPOINT STATUS")
    print("-" * 40)
    
    manager = LineupJobManager(environment="production")
    checkpoint = manager.load_checkpoint()
    
    if checkpoint:
        print(f"Checkpoint exists for job: {checkpoint.get('job_id', 'Unknown')}")
        print(f"Current Date: {checkpoint.get('current_date')}")
        print(f"Dates Completed: {len(checkpoint.get('dates_completed', []))}")
        
        if status == 'running':
            print()
            print("[INFO] Collection is currently running.")
            print("       You can interrupt with Ctrl+C and resume later.")
        elif status in ['failed', 'paused']:
            print()
            print("[ACTION REQUIRED] Collection is not running.")
            print("To resume, run:")
            print("  python daily_lineups/refresh_and_collect.py --resume")
    else:
        print("No checkpoint found.")
        if status in ['failed', 'paused']:
            print()
            print("[WARNING] Job failed/paused with no checkpoint.")
            print("You may need to restart the collection.")
    
    # Show recent dates collected
    print()
    print("RECENT DATES COLLECTED")
    print("-" * 40)
    cursor.execute("""
        SELECT date, COUNT(DISTINCT team_key) as teams, COUNT(*) as records
        FROM daily_lineups
        WHERE date >= date('now', '-7 days')
        GROUP BY date
        ORDER BY date DESC
        LIMIT 10
    """)
    
    recent = cursor.fetchall()
    if recent:
        print(f"{'Date':<12} {'Teams':<8} {'Records':<10}")
        for row in recent:
            print(f"{row[0]:<12} {row[1]:<8} {row[2]:<10}")
    else:
        print("No recent data.")
    
    conn.close()
    
    print()
    print("=" * 70)
    print("END OF REPORT")
    print("=" * 70)


if __name__ == "__main__":
    monitor_progress()