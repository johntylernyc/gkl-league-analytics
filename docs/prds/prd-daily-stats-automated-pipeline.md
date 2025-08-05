# PRD: Daily Stats Automated Pipeline

## Executive Summary

This PRD outlines the implementation plan for extending the GKL League Analytics automated data pipeline to include player_stats collection. The goal is to follow the established patterns from daily_lineups and league_transactions modules, enabling automatic MLB statistics collection via GitHub Actions with direct Cloudflare D1 writes.

## Background

### Current State
- **Existing Automation**: daily_lineups and league_transactions modules successfully collect data via GitHub Actions 3x daily
- **Player Stats Module**: Fully implemented with backfill/update scripts but not integrated into automated workflows
- **Data Flow**: Yahoo API → Python scripts → Direct D1 writes (no local SQLite intermediary in production)
- **Infrastructure**: GitHub Actions scheduled workers with D1 HTTP API integration

### Problem Statement
Player statistics data is currently collected manually, creating gaps in analytics capabilities and requiring manual intervention for updates. This limits the system's ability to provide real-time player performance insights.

## Goals & Success Criteria

### Primary Goals
1. Automate daily MLB player statistics collection via GitHub Actions
2. Implement direct D1 database writes following existing patterns
3. Maintain data quality and foreign key integrity
4. Enable incremental updates with stat correction detection

### Success Criteria
- Player stats updated automatically 3x daily alongside lineups/transactions
- < 5 minute execution time for incremental updates
- 99%+ success rate for scheduled runs
- Zero manual intervention required for daily operations
- Comprehensive audit trail via job_log integration

## Technical Requirements

### Database Schema
The player_stats module uses four primary tables already defined in schema.sql:
- `mlb_batting_stats_staging` - Raw batting data from pybaseball
- `mlb_pitching_stats_staging` - Raw pitching data from pybaseball
- `player_id_mapping` - Yahoo ↔ MLB player ID relationships
- `daily_gkl_player_stats` - Final processed statistics

### Data Collection Pattern
Following the established pattern from daily_lineups and league_transactions:

1. **Backfill Script** (`backfill_stats.py`)
   - Bulk historical data collection
   - Parallel processing support
   - Resume capability for interrupted jobs
   - Used for initial data load and gap filling

2. **Update Script** (`update_stats.py` - to be created)
   - Incremental daily updates
   - Configurable lookback window (default 7 days for stat corrections)
   - D1 direct write support via `--use-d1` flag
   - Auto-detection of database type based on environment

3. **Data Quality Validation** (`data_validator.py`)
   - Field completeness checks
   - Statistical validation (e.g., batting average bounds)
   - Player ID mapping verification

## Implementation Plan

### Phase 1: Local Development & Testing (Week 1)

#### 1.1 Create Update Script
Create `data_pipeline/player_stats/update_stats.py` following the pattern from update_lineups.py:
- Implement D1Connection integration
- Support `--use-d1` and `--use-sqlite` flags
- Add configurable lookback window
- Include job logging and error handling

#### 1.2 Enhance D1Connection Module
Update `data_pipeline/common/d1_connection.py`:
- Add `insert_player_stats()` method for batch inserts
- Add `insert_player_mappings()` for ID mapping updates
- Handle staging table operations

#### 1.3 Test Local Collection
- Run update script against test database
- Verify data quality and completeness
- Test stat correction detection
- Validate foreign key relationships

### Phase 2: Production Database Setup (Week 1)

#### 2.1 Update sync_to_production.py
Add player_stats export functionality:
```python
def export_recent_player_stats(conn, export_dir, days_back=7):
    """Export recent player stats and related tables."""
    # Export daily_gkl_player_stats
    # Export player_id_mapping updates
    # Handle job_id dependencies
```

#### 2.2 D1 Schema Verification
- Verify all player_stats tables exist in D1
- Create tables if missing using schema.sql
- Test manual data import via wrangler

#### 2.3 Initial Data Load
- Run backfill for current season to local.prod
- Export and import to D1 using sync_to_production
- Verify data integrity in production

### Phase 3: GitHub Actions Integration (Week 2)

#### 3.1 Update Workflow Configuration
Modify `.github/workflows/data-refresh.yml`:
```yaml
refresh-player-stats:
  name: Refresh Player Stats
  needs: determine-refresh-params
  runs-on: ubuntu-latest
  
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests python-dotenv pybaseball pandas numpy
    
    - name: Run player stats update
      env:
        # Yahoo API credentials
        YAHOO_CLIENT_ID: ${{ secrets.YAHOO_CLIENT_ID }}
        YAHOO_CLIENT_SECRET: ${{ secrets.YAHOO_CLIENT_SECRET }}
        YAHOO_REFRESH_TOKEN: ${{ secrets.YAHOO_REFRESH_TOKEN }}
        # Cloudflare credentials
        CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        D1_DATABASE_ID: ${{ secrets.D1_DATABASE_ID }}
      run: |
        python data_pipeline/player_stats/update_stats.py \
          --days $DAYS \
          --environment ${{ needs.determine-refresh-params.outputs.environment }} \
          --use-d1
```

#### 3.2 Parallel Execution
- Run player_stats job in parallel with transactions and lineups
- Ensure no dependencies between jobs
- Monitor execution time and optimize if needed

#### 3.3 Error Handling & Monitoring
- Add comprehensive error logging
- Include in notification job for failures
- Monitor D1 API rate limits

### Phase 4: Production Rollout (Week 2)

#### 4.1 Staged Deployment
1. Test workflow manually via GitHub Actions UI
2. Enable for test environment only
3. Monitor for 24 hours
4. Enable for production environment
5. Monitor for 1 week

#### 4.2 Performance Optimization
- Analyze execution times
- Optimize batch sizes if needed
- Implement caching for player ID mappings
- Consider reducing API calls via smarter lookback logic

#### 4.3 Documentation Updates
- Update CLAUDE.md with new commands
- Update permanent-docs with architecture changes
- Add troubleshooting guide for common issues
- Document manual intervention procedures

## Risk Mitigation

### Technical Risks

1. **API Rate Limits**
   - Risk: PyBaseball API rate limiting
   - Mitigation: Implement exponential backoff, cache responses

2. **Data Volume**
   - Risk: Large number of players × daily stats
   - Mitigation: Batch processing, optimize queries

3. **Player ID Mapping Failures**
   - Risk: New players without mappings
   - Mitigation: Fuzzy matching, manual review process

4. **D1 API Limitations**
   - Risk: 1MB response size, 100 statement batch limits
   - Mitigation: Chunk operations, individual query fallback

### Operational Risks

1. **Stat Corrections**
   - Risk: MLB stat corrections up to 7 days later
   - Mitigation: 7-day lookback window, content hash tracking

2. **Schema Evolution**
   - Risk: New stat categories added by MLB
   - Mitigation: Flexible schema, validation warnings

3. **Dependency Management**
   - Risk: PyBaseball library updates
   - Mitigation: Pin versions, test before updates

## Testing Strategy

### Unit Testing
- Test D1Connection player_stats methods
- Validate data transformation logic
- Test error handling paths

### Integration Testing
1. **Local SQLite**: Full pipeline test with test data
2. **D1 Test Environment**: Verify direct writes work
3. **End-to-End**: Complete workflow from API to D1

### Data Quality Testing
- Compare stats with official MLB sources
- Verify player ID mappings
- Check for data gaps or anomalies
- Validate stat calculations

### Performance Testing
- Measure execution time for various date ranges
- Test parallel processing efficiency
- Monitor memory usage
- Check D1 API response times

## Success Metrics

### Operational Metrics
- **Uptime**: 99%+ successful scheduled runs
- **Execution Time**: < 5 minutes for daily updates
- **Data Freshness**: Stats available by 7 AM ET daily
- **Error Rate**: < 1% failed player mappings

### Data Quality Metrics
- **Completeness**: 100% of rostered players have stats
- **Accuracy**: < 0.1% data quality issues
- **Timeliness**: Stat corrections detected within 24 hours
- **Coverage**: All standard MLB stat categories included

## Timeline

### Week 1: Development & Testing
- Days 1-2: Create update script and D1 integration
- Days 3-4: Local testing and data quality validation
- Days 5-7: Production database setup and initial load

### Week 2: Production Integration
- Days 8-9: GitHub Actions workflow updates
- Days 10-11: Staging environment testing
- Days 12-14: Production rollout and monitoring

### Week 3: Optimization & Documentation
- Performance tuning based on production metrics
- Complete documentation updates
- Knowledge transfer and training

## Future Enhancements

1. **Real-time Updates**: Integrate with live game feeds
2. **Advanced Metrics**: Add Statcast and sabermetric data
3. **Predictive Analytics**: Use stats for performance predictions
4. **API Endpoints**: Expose player stats via Workers API
5. **Caching Layer**: Implement KV storage for frequently accessed stats

## Approval & Sign-off

This PRD requires approval from:
- [ ] Technical Lead - Architecture and implementation approach
- [ ] Product Owner - Feature requirements and timeline
- [ ] Operations - Infrastructure and monitoring plan

---

*Document Version: 1.0*  
*Created: August 2025*  
*Status: Draft - Awaiting Review*