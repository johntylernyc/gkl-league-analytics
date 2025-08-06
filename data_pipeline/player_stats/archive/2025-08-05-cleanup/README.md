# Archived Player Stats Scripts - August 5-6, 2025

## Archived Files

### One-Time Population Scripts
- `fix_star_player_mappings.py` - Fixed star player mapping issues
- `populate_core_mappings.py` - Initial population of player ID mappings
- `populate_external_ids.py` - Population of external ID mappings

### Replaced Scripts
- `incremental_update.py` - Original incremental update script (replaced by `update_stats.py`)
- `update_stats_original.py` - Backup of update_stats.py before schema fixes

### Data Files
- `mapping_candidates.csv` - Temporary mapping candidates file

## Reason for Archival
- One-time scripts: Used during initial setup and data fixes, no longer needed for regular operations
- Replaced scripts: Superseded by modernized versions following established patterns
- Schema issues: Original scripts had dependencies on non-existent columns (content_hash, has_correction)