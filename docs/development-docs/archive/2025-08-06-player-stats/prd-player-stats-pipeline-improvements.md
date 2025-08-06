# PRD: Player Stats Pipeline Improvements

**Status**: Implemented  
**Implementation Date**: August 5, 2025

## Executive Summary

This PRD outlines the plan to modernize the player_stats module to align with the recently improved patterns established in the daily_lineups and league_transactions modules. The goal is to create a consistent, maintainable data pipeline architecture across all data collection modules while preserving the core working logic.

## Background

### Current State

The player_stats module currently has:
- Multiple scripts with overlapping functionality
- One-time population scripts mixed with regular collection scripts
- Missing data quality validation module
- Inconsistent naming patterns compared to other modules
- No clear separation between bulk backfill and incremental update operations

### Recent Improvements to Other Modules

In the past 24 hours, daily_lineups and league_transactions were refactored to follow a clean 3-script pattern:
1. **backfill_*.py** - Bulk historical data collection with parallel processing
2. **update_*.py** - Incremental updates for automation
3. **data_quality_check.py** - Data validation and quality reporting

These improvements included:
- Clear separation of concerns
- Consistent naming patterns
- Comprehensive job logging
- D1 database support
- Archive directories for deprecated scripts
- Updated documentation

## Goals & Success Criteria

### Primary Goals
1. Align player_stats module with the established 3-script pattern
2. Archive deprecated and one-time scripts
3. Create missing data quality validation module
4. Update documentation to match other modules
5. Maintain all existing functionality while improving organization

### Success Criteria
- Module structure matches daily_lineups and league_transactions
- All core functionality preserved and tested
- Clear separation between bulk and incremental operations
- Comprehensive data quality validation
- Clean directory with archived legacy scripts

## Detailed Requirements

### 1. Script Consolidation & Renaming

#### Core Scripts (Keep/Refactor)
- **backfill_stats.py** - Already follows pattern, minor updates needed:
  - Ensure D1 support via `--use-d1` flag
  - Verify job logging integration
  - Update to use common patterns from other modules
  
- **incremental_update.py** → **update_stats.py**:
  - Rename to match naming convention
  - Add D1 support following update_lineups.py pattern
  - Add command-line options: `--days`, `--since-last`, `--date`, `--quiet`
  - Ensure minimal output for automation
  - Update imports and references

- **Create data_quality_check.py**:
  - New module following patterns from other pipelines
  - Validate player ID mappings
  - Check stat boundaries (e.g., batting average 0-1)
  - Verify data completeness
  - Generate human-readable reports

#### Supporting Modules (Keep)
- collector.py - Core collection logic
- repository.py - Database access layer
- job_manager.py - Job tracking
- config.py - Configuration
- player_id_mapper.py - Player ID mapping logic
- mlb_stats_api.py - MLB API integration
- pybaseball_integration.py - PyBaseball wrapper
- data_validator.py - Existing validation (integrate with data_quality_check.py)

#### Scripts to Archive
Move to `archive/2025-08-05-cleanup/`:
- fix_star_player_mappings.py - One-time fix
- populate_core_mappings.py - One-time population
- populate_external_ids.py - One-time population
- Any test scripts in root directory

#### Files to Remove/Archive
- mapping_candidates.csv - Move to archive
- Temporary files in cache/, temp/, logs/ - Clean up

### 2. Environment Separation

Ensure clear separation between test and production environments:
- Support `--environment` flag (test/production)
- Use table name functions for environment-specific tables
- Follow database configuration patterns from other modules

### 3. D1 Integration

Update scripts to support direct D1 writes:
```python
# Pattern from update_lineups.py
from data_pipeline.common.d1_connection import D1Connection, is_d1_available

def __init__(self, environment='production', use_d1=None):
    if use_d1 is None:
        self.use_d1 = D1_AVAILABLE and is_d1_available()
    else:
        self.use_d1 = use_d1
```

Add to D1Connection module:
- `insert_player_stats()` method
- `insert_player_mappings()` method
- `update_staging_tables()` method

### 4. Documentation Updates

#### Update README.md
Follow the structure from daily_lineups/README.md:
- Clear script descriptions
- Usage examples for each script
- Data flow explanation
- Important notes about rate limiting, data volume
- Automation examples
- Troubleshooting section

#### Key Sections to Include:
1. Scripts overview (3 main scripts)
2. Data flow diagram
3. Supporting modules description
4. Database schema reference
5. Important implementation notes
6. Automation guidance
7. Troubleshooting guide

### 5. Directory Structure

Final structure should be:
```
player_stats/
├── README.md                    # Updated documentation
├── __init__.py
├── backfill_stats.py           # Bulk collection (updated)
├── update_stats.py             # Incremental updates (renamed)
├── data_quality_check.py       # New validation module
├── collector.py                # Core logic
├── repository.py              # Database layer
├── job_manager.py             # Job tracking
├── config.py                  # Configuration
├── player_id_mapper.py        # ID mapping
├── mlb_stats_api.py          # MLB API
├── pybaseball_integration.py  # PyBaseball wrapper
├── data_validator.py         # Validation utilities
├── schema.sql                # Database schema
├── archive/                  # Deprecated scripts
│   └── 2025-08-05-cleanup/
│       ├── fix_star_player_mappings.py
│       ├── populate_core_mappings.py
│       ├── populate_external_ids.py
│       └── mapping_candidates.csv
├── scripts/                  # Utility scripts
│   └── setup_schema.py
├── tests/                    # Unit tests
└── progress/                 # Progress tracking
```

## Implementation Plan

### Phase 1: File Organization (Day 1)
1. Create archive directory structure
2. Move deprecated scripts to archive
3. Clean up temporary files and directories
4. Rename incremental_update.py to update_stats.py
5. Update all import references

### Phase 2: Script Updates (Day 1-2)
1. Update backfill_stats.py:
   - Add D1 support
   - Ensure consistent CLI interface
   - Verify job logging
   
2. Update update_stats.py:
   - Implement standard CLI options
   - Add D1 support
   - Minimize output for automation
   - Follow update_lineups.py patterns

3. Create data_quality_check.py:
   - Implement validation classes
   - Add batch validation support
   - Create report generation

### Phase 3: D1 Integration (Day 2)
1. Update D1Connection module with player_stats methods
2. Test D1 writes with small dataset
3. Verify foreign key handling
4. Update sync_to_production.py

### Phase 4: Documentation (Day 3)
1. Rewrite README.md following established patterns
2. Update module docstrings
3. Add inline documentation for complex logic
4. Update CLAUDE.md references

### Phase 5: Testing & Validation (Day 3)
1. Test all three scripts end-to-end
2. Verify archived scripts aren't referenced
3. Validate data quality checks work
4. Test automation scenarios

## Migration Considerations

### Backwards Compatibility
- Preserve all database schemas
- Maintain existing job_id patterns
- Keep API interfaces unchanged
- Support existing automation scripts during transition

### Data Integrity
- No data migration required
- Existing data remains untouched
- New scripts work with existing tables
- Job logging continues seamlessly

## Risk Mitigation

### Technical Risks
1. **Breaking existing automation**
   - Mitigation: Keep old script names as symlinks temporarily
   - Document migration path for users

2. **D1 integration issues**
   - Mitigation: Implement gradual rollout
   - Test thoroughly in test environment first

3. **Data quality regression**
   - Mitigation: Run parallel validation
   - Compare results with existing scripts

### Operational Risks
1. **Documentation gaps**
   - Mitigation: Review with team
   - Update based on feedback

2. **Missing functionality**
   - Mitigation: Careful code review
   - Test all code paths

## Success Metrics

- All tests passing
- Module structure matches other pipelines
- Documentation complete and accurate
- No functionality regression
- Clean, organized directory structure
- Successful D1 integration

## Timeline

- **Day 1**: File organization and script updates
- **Day 2**: D1 integration and testing
- **Day 3**: Documentation and final validation

## Approval

This PRD requires approval before implementation to ensure:
- No critical scripts are archived incorrectly
- D1 integration approach is sound
- Documentation meets team standards

---

*Document Version: 1.0*  
*Created: August 2025*  
*Status: Draft - Awaiting Review*