#!/usr/bin/env python3
"""
Trigger GitHub Actions Workflow via API

This script triggers the data-refresh workflow using the GitHub API.
You'll need a personal access token with 'repo' and 'workflow' permissions.

Usage:
    python trigger_workflow.py --token YOUR_GITHUB_TOKEN
    python trigger_workflow.py --token YOUR_GITHUB_TOKEN --refresh-type afternoon
"""

import sys
import json
import argparse
import requests
from datetime import datetime

def trigger_workflow(token, owner, repo, workflow_id, inputs):
    """Trigger a GitHub Actions workflow."""
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "ref": "main",  # Branch to run on
        "inputs": inputs
    }
    
    print(f"Triggering workflow: {workflow_id}")
    print(f"Repository: {owner}/{repo}")
    print(f"Inputs: {json.dumps(inputs, indent=2)}")
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 204:
        print("\n✅ Workflow triggered successfully!")
        print("Check status at: https://github.com/{owner}/{repo}/actions")
        return True
    else:
        print(f"\n❌ Failed to trigger workflow")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def get_recent_runs(token, owner, repo, workflow_id, limit=5):
    """Get recent workflow runs."""
    
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}"
    }
    
    params = {
        "per_page": limit
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        runs = response.json()["workflow_runs"]
        print(f"\nRecent workflow runs (last {limit}):")
        for run in runs:
            created = datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            status = run["status"]
            conclusion = run["conclusion"] or "in progress"
            print(f"  - {created.strftime('%Y-%m-%d %H:%M')} UTC: {status} ({conclusion})")
    else:
        print(f"Failed to get workflow runs: {response.status_code}")


def main():
    parser = argparse.ArgumentParser(
        description='Trigger GitHub Actions workflow via API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--token', required=True,
                       help='GitHub personal access token')
    parser.add_argument('--owner', default='your-github-username',
                       help='Repository owner (GitHub username)')
    parser.add_argument('--repo', default='gkl-league-analytics',
                       help='Repository name')
    parser.add_argument('--workflow', default='data-refresh.yml',
                       help='Workflow file name')
    parser.add_argument('--refresh-type', default='manual',
                       choices=['morning', 'afternoon', 'night', 'manual'],
                       help='Type of refresh')
    parser.add_argument('--environment', default='production',
                       choices=['production', 'test'],
                       help='Environment to run in')
    parser.add_argument('--date-range',
                       help='Date range (start,end in YYYY-MM-DD format)')
    parser.add_argument('--check-status', action='store_true',
                       help='Just check recent run status')
    
    args = parser.parse_args()
    
    # Update this with your actual GitHub username
    if args.owner == 'your-github-username':
        print("⚠️  Please update --owner with your GitHub username")
        print("   Example: python trigger_workflow.py --token YOUR_TOKEN --owner johndoe")
        return
    
    if args.check_status:
        get_recent_runs(args.token, args.owner, args.repo, args.workflow)
    else:
        inputs = {
            "refresh_type": args.refresh_type,
            "environment": args.environment
        }
        
        if args.date_range:
            inputs["date_range"] = args.date_range
        
        success = trigger_workflow(
            args.token,
            args.owner,
            args.repo,
            args.workflow,
            inputs
        )
        
        if success:
            # Show recent runs
            get_recent_runs(args.token, args.owner, args.repo, args.workflow, 3)


if __name__ == '__main__':
    main()