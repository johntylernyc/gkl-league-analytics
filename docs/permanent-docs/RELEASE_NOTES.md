# Release Notes

## [2.1.0] - 2025-08-06

### 🎯 Major Feature: Comprehensive MLB Player Statistics Pipeline

#### Overview
Implemented a comprehensive player statistics system that tracks ALL MLB players (~750+ active daily), not just fantasy roster players. This enables advanced analytics and seamless integration with Yahoo Fantasy Sports.

#### Key Features

##### 🔄 Comprehensive Data Collection
- **All MLB Players**: Tracks every active MLB player daily, not limited to fantasy rosters
- **Multi-Platform ID Mapping**: Maintains player IDs across MLB, Yahoo, Baseball Reference, and FanGraphs
- **Real-time Stats**: Daily game-by-game statistics with automatic rate stat calculations

##### 🔗 Yahoo Fantasy Integration
- **79% Yahoo ID Coverage**: 1,583 of 2,004 active players mapped to Yahoo IDs
- **99.7% Coverage for Active Players**: Near-perfect matching for players with recent stats
- **Click-through Capability**: Enables direct navigation from player spotlights to Yahoo add/drop pages
- **Jr./Sr. Suffix Handling**: Fixed critical matching issues with player name suffixes

##### 📊 Enhanced Statistics
- **Batting Stats**: 28 counting stats + 6 calculated rate stats (AVG, OBP, SLG, OPS, ISO, BABIP)
- **Pitching Stats**: 20 counting stats + 6 calculated rate stats (ERA, WHIP, K/9, BB/9, HR/9, K/BB)
- **Historical Backfill**: Supports bulk collection with parallel processing
- **Incremental Updates**: Daily updates with configurable lookback periods

##### 🗄️ Multi-Database Support
- **SQLite**: Local development and testing
- **Cloudflare D1**: Production edge database with global availability
- **Database Abstraction**: Seamless switching between database targets

#### Technical Improvements

##### Architecture
- **Modular Design**: Three production-ready scripts (backfill, update, data quality)
- **Job Logging**: Comprehensive audit trail for all data operations
- **Error Recovery**: Resume capability for interrupted bulk operations
- **Parallel Processing**: Up to 4 concurrent workers for bulk backfill

##### Data Quality
- **Health Scoring**: 0-100 scoring system with letter grades (A-F)
- **Validation Checks**: Completeness, validity, ID mappings, freshness
- **CSV Export**: Data quality reports for analysis

##### Performance
- **Collection Speed**: ~30 seconds per game day
- **Bulk Processing**: ~90 seconds for 3-day updates
- **D1 Optimization**: Sub-second query performance at edge

#### API Changes
- No breaking changes to existing APIs
- Enhanced player data now includes multi-platform IDs
- Yahoo player IDs automatically populated in responses

#### Database Schema Changes

##### New Tables
- `player_mapping`: Comprehensive player ID mapping table
  - 2,779 total players tracked
  - Multi-platform ID support (MLB, Yahoo, Baseball Reference, FanGraphs)
  - Active player tracking and verification timestamps

##### Modified Tables
- `daily_gkl_player_stats`: Enhanced with multi-platform IDs
  - Added `baseball_reference_id` and `fangraphs_id` columns
  - Improved Yahoo ID population (99.7% coverage)

#### Scripts Added
- `comprehensive_collector.py`: Core stats collection engine
- `yahoo_id_matcher.py`: Fuzzy name matching with suffix handling
- `yahoo_player_search.py`: Yahoo Fantasy API integration
- `data_quality_check.py`: Health monitoring and validation

#### Scripts Removed
- `fix_star_player_mappings.py`: Replaced by comprehensive system
- `incremental_update.py`: Consolidated into update_stats.py
- `populate_core_mappings.py`: Replaced by comprehensive_collector
- `populate_external_ids.py`: Integrated into main pipeline

#### Configuration
- No configuration changes required
- Existing environment variables remain compatible
- Optional D1 configuration for edge deployment

#### Migration Notes
- Existing stats data automatically enhanced with Yahoo IDs
- No data loss during migration
- Backward compatible with existing queries

#### Known Issues
- Yahoo API tokens expire hourly (existing limitation)
- D1 API requires authentication token for direct writes

#### Deployment Status
- ✅ Local SQLite database updated
- ✅ Cloudflare D1 production deployed
- ✅ GitHub Actions automation ready
- ✅ Documentation complete

---

## [2.0.0] - 2025-08-05

### Post-Mortem: Transaction Display Incident

#### Summary
Production outage where transactions page showed empty results due to DESC ordering change that wasn't tested with production data patterns.

#### Key Learnings
- Always test with production-like data
- Never deploy uncommitted code
- Remove `.env.local` before production builds
- Verify build outputs change when expected

#### New Standards
- Mandatory pre-deployment checklist
- Prohibited use of `--commit-dirty=true`
- Feature branch workflow required

---

## Previous Releases

See git history for releases prior to 2.0.0

---

*Last Updated: 2025-08-06*