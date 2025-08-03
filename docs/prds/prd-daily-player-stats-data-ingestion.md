# PRD: Daily Player Stats Data Ingestion

*Synced from Notion on 2025-08-03 12:22:50*

*Page ID: 2441a736-211e-81b0-ac01-d9de7a715510*

---

**Author:** Senior Product Manager

**Date:** August 3, 2025

**Status:** Draft

**Version:** 1.0

---

## Executive Summary

The Daily Player Stats Data Ingestion feature will systematically collect and store MLB player performance statistics for every player in our database across each day of the 2025 MLB season. By leveraging pybaseball's comprehensive data access to Fangraphs, Baseball Reference, and Statcast, this feature will create a foundational data layer that powers advanced analytics, player comparisons, and performance tracking aligned with our league's specific scoring categories.

## Problem Statement

### Current State

- No systematic collection of daily MLB player statistics

- Missing historical performance data needed for trend analysis

- Unable to correlate fantasy performance with actual MLB statistics

- Lack of data foundation for advanced features (optimal lineups, projections)

- Manual lookups required for player performance context

### Desired State

- Automated daily ingestion of all relevant MLB statistics

- Complete historical record for the 2025 season

- Statistics aligned with league scoring categories

- Foundation for performance analytics and predictions

- Seamless integration with existing fantasy roster data

## User Personas

### Primary: System Administrator

- **Goals:** Reliable, automated data collection with minimal maintenance

- **Pain Points:** Manual data updates, incomplete statistics, system failures

- **Needs:** Monitoring tools, error handling, data validation

### Secondary: Data Analyst/Power User

- **Goals:** Access to comprehensive player statistics for analysis

- **Pain Points:** Data gaps, inconsistent formats, missing context

- **Needs:** Complete data coverage, standardized schema, query performance

### Tertiary: Fantasy Manager (Indirect)

- **Goals:** Make informed decisions based on player performance

- **Pain Points:** Lack of statistical context for roster decisions

- **Needs:** Accurate, timely data that surfaces in application features

## Feature Overview

### Core Capabilities

1. **Automated Data Collection**

1. **Comprehensive Stat Coverage**

1. **Data Quality Assurance**

1. **Performance Optimization**

## Technical Requirements

### Data Sources and Methods

1. **Primary Data Collection via pybaseball**

1. **Data Schema Design**

1. **Aggregation Tables for Performance**

### Data Collection Process

1. **Daily Schedule (6 AM ET)**

1. **Collection Logic**

1. **Error Handling and Retry Logic**

### Performance Requirements

- **Data Freshness:** Stats available by 7 AM ET daily

- **Collection Time:** < 30 minutes for full league

- **Query Performance:** < 100ms for single player lookups

- **Storage Efficiency:** ~50KB per player per season

- **Uptime:** 99.5% availability for scheduled jobs

## Implementation Phases

### Phase 1: Core Infrastructure (2 weeks)

- Database schema creation and indexing

- Basic pybaseball integration

- Player ID mapping system

- Manual collection scripts

### Phase 2: Automation (2 weeks)

- Scheduled job framework

- Error handling and retry logic

- Monitoring and alerting

- Data validation rules

### Phase 3: Historical Backfill (1 week)

- 2025 season start to current date

- Data quality verification

- Performance optimization

- Missing data identification

### Phase 4: Advanced Features (2 weeks)

- Real-time game updates (optional)

- Aggregation tables

- API endpoints for data access

- Integration with existing features

## Data Quality & Validation

### Validation Rules

1. **Range Checks**

1. **Consistency Checks**

1. **Completeness Checks**

### Monitoring Dashboard

- Daily collection status

- Data completeness metrics

- API usage and limits

- Error logs and alerts

- Performance metrics

## Risks & Mitigations

[Unsupported block type: table]

## Success Metrics

- **Primary:** 99%+ daily collection success rate

- **Secondary:** < 0.1% data quality issues

- **Coverage:** 100% of rostered players tracked

- **Timeliness:** 95% of stats available by 7 AM ET

- **Performance:** 99th percentile query time < 200ms

## Dependencies

- pybaseball library (latest version)

- SQLite database with proper configuration

- Job scheduling system (cron/airflow)

- Player ID mapping system

- Monitoring infrastructure

## Future Considerations

1. **Real-time Updates**

1. **Advanced Metrics**

1. **Predictive Features**

1. **External Integrations**

## Appendix

### A. Sample API Calls

```python
# Get batting stats for a date range
from pybaseball import batting_stats_range
data = batting_stats_range('2025-04-01', '2025-04-01')

# Get specific player's game logs
from pybaseball import playerid_lookup, statcast_batter
player = playerid_lookup('trout', 'mike')
stats = statcast_batter('2025-04-01', '2025-04-01', player_id=player['key_mlbam'].values[0])
```

### B. Fantasy Point Calculations

```python
def calculate_batting_points(stats):
    return {
        'R': stats['runs'],
        'H': stats['hits'],
        '3B': stats['triples'],
        'HR': stats['home_runs'],
        'RBI': stats['rbi'],
        'SB': stats['stolen_bases'],
        'AVG': stats['batting_avg'],
        'OBP': stats['on_base_pct'],
        'SLG': stats['slugging_pct']
    }

def calculate_pitching_points(stats):
    return {
        'APP': stats['appearances'],
        'W': stats['wins'],
        'SV': stats['saves'],
        'K': stats['strikeouts_pitched'],
        'HLD': stats['holds'],
        'ERA': stats['era'],
        'WHIP': stats['whip'],
        'K/BB': stats['k_per_bb'],
        'QS': stats['quality_starts']
    }
```

### C. Monitoring Queries

```sql
-- Daily collection status
SELECT 
    date,
    COUNT(DISTINCT player_id) as players_collected,
    COUNT(CASE WHEN batting_avg IS NOT NULL THEN 1 END) as batters,
    COUNT(CASE WHEN era IS NOT NULL THEN 1 END) as pitchers,
    MIN(created_at) as collection_start,
    MAX(created_at) as collection_end
FROM player_daily_stats
WHERE date = CURRENT_DATE - 1
GROUP BY date;

-- Data quality check
SELECT 
    player_id,
    date,
    'Invalid AVG' as issue
FROM player_daily_stats
WHERE batting_avg > 1.0 OR batting_avg < 0
UNION ALL
SELECT 
    player_id,
    date,
    'Hits exceed at-bats' as issue
FROM player_daily_stats  
WHERE hits > at_bats;
```
