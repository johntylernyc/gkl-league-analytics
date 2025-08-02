# Daily Lineups Module

## Overview

The Daily Lineups module provides comprehensive historical roster analysis capabilities for Yahoo Fantasy Baseball leagues. This module enables tracking, analyzing, and visualizing daily lineup decisions across all teams in your league.

## Features

### Core Capabilities
- **Historical Lineup Tracking**: Complete record of daily starting lineups and bench decisions
- **Player Usage Analytics**: Start/sit patterns, position utilization, bench frequency
- **Team Strategy Insights**: Lineup consistency metrics, streaming patterns
- **Optimal Lineup Analysis**: Compare actual vs optimal lineups based on performance
- **Search & Discovery**: Find specific lineup patterns and player usage trends

### Key Metrics
- Start percentage by player
- Bench value analysis
- Position depth utilization
- Lineup consistency scores
- Streaming pattern detection

## Project Structure

```
daily_lineups/
├── README.md                  # This file
├── implementation_plan.md     # Detailed development roadmap
├── __init__.py               # Module initialization
├── collector.py              # Yahoo API data collection
├── parser.py                 # XML response parsing
├── repository.py             # Data access layer
├── job_manager.py            # Job logging integration
├── backfill_lineups.py       # Historical data collection
├── update_lineups.py         # Incremental updates
├── scripts/
│   ├── schema.sql            # Database schema for lineup tables
│   ├── validate_data.py      # Data validation
│   └── export_lineups.py     # Export utilities
├── tests/
│   ├── test_collector.py     # Unit tests
│   ├── test_parser.py
│   └── test_repository.py
```

## Installation

### Prerequisites
- Python 3.8+
- SQLite 3
- Yahoo Fantasy API credentials
- Existing `gkl-league-analytics` setup

### Setup Steps

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Initialize Database**
```bash
# Run from project root
sqlite3 database/league_analytics.db < daily_lineups/scripts/schema.sql
```

3. **Configure Authentication**
Ensure Yahoo API tokens are configured in `auth/tokens.json`

## Usage

### Collecting Current Season Data

```python
from daily_lineups import DailyLineupsCollector
from auth import TokenManager

# Initialize collector
token_manager = TokenManager()
collector = DailyLineupsCollector(token_manager)

# Collect lineups for a date range
collector.collect_date_range(
    start_date="2025-06-01",
    end_date="2025-08-02",
    environment="production"
)
```

### Backfilling Historical Data

```bash
# Run historical backfill for 2025 season
python daily_lineups/backfill_lineups.py --season 2025 --env production

# Resume from checkpoint if interrupted
python daily_lineups/backfill_lineups.py --resume
```

### Incremental Updates

```bash
# Update lineups for the last 7 days
python daily_lineups/update_lineups.py --days 7

# Update specific date range
python daily_lineups/update_lineups.py --start 2025-07-01 --end 2025-07-31
```

### Querying Lineup Data

```python
from daily_lineups import LineupRepository

repo = LineupRepository()

# Get lineup for specific date/team
lineup = repo.get_lineup("mlb.l.6966.t.1", "2025-07-15")

# Get player usage stats
usage = repo.get_player_usage("player_123", "2025-06-01", "2025-08-01")

# Find bench decisions that cost points
costly_benches = repo.get_costly_bench_decisions("mlb.l.6966.t.1", "2025-07")
```

## API Endpoints

### REST API Routes

```
GET /api/lineups/:date/:teamId        # Get lineup for specific date/team
GET /api/lineups/player/:playerId     # Player usage history
GET /api/lineups/team/:teamId/summary # Team lineup patterns
GET /api/lineups/analytics/bench      # Bench value analysis
GET /api/lineups/search               # Search lineups
POST /api/lineups/export              # Export lineup data
```

### Example API Response

```json
{
  "date": "2025-07-15",
  "team": {
    "key": "mlb.l.6966.t.1",
    "name": "Bash Brothers"
  },
  "lineup": {
    "starting": [
      {
        "position": "C",
        "player": {
          "id": "12345",
          "name": "Will Smith",
          "status": "healthy",
          "eligiblePositions": ["C", "1B"]
        }
      }
    ],
    "bench": [
      {
        "player": {
          "id": "67890",
          "name": "Mike Trout",
          "status": "DTD"
        }
      }
    ]
  },
  "metadata": {
    "rosterSize": 26,
    "activeCount": 14,
    "benchCount": 10,
    "injuredCount": 2
  }
}
```

## Database Schema

### Main Tables

- **daily_lineups**: Core lineup data
- **daily_lineups_test**: Test environment data
- **lineup_positions**: Position definitions
- **player_usage_summary**: Aggregated usage stats
- **team_lineup_patterns**: Lineup pattern tracking

### Key Indexes

- Date-based queries: `idx_lineups_date`
- Team queries: `idx_lineups_team`
- Player queries: `idx_lineups_player`
- Composite: `idx_lineups_date_team`

## Configuration

### Environment Variables

```bash
# Set environment for data collection
export LINEUP_ENV=production  # or 'test'

# Configure collection mode
export LINEUP_MODE=incremental  # or 'backfill', 'full'

# Set date range for collection
export LINEUP_START_DATE=2025-06-01
export LINEUP_END_DATE=2025-08-02
```

### Settings

Configuration in `daily_lineups/config.py`:

```python
# Rate limiting
API_DELAY_SECONDS = 2
MAX_CONCURRENT_WORKERS = 2

# Batch processing
BATCH_SIZE = 100
CHECKPOINT_FREQUENCY = 10  # Save progress every N batches

# Data retention
KEEP_HISTORICAL_YEARS = 5
```

## Development

### Running Tests

```bash
# Run all tests
pytest daily_lineups/tests/

# Run specific test file
pytest daily_lineups/tests/test_collector.py

# Run with coverage
pytest --cov=daily_lineups daily_lineups/tests/
```

### Code Style

```bash
# Format code
black daily_lineups/

# Check linting
flake8 daily_lineups/

# Type checking
mypy daily_lineups/
```

## Monitoring

### Job Logging

All data collection operations are tracked in the `job_log` table:

```sql
SELECT 
    job_id,
    job_type,
    environment,
    status,
    records_processed,
    error_message
FROM job_log
WHERE job_type LIKE 'lineup_%'
ORDER BY start_time DESC;
```

### Health Checks

```python
# Check data freshness
from daily_lineups import health_check

status = health_check()
print(f"Last update: {status['last_update']}")
print(f"Data lag: {status['lag_hours']} hours")
print(f"Coverage: {status['coverage_percentage']}%")
```

## Troubleshooting

### Common Issues

1. **Token Expiration**
   - Solution: Tokens auto-refresh hourly, check `auth/tokens.json`

2. **Rate Limiting**
   - Solution: Adjust `API_DELAY_SECONDS` in config

3. **Duplicate Data**
   - Solution: UNIQUE constraints prevent duplicates automatically

4. **Missing Historical Data**
   - Solution: Use backfill script with appropriate date range

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with verbose output
collector = DailyLineupsCollector(debug=True)
```

## Performance Considerations

- **Query Optimization**: All common queries use indexes
- **Batch Processing**: Data inserted in batches of 100
- **Caching**: Player usage summaries cached in aggregate tables
- **Pagination**: Large result sets paginated automatically

## Contributing

1. Follow the implementation plan stages
2. Write tests for new functionality
3. Update documentation
4. Run linting and formatting
5. Submit PR with clear description

## License

Part of the gkl-league-analytics project. See main project LICENSE.

## Support

For issues or questions:
1. Check troubleshooting section
2. Review implementation_plan.md
3. Check existing GitHub issues
4. Create new issue with details

## Roadmap

See `implementation_plan.md` for detailed development timeline and milestones.

### Upcoming Features
- [ ] MLB data integration via pybaseball
- [ ] Advanced pattern recognition
- [ ] Machine learning predictions
- [ ] Mobile app support
- [ ] Real-time lineup notifications