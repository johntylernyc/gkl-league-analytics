"""
Helper script to refresh tokens and start collection.
"""

import sys
import os
from pathlib import Path
import json
import requests
import base64
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from auth.config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL, REDIRECT_URI

def refresh_tokens():
    """Refresh the access token using the refresh token."""
    
    token_file = Path(__file__).parent.parent / "auth" / "tokens.json"
    
    # Read existing tokens
    with open(token_file, 'r') as f:
        tokens = json.load(f)
    
    refresh_token = tokens.get('refresh_token')
    if not refresh_token:
        print("No refresh token found!")
        return False
    
    # Prepare request
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'grant_type': 'refresh_token',
        'redirect_uri': REDIRECT_URI,
        'refresh_token': refresh_token
    }
    
    print(f"Refreshing tokens at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        new_tokens = response.json()
        
        # Save new tokens
        with open(token_file, 'w') as f:
            json.dump(new_tokens, f, indent=4)
        
        print("[OK] Tokens refreshed successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to refresh tokens: {e}")
        return False


def start_collection(start_date, end_date, resume=False):
    """Start the lineup collection."""
    
    from daily_lineups.collector_enhanced import EnhancedLineupsCollector
    
    print(f"\nStarting collection from {start_date} to {end_date}")
    print("This will take approximately 2-3 hours for the full season.")
    print("The collection has checkpoint/resume capability - you can interrupt with Ctrl+C")
    print("-" * 60)
    
    collector = EnhancedLineupsCollector(environment="production")
    
    try:
        if resume:
            job_id = collector.collect_date_range_with_resume(
                start_date="",
                end_date="",
                league_key=None,
                resume=True
            )
        else:
            job_id = collector.collect_date_range_with_resume(
                start_date=start_date,
                end_date=end_date,
                league_key="mlb.l.6966",
                resume=False
            )
        
        print(f"\n[OK] Collection completed successfully!")
        print(f"Job ID: {job_id}")
        
        # Show summary
        from daily_lineups.job_manager import LineupJobManager
        manager = LineupJobManager(environment="production")
        status = manager.get_job_status(job_id)
        
        if status:
            print(f"\nSummary:")
            print(f"  Status: {status['status']}")
            print(f"  Records processed: {status['records_processed']:,}")
            print(f"  Records inserted: {status['records_inserted']:,}")
            print(f"  Time: {status['start_time']} to {status['end_time']}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Collection interrupted by user")
        print("The checkpoint has been saved. You can resume with:")
        print("  python daily_lineups/refresh_and_collect.py --resume")
        return False
        
    except Exception as e:
        print(f"\n[ERROR] Collection failed: {e}")
        print("\nIf the error is token-related, try running this script again.")
        print("If you were interrupted, you can resume with:")
        print("  python daily_lineups/refresh_and_collect.py --resume")
        return False


def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Refresh tokens and collect lineup data")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--no-refresh", action="store_true", help="Skip token refresh")
    parser.add_argument("--start", default="2025-03-27", help="Start date (default: 2025-03-27)")
    parser.add_argument("--end", default="2025-09-28", help="End date (default: 2025-09-28)")
    
    args = parser.parse_args()
    
    # Check for checkpoint if resuming
    if args.resume:
        from daily_lineups.job_manager import LineupJobManager
        manager = LineupJobManager(environment="production")
        checkpoint = manager.load_checkpoint()
        
        if checkpoint:
            print(f"Found checkpoint for job: {checkpoint['job_id']}")
            print(f"Will resume from: {checkpoint.get('current_date')}")
            print(f"Dates completed: {len(checkpoint.get('dates_completed', []))}")
        else:
            print("No checkpoint found. Starting fresh collection.")
            args.resume = False
    
    # Refresh tokens unless skipped
    if not args.no_refresh:
        if not refresh_tokens():
            print("\nFailed to refresh tokens. You may need to re-authenticate.")
            return 1
    
    # Start collection
    if start_collection(args.start, args.end, args.resume):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())