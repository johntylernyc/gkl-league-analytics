"""
System monitoring script for automated data refresh.
Shows recent job status, data updates, and system health.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

def monitor_system():
    """Monitor the automated data refresh system."""
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    
    if not db_path.exists():
        print("❌ Database not found. System may not be running yet.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 GKL FANTASY ANALYTICS - SYSTEM MONITOR")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Recent Jobs (Last 7 Days)
    print("📊 RECENT JOBS (Last 7 Days)")
    print("-" * 50)
    
    cursor.execute("""
        SELECT job_type, environment, status, 
               datetime(start_time) as start,
               datetime(end_time) as end,
               records_processed, records_inserted,
               CASE 
                 WHEN end_time IS NOT NULL THEN
                   ROUND((julianday(end_time) - julianday(start_time)) * 24 * 60, 1)
                 ELSE NULL
               END as duration_minutes
        FROM job_log
        WHERE date(start_time) >= date('now', '-7 days')
        ORDER BY start_time DESC
        LIMIT 15
    """)
    
    jobs = cursor.fetchall()
    
    if jobs:
        print(f"{'Type':<20} {'Env':<4} {'Status':<10} {'Start':<16} {'Duration':<8} {'Records':<8}")
        print("-" * 75)
        
        for job in jobs:
            job_type, env, status, start, end, processed, inserted, duration = job
            
            # Status indicator
            if status == 'completed':
                status_icon = "✅"
            elif status == 'failed':
                status_icon = "❌"
            else:
                status_icon = "⏳"
            
            # Format duration
            duration_str = f"{duration}m" if duration else "N/A"
            
            # Format records
            records_str = f"{processed or 0}"
            
            print(f"{job_type[:20]:<20} {env:<4} {status_icon} {status:<8} {start:<16} {duration_str:<8} {records_str:<8}")
    else:
        print("No recent jobs found.")
    
    print()
    
    # System Health Check
    print("🏥 SYSTEM HEALTH")
    print("-" * 50)
    
    # Check for recent successful runs
    cursor.execute("""
        SELECT COUNT(*) 
        FROM job_log 
        WHERE status = 'completed' 
          AND date(start_time) >= date('now', '-1 days')
    """)
    recent_success = cursor.fetchone()[0]
    
    # Check for recent failures
    cursor.execute("""
        SELECT COUNT(*) 
        FROM job_log 
        WHERE status = 'failed' 
          AND date(start_time) >= date('now', '-1 days')
    """)
    recent_failures = cursor.fetchone()[0]
    
    # Check last successful run
    cursor.execute("""
        SELECT datetime(start_time), job_type
        FROM job_log 
        WHERE status = 'completed'
        ORDER BY start_time DESC
        LIMIT 1
    """)
    last_success = cursor.fetchone()
    
    print(f"✅ Successful runs (24h): {recent_success}")
    print(f"❌ Failed runs (24h): {recent_failures}")
    
    if last_success:
        print(f"🕐 Last successful run: {last_success[0]} ({last_success[1]})")
    else:
        print("⚠️  No successful runs found")
    
    # Health status
    if recent_success > 0 and recent_failures == 0:
        print("🟢 System Status: HEALTHY")
    elif recent_success > recent_failures:
        print("🟡 System Status: DEGRADED (some failures)")
    else:
        print("🔴 System Status: UNHEALTHY (frequent failures)")
    
    print()
    
    # Data Activity (Recent Changes)
    print("📈 DATA ACTIVITY (Last 24 Hours)")
    print("-" * 50)
    
    # Lineup changes
    cursor.execute("""
        SELECT COUNT(*) 
        FROM lineup_changes 
        WHERE date(detected_at) >= date('now', '-1 days')
    """)
    lineup_changes = cursor.fetchone()[0]
    
    # Stat corrections  
    cursor.execute("""
        SELECT COUNT(*) 
        FROM stat_corrections 
        WHERE date(correction_detected_at) >= date('now', '-1 days')
    """)
    stat_corrections = cursor.fetchone()[0]
    
    # New transactions
    cursor.execute("""
        SELECT COUNT(*) 
        FROM league_transactions 
        WHERE date(created_at) >= date('now', '-1 days')
    """)
    new_transactions = cursor.fetchone()[0]
    
    print(f"🔄 Lineup changes detected: {lineup_changes}")
    print(f"📊 Stat corrections found: {stat_corrections}")
    print(f"💰 New transactions: {new_transactions}")
    
    total_activity = lineup_changes + stat_corrections + new_transactions
    if total_activity > 0:
        print(f"📊 Total data changes: {total_activity}")
    else:
        print("ℹ️  No data changes detected (normal during off-season)")
    
    print()
    
    # Database Size
    print("💾 DATABASE INFO")
    print("-" * 50)
    
    # Get table counts
    tables = [
        'job_log',
        'league_transactions', 
        'daily_lineups',
        'daily_gkl_player_stats',
        'lineup_changes',
        'stat_corrections'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📋 {table}: {count:,} records")
        except sqlite3.OperationalError:
            print(f"❌ {table}: Table not found")
    
    # Database file size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"💾 Database size: {db_size_mb:.1f} MB")
    
    print()
    
    # Next Expected Run
    print("⏰ SCHEDULE INFO")
    print("-" * 50)
    
    now = datetime.now()
    
    # Define schedule times (in local time)
    schedule_times = [
        (6, 0, "Morning Full Refresh"),
        (13, 0, "Afternoon Incremental"),
        (22, 0, "Night Incremental")
    ]
    
    # Find next run
    next_runs = []
    for hour, minute, description in schedule_times:
        # Today's run
        today_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if today_run > now:
            next_runs.append((today_run, description))
        
        # Tomorrow's run
        tomorrow_run = today_run + timedelta(days=1)
        next_runs.append((tomorrow_run, description))
    
    # Sort and get next 3
    next_runs.sort()
    next_runs = next_runs[:3]
    
    print("Next scheduled runs:")
    for run_time, description in next_runs:
        time_str = run_time.strftime('%Y-%m-%d %H:%M ET')
        delta = run_time - now
        
        if delta.days > 0:
            delta_str = f"in {delta.days}d {delta.seconds//3600}h"
        elif delta.seconds > 3600:
            delta_str = f"in {delta.seconds//3600}h {(delta.seconds%3600)//60}m"
        else:
            delta_str = f"in {delta.seconds//60}m"
        
        print(f"  🕐 {time_str} - {description} ({delta_str})")
    
    print()
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    try:
        monitor_system()
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        sys.exit(1)