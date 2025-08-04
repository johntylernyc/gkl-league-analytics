# PRD: Scheduled Data Refreshes for Production and Local Environments

## Executive Summary

This document specifies the implementation of automated data refresh mechanisms for the GKL Fantasy Baseball Analytics platform, ensuring data freshness in both production (CloudFlare) and local development environments while preventing data duplication and maintaining system efficiency.

## Problem Statement

Currently, data updates require manual execution of Python scripts that:
- Require hourly OAuth token refresh
- Run on local machines only
- Have no automated production update mechanism
- Risk data duplication without proper controls
- Lack synchronization between production and development environments
- Cannot detect and update changed data (lineup modifications, stat corrections)

## Goals

1. **Production Updates**: Automated data refreshes at 6AM, 1PM, 10PM ET daily
2. **Incremental Updates**: Only fetch new/changed data, not full backfills
3. **Change Detection**: Identify and update modified lineups and stat corrections
4. **Data Integrity**: Prevent duplicates while ensuring completeness
5. **Local Sync**: Daily local environment updates to mirror production
6. **Monitoring**: Track update success/failure with proper logging

## Technical Architecture

### Production Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  CloudFlare Workers                      │
│                    (Cron Triggers)                       │
│              6AM, 1PM, 10PM ET Daily                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Actions Runner                       │
│          (Triggered via webhook from CF)                 │
│    • Maintains OAuth tokens                             │
│    • Runs Python collection scripts                     │
│    • Exports incremental updates                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              CloudFlare D1 Database                      │
│         (Production data via Wrangler API)              │
└─────────────────────────────────────────────────────────┘
```

## Implementation Specifications

### 1. Production Scheduled Updates

#### 1.1 CloudFlare Worker Cron Configuration

**File**: `cloudflare-deployment/src/scheduled-updates.js`

```javascript
export default {
  async scheduled(event, env, ctx) {
    const updateType = determineUpdateType(event.cron);
    
    // Track job start
    const jobId = await startJobLog(env.DB, {
      type: `scheduled_${updateType}`,
      trigger: event.cron,
      environment: 'production'
    });

    try {
      // Trigger GitHub Action via webhook
      const response = await fetch('https://api.github.com/repos/[owner]/[repo]/dispatches', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
          'Accept': 'application/vnd.github.v3+json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          event_type: 'data-refresh',
          client_payload: {
            update_type: updateType,
            job_id: jobId,
            timestamp: new Date().toISOString()
          }
        })
      });

      if (!response.ok) {
        throw new Error(`GitHub webhook failed: ${response.status}`);
      }

      await updateJobLog(env.DB, jobId, 'triggered');
      
    } catch (error) {
      await updateJobLog(env.DB, jobId, 'failed', error.message);
      throw error;
    }
  }
};

function determineUpdateType(cron) {
  // Map cron expressions to update types
  const cronMap = {
    '0 11 * * *': 'morning',    // 6AM ET (11 UTC)
    '0 18 * * *': 'afternoon',  // 1PM ET (18 UTC)
    '0 3 * * *': 'evening'      // 10PM ET (3 UTC next day)
  };
  return cronMap[cron] || 'unknown';
}
```

**File**: `cloudflare-deployment/wrangler.toml` (addition)

```toml
[triggers]
crons = [
  "0 11 * * *",  # 6AM ET (11 UTC) - Morning update
  "0 18 * * *",  # 1PM ET (18 UTC) - Afternoon update
  "0 3 * * *"    # 10PM ET (3 UTC) - Evening update
]
```

#### 1.2 GitHub Actions Workflow

**File**: `.github/workflows/scheduled-data-refresh.yml`

```yaml
name: Scheduled Data Refresh

on:
  repository_dispatch:
    types: [data-refresh]
  workflow_dispatch:
    inputs:
      update_type:
        description: 'Update type (morning/afternoon/evening)'
        required: true
        default: 'morning'

jobs:
  refresh-data:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install -g wrangler
          
      - name: Configure environment
        env:
          YAHOO_CLIENT_ID: ${{ secrets.YAHOO_CLIENT_ID }}
          YAHOO_CLIENT_SECRET: ${{ secrets.YAHOO_CLIENT_SECRET }}
          YAHOO_REFRESH_TOKEN: ${{ secrets.YAHOO_REFRESH_TOKEN }}
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: |
          echo "Setting up environment variables"
          
      - name: Refresh OAuth Token
        run: |
          python scripts/refresh_oauth_token.py
          
      - name: Determine Update Range
        id: range
        run: |
          python scripts/determine_update_range.py \
            --update-type=${{ github.event.client_payload.update_type || inputs.update_type }}
            
      - name: Collect Daily Lineups
        run: |
          python daily_lineups/incremental_update.py \
            --start-date=${{ steps.range.outputs.start_date }} \
            --end-date=${{ steps.range.outputs.end_date }}
            
      - name: Collect Transactions
        run: |
          python league_transactions/incremental_update.py \
            --start-date=${{ steps.range.outputs.start_date }} \
            --end-date=${{ steps.range.outputs.end_date }}
            
      - name: Collect MLB Stats
        run: |
          python player_stats/incremental_update.py \
            --start-date=${{ steps.range.outputs.start_date }} \
            --end-date=${{ steps.range.outputs.end_date }}
            
      - name: Export Incremental Updates
        run: |
          python scripts/export_incremental.py \
            --since=${{ steps.range.outputs.start_date }} \
            --output=incremental_update.sql
            
      - name: Deploy to CloudFlare D1
        run: |
          wrangler d1 execute gkl-fantasy \
            --file=incremental_update.sql \
            --remote
            
      - name: Update Job Status
        if: always()
        run: |
          python scripts/update_job_status.py \
            --job-id=${{ github.event.client_payload.job_id }} \
            --status=${{ job.status }}
```

### 2. Change Tracking and Detection

#### 2.1 Change Detection Strategy

Fantasy lineups and MLB stats can change after initial collection due to:
- **Lineup Changes**: Managers modify lineups between collection times (e.g., 12PM to 10PM)
- **Stat Corrections**: MLB retroactively corrects player statistics
- **Transaction Updates**: Late-reported trades or roster moves

To handle these cases, we implement a multi-layered change tracking system:

1. **Content Hash Tracking**: Generate hashes of lineup/stat data to detect changes
2. **Timestamp Comparison**: Track when data was last fetched vs last modified
3. **Force Refresh Window**: Always re-fetch recent data (last 3 days) regardless of existence

#### 2.2 Content Hash Implementation

**File**: `scripts/change_tracking.py`

```python
"""
Change tracking utilities for detecting data modifications.
"""

import hashlib
import json
from typing import Dict, List, Any

def generate_lineup_hash(lineup_data: Dict[str, Any]) -> str:
    """
    Generate a deterministic hash for lineup data.
    
    Args:
        lineup_data: Dictionary containing lineup information
    
    Returns:
        SHA256 hash of the normalized lineup data
    """
    # Normalize the data for consistent hashing
    normalized = {
        'date': lineup_data['date'],
        'team_key': lineup_data['team_key'],
        'players': sorted([
            {
                'player_id': p['player_id'],
                'position': p['selected_position'],
                'status': p.get('status', 'active')
            }
            for p in lineup_data.get('players', [])
        ], key=lambda x: x['player_id'])
    }
    
    # Generate hash
    data_str = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()

def generate_stats_hash(stats_data: Dict[str, Any]) -> str:
    """
    Generate a deterministic hash for player stats.
    
    Args:
        stats_data: Dictionary containing player statistics
    
    Returns:
        SHA256 hash of the normalized stats data
    """
    # Normalize stats for consistent hashing
    normalized = {
        'player_id': stats_data['player_id'],
        'date': stats_data['date'],
        'stats': {k: v for k, v in sorted(stats_data.get('stats', {}).items())}
    }
    
    data_str = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()

def detect_changes(
    existing_hash: str, 
    new_data: Dict[str, Any], 
    hash_func: callable
) -> tuple[bool, str]:
    """
    Detect if data has changed based on content hash.
    
    Args:
        existing_hash: Previously stored hash
        new_data: Newly fetched data
        hash_func: Function to generate hash from data
    
    Returns:
        Tuple of (has_changed, new_hash)
    """
    new_hash = hash_func(new_data)
    has_changed = existing_hash != new_hash
    return has_changed, new_hash
```

### 3. Incremental Update Scripts with Change Detection

#### 3.1 Daily Lineups Incremental Update with Change Tracking

**File**: `daily_lineups/incremental_update.py`

```python
"""
Incremental update script for daily lineups with change detection.
Fetches new data and updates existing data that has changed.
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth.config import get_oauth_session
from daily_lineups.collector import DailyLineupCollector
from daily_lineups.job_manager import start_job_log, update_job_log
from scripts.change_tracking import generate_lineup_hash, detect_changes

# Force refresh window for recent data (in days)
FORCE_REFRESH_DAYS = 3

def get_existing_lineup_data(conn, start_date, end_date):
    """Get existing lineup data with content hashes."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, team_key, content_hash, last_fetched
        FROM daily_lineups_metadata 
        WHERE date BETWEEN ? AND ?
        ORDER BY date, team_key
    """, (start_date, end_date))
    
    existing = {}
    for row in cursor.fetchall():
        date, team_key, content_hash, last_fetched = row
        if date not in existing:
            existing[date] = {}
        existing[date][team_key] = {
            'content_hash': content_hash,
            'last_fetched': last_fetched
        }
    return existing

def should_refresh_lineup(date_str, team_key, existing_data):
    """
    Determine if a lineup should be refreshed.
    
    Refresh if:
    1. Data doesn't exist
    2. Data is within force refresh window
    3. Last fetch was before the most recent scheduled update
    """
    if date_str not in existing_data:
        return True, "new_date"
    
    if team_key not in existing_data[date_str]:
        return True, "new_team"
    
    # Check if within force refresh window
    date = datetime.strptime(date_str, '%Y-%m-%d')
    days_old = (datetime.now() - date).days
    if days_old <= FORCE_REFRESH_DAYS:
        return True, "recent_data"
    
    # Check if fetched before last scheduled update
    last_fetched = datetime.fromisoformat(existing_data[date_str][team_key]['last_fetched'])
    last_scheduled = get_last_scheduled_update_time()
    if last_fetched < last_scheduled:
        return True, "stale_data"
    
    return False, "up_to_date"

def get_last_scheduled_update_time():
    """Get the timestamp of the most recent scheduled update."""
    now = datetime.now()
    update_times = [
        now.replace(hour=6, minute=0, second=0),   # 6AM ET
        now.replace(hour=13, minute=0, second=0),  # 1PM ET
        now.replace(hour=22, minute=0, second=0),  # 10PM ET
    ]
    
    # Find the most recent past update time
    for update_time in reversed(update_times):
        if update_time <= now:
            return update_time
    
    # If none today, use yesterday's last update
    return (now - timedelta(days=1)).replace(hour=22, minute=0, second=0)

def update_lineup_with_change_detection(conn, lineup_data, job_id):
    """
    Update lineup data with change detection.
    
    Returns:
        Dictionary with stats: {new: int, updated: int, unchanged: int}
    """
    stats = {'new': 0, 'updated': 0, 'unchanged': 0}
    cursor = conn.cursor()
    
    # Generate content hash
    content_hash = generate_lineup_hash(lineup_data)
    date = lineup_data['date']
    team_key = lineup_data['team_key']
    
    # Check if lineup exists and has changed
    cursor.execute("""
        SELECT content_hash FROM daily_lineups_metadata
        WHERE date = ? AND team_key = ?
    """, (date, team_key))
    
    existing = cursor.fetchone()
    
    if not existing:
        # New lineup
        stats['new'] += 1
        action = 'INSERT'
    elif existing[0] != content_hash:
        # Lineup has changed
        stats['updated'] += 1
        action = 'UPDATE'
        
        # Log the change
        cursor.execute("""
            INSERT INTO lineup_changes (
                date, team_key, old_hash, new_hash, 
                change_detected_at, job_id
            ) VALUES (?, ?, ?, ?, datetime('now'), ?)
        """, (date, team_key, existing[0], content_hash, job_id))
    else:
        # No changes
        stats['unchanged'] += 1
        # Still update last_fetched timestamp
        cursor.execute("""
            UPDATE daily_lineups_metadata
            SET last_fetched = datetime('now')
            WHERE date = ? AND team_key = ?
        """, (date, team_key))
        return stats
    
    # Perform insert or update
    if action == 'INSERT':
        # Insert new lineup data
        for player in lineup_data['players']:
            cursor.execute("""
                INSERT INTO daily_lineups (
                    date, team_key, player_id, selected_position,
                    job_id, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (date, team_key, player['player_id'], 
                  player['selected_position'], job_id))
        
        # Insert metadata
        cursor.execute("""
            INSERT INTO daily_lineups_metadata (
                date, team_key, content_hash, last_fetched, job_id
            ) VALUES (?, ?, ?, datetime('now'), ?)
        """, (date, team_key, content_hash, job_id))
        
    else:  # UPDATE
        # Delete existing lineup entries
        cursor.execute("""
            DELETE FROM daily_lineups 
            WHERE date = ? AND team_key = ?
        """, (date, team_key))
        
        # Insert updated lineup data
        for player in lineup_data['players']:
            cursor.execute("""
                INSERT INTO daily_lineups (
                    date, team_key, player_id, selected_position,
                    job_id, created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, 
                    (SELECT created_at FROM daily_lineups 
                     WHERE date = ? AND team_key = ? LIMIT 1),
                    datetime('now'))
            """, (date, team_key, player['player_id'], 
                  player['selected_position'], job_id, date, team_key))
        
        # Update metadata
        cursor.execute("""
            UPDATE daily_lineups_metadata
            SET content_hash = ?, last_fetched = datetime('now'), job_id = ?
            WHERE date = ? AND team_key = ?
        """, (content_hash, job_id, date, team_key))
    
    conn.commit()
    return stats

def incremental_update(start_date=None, end_date=None):
    """
    Perform incremental update of daily lineups with change detection.
    
    Args:
        start_date: Start date (default: 3 days ago)
        end_date: End date (default: today)
    """
    # Default to last 3 days if not specified
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=FORCE_REFRESH_DAYS)).strftime('%Y-%m-%d')
    
    # Start job logging
    job_id = start_job_log(
        job_type='daily_lineups_incremental',
        environment='production',
        date_range_start=start_date,
        date_range_end=end_date,
        metadata={'update_type': 'incremental_with_changes'}
    )
    
    try:
        # Connect to database
        conn = sqlite3.connect('database/league_analytics.db')
        
        # Get existing lineup metadata
        existing_data = get_existing_lineup_data(conn, start_date, end_date)
        
        # Initialize collector
        session = get_oauth_session()
        collector = DailyLineupCollector(session)
        
        # Generate list of dates to process
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        total_stats = {'new': 0, 'updated': 0, 'unchanged': 0, 'checked': 0}
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            print(f"Processing lineups for {date_str}...")
            
            # Fetch all lineups for the date
            lineups = collector.fetch_lineups_for_date(date_str)
            
            for lineup in lineups:
                team_key = lineup['team_key']
                should_refresh, reason = should_refresh_lineup(
                    date_str, team_key, existing_data
                )
                
                if should_refresh:
                    print(f"  Refreshing {team_key}: {reason}")
                    stats = update_lineup_with_change_detection(
                        conn, lineup, job_id
                    )
                    total_stats['new'] += stats['new']
                    total_stats['updated'] += stats['updated']
                    total_stats['unchanged'] += stats['unchanged']
                
                total_stats['checked'] += 1
            
            current += timedelta(days=1)
        
        # Update job status
        update_job_log(job_id, 'completed', 
                      records_processed=total_stats['checked'],
                      records_inserted=total_stats['new'],
                      metadata={
                          'new_lineups': total_stats['new'],
                          'updated_lineups': total_stats['updated'],
                          'unchanged_lineups': total_stats['unchanged']
                      })
        
        print(f"\nUpdate Summary:")
        print(f"  Checked: {total_stats['checked']} lineups")
        print(f"  New: {total_stats['new']}")
        print(f"  Updated: {total_stats['updated']}")
        print(f"  Unchanged: {total_stats['unchanged']}")
        
    except Exception as e:
        update_job_log(job_id, 'failed', error_message=str(e))
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    incremental_update(args.start_date, args.end_date)
```

#### 3.2 MLB Stats Update with Stat Correction Detection

**File**: `player_stats/incremental_update.py`

```python
"""
Incremental update for MLB stats with stat correction detection.
Handles retroactive stat corrections from official MLB sources.
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth.config import get_oauth_session
from player_stats.collector import MLBStatsCollector
from player_stats.job_manager import start_job_log, update_job_log
from scripts.change_tracking import generate_stats_hash

# Window for checking stat corrections (in days)
STAT_CORRECTION_WINDOW = 7

def detect_stat_corrections(conn, stats_data, job_id):
    """
    Detect and handle MLB stat corrections.
    
    MLB can retroactively correct stats up to 7 days after a game.
    This function checks for changes in previously collected stats.
    """
    cursor = conn.cursor()
    player_id = stats_data['player_id']
    date = stats_data['date']
    
    # Generate hash of current stats
    new_hash = generate_stats_hash(stats_data)
    
    # Check for existing stats
    cursor.execute("""
        SELECT content_hash, stats_json 
        FROM daily_gkl_player_stats
        WHERE date = ? AND yahoo_player_id = ?
    """, (date, player_id))
    
    existing = cursor.fetchone()
    
    if existing and existing[0] != new_hash:
        # Stat correction detected
        old_stats = json.loads(existing[1])
        
        # Log the correction
        cursor.execute("""
            INSERT INTO stat_corrections (
                player_id, date, stat_category, 
                old_value, new_value, 
                correction_detected_at, job_id
            ) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """, (player_id, date, 
              json.dumps(old_stats), 
              json.dumps(stats_data['stats']),
              job_id))
        
        # Update the stats
        cursor.execute("""
            UPDATE daily_gkl_player_stats
            SET stats_json = ?, 
                content_hash = ?,
                last_updated = datetime('now'),
                has_correction = 1
            WHERE date = ? AND yahoo_player_id = ?
        """, (json.dumps(stats_data['stats']), new_hash, date, player_id))
        
        return True
    
    return False

def incremental_stats_update(start_date=None, end_date=None):
    """
    Update MLB stats with correction detection.
    
    Always re-checks stats within the correction window.
    """
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        # Go back further for stat corrections
        start_date = (datetime.now() - timedelta(days=STAT_CORRECTION_WINDOW)).strftime('%Y-%m-%d')
    
    job_id = start_job_log(
        job_type='mlb_stats_incremental',
        environment='production',
        date_range_start=start_date,
        date_range_end=end_date,
        metadata={'correction_window': STAT_CORRECTION_WINDOW}
    )
    
    try:
        conn = sqlite3.connect('database/league_analytics.db')
        session = get_oauth_session()
        collector = MLBStatsCollector(session)
        
        stats_summary = {
            'new': 0,
            'updated': 0,
            'corrections': 0,
            'unchanged': 0
        }
        
        # Process each date
        current = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            days_old = (datetime.now() - current).days
            
            # Determine if we should check for corrections
            check_corrections = days_old <= STAT_CORRECTION_WINDOW
            
            print(f"Processing stats for {date_str} (corrections: {check_corrections})...")
            
            # Fetch stats for all players who played on this date
            player_stats = collector.fetch_stats_for_date(date_str)
            
            for stats in player_stats:
                if check_corrections:
                    # Check for stat corrections
                    had_correction = detect_stat_corrections(conn, stats, job_id)
                    if had_correction:
                        stats_summary['corrections'] += 1
                    else:
                        stats_summary['unchanged'] += 1
                else:
                    # Just insert/update normally
                    stats_summary['new'] += 1
            
            current += timedelta(days=1)
        
        # Commit all changes
        conn.commit()
        
        # Update job log
        update_job_log(job_id, 'completed',
                      records_processed=sum(stats_summary.values()),
                      metadata=stats_summary)
        
        print(f"\nStats Update Summary:")
        print(f"  New: {stats_summary['new']}")
        print(f"  Corrections: {stats_summary['corrections']}")
        print(f"  Unchanged: {stats_summary['unchanged']}")
        
    except Exception as e:
        update_job_log(job_id, 'failed', error_message=str(e))
        raise
    finally:
        conn.close()
```

### 4. Database Schema for Change Tracking

**File**: `scripts/change_tracking_schema.sql`

```sql
-- Metadata table for tracking lineup changes
CREATE TABLE IF NOT EXISTS daily_lineups_metadata (
    date TEXT NOT NULL,
    team_key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    PRIMARY KEY (date, team_key)
);

-- Log table for lineup changes
CREATE TABLE IF NOT EXISTS lineup_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    team_key TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT,
    change_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    INDEX idx_lineup_changes_date (date),
    INDEX idx_lineup_changes_team (team_key)
);

-- Metadata for player stats with content tracking
ALTER TABLE daily_gkl_player_stats 
ADD COLUMN content_hash TEXT;

ALTER TABLE daily_gkl_player_stats 
ADD COLUMN has_correction BOOLEAN DEFAULT 0;

-- Log table for stat corrections
CREATE TABLE IF NOT EXISTS stat_corrections (
    correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    stat_category TEXT,
    old_value TEXT,
    new_value TEXT,
    correction_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    INDEX idx_stat_corrections_player (player_id),
    INDEX idx_stat_corrections_date (date)
);

-- Transaction change tracking
CREATE TABLE IF NOT EXISTS transaction_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    change_type TEXT NOT NULL, -- 'new', 'modified', 'cancelled'
    old_data TEXT,
    new_data TEXT,
    change_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_id TEXT,
    INDEX idx_transaction_changes (transaction_id)
);

-- Ensure unique constraints with REPLACE semantics
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_lineups_unique 
ON daily_lineups(date, team_key, player_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_unique 
ON transactions(transaction_id, player_id, movement_type);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_stats_unique 
ON daily_gkl_player_stats(date, yahoo_player_id);
```

### 5. Local Development Environment Sync with Change Tracking

#### 5.1 Local Sync Script with Change Detection

**File**: `scripts/sync_local_from_production.py`

```python
"""
Sync local development database with production CloudFlare D1.
Runs once daily to mirror production data.
"""

import os
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path

def export_production_data():
    """Export data from CloudFlare D1 to local SQL file."""
    print("Exporting production data from CloudFlare D1...")
    
    tables = ['transactions', 'daily_lineups', 'daily_gkl_player_stats', 'job_log']
    
    for table in tables:
        print(f"Exporting {table}...")
        subprocess.run([
            'wrangler', 'd1', 'execute', 'gkl-fantasy',
            '--command', f"SELECT * FROM {table}",
            '--json'
        ], capture_output=True, text=True)
        
        # Parse JSON and convert to SQL INSERT statements
        # ... conversion logic here ...

def import_to_local(sql_file):
    """Import SQL file to local SQLite database."""
    print("Importing to local SQLite database...")
    
    conn = sqlite3.connect('database/league_analytics.db')
    
    with open(sql_file, 'r') as f:
        sql_script = f.read()
        
    # Begin transaction for atomic update
    conn.executescript(f"""
        BEGIN TRANSACTION;
        
        -- Clear existing data (optional - for full sync)
        DELETE FROM transactions WHERE date >= date('now', '-7 days');
        DELETE FROM daily_lineups WHERE date >= date('now', '-7 days');
        DELETE FROM daily_gkl_player_stats WHERE date >= date('now', '-7 days');
        
        -- Import new data
        {sql_script}
        
        -- Update sync metadata
        INSERT OR REPLACE INTO sync_log (
            sync_date, 
            sync_type, 
            status, 
            records_synced
        ) VALUES (
            datetime('now'),
            'production_to_local',
            'completed',
            changes()
        );
        
        COMMIT;
    """)
    
    conn.close()
    print("Local sync completed successfully")

def main():
    """Main sync process."""
    try:
        # Export from production
        export_production_data()
        
        # Import to local
        import_to_local('production_export.sql')
        
        # Log success
        print(f"Sync completed at {datetime.now()}")
        
    except Exception as e:
        print(f"Sync failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

#### 5.2 Local Scheduler Configuration

**For Windows (Task Scheduler)** - `scripts/windows_daily_sync.bat`:

```batch
@echo off
echo Starting daily local sync at %date% %time%

REM Navigate to project directory
cd /d "C:\path\to\gkl-league-analytics"

REM Activate Python virtual environment (if using)
call venv\Scripts\activate

REM Run sync script
python scripts\sync_local_from_production.py

REM Log completion
echo Sync completed at %date% %time% >> sync.log

pause
```

**For Linux/Mac (Cron)** - Add to crontab:

```bash
# Daily sync at 7AM local time
0 7 * * * cd /path/to/gkl-league-analytics && python scripts/sync_local_from_production.py >> sync.log 2>&1
```

### 6. Monitoring and Alerting with Change Tracking

#### 6.1 Health Check Endpoint with Change Metrics

**File**: `cloudflare-deployment/src/health-check.js`

```javascript
export async function checkDataFreshness(env) {
  // Main data freshness checks
  const freshness = await env.DB.prepare(`
    SELECT 
      'transactions' as table_name,
      MAX(date) as latest_date,
      COUNT(*) as total_records,
      CASE 
        WHEN MAX(date) >= date('now', '-1 day') THEN 'fresh'
        WHEN MAX(date) >= date('now', '-3 days') THEN 'stale'
        ELSE 'critical'
      END as status
    FROM transactions
    
    UNION ALL
    
    SELECT 
      'daily_lineups' as table_name,
      MAX(date) as latest_date,
      COUNT(*) as total_records,
      CASE 
        WHEN MAX(date) >= date('now', '-1 day') THEN 'fresh'
        WHEN MAX(date) >= date('now', '-3 days') THEN 'stale'
        ELSE 'critical'
      END as status
    FROM daily_lineups
    
    UNION ALL
    
    SELECT 
      'player_stats' as table_name,
      MAX(date) as latest_date,
      COUNT(*) as total_records,
      CASE 
        WHEN MAX(date) >= date('now', '-1 day') THEN 'fresh'
        WHEN MAX(date) >= date('now', '-3 days') THEN 'stale'
        ELSE 'critical'
      END as status
    FROM daily_gkl_player_stats
  `).all();
  
  // Change tracking metrics
  const changeMetrics = await env.DB.prepare(`
    SELECT 
      'lineup_changes' as metric_type,
      COUNT(*) as count,
      MAX(change_detected_at) as last_change
    FROM lineup_changes
    WHERE change_detected_at >= datetime('now', '-24 hours')
    
    UNION ALL
    
    SELECT 
      'stat_corrections' as metric_type,
      COUNT(*) as count,
      MAX(correction_detected_at) as last_change
    FROM stat_corrections
    WHERE correction_detected_at >= datetime('now', '-7 days')
    
    UNION ALL
    
    SELECT 
      'transaction_changes' as metric_type,
      COUNT(*) as count,
      MAX(change_detected_at) as last_change
    FROM transaction_changes
    WHERE change_detected_at >= datetime('now', '-24 hours')
  `).all();
  
  // Recent job status
  const recentJobs = await env.DB.prepare(`
    SELECT 
      job_type,
      status,
      COUNT(*) as count
    FROM job_log
    WHERE start_time >= datetime('now', '-24 hours')
    GROUP BY job_type, status
  `).all();
  
  return {
    timestamp: new Date().toISOString(),
    data_freshness: freshness.results,
    change_tracking: {
      last_24h: changeMetrics.results,
      summary: {
        lineup_changes: changeMetrics.results.find(m => m.metric_type === 'lineup_changes')?.count || 0,
        stat_corrections: changeMetrics.results.find(m => m.metric_type === 'stat_corrections')?.count || 0,
        transaction_changes: changeMetrics.results.find(m => m.metric_type === 'transaction_changes')?.count || 0
      }
    },
    recent_jobs: recentJobs.results,
    overall_status: freshness.results.every(c => c.status === 'fresh') ? 'healthy' : 'degraded'
  };
}
```

#### 6.2 Alerting Configuration with Change Notifications

```javascript
// In scheduled worker
const healthCheck = await checkDataFreshness(env);

// Alert on failures or critical data staleness
if (updateStatus === 'failed' || healthCheck.overall_status === 'critical') {
  await sendAlert(env, {
    type: 'data_freshness_alert',
    severity: 'high',
    message: `Data refresh failed or data is critically stale`,
    details: healthCheck
  });
}

// Alert on unusual change activity
if (healthCheck.change_tracking.summary.stat_corrections > 10) {
  await sendAlert(env, {
    type: 'stat_correction_alert',
    severity: 'medium',
    message: `Unusual number of stat corrections detected: ${healthCheck.change_tracking.summary.stat_corrections}`,
    details: healthCheck.change_tracking
  });
}

// Daily summary of changes
if (updateType === 'morning') {
  await sendDailySummary(env, {
    lineup_changes: healthCheck.change_tracking.summary.lineup_changes,
    stat_corrections: healthCheck.change_tracking.summary.stat_corrections,
    transaction_changes: healthCheck.change_tracking.summary.transaction_changes,
    job_summary: healthCheck.recent_jobs
  });
}
```

### 7. Error Recovery and Change Reconciliation

#### 7.1 Retry Logic with Change Detection

```python
def retry_with_backoff(func, max_retries=3, initial_delay=60):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
```

#### 7.2 Manual Recovery Process with Change Audit

```bash
# Check failed jobs
sqlite3 database/league_analytics.db \
  "SELECT * FROM job_log WHERE status = 'failed' ORDER BY start_time DESC LIMIT 5"

# Check recent changes
sqlite3 database/league_analytics.db \
  "SELECT * FROM lineup_changes WHERE change_detected_at >= datetime('now', '-24 hours')"

# View stat corrections
sqlite3 database/league_analytics.db \
  "SELECT player_id, date, old_value, new_value FROM stat_corrections 
   WHERE correction_detected_at >= datetime('now', '-7 days')"

# Identify missing date ranges
python scripts/identify_gaps.py --table=daily_lineups

# Force refresh with change detection for specific dates
python daily_lineups/incremental_update.py \
  --start-date=2025-08-01 --end-date=2025-08-03 --force-refresh

# Manual reconciliation for stat corrections
python player_stats/reconcile_corrections.py --date=2025-08-01

# Re-export with change tracking
python scripts/export_incremental.py \
  --since=2025-08-01 \
  --include-changes \
  --output=incremental_update_with_changes.sql

# Deploy to CloudFlare
wrangler d1 execute gkl-fantasy --file=incremental_update_with_changes.sql --remote

# Verify changes were applied
wrangler d1 execute gkl-fantasy \
  --command="SELECT COUNT(*) FROM lineup_changes WHERE date >= '2025-08-01'" --remote
```

## Implementation Strategy

### Stage 1: Foundation Setup (Days 1-3)
**Goal**: Establish core infrastructure without breaking existing functionality

**Deliverables**:
- [ ] Database schema updates for change tracking tables
- [ ] Content hash generation utilities (`scripts/change_tracking.py`)
- [ ] Unit tests for hash generation
- [ ] Verification that existing queries still work

**Testing Criteria**:
- Hash generation produces consistent results
- Existing database operations unaffected
- No performance degradation

### Stage 2: Manual Change Detection (Days 4-5)
**Goal**: Validate change detection logic before automation

**Deliverables**:
- [ ] Manual detection script for lineup changes
- [ ] Manual detection script for stat corrections
- [ ] Force refresh logic for date ranges
- [ ] Change detection logging

**Testing Criteria**:
- Known changes are detected correctly
- Force refresh windows work as expected
- No false positives in change detection

### Stage 3: Incremental Update Scripts (Days 6-10)
**Goal**: Replace existing collection scripts with change-aware versions

**Deliverables**:
- [ ] `daily_lineups/incremental_update.py` with change detection
- [ ] `player_stats/incremental_update.py` with stat corrections
- [ ] `league_transactions/incremental_update.py` with modifications
- [ ] Hash comparison and change logging

**Testing Criteria**:
- All changes detected and logged
- Performance within acceptable limits
- Backward compatibility maintained

### Stage 4: Local Testing Environment (Days 11-12)
**Goal**: Thoroughly test before production deployment

**Deliverables**:
- [ ] Test database with known change scenarios
- [ ] Performance benchmarks documented
- [ ] Query optimization if needed
- [ ] Test results documentation

**Testing Criteria**:
- 100% change detection accuracy
- Updates complete within 5 minutes
- No data loss or corruption

### Stage 5: GitHub Actions Integration (Days 13-15)
**Goal**: Automate data collection with GitHub Actions

**Deliverables**:
- [ ] `.github/workflows/scheduled-data-refresh.yml`
- [ ] GitHub Secrets configuration
- [ ] Repository dispatch setup
- [ ] Error handling and retry logic

**Testing Criteria**:
- Manual workflow runs succeed
- Authentication works correctly
- Error recovery functions properly

### Stage 6: CloudFlare Integration (Days 16-18)
**Goal**: Connect automated updates to production

**Deliverables**:
- [ ] `cloudflare-deployment/src/scheduled-updates.js`
- [ ] Cron triggers (6AM, 1PM, 10PM ET)
- [ ] GitHub webhook integration
- [ ] Export scripts with change metadata

**Testing Criteria**:
- Worker triggers on schedule
- Webhook successfully triggers GitHub Actions
- Data exports import to D1 correctly

### Stage 7: Monitoring & Alerting (Days 19-20)
**Goal**: Add visibility into the update process

**Deliverables**:
- [ ] Health check endpoints with change metrics
- [ ] Alert configuration for failures
- [ ] Change pattern detection
- [ ] Daily summary reports

**Testing Criteria**:
- Health checks return accurate metrics
- Alerts fire on appropriate conditions
- Reports generated correctly

### Stage 8: Production Rollout (Days 21-25)
**Goal**: Deploy to production with safety measures

**Rollout Plan**:
1. Day 21: Enable morning update only (6AM ET)
2. Day 22-23: Monitor and verify
3. Day 24: Add afternoon update (1PM ET)
4. Day 25: Add evening update (10PM ET)

**Testing Criteria**:
- All updates run on schedule
- Change detection working in production
- No data inconsistencies
- Performance metrics met

### Stage 9: Documentation & Local Sync (Days 26-28)
**Goal**: Ensure maintainability and complete local sync

**Deliverables**:
- [ ] Complete documentation update
- [ ] Troubleshooting guide
- [ ] Local sync scripts and schedulers
- [ ] Runbooks for common issues

**Testing Criteria**:
- Documentation is comprehensive
- Local sync works on all platforms
- Runbooks cover known issues

## Implementation Timeline

### Week 1 (Stages 1-3)
- Core infrastructure and change detection logic
- Manual testing and validation
- Incremental update script development

### Week 2 (Stages 4-6)
- Local testing and performance optimization
- GitHub Actions and CloudFlare integration
- Automated scheduling setup

### Week 3 (Stages 7-8)
- Monitoring and alerting implementation
- Gradual production rollout
- Production monitoring and verification

### Week 4 (Stage 9 & Buffer)
- Documentation and local sync completion
- Buffer time for issues and refinements
- Final validation and sign-off

## Decision Gates

**Gate 1 (After Stage 2)**: Validate change detection accuracy
- Required: >99% detection accuracy on test data
- Decision: Proceed or refine detection logic

**Gate 2 (After Stage 4)**: Performance validation
- Required: Updates complete in <5 minutes
- Decision: Proceed or optimize

**Gate 3 (After Stage 6)**: Integration validation
- Required: Successful end-to-end test
- Decision: Proceed to production or debug

**Gate 4 (After Stage 8)**: Production validation
- Required: 3 days of successful production runs
- Decision: Full rollout or rollback

## Success Metrics

1. **Data Freshness**: 95% of updates complete within 5 minutes of scheduled time
2. **Change Detection**: 100% of lineup changes detected within same-day refresh cycles
3. **Stat Corrections**: 100% of MLB stat corrections captured within 7-day window
4. **Success Rate**: >99% successful updates per month
5. **Deduplication**: Zero duplicate records in production
6. **Change Accuracy**: <0.1% false positive change detections
7. **Local Sync**: Daily sync completes in <5 minutes with all changes propagated
8. **Monitoring**: Alert response time <2 minutes for critical issues
9. **Audit Trail**: Complete change history maintained for 90 days

## Security Considerations

1. **Token Management**:
   - Store OAuth refresh tokens in GitHub Secrets
   - Rotate tokens monthly
   - Never commit tokens to repository

2. **API Rate Limiting**:
   - Respect Yahoo API rate limits (1 req/sec)
   - Implement backoff strategies
   - Monitor API usage

3. **Database Access**:
   - Use read-only credentials where possible
   - Audit all write operations
   - Backup before major updates

## Rollback Strategy

```bash
# Create backup before update
wrangler d1 backup create gkl-fantasy

# If update fails, restore from backup
wrangler d1 backup restore gkl-fantasy --backup-id=<backup-id>

# Verify restoration
wrangler d1 execute gkl-fantasy --command="SELECT COUNT(*) FROM transactions" --remote
```

## Alternative Approaches Considered

1. **Direct CloudFlare to Yahoo API**: Rejected due to OAuth complexity and token management
2. **Self-hosted update service**: Rejected due to infrastructure overhead
3. **Manual daily updates**: Rejected due to human error risk and time requirements
4. **Full daily backfill**: Rejected due to API rate limits and unnecessary data transfer

## Appendices

### A. Environment Variables Required

```env
# GitHub Secrets
YAHOO_CLIENT_ID=xxx
YAHOO_CLIENT_SECRET=xxx
YAHOO_REFRESH_TOKEN=xxx
CLOUDFLARE_API_TOKEN=xxx
CLOUDFLARE_ACCOUNT_ID=xxx
GITHUB_TOKEN=xxx

# CloudFlare Worker Secrets
GITHUB_TOKEN=xxx
ALERT_WEBHOOK_URL=xxx
```

### B. Database Schema Additions

```sql
-- Sync tracking table
CREATE TABLE IF NOT EXISTS sync_log (
    sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL,
    records_synced INTEGER,
    error_message TEXT,
    duration_seconds REAL
);

-- Add last_updated columns for incremental tracking
ALTER TABLE transactions ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE daily_lineups ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE daily_gkl_player_stats ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

### C. Testing Plan

1. **Unit Tests**: Test each incremental update function
2. **Integration Tests**: Test full update pipeline
3. **Load Tests**: Verify system handles peak update times
4. **Failure Tests**: Test retry and recovery mechanisms
5. **Sync Tests**: Verify local/production consistency

## Change Tracking Best Practices

### 1. Hash Generation Standards
- Always normalize data before hashing (sort keys, consistent formatting)
- Use SHA256 for content hashes
- Store hashes alongside data for quick comparison
- Never hash sensitive data directly (use redacted versions)

### 2. Refresh Windows
- **Live Games**: Refresh every scheduled update (6AM, 1PM, 10PM ET)
- **Recent Data (0-3 days)**: Always refresh regardless of existing data
- **Historical Data (4-7 days)**: Check for stat corrections only
- **Archive Data (>7 days)**: Only update if explicitly requested

### 3. Change Notification Priorities
- **Critical**: Failed updates, data older than 3 days
- **High**: Unusual number of stat corrections (>10 in 24h)
- **Medium**: Large lineup changes (>50% of teams modified)
- **Low**: Normal daily changes, successful updates

### 4. Performance Optimization
- Batch change detection queries to minimize database load
- Use database indexes on change tracking tables
- Implement connection pooling for concurrent checks
- Cache unchanged data hashes for 24 hours

### 5. Data Consistency Rules
- Never delete original data when changes detected
- Always maintain audit trail of all changes
- Use database transactions for atomic updates
- Implement version numbering for critical data

---

*Document Version: 2.0*  
*Last Updated: August 2025*  
*Author: GKL Fantasy Baseball Analytics Team*
*Major Revision: Added comprehensive change tracking and detection capabilities*