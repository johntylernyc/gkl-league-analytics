"""
Deployment verification script.
Checks that all components are properly configured and working.
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

def check_database():
    """Verify database and tables exist."""
    print("\n" + "="*60)
    print("DATABASE CHECK")
    print("="*60)
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    
    if not db_path.exists():
        print("[FAIL] Database not found at:", db_path)
        return False
    
    print("[OK] Database found")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check required tables
    required_tables = [
        'job_log',
        'daily_lineups',
        'daily_lineups_metadata',
        'daily_gkl_player_stats',
        'league_transactions',
        'lineup_changes',
        'stat_corrections'
    ]
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
    """)
    
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    all_tables_exist = True
    for table in required_tables:
        if table in existing_tables:
            print(f"[OK] Table '{table}' exists")
        else:
            print(f"[FAIL] Table '{table}' missing")
            all_tables_exist = False
    
    conn.close()
    return all_tables_exist

def check_recent_jobs():
    """Check for recent job executions."""
    print("\n" + "="*60)
    print("RECENT JOBS")
    print("="*60)
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get jobs from last 7 days
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT job_id, job_type, environment, status, 
               datetime(start_time), datetime(end_time),
               records_processed, records_inserted
        FROM job_log
        WHERE date(start_time) >= ?
        ORDER BY start_time DESC
        LIMIT 10
    """, (seven_days_ago,))
    
    jobs = cursor.fetchall()
    
    if not jobs:
        print("[WARN] No jobs found in last 7 days")
        print("       Run a manual test to verify system works")
        return False
    
    print(f"\nFound {len(jobs)} recent jobs:\n")
    print(f"{'Job Type':<25} {'Status':<12} {'Env':<8} {'Start Time':<20} {'Records':<10}")
    print("-" * 85)
    
    has_successful = False
    for job in jobs:
        job_id, job_type, env, status, start_time, end_time, processed, inserted = job
        
        if status == 'completed':
            has_successful = True
            status_display = f"[OK] {status}"
        elif status == 'failed':
            status_display = f"[FAIL] {status}"
        else:
            status_display = f"[WARN] {status}"
        
        print(f"{job_type[:25]:<25} {status_display:<12} {env:<8} {start_time or 'N/A':<20} {processed or 0:<10}")
    
    conn.close()
    
    if has_successful:
        print("\n[OK] Found successful job completions")
        return True
    else:
        print("\n[WARN] No successful jobs found")
        return False

def check_change_tracking():
    """Check if change tracking is working."""
    print("\n" + "="*60)
    print("CHANGE TRACKING")
    print("="*60)
    
    db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check lineup changes
    cursor.execute("""
        SELECT COUNT(*) FROM lineup_changes
    """)
    lineup_changes = cursor.fetchone()[0]
    
    # Check stat corrections
    cursor.execute("""
        SELECT COUNT(*) FROM stat_corrections
    """)
    stat_corrections = cursor.fetchone()[0]
    
    # Check metadata
    cursor.execute("""
        SELECT COUNT(*) FROM daily_lineups_metadata
        WHERE content_hash IS NOT NULL
    """)
    lineup_hashes = cursor.fetchone()[0]
    
    print(f"Lineup changes tracked: {lineup_changes}")
    print(f"Stat corrections tracked: {stat_corrections}")
    print(f"Lineups with content hashes: {lineup_hashes}")
    
    if lineup_hashes > 0:
        print("\n[OK] Change tracking is configured")
        return True
    else:
        print("\n[WARN] No content hashes found - run incremental update to initialize")
        return False

def check_github_workflow():
    """Check if GitHub workflow file exists."""
    print("\n" + "="*60)
    print("GITHUB WORKFLOW")
    print("="*60)
    
    workflow_path = Path(__file__).parent.parent / '.github' / 'workflows' / 'data-refresh.yml'
    
    if workflow_path.exists():
        print(f"[OK] Workflow file exists: {workflow_path}")
        
        # Check workflow content
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'schedule:' in content:
            print("[OK] Scheduled triggers configured")
        else:
            print("[WARN] No scheduled triggers found")
            
        if 'workflow_dispatch:' in content:
            print("[OK] Manual trigger configured")
        else:
            print("[WARN] No manual trigger found")
            
        return True
    else:
        print(f"[FAIL] Workflow file not found: {workflow_path}")
        return False

def check_cloudflare_config():
    """Check if CloudFlare Worker is configured."""
    print("\n" + "="*60)
    print("CLOUDFLARE CONFIGURATION")
    print("="*60)
    
    worker_path = Path(__file__).parent.parent / 'cloudflare' / 'worker.js'
    wrangler_path = Path(__file__).parent.parent / 'cloudflare' / 'wrangler.toml'
    
    checks_passed = True
    
    if worker_path.exists():
        print(f"[OK] Worker script exists: {worker_path}")
        
        with open(worker_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'your-github-username' in content:
            print("[WARN] GitHub username not configured in worker.js")
            print("      Update: const GITHUB_OWNER = 'your-actual-username';")
            checks_passed = False
        else:
            print("[OK] GitHub username configured")
    else:
        print(f"[FAIL] Worker script not found: {worker_path}")
        checks_passed = False
    
    if wrangler_path.exists():
        print(f"[OK] Wrangler config exists: {wrangler_path}")
        
        with open(wrangler_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'YOUR_CLOUDFLARE_ACCOUNT_ID' in content:
            print("[WARN] CloudFlare account ID not configured in wrangler.toml")
            print("      Update: account_id = \"your-actual-account-id\"")
            checks_passed = False
        else:
            print("[OK] CloudFlare account ID configured")
            
        # Check for cron triggers
        if 'crons = [' in content:
            print("[OK] Scheduled triggers configured")
        else:
            print("[WARN] No scheduled triggers found")
    else:
        print(f"[FAIL] Wrangler config not found: {wrangler_path}")
        checks_passed = False
    
    return checks_passed

def check_env_file():
    """Check if .env file exists with required variables."""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES")
    print("="*60)
    
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        print("[FAIL] .env file not found")
        print("      Create .env with Yahoo OAuth credentials")
        return False
    
    print("[OK] .env file exists")
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_vars = [
        'YAHOO_CLIENT_ID',
        'YAHOO_CLIENT_SECRET',
        'YAHOO_REDIRECT_URI',
        'YAHOO_AUTHORIZATION_CODE'
    ]
    
    all_vars_present = True
    for var in required_vars:
        if f'{var}=' in content:
            print(f"[OK] {var} is set")
        else:
            print(f"[FAIL] {var} is missing")
            all_vars_present = False
    
    return all_vars_present

def main():
    """Run all verification checks."""
    print("\n" + "="*60)
    print("GKL FANTASY ANALYTICS - DEPLOYMENT VERIFICATION")
    print("="*60)
    
    checks = {
        'Environment Variables': check_env_file(),
        'Database': check_database(),
        'GitHub Workflow': check_github_workflow(),
        'CloudFlare Config': check_cloudflare_config(),
        'Recent Jobs': check_recent_jobs(),
        'Change Tracking': check_change_tracking()
    }
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{check_name:<25} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n[SUCCESS] ALL CHECKS PASSED - System is ready for deployment!")
        print("\nNext steps:")
        print("1. Add GitHub secrets (see docs/development-docs/guides/)")
        print("2. Deploy CloudFlare Worker (see docs/development-docs/guides/)")
        print("3. Test the system (see docs/development-docs/deployment/)")
    else:
        print("\n[WARNING] SOME CHECKS FAILED - Review the issues above")
        print("\nRefer to deployment guides in docs/development-docs/")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())