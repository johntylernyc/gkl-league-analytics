# Plan: Integrate Multi-Season League Keys and Dates for Historical Data Collection

## Overview
Integrate the `metadata/league_keys.py` file containing league keys and season dates for 2008-2025 into the data backfill system, enabling collection of historical data across multiple seasons while maintaining selective control and existing requirements.

## Current State Analysis
1. **Duplicate Configuration**: Both `daily_lineups/config.py` and `league_transactions/backfill_transactions_optimized.py` have their own LEAGUE_KEYS and SEASON_DATES dictionaries
2. **Limited Coverage**: Current configs only include 2025 data (with some files having partial historical data)
3. **Metadata File**: New `metadata/league_keys.py` has complete data for 2008-2025
4. **Database Design**: Tables already have `season` column for multi-season support

## Implementation Plan

### Phase 1: Centralize Configuration (Single Source of Truth)
1. **Update auth/config.py**:
   - Import league keys and season dates from `metadata/league_keys.py`
   - Remove duplicate definitions
   - Add helper functions for season management

2. **Update daily_lineups/config.py**:
   - Remove local LEAGUE_KEYS and SEASON_DATES
   - Import from centralized metadata module
   - Keep module-specific configuration

3. **Update league_transactions scripts**:
   - Modify `backfill_transactions_optimized.py` to use centralized config
   - Update `update_transactions.py` similarly

### Phase 2: Enhance Backfill Scripts with Multi-Season Support

1. **Create shared season manager** (`common/season_manager.py`):
   ```python
   - get_available_seasons() -> List of configured seasons
   - validate_season(year) -> Check if season data exists
   - get_season_info(year) -> League key and dates
   - calculate_season_days(year) -> Total days in season
   - get_seasons_in_range(start_year, end_year) -> List of seasons
   ```

2. **Update daily_lineups/backfill_lineups.py**:
   - Add `--seasons` parameter for multiple seasons (e.g., "2023-2025")
   - Add `--all-seasons` flag to process all available seasons
   - Implement season-aware parallel processing
   - Update validation reports to handle multiple seasons

3. **Update daily_lineups/parallel_collection.py**:
   - Add multi-season support to parallel collection
   - Implement cross-season load balancing
   - Add season-specific job tracking

4. **Update transaction collection scripts**:
   - Similar enhancements for transaction backfill
   - Ensure consistency with lineup collection approach

### Phase 3: Add Selective Control Features

1. **Implement flexible date selection**:
   - Support individual seasons: `--season 2023`
   - Support season ranges: `--seasons 2020-2023`
   - Support custom date ranges: `--start 2022-06-01 --end 2023-08-15`
   - Support exclusions: `--exclude-seasons 2020,2021`

2. **Add collection profiles**:
   ```python
   COLLECTION_PROFILES = {
       "recent": "Last 3 seasons",
       "historical": "All seasons before current",
       "full": "All available seasons",
       "custom": "User-defined selection"
   }
   ```

3. **Implement smart collection modes**:
   - `missing-only`: Only collect uncollected dates
   - `update`: Refresh existing data
   - `validate`: Check data completeness
   - `repair`: Fix incomplete dates

### Phase 4: Database and Performance Optimizations

1. **Database enhancements**:
   - Add season-based partitioning indexes
   - Create season summary tables
   - Add cross-season views for analysis

2. **Performance optimizations**:
   - Implement season-aware caching
   - Add bulk insert optimizations for historical data
   - Create season-specific checkpoints

3. **Resource management**:
   - Adaptive worker allocation based on date range
   - Memory-efficient batch processing for large historical collections
   - Progressive collection with interim commits

### Phase 5: Monitoring and Validation

1. **Create multi-season monitoring**:
   - Season coverage dashboard
   - Cross-season data quality reports
   - Historical collection progress tracking

2. **Add validation tools**:
   - Season completeness checker
   - Data consistency validator across seasons
   - Missing data identifier with season context

## File Changes Required

### New Files
- `common/season_manager.py` - Centralized season management
- `scripts/collect_historical.py` - Multi-season collection orchestrator
- `scripts/validate_seasons.py` - Season data validation

### Modified Files
- `auth/config.py` - Import from metadata
- `daily_lineups/config.py` - Use centralized config
- `daily_lineups/backfill_lineups.py` - Add multi-season support
- `daily_lineups/parallel_collection.py` - Season-aware parallelization
- `league_transactions/backfill_transactions_optimized.py` - Use centralized config
- All collector and update scripts - Add season parameter support

## Benefits
1. **Single source of truth** for league keys and season dates
2. **Flexible collection** - collect any combination of seasons/dates
3. **Backwards compatible** - existing single-season scripts continue working
4. **Scalable** - efficiently handle 18 years of historical data
5. **Maintainable** - easy to add future seasons

## Testing Strategy
1. Test with single season (current behavior)
2. Test with small historical range (2-3 seasons)
3. Test with custom date ranges across seasons
4. Validate data completeness for each season
5. Performance test with full historical collection

## Rollout Plan
1. **Phase 1-2**: Core integration (immediate)
2. **Phase 3**: Selective control (next iteration)
3. **Phase 4-5**: Optimization and monitoring (future enhancement)

## Example Usage After Implementation

### Single Season Collection
```bash
# Collect 2023 season
python daily_lineups/backfill_lineups.py backfill --season 2023

# Collect current season (2025)
python daily_lineups/backfill_lineups.py backfill
```

### Multiple Season Collection
```bash
# Collect seasons 2020-2023
python daily_lineups/backfill_lineups.py backfill --seasons 2020-2023

# Collect all available seasons
python daily_lineups/backfill_lineups.py backfill --all-seasons

# Collect recent 3 seasons
python daily_lineups/backfill_lineups.py backfill --profile recent
```

### Custom Date Ranges
```bash
# Collect specific date range across seasons
python daily_lineups/backfill_lineups.py backfill --start 2022-06-01 --end 2023-08-15

# Collect missing dates only for 2021-2023
python daily_lineups/backfill_lineups.py backfill --seasons 2021-2023 --mode missing
```

### Parallel Collection with Multiple Seasons
```bash
# Run 4 parallel processes for seasons 2020-2023
python daily_lineups/parallel_collection.py collect --seasons 2020-2023 --processes 4

# Distribute historical collection across workers
python daily_lineups/parallel_collection.py collect --all-seasons --processes 8 --mode smart
```

### Validation and Monitoring
```bash
# Validate all seasons
python scripts/validate_seasons.py --all

# Check specific season completeness
python scripts/validate_seasons.py --season 2023

# Monitor multi-season collection progress
python daily_lineups/monitor_collection.py --seasons 2020-2025
```

## Implementation Priority

### High Priority (Immediate)
1. Centralize configuration using metadata/league_keys.py
2. Update existing scripts to use centralized config
3. Add basic multi-season support to backfill scripts

### Medium Priority (Next Sprint)
1. Implement selective control features
2. Add collection profiles
3. Create season validation tools

### Low Priority (Future)
1. Performance optimizations for large historical collections
2. Advanced monitoring dashboards
3. Cross-season analytics features

## Notes
- The 2025 season dates in metadata/league_keys.py show "2025-06-01" to "2025-06-07" which appears incorrect. The daily_lineups/config.py has "2025-03-27" to "2025-09-28" which matches MLB season dates. This discrepancy needs to be resolved.
- Consider adding a configuration validation step to ensure league keys and dates are valid before collection begins
- Token management may need enhancement for long-running historical collections
- Database indexes should be reviewed and optimized for multi-season queries