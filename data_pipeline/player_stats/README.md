# Player Stats Module

This module provides automated collection and management of daily MLB player statistics for fantasy baseball analysis.

## Overview

The Player Stats module integrates with the pybaseball library to collect comprehensive MLB player performance data from sources like Fangraphs, Baseball Reference, and Statcast. Statistics are aligned with fantasy baseball scoring categories and stored in a normalized database schema.

## Features

- **Automated Daily Collection**: Scheduled collection of MLB stats for all rostered players
- **Historical Backfill**: Ability to collect historical data for the entire season
- **Data Quality Assurance**: Comprehensive validation and quality checks
- **Player ID Mapping**: Yahoo Fantasy ↔ MLB player identification system
- **Performance Optimization**: Efficient batch processing and query optimization
- **Job Tracking**: Integration with existing job logging infrastructure

## Quick Start

### 1. Install Dependencies

```bash
pip install pybaseball pandas numpy
```

### 2. Set Up Database Schema

```bash
python player_stats/scripts/setup_schema.py
```

### 3. Initialize Player ID Mapping

```bash
python player_stats/player_id_mapper.py --initialize
```

### 4. Run Daily Collection

```bash
python player_stats/update_stats.py --date 2025-08-03
```

### 5. Backfill Historical Data

```bash
python player_stats/backfill_stats.py --start-date 2025-03-27 --end-date 2025-08-02
```

## Configuration

The module follows existing configuration patterns:

- **Environment**: Production/test separation via `DATA_ENV` variable
- **Database**: Uses centralized database configuration
- **Logging**: Integrates with existing job logging system
- **Scheduling**: 6 AM ET daily execution target

## Data Schema

### Primary Tables

- **`daily_mlb_stats`**: Daily player statistics (batting + pitching)
- **`player_id_mapping`**: Yahoo ↔ MLB player ID relationships
- **`player_stats_summary`**: Aggregated statistics for performance

### Key Statistics Collected

**Batting**: Games, At-Bats, Runs, Hits, Doubles, Triples, Home Runs, RBIs, Stolen Bases, Walks, Strikeouts, AVG, OBP, SLG

**Pitching**: Appearances, Innings, Wins, Losses, Saves, Holds, ERA, WHIP, Strikeouts, Quality Starts

## Performance Targets

- **Collection Time**: < 30 minutes for full league
- **Query Performance**: < 100ms for single player lookups  
- **Data Freshness**: Available by 7 AM ET daily
- **Success Rate**: 99%+ daily collection success
- **Quality**: < 0.1% data quality issues

## Integration Points

- **Job Logging**: Uses existing `job_log` table and patterns
- **Player Data**: Integrates with `daily_lineups` and `transactions` tables
- **Configuration**: Follows `config/database_config.py` patterns
- **Season Management**: Uses `common/season_manager.py` for date validation

## API Usage Examples

### Collect Stats for a Date

```python
from player_stats import PlayerStatsCollector

collector = PlayerStatsCollector(environment="production")
job_id = collector.collect_daily_stats("2025-08-03")
```

### Query Player Statistics

```python
from player_stats import PlayerStatsRepository

repo = PlayerStatsRepository(environment="production")
stats = repo.get_player_stats("12345", "2025-08-03")
```

### Validate Data Quality

```python
from player_stats import PlayerStatsValidator

validator = PlayerStatsValidator(environment="production")
issues = validator.validate_date("2025-08-03")
```

## File Structure

```
player_stats/
├── __init__.py              # Module initialization
├── README.md               # This file
├── config.py               # Configuration settings
├── collector.py            # Core data collection
├── job_manager.py          # Job tracking and management
├── repository.py           # Data access layer
├── player_id_mapper.py     # Player ID mapping system
├── data_validator.py       # Data quality validation
├── scheduler.py            # Daily automation
├── schema.sql              # Database schema
├── update_stats.py         # Daily update script
├── backfill_stats.py       # Historical backfill script
├── scripts/                # Utility scripts
│   ├── setup_schema.py     # Initial schema setup
│   ├── migrate_stats.py    # Schema migrations
│   └── validate_collection.py  # Collection verification
└── tests/                  # Unit tests
    ├── test_collector.py
    ├── test_player_mapper.py
    └── test_data_validator.py
```

## Monitoring and Maintenance

### Daily Monitoring

```bash
# Check collection status
python player_stats/scripts/validate_collection.py --date 2025-08-03

# View job logs
python -c "
from player_stats import PlayerStatsJobManager
manager = PlayerStatsJobManager()
recent_jobs = manager.get_recent_jobs(limit=5)
for job in recent_jobs:
    print(f'{job.job_id}: {job.status} - {job.records_inserted} records')
"
```

### Data Quality Checks

```bash
# Run comprehensive validation
python player_stats/data_validator.py --validate-date 2025-08-03 --check-all

# Check for data gaps
python player_stats/scripts/validate_collection.py --check-gaps --start-date 2025-03-27
```

## Troubleshooting

### Common Issues

1. **pybaseball API failures**: Check network connectivity and API rate limits
2. **Player ID mapping failures**: Review fuzzy matching parameters
3. **Data quality issues**: Check source data consistency
4. **Performance issues**: Review query indexes and batch sizes

### Debug Mode

```bash
# Enable debug logging
export DEBUG_PLAYER_STATS=1
python player_stats/update_stats.py --date 2025-08-03 --debug
```

## Future Enhancements

- Real-time game updates during live games
- Advanced Statcast metrics integration
- Predictive modeling data preparation
- Enhanced aggregation tables for analytics
- API endpoints for external consumption

For detailed implementation information, see the individual module documentation.