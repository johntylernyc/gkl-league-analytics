# Player Stats Pipeline Improvements - Technical Implementation Plan

## Overview

This document provides the detailed technical implementation plan for modernizing the player_stats module to align with the patterns established in daily_lineups and league_transactions modules.

**Status**: Completed  
**Start Date**: August 5, 2025  
**Completion Date**: August 5, 2025

## Pre-Implementation Checklist

- [x] Backup current player_stats directory
- [x] Document any running cron jobs using player_stats scripts
- [x] Verify no active data collection processes
- [x] Create feature branch: `feature/player-stats-pipeline-improvements`

## Phase 1: File Organization and Archival

### 1.1 Create Archive Directory Structure

```bash
cd data_pipeline/player_stats
mkdir -p archive/2025-08-05-cleanup
```

### 1.2 Archive Deprecated Scripts

Move the following files to `archive/2025-08-05-cleanup/`:
```bash
# One-time population scripts
mv fix_star_player_mappings.py archive/2025-08-05-cleanup/
mv populate_core_mappings.py archive/2025-08-05-cleanup/
mv populate_external_ids.py archive/2025-08-05-cleanup/

# Temporary data file
mv mapping_candidates.csv archive/2025-08-05-cleanup/

# Create archive README
cat > archive/2025-08-05-cleanup/README.md << 'EOF'
# Archived Player Stats Scripts - August 5, 2025

## Archived Files

### One-Time Population Scripts
- `fix_star_player_mappings.py` - Fixed star player mapping issues
- `populate_core_mappings.py` - Initial population of player ID mappings
- `populate_external_ids.py` - Population of external ID mappings

### Data Files
- `mapping_candidates.csv` - Temporary mapping candidates file

## Reason for Archival
These scripts were one-time utilities used during initial setup and data fixes.
They are no longer needed for regular pipeline operations.
EOF
```

### 1.3 Clean Temporary Directories

```bash
# Clean cache directory (keep .gitkeep if exists)
find cache/ -type f ! -name '.gitkeep' -delete

# Clean temp directory
find temp/ -type f ! -name '.gitkeep' -delete

# Clean old logs (keep recent ones)
find logs/ -type f -mtime +30 -delete
```

### 1.4 Rename Core Script

```bash
# Rename incremental_update.py to update_stats.py
git mv incremental_update.py update_stats.py
```

## Phase 2: Script Updates

### 2.1 Update backfill_stats.py

#### Add D1 Support

```python
# Add at the top with other imports
try:
    from data_pipeline.common.d1_connection import D1Connection, is_d1_available
    D1_AVAILABLE = True
except ImportError:
    D1_AVAILABLE = False
    D1Connection = None
    is_d1_available = lambda: False

# Update class initialization
class PlayerStatsBackfiller:
    def __init__(self, environment='production', use_d1=None):
        self.environment = environment
        
        # Determine database type
        if use_d1 is None:
            self.use_d1 = D1_AVAILABLE and is_d1_available()
        else:
            self.use_d1 = use_d1
        
        if self.use_d1:
            if not D1_AVAILABLE:
                raise RuntimeError("D1 connection module not available")
            self.d1_conn = D1Connection()
            self.db_path = None
        else:
            # Use SQLite
            config = get_config_for_environment(environment)
            self.db_path = config['database_path']
            self.d1_conn = None
```

#### Update CLI Arguments

```python
# In main() function, add:
parser.add_argument('--use-d1', action='store_true',
                   help='Force use of Cloudflare D1 database')
parser.add_argument('--use-sqlite', action='store_true',
                   help='Force use of local SQLite database')

# Add validation
if args.use_d1 and args.use_sqlite:
    parser.error("Cannot specify both --use-d1 and --use-sqlite")

use_d1 = None
if args.use_d1:
    use_d1 = True
elif args.use_sqlite:
    use_d1 = False
```

### 2.2 Update update_stats.py (renamed from incremental_update.py)

#### Update All Import References

```python
# Search and replace in all files:
# "from incremental_update import" → "from update_stats import"
# "import incremental_update" → "import update_stats"
```

#### Align with update_lineups.py Pattern

```python
# Add standard CLI options
parser.add_argument('--days', type=int, default=7,
                   help='Number of days to look back (default: 7)')
parser.add_argument('--since-last', action='store_true',
                   help='Update from last stats date in database')
parser.add_argument('--date', type=str,
                   help='Update specific date (YYYY-MM-DD)')
parser.add_argument('--environment', default='production',
                   choices=['test', 'production'])
parser.add_argument('--quiet', action='store_true',
                   help='Minimal output for automation')
parser.add_argument('--use-d1', action='store_true',
                   help='Force use of Cloudflare D1 database')
parser.add_argument('--use-sqlite', action='store_true',
                   help='Force use of local SQLite database')
```

#### Implement Quiet Mode

```python
# Add logging control
if args.quiet:
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)

# Replace print statements with logger
logger.info(f"Starting player stats update for {date}")
```

### 2.3 Create data_quality_check.py

```python
#!/usr/bin/env python3
"""
Player Stats Data Quality Validation Module

Validates player statistics data for completeness, accuracy, and consistency.
Follows patterns established in daily_lineups and league_transactions modules.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PlayerStatsDataQualityChecker:
    """Validates player statistics data quality."""
    
    def __init__(self):
        self.validation_rules = {
            'required_fields': [
                'date', 'yahoo_player_id', 'player_name', 'team_code'
            ],
            'stat_bounds': {
                'batting_avg': (0.0, 1.0),
                'batting_obp': (0.0, 1.0),
                'batting_slg': (0.0, 5.0),
                'pitching_era': (0.0, 30.0),
                'pitching_whip': (0.0, 10.0)
            },
            'valid_positions': [
                'C', '1B', '2B', '3B', 'SS', 'OF', 'DH', 
                'SP', 'RP', 'P', 'BN', 'IL', 'IL+', 'NA'
            ]
        }
    
    def validate_single(self, stat_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single player stat record.
        
        Returns:
            Dict with keys: is_valid, errors, warnings
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in self.validation_rules['required_fields']:
            if field not in stat_record or stat_record[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate stat bounds
        for stat_name, (min_val, max_val) in self.validation_rules['stat_bounds'].items():
            if stat_name in stat_record and stat_record[stat_name] is not None:
                value = stat_record[stat_name]
                if not (min_val <= value <= max_val):
                    errors.append(f"{stat_name} out of bounds: {value} (expected {min_val}-{max_val})")
        
        # Validate player ID mapping
        if 'yahoo_player_id' in stat_record and not stat_record.get('mapping_confidence'):
            warnings.append("No player ID mapping confidence score")
        
        # Check data consistency
        if stat_record.get('games_played', 0) == 0:
            if any(stat_record.get(f'batting_{stat}', 0) > 0 for stat in ['hits', 'runs', 'rbis']):
                errors.append("Player has batting stats but games_played is 0")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_batch(self, stat_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of player stat records."""
        results = {
            'total': len(stat_records),
            'valid': 0,
            'invalid': 0,
            'warnings': 0,
            'errors_by_type': {},
            'sample_errors': []
        }
        
        for record in stat_records:
            validation = self.validate_single(record)
            
            if validation['is_valid']:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                
                # Track error types
                for error in validation['errors']:
                    error_type = error.split(':')[0]
                    results['errors_by_type'][error_type] = \
                        results['errors_by_type'].get(error_type, 0) + 1
                
                # Keep sample of errors
                if len(results['sample_errors']) < 5:
                    results['sample_errors'].append({
                        'player': record.get('player_name', 'Unknown'),
                        'date': record.get('date', 'Unknown'),
                        'errors': validation['errors']
                    })
            
            if validation['warnings']:
                results['warnings'] += len(validation['warnings'])
        
        return results
    
    def check_player_mappings(self, conn) -> Dict[str, Any]:
        """Check player ID mapping quality."""
        cursor = conn.cursor()
        
        # Get mapping statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_mappings,
                COUNT(CASE WHEN confidence_score >= 0.9 THEN 1 END) as high_confidence,
                COUNT(CASE WHEN confidence_score < 0.7 THEN 1 END) as low_confidence,
                COUNT(CASE WHEN validation_status = 'failed' THEN 1 END) as failed_mappings,
                AVG(confidence_score) as avg_confidence
            FROM player_id_mapping
            WHERE is_active = TRUE
        """)
        
        result = cursor.fetchone()
        
        return {
            'total_mappings': result[0],
            'high_confidence': result[1],
            'low_confidence': result[2],
            'failed_mappings': result[3],
            'avg_confidence': result[4] or 0
        }
    
    def generate_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate human-readable validation report."""
        report = []
        report.append("=" * 60)
        report.append("PLAYER STATS DATA QUALITY REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Records: {validation_results['total']}")
        report.append(f"Valid Records: {validation_results['valid']} "
                     f"({validation_results['valid']/validation_results['total']*100:.1f}%)")
        report.append(f"Invalid Records: {validation_results['invalid']}")
        report.append(f"Total Warnings: {validation_results['warnings']}")
        report.append("")
        
        # Error breakdown
        if validation_results['errors_by_type']:
            report.append("ERROR BREAKDOWN")
            report.append("-" * 20)
            for error_type, count in sorted(validation_results['errors_by_type'].items()):
                report.append(f"{error_type}: {count}")
            report.append("")
        
        # Sample errors
        if validation_results['sample_errors']:
            report.append("SAMPLE ERRORS")
            report.append("-" * 20)
            for i, sample in enumerate(validation_results['sample_errors'], 1):
                report.append(f"{i}. Player: {sample['player']} (Date: {sample['date']})")
                for error in sample['errors']:
                    report.append(f"   - {error}")
            report.append("")
        
        report.append("=" * 60)
        return "\n".join(report)


# CLI interface
if __name__ == "__main__":
    import argparse
    import sqlite3
    from config import get_config_for_environment
    
    parser = argparse.ArgumentParser(description="Validate player stats data quality")
    parser.add_argument('--environment', default='production',
                       choices=['test', 'production'])
    parser.add_argument('--date', help='Validate specific date')
    parser.add_argument('--check-mappings', action='store_true',
                       help='Check player ID mapping quality')
    
    args = parser.parse_args()
    
    # Connect to database
    config = get_config_for_environment(args.environment)
    conn = sqlite3.connect(config['database_path'])
    
    checker = PlayerStatsDataQualityChecker()
    
    if args.check_mappings:
        mapping_stats = checker.check_player_mappings(conn)
        print("\nPLAYER ID MAPPING STATISTICS")
        print("-" * 30)
        for key, value in mapping_stats.items():
            print(f"{key}: {value}")
    
    # Validate recent stats
    query = "SELECT * FROM daily_gkl_player_stats"
    params = []
    
    if args.date:
        query += " WHERE date = ?"
        params.append(args.date)
    else:
        query += " WHERE date >= date('now', '-7 days')"
    
    query += " LIMIT 1000"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    # Convert to dict format
    columns = [desc[0] for desc in cursor.description]
    records = []
    for row in cursor.fetchall():
        records.append(dict(zip(columns, row)))
    
    if records:
        results = checker.validate_batch(records)
        print(checker.generate_report(results))
    else:
        print("No records found to validate")
    
    conn.close()
```

## Phase 3: D1 Integration

### 3.1 Update D1Connection Module

Add the following methods to `data_pipeline/common/d1_connection.py`:

```python
def insert_player_stats(self, stats: List[Dict], job_id: str) -> Tuple[int, int]:
    """
    Insert player statistics records.
    
    Args:
        stats: List of stat dictionaries
        job_id: Job ID for tracking
        
    Returns:
        Tuple of (inserted_count, error_count)
    """
    if not stats:
        return 0, 0
    
    # Ensure job exists
    self.ensure_job_exists(job_id, 'player_stats_collection', 'production')
    
    inserted = 0
    errors = 0
    
    # Process in batches
    for batch in self._chunk_list(stats, 50):
        try:
            for stat in batch:
                query = """
                    REPLACE INTO daily_gkl_player_stats (
                        job_id, date, yahoo_player_id, player_name, team_code,
                        position_codes, games_played, is_starter,
                        batting_at_bats, batting_runs, batting_hits, batting_doubles,
                        batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                        batting_walks, batting_strikeouts, batting_avg, batting_obp, batting_slg,
                        pitching_wins, pitching_losses, pitching_saves, pitching_holds,
                        pitching_innings_pitched, pitching_strikeouts, pitching_era, pitching_whip,
                        has_batting_data, has_pitching_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """
                
                params = [
                    job_id,
                    stat.get('date'),
                    stat.get('yahoo_player_id'),
                    stat.get('player_name'),
                    stat.get('team_code'),
                    stat.get('position_codes'),
                    stat.get('games_played', 0),
                    stat.get('is_starter', False),
                    # Batting stats
                    stat.get('batting_at_bats'),
                    stat.get('batting_runs'),
                    stat.get('batting_hits'),
                    stat.get('batting_doubles'),
                    stat.get('batting_triples'),
                    stat.get('batting_home_runs'),
                    stat.get('batting_rbis'),
                    stat.get('batting_stolen_bases'),
                    stat.get('batting_walks'),
                    stat.get('batting_strikeouts'),
                    stat.get('batting_avg'),
                    stat.get('batting_obp'),
                    stat.get('batting_slg'),
                    # Pitching stats
                    stat.get('pitching_wins'),
                    stat.get('pitching_losses'),
                    stat.get('pitching_saves'),
                    stat.get('pitching_holds'),
                    stat.get('pitching_innings_pitched'),
                    stat.get('pitching_strikeouts'),
                    stat.get('pitching_era'),
                    stat.get('pitching_whip'),
                    # Flags
                    stat.get('has_batting_data', False),
                    stat.get('has_pitching_data', False)
                ]
                
                self.execute(query, params)
                inserted += 1
                
        except Exception as e:
            logger.error(f"Error inserting player stats batch: {str(e)}")
            errors += len(batch)
    
    return inserted, errors

def insert_player_mappings(self, mappings: List[Dict]) -> Tuple[int, int]:
    """
    Insert or update player ID mappings.
    
    Args:
        mappings: List of mapping dictionaries
        
    Returns:
        Tuple of (inserted_count, error_count)
    """
    if not mappings:
        return 0, 0
    
    inserted = 0
    errors = 0
    
    for mapping in mappings:
        try:
            query = """
                REPLACE INTO player_id_mapping (
                    yahoo_player_id, yahoo_player_name, mlb_player_id,
                    fangraphs_id, bbref_id, standardized_name, team_code,
                    position_codes, confidence_score, mapping_method,
                    is_active, validation_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """
            
            params = [
                mapping.get('yahoo_player_id'),
                mapping.get('yahoo_player_name'),
                mapping.get('mlb_player_id'),
                mapping.get('fangraphs_id'),
                mapping.get('bbref_id'),
                mapping.get('standardized_name'),
                mapping.get('team_code'),
                mapping.get('position_codes'),
                mapping.get('confidence_score', 0.0),
                mapping.get('mapping_method', 'fuzzy'),
                mapping.get('is_active', True),
                mapping.get('validation_status', 'pending')
            ]
            
            self.execute(query, params)
            inserted += 1
            
        except Exception as e:
            logger.error(f"Error inserting player mapping: {str(e)}")
            errors += 1
    
    return inserted, errors
```

### 3.2 Update sync_to_production.py

Add player stats export function:

```python
def export_recent_player_stats(conn, export_dir, days_back=7):
    """Export recent player stats to SQL file."""
    cursor = conn.cursor()
    
    # Check if daily_gkl_player_stats table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_gkl_player_stats'")
    if not cursor.fetchone():
        print("⚠️  daily_gkl_player_stats table not found, skipping")
        return None, set()
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    # Get player stats
    cursor.execute("""
        SELECT * FROM daily_gkl_player_stats 
        WHERE date >= ? 
        ORDER BY date DESC
    """, (cutoff_date,))
    
    stats = cursor.fetchall()
    
    if not stats:
        print(f"No player stats found since {cutoff_date}")
        return None, set()
    
    # Get column names and find job_id column index
    cursor.execute("PRAGMA table_info(daily_gkl_player_stats)")
    columns_info = cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    # Find job_id column index
    job_id_index = None
    for i, col in enumerate(columns):
        if col == 'job_id':
            job_id_index = i
            break
    
    # Collect unique job_ids
    job_ids = set()
    if job_id_index is not None:
        for row in stats:
            if row[job_id_index]:
                job_ids.add(row[job_id_index])
    
    # Also export player_id_mapping updates
    cursor.execute("""
        SELECT * FROM player_id_mapping 
        WHERE updated_at >= ? OR created_at >= ?
    """, (cutoff_date, cutoff_date))
    
    mappings = cursor.fetchall()
    
    # Generate SQL file
    sql_file = export_dir / f'player_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
    
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Recent player stats export\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Stats since: {cutoff_date}\n")
        f.write(f"-- Count: {len(stats)} stats, {len(mappings)} mappings\n\n")
        
        # Export stats
        for row in stats:
            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                elif isinstance(val, bool):
                    values.append('1' if val else '0')
                else:
                    values.append(str(val))
            
            f.write(f"REPLACE INTO daily_gkl_player_stats ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
        
        # Export mappings if any
        if mappings:
            f.write("\n-- Player ID mapping updates\n")
            cursor.execute("PRAGMA table_info(player_id_mapping)")
            mapping_columns = [col[1] for col in cursor.fetchall()]
            
            for row in mappings:
                values = []
                for val in row:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, str):
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                    elif isinstance(val, bool):
                        values.append('1' if val else '0')
                    else:
                        values.append(str(val))
                
                f.write(f"REPLACE INTO player_id_mapping ({', '.join(mapping_columns)}) VALUES ({', '.join(values)});\n")
    
    print(f"✅ Exported {len(stats)} player stats and {len(mappings)} mappings to {sql_file}")
    return sql_file, job_ids

# Add to main() function after lineup export:
# Export player stats
player_stats_file, player_stats_job_ids = export_recent_player_stats(conn, export_dir, days_back=days_back)
if player_stats_job_ids:
    all_job_ids.update(player_stats_job_ids)
```

## Phase 4: Documentation Updates

### 4.1 Update README.md

Create new README.md following the established pattern:

```markdown
# Player Stats Data Pipeline

This module handles the collection and management of MLB player statistics data using pybaseball and Yahoo Fantasy Sports APIs.

## Scripts

### 1. `backfill_stats.py` - Bulk Historical Data Collection

Used for initial data population or bulk historical data collection.

**Features:**
- Parallel processing with configurable workers (max 4)
- Automatic rate limiting for API calls
- Comprehensive job logging
- Resume capability for interrupted jobs
- Data quality validation
- Multi-season support
- Player ID mapping integration

**Usage:**
```bash
# Backfill entire season
python backfill_stats.py --season 2025

# Backfill date range with parallel workers
python backfill_stats.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Backfill with specific environment
python backfill_stats.py --season 2025 --environment test

# Use D1 database directly
python backfill_stats.py --season 2025 --use-d1
```

### 2. `update_stats.py` - Incremental Daily Updates

Used for regular updates to keep the database current. Designed for automation (cron/scheduled tasks).

**Features:**
- Default 7-day lookback window (for stat corrections)
- Automatic duplicate detection
- Player ID mapping updates
- Minimal output for automation
- Job logging for audit trail
- Direct D1 support

**Usage:**
```bash
# Default 7-day update
python update_stats.py

# Custom lookback period
python update_stats.py --days 14

# Update from last stats date
python update_stats.py --since-last

# Update specific date
python update_stats.py --date 2025-08-04

# Quiet mode for cron
python update_stats.py --quiet

# Force D1 database
python update_stats.py --use-d1
```

### 3. `data_quality_check.py` - Data Validation Module

Validates player statistics data completeness and quality.

**Features:**
- Stat boundary validation (batting average, ERA, etc.)
- Player ID mapping confidence checks
- Data consistency validation
- Field completeness validation
- Human-readable reports

**Usage:**
```python
from data_quality_check import PlayerStatsDataQualityChecker

checker = PlayerStatsDataQualityChecker()
results = checker.validate_batch(stats)
print(checker.generate_report(results))
```

**CLI Usage:**
```bash
# Check recent stats
python data_quality_check.py

# Check specific date
python data_quality_check.py --date 2025-08-04

# Check player mappings
python data_quality_check.py --check-mappings
```

## Data Flow

1. **Initial Setup**: 
   - Run `backfill_stats.py` to populate historical data
   - Verify player ID mappings are populated
   
2. **Daily Updates**: 
   - Schedule `update_stats.py` to run daily (recommend 6 AM ET)
   - Stats include 7-day lookback for corrections
   
3. **Quality Checks**: 
   - Both scripts automatically validate data before insertion
   - Run `data_quality_check.py` periodically for audits

## Supporting Modules

### Core Components
- **collector.py** - Core MLB stats collection logic
- **repository.py** - Database access layer
- **job_manager.py** - Job tracking and logging
- **config.py** - Configuration settings
- **player_id_mapper.py** - Yahoo ↔ MLB player ID mapping
- **mlb_stats_api.py** - MLB statistics API integration
- **pybaseball_integration.py** - PyBaseball library wrapper
- **data_validator.py** - Data validation utilities

## Database Schema

### Primary Tables

#### daily_gkl_player_stats
Main statistics table containing daily player performance data:
- Player identification (Yahoo ID, name, team)
- Game participation info
- Batting statistics (if applicable)
- Pitching statistics (if applicable)
- Fantasy point calculations
- Data quality metadata

#### player_id_mapping
Maps Yahoo Fantasy player IDs to MLB data sources:
- Yahoo player information
- MLB official player IDs
- External IDs (Fangraphs, Baseball Reference)
- Mapping confidence scores
- Validation status

#### Staging Tables
- `mlb_batting_stats_staging` - Raw batting data
- `mlb_pitching_stats_staging` - Raw pitching data

### Constraints
- Unique constraint on (date, yahoo_player_id) in daily_gkl_player_stats
- Foreign key to job_log table for audit trail

## Important Notes

### Data Volume
With ~750 active MLB players and daily stats, expect:
- ~750 records per day during season
- ~135,000 records for a full season (180 days)
- Player ID mappings: ~1,500 total players (includes minors/inactive)

### API Rate Limiting
- PyBaseball: Respectful delays built-in
- Yahoo API: 1 request/second limit
- MLB Stats API: No hard limit but be respectful

### Stat Corrections
MLB occasionally corrects statistics up to 7 days after games. The update script's default 7-day lookback window handles these corrections automatically.

### Player ID Mapping
The system uses fuzzy matching to map Yahoo player IDs to MLB data sources. New players may need manual mapping verification.

## Automation Example

Add to crontab for daily updates at 6 AM ET:
```bash
# Player stats update (after lineups/transactions)
0 6 * * * cd /path/to/data_pipeline/player_stats && python update_stats.py --quiet
```

## Troubleshooting

### No Stats Found
- Check if games were played on the date
- Verify player ID mappings exist
- Check PyBaseball API availability

### Player Mapping Issues
- Run `data_quality_check.py --check-mappings`
- Check confidence scores for low-quality mappings
- Manual mappings may be needed for new players

### API Errors
- PyBaseball may have temporary outages
- Check network connectivity
- Verify no API changes

### Data Quality Issues
- Run data quality check for detailed report
- Common issues: missing stats for injured players
- Stat corrections may cause temporary mismatches

## Archive

Old scripts have been archived to `archive/2025-08-05-cleanup/` for reference.
```

### 4.2 Update CLAUDE.md

Add references to the new player_stats structure in the common development commands section.

## Phase 5: Testing & Validation

### 5.1 Test Scripts

```bash
# Test backfill with small date range
python backfill_stats.py --start 2025-08-01 --end 2025-08-03 --environment test

# Test update script
python update_stats.py --days 3 --environment test

# Test data quality
python data_quality_check.py --environment test

# Test D1 support
python update_stats.py --days 1 --use-d1
```

### 5.2 Verify Imports

```bash
# Check for old import references
grep -r "incremental_update" . --include="*.py"

# Verify new imports work
python -c "from data_pipeline.player_stats import update_stats"
```

### 5.3 Integration Testing

1. Run full pipeline test in test environment
2. Verify job logging works correctly
3. Check data quality reports
4. Test automation scenarios

## Post-Implementation Checklist

- [x] All scripts tested and working
- [x] Documentation updated and accurate
- [x] Archive directory created with README
- [x] No references to archived scripts
- [x] D1 integration tested
- [x] sync_to_production.py updated
- [x] CLAUDE.md updated
- [ ] PR created and reviewed
- [ ] Merge to main branch
- [ ] Update any external documentation

## Rollback Plan

If issues arise:
1. Git revert the merge commit
2. Restore archived scripts from archive directory
3. Update any import references back
4. Document issues for resolution

---

*Implementation Plan Version: 1.0*  
*Created: August 5, 2025*  
*Status: Ready for Implementation*