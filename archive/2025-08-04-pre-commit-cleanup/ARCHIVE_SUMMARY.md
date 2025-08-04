# Pre-Commit Cleanup Archive - August 4, 2025

## Archived Files Summary

### Debug Scripts (`debug-scripts/`)
- `debug_performance_breakdown.js` - Debug script for performance breakdown API testing
- `debug_player_12194.js` - Player-specific debugging script

### Test Data (`test-data/`)
- `riley_greene_data.json` - Riley Greene player data for testing
- `riley_greene_fixed.json` - Fixed version of Riley Greene data
- `riley_greene_teams_fixed.json` - Team history fix data
- `riley_greene_current.json` - Current Riley Greene data
- `logan_ohoppe.json` - Logan O'Hoppe player test data
- `clayton_kershaw.json` - Clayton Kershaw player test data

### Deployment Scripts (`deployment-scripts/`)
- `deploy.bat` - Deployment batch script
- `import-chunks-simple.bat` - SQL import script
- `import-chunks.bat` - Advanced SQL import script
- `import-full-data.bat` - Full data import script
- `split-large-sql.bat` - SQL file splitting script
- `test-home-page.html` - HTML test file
- `dev.log` - Development log file
- Various web-ui test files (`test-*.js`)

## Reason for Archival
These files were moved to archive as part of pre-commit cleanup to:
1. Remove debug/test code from main repository
2. Clean up temporary deployment scripts
3. Secure repository by removing test data files
4. Prepare for production-ready commit

## Recovery
If any of these files are needed in the future, they can be restored from this archive directory.

Archive Date: August 4, 2025
Archive Reason: Pre-commit security and cleanup preparation