# Project Cleanup Summary
**Date:** August 3, 2025

## Overview
This cleanup was performed to organize the project structure, archive old files, and improve maintainability.

## Files Archived

### Player Stats Module
**Test Scripts** (moved to `test_scripts/`):
- test_pybaseball_daily.py
- test_game_logs.py
- test_splits.py
- test_debug_range.py
- test_daily_mlb_api.py
- test_ratio_calculations.py

**Old Backfill Scripts** (moved to `backfill_scripts/`):
- backfill_2025_season.py
- backfill_yahoo_ids.py
- continue_backfill.py
- multiworker_backfill.py

**Experimental Scripts** (moved to `experimental_scripts/`):
- populate_player_mapping.py
- populate_player_mapping_simple.py
- direct_yahoo_id_update.py
- fix_yahoo_id_integration.py
- simple_yahoo_update.py
- batch_yahoo_update.py
- collector_updated.py
- pybaseball_daily_alternative.py
- quick_process.py
- player_analysis.py

### Daily Lineups Module
**Test/Experimental Scripts**:
- test_parallel_collection.py
- validate_parallel.py
- preflight_backfill.py
- backfill_multi_season.py
- daily_lineups_current.py
- collector_enhanced.py

### Database Files
**Backup Files** (moved to `database/backups/`):
- league_analytics_backup_20250803.db
- league_analytics_backup_20250803_172015.db
- league_analytics_backup_20250803_172021.db
- test_empty.db
- fantasy_league.db
- gkl_league_analytics.db
- league_analytics_test.db

### Root Level Test Files
- test_not_rostered.py
- test_other_roster.py
- debug_aug3.py

## Files Removed
- daily_lineups/checkpoint.json (temporary file)
- player_stats/mapping_candidates_summary.txt (redundant)
- player_stats/migrate_schema.py (old migration)
- player_stats/schema_update.sql (old schema)
- player_stats/update_stats.py (replaced)
- Empty directories: logs/, cache/, temp/, exports/
- nul files (Windows artifacts)

## Active Files Retained

### Core Modules
**Player Stats:**
- collector.py (main collection module)
- repository.py (data access layer)
- job_manager.py (job tracking)
- data_validator.py (validation)
- pybaseball_integration.py (MLB data)
- player_id_mapper.py (ID mapping)
- mlb_stats_api.py (API integration)
- backfill_stats.py (primary backfill script)
- populate_core_mappings.py (Yahoo ID mapping)
- populate_external_ids.py (external ID mapping)
- fix_star_player_mappings.py (manual fixes)

**Daily Lineups:**
- collector.py (main collection)
- repository.py (data access)
- parser.py (XML parsing)
- job_manager.py (job tracking)
- backfill_lineups.py (backfill script)
- update_lineups.py (incremental updates)

**Database:**
- league_analytics.db (primary database)
- All existing archive/ contents retained

## Directory Structure (Post-Cleanup)
```
gkl-league-analytics/
├── archive/                     # All archived files
│   ├── 2025-08-02_*/           # Previous archives
│   └── 2025-08-03_cleanup/     # Today's cleanup
├── auth/                        # Authentication module
├── common/                      # Shared utilities
├── config/                      # Configuration
├── daily_lineups/              # Daily lineups module (cleaned)
├── database/                   # Database files (cleaned)
├── docs/                       # Documentation
├── league_transactions/        # Transaction module
├── metadata/                   # League metadata
├── player_stats/              # Player stats module (cleaned)
├── scripts/                   # Utility scripts
└── web-ui/                    # Web interface

## Benefits
1. Cleaner project structure
2. Easier navigation
3. Clear separation of production vs experimental code
4. Preserved all potentially useful code in archive
5. Reduced clutter in main directories
6. Better organization for future development