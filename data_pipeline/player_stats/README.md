# Player Statistics Pipeline

## Overview

The Player Statistics Pipeline provides comprehensive MLB player statistics collection with Yahoo Fantasy ID mapping. This module collects daily batting and pitching statistics for ALL active MLB players (~750+), not just those on fantasy rosters, enabling advanced analytics and player tracking.

## Key Features

- **Comprehensive Coverage**: Tracks all MLB players, not limited to fantasy rosters
- **Yahoo ID Mapping**: Maps Yahoo Fantasy IDs to MLB/PyBaseball identifiers (79% coverage)
- **Automated Collection**: Runs 3x daily via GitHub Actions (6 AM, 1 PM, 10 PM ET)
- **Multi-Environment Support**: Works with both SQLite (test) and Cloudflare D1 (production)
- **Data Quality Validation**: Built-in health scoring and validation reporting
- **Resume Capability**: Can resume interrupted bulk operations

## Quick Start

### Prerequisites

```bash
pip install pybaseball pandas requests python-dotenv
```

### Basic Usage

#### Incremental Update (Daily)
```bash
# Default: Last 7 days to local SQLite
python update_stats.py

# Production: Direct to D1
python update_stats.py --use-d1 --environment production

# Custom date range
python update_stats.py --days 14
```

#### Historical Backfill
```bash
# Full season
python backfill_stats.py --season 2025

# Date range with parallel processing
python backfill_stats.py --start 2025-07-01 --end 2025-07-31 --workers 4
```

#### Data Quality Check
```bash
# Generate validation report
python data_quality_check.py --days 7
```

## Architecture

```
player_stats/
├── Core Scripts
│   ├── backfill_stats.py         # Bulk historical data collection
│   ├── update_stats.py           # Incremental daily updates
│   └── data_quality_check.py     # Validation and reporting
│
├── Collection Engine
│   ├── comprehensive_collector.py # All-MLB player collection
│   ├── pybaseball_integration.py # MLB Stats API interface
│   └── mlb_stats_api.py          # Direct MLB API access
│
├── ID Mapping
│   ├── yahoo_id_matcher.py       # Enhanced name matching
│   ├── yahoo_player_search.py    # Yahoo API integration
│   └── player_id_mapper.py       # Core mapping logic
│
└── Infrastructure
    ├── job_manager.py            # Job tracking
    ├── config.py                 # Environment config
    └── repository.py             # Database operations
```

## Database Schema

### Primary Tables

- **`daily_gkl_player_stats`**: Comprehensive batting and pitching statistics
  - Primary key: (date, yahoo_player_id)
  - 50+ statistical columns including rate stats
  - Health scoring and grading system

- **`player_mapping`**: Yahoo to MLB player ID mappings
  - Primary key: yahoo_player_id
  - Confidence scoring (0.0-1.0)
  - Mapping method tracking

### Key Statistics Collected

**Batting**: Games, At-Bats, Runs, Hits, Doubles, Triples, Home Runs, RBIs, Stolen Bases, Walks, Strikeouts, HBP, Sac Flies, GIDP, Total Bases, AVG, OBP, SLG, OPS

**Pitching**: Games, Starts, Complete Games, Shutouts, Wins, Losses, Saves, Blown Saves, Holds, Innings, Hits Allowed, Runs, Earned Runs, Home Runs, Walks, Strikeouts, Wild Pitches, Balks, Quality Starts, ERA, WHIP

## Performance Metrics

| Metric | Value |
|--------|-------|
| Players Tracked | ~750 active MLB |
| Yahoo IDs Mapped | 1,583 (79%) |
| Daily Records | 750-1,000 |
| Collection Time | 2-3 min/day |
| Backfill Speed | ~100 days/hour |
| Database Growth | 15-20 MB/month |
| Data Health Score | 96% (Grade A) |

## Yahoo ID Mapping

The system maintains mappings between Yahoo Fantasy and MLB identifiers:

- **Coverage**: 1,583 of ~2,000 Yahoo players mapped
- **Methods**: Exact match, fuzzy match, manual override
- **Confidence**: Scored 0.0-1.0 based on match quality
- **Special Cases**: Handles Jr./Sr./III suffixes correctly

### Mapping Process
1. Standardize player names
2. Query Yahoo API for player search
3. Apply fuzzy matching algorithm
4. Score confidence based on match quality
5. Store mapping with metadata

## Data Quality

### Health Scoring System

Each player's daily stats receive a health score and letter grade:

- **Grade A (90-100)**: Excellent data quality
- **Grade B (80-89)**: Good data quality
- **Grade C (70-79)**: Acceptable quality
- **Grade D (60-69)**: Poor quality
- **Grade F (0-59)**: Insufficient data

### Validation Checks
- Field completeness
- Statistical consistency
- Date range validity
- Player ID mapping coverage
- Duplicate detection

## GitHub Actions Integration

The pipeline runs automatically via GitHub Actions:

```yaml
# .github/workflows/data-refresh.yml
refresh-stats:
  schedule:
    - cron: '0 10 * * *'  # 6 AM ET
    - cron: '0 17 * * *'  # 1 PM ET
    - cron: '0 2 * * *'   # 10 PM ET
```

## Troubleshooting

### Common Issues

#### "No Yahoo ID found"
- Player may not be in Yahoo's database
- Try manual search on Yahoo Fantasy
- Check for name variations

#### "MLB API timeout"
- Rate limiting (1 request/second)
- Reduce worker count for backfill
- Check internet connection

#### "Foreign key constraint failed"
- Missing job_log entry
- Run with proper job tracking
- Check job_id exists

#### "Column mismatch error"
- Production uses `mlb_player_id`
- Test uses `mlb_id`
- Script handles automatically

### Debug Mode

```bash
# Enable verbose logging
python update_stats.py --verbose

# Test single date
python update_stats.py --date 2025-08-01 --verbose
```

## API Rate Limits

- **MLB Stats API**: 1 request/second
- **Yahoo Fantasy API**: 20,000 requests/day
- **PyBaseball**: Inherits MLB limits

## Data Retention

- **Local SQLite**: No automatic cleanup
- **Production D1**: Approaching 500MB limit
- **Recommendation**: Archive season data annually

## Support

For issues or questions:
1. Check this README
2. Review GitHub Actions logs
3. File issue on GitHub