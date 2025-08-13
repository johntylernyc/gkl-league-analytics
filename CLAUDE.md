# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GKL League Analytics is a production fantasy baseball analytics platform that collects, processes, and visualizes data from Yahoo Fantasy Sports leagues. The system runs on Cloudflare's global edge network, providing real-time insights through a React frontend and Workers API backend.

**Current Implementation Status**: 
- ✅ Production deployment on Cloudflare (goldenknightlounge.com)
- ✅ Transaction data collection with comprehensive job logging
- ✅ Daily lineup tracking and analysis  
- ✅ React-based web UI with player spotlight features
- ✅ GitHub Actions scheduled data refresh with direct D1 writes
- ✅ Dual database support (SQLite for development, D1 for production)
- ✅ Automated foreign key dependency management
- ⏳ Player stats collection via PyBaseball (in progress - comprehensive MLB coverage)
- ⏳ Advanced predictive analytics (planned)

## Windows Development Environment

**IMPORTANT**: This project is developed on Windows using PowerShell. Claude must:

### Command Line Considerations:
- **Always use PowerShell syntax** for commands (not bash/Unix)
  - Use `Remove-Item -Recurse -Force` instead of `rm -rf`
  - Use `Copy-Item` instead of `cp`
  - Use `Move-Item` instead of `mv`
  - Use `Get-Content` instead of `cat`
  - Use backslashes `\` for Windows paths or forward slashes `/` (both work)
- **Handle Windows-specific issues**:
  - No native `sqlite3` command - use Python scripts instead
  - Different environment variable syntax: `$env:VAR_NAME` or `set VAR_NAME=value`
  - Case-insensitive file system
- **Unicode/Encoding Issues**:
  - Avoid Unicode symbols in print statements (✅ ❌ 📊 etc.)
  - Use ASCII alternatives: `[OK]`, `[ERROR]`, `[INFO]`, `[SUCCESS]`
  - Python scripts may encounter `cp1252` encoding errors with Unicode
  - Use `encoding='utf-8'` when opening files in Python

### Python Development:
- Default Python installation path: `C:\Users\johnt\AppData\Local\Programs\Python\Python313\`
- Always handle encoding explicitly in file operations
- Use raw strings or forward slashes for paths to avoid escape issues

### Node.js/NPM Commands:
- Use `npx` to run local packages
- Clear npm cache issues with: `npm cache clean --force`
- Remove node_modules with: `Remove-Item -Recurse -Force node_modules`

## Critical Development Rules

### 1. Development Process Requirements

**MANDATORY: Before ANY development work**, Claude must:

1. **Review Requirements** - Understand what needs to be built
2. **Analyze Current State** - Examine existing code and architecture
3. **Understand Scope** - Define boundaries of changes
4. **Consider Impacts** - Identify upstream/downstream dependencies
5. **Draft Implementation Plan** - Create detailed methodology
6. **Validate with User** - Get approval before proceeding

**Documentation Requirements**:
- Create implementation plan in `/docs/development-docs/` BEFORE coding
- Include clear list of artifacts to be created/modified
- Update documentation after user confirms feature works
- Track all files, scripts, and components created

### 2. Post-Release Documentation Updates

**After each GitHub commit**, Claude must:
- Review and update `/docs/permanent-docs/` to reflect current state
- Update this CLAUDE.md file with any architectural changes
- Ensure README.md accurately describes the production system
- Archive outdated development documentation

### 3. Data Integrity Rules

**For ALL data processing work** (pipelines, ETL, database changes, APIs):
- **NEVER use mock/simulated data** unless explicitly approved by user
- Always use real Yahoo API data for testing
- Validate data quality before database insertion
- Maintain audit trails via job logging
- Test data transformations with production-like data

### 4. API Change Management

**Before modifying ANY endpoint or API**:
1. Conduct full change assessment
2. Document all consumers of the endpoint
3. Identify breaking vs non-breaking changes
4. Create migration plan if needed
5. Review assessment with user before proceeding
6. Update all affected components

### 5. Environment Management

**Test/Production Separation**:
1. **Test Environment** - Mirror production configuration
2. **Development Flow** - Test locally → Validate → Deploy to production
3. **Backup Procedures** - Document rollback steps for:
   - GitHub (git revert commands)
   - Database (D1 backup/restore)
   - Cloudflare (worker rollback)
   - Configuration (wrangler.toml versions)

### 6. Release Documentation

**Public Release Notes (Website)**:

The platform maintains user-facing release notes at `/release-notes` on the production website.

**Updating Website Release Notes**:
1. Edit `web-ui/frontend/src/data/releaseNotes.js`
2. Add new release at TOP of array (newest first)
3. Follow semantic versioning (MAJOR.MINOR.PATCH)
4. Include 3-4 user-friendly bullet points in highlights
5. Test locally at http://localhost:3000/release-notes

**Versioning System**:
- **MAJOR** (X.0.0): Breaking changes, major architecture shifts
- **MINOR** (1.X.0): New features, significant improvements
- **PATCH** (1.0.X): Bug fixes, minor improvements
- Starting version: 1.0.0 (August 1, 2024)

**Release Notes Required For**:
- ✅ New features visible to users
- ✅ User interface changes or improvements  
- ✅ API changes that affect user experience
- ✅ Performance improvements users would notice
- ✅ Major bug fixes that restore broken functionality

**Release Notes NOT Required For**:
- ❌ Documentation updates
- ❌ Internal code refactoring with no user impact
- ❌ Developer tooling changes
- ❌ Configuration changes
- ❌ Minor text corrections

**Internal Documentation**:
For detailed technical documentation, also create files in `docs/release-notes/` following the format `YYYY-MM-DD-feature-name.md`

### 7. Pre-Commit Security Review

**Before EVERY GitHub commit**, Claude must:

1. **Scan for Sensitive Information**:
   - Check for API keys, tokens, passwords
   - Review for client IDs and secrets
   - Verify no database credentials exposed
   - Look for hardcoded URLs with auth parameters
   - Check for personal information (emails, IPs)

2. **Update .gitignore**:
   - Add test scripts (test_*.py, debug_*.py)
   - Exclude single-use debugging files
   - Remove temporary data files
   - Exclude local configuration files
   - Add any generated credential files

3. **Security Checklist**:
   ```bash
   # Before committing, verify:
   git diff --staged | grep -E "(password|secret|token|key|api_key|client_id)"
   git status --ignored  # Review what's being excluded
   ```

### 7. Deployment Checklist (MANDATORY)

**Before ANY production deployment**, Claude must complete ALL items:

1. **Pre-Deployment Verification**:
   - [ ] All changes committed to Git (no uncommitted files)
   - [ ] Feature branch created and used (never deploy from main directly)
   - [ ] Tests run and passing locally
   - [ ] Data quality validation completed
   - [ ] Release notes created in `/docs/release-notes/`

2. **GitHub Actions Integration**:
   - [ ] Verify workflow changes are NOT commented out
   - [ ] Check job dependencies are correct
   - [ ] Ensure environment variables are configured
   - [ ] Test workflow syntax is valid
   - [ ] Confirm schedule/triggers are appropriate

3. **Documentation Requirements**:
   - [ ] Create release notes in `/docs/release-notes/YYYY-MM-DD-feature.md`
   - [ ] Update module README.md files
   - [ ] Update `/docs/permanent-docs/` with architectural changes
   - [ ] Document database schema changes
   - [ ] Update CLAUDE.md if new patterns emerge

4. **Pull Request Process**:
   - [ ] Create PR from feature branch to main
   - [ ] Include comprehensive PR description
   - [ ] Link to related issues/PRDs
   - [ ] Request review if available
   - [ ] Merge only after checks pass

5. **Post-Deployment Verification**:
   - [ ] Monitor first automated run
   - [ ] Check logs for errors
   - [ ] Verify data in production
   - [ ] Document any issues found
   - [ ] Create follow-up tasks if needed

### 8. Post-Release Cleanup

**After EACH release/commit**, Claude must:

1. **Remove Ephemeral Files**:
   - Delete test databases (*.test.db, test_*.db)
   - Remove debugging scripts (debug_*.py, test_*.py)
   - Clean up temporary data files (*.tmp, *.temp)
   - Delete single-use migration scripts
   - Remove development logs (*.log in dev directories)

2. **Archive Development Artifacts**:
   - Move useful test scripts to `/archive/` with date prefix
   - Document why files were kept or removed
   - Update .gitignore for new patterns discovered

3. **Cleanup Commands**:
   ```bash
   # Standard cleanup after release
   find . -name "test_*.py" -type f -delete
   find . -name "debug_*.py" -type f -delete
   find . -name "*.test.db" -type f -delete
   find . -name "*.tmp" -type f -delete
   
   # Archive useful scripts
   mkdir -p archive/$(date +%Y-%m-%d)
   mv useful_test_script.py archive/$(date +%Y-%m-%d)/
   ```

4. **Documentation**:
   - List removed files in development-docs
   - Note any files moved to archive
   - Update CLAUDE.md if new patterns emerge

## Common Development Commands

### Local Development Setup
```bash
# Start backend API (port 3001)
cd web-ui/backend
npm install && npm start

# Start frontend (port 3000) - in new terminal
cd web-ui/frontend
npm install && npm start

# Frontend will use local API if .env.local exists
```

### Authentication & Setup
```bash
# Initialize OAuth tokens (expire hourly)
python auth/generate_auth_url.py      # Get authorization URL
python auth/initialize_tokens.py      # Exchange code for tokens
python auth/test_auth.py              # Verify authentication
```

### Data Collection
```bash
cd data_pipeline

# Transaction collection - Bulk backfill
python league_transactions/backfill_transactions.py --season 2025
python league_transactions/backfill_transactions.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Transaction collection - Incremental updates
python league_transactions/update_transactions.py        # Default 7-day lookback (SQLite)
python league_transactions/update_transactions.py --use-d1     # Force Cloudflare D1
python league_transactions/update_transactions.py --since-last
python league_transactions/update_transactions.py --date 2025-08-04

# Lineup collection - Bulk backfill
python daily_lineups/backfill_lineups.py --season 2025
python daily_lineups/backfill_lineups.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Lineup collection - Incremental updates  
python daily_lineups/update_lineups.py        # Default 7-day lookback (SQLite)
python daily_lineups/update_lineups.py --use-d1     # Force Cloudflare D1
python daily_lineups/update_lineups.py --since-last
python daily_lineups/update_lineups.py --date 2025-08-04

# Draft results (once per season after draft)
python draft_results/collector.py --league_key "458.l.6966" --season 2025

# Player statistics - Bulk backfill
python player_stats/backfill_stats.py --season 2025
python player_stats/backfill_stats.py --start 2025-03-01 --end 2025-09-30 --workers 4

# Player statistics - Incremental updates
python player_stats/update_stats.py        # Default 7-day lookback (SQLite)
python player_stats/update_stats.py --use-d1     # Force Cloudflare D1
python player_stats/update_stats.py --since-last
python player_stats/update_stats.py --date 2025-08-04

# Player statistics - Data quality check
python player_stats/data_quality_check.py --days 7
python player_stats/data_quality_check.py --season 2025
```

### Database Operations

#### Testing D1 Connection
```bash
# Test Cloudflare D1 connection and credentials
python scripts/test_d1_connection.py

# Required environment variables:
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_API_TOKEN="your-api-token"  
export D1_DATABASE_ID="your-database-id"
```

#### Manual Sync (Development)
```bash
# Sync local to production (handles foreign keys automatically)
python scripts/sync_to_production.py

# The sync script will:
# 1. Export recent transactions and lineups
# 2. Extract all referenced job_ids
# 3. Export corresponding job_log entries
# 4. Generate import commands in correct order

# Import to production D1 - MUST FOLLOW THIS ORDER:
cd cloudflare-production
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/job_logs_*.sql --remote    # FIRST
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/transactions_*.sql --remote # SECOND
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/lineups_*.sql --remote      # THIRD

# For draft results (once per season):
# Create table if first time:
npx wrangler d1 execute gkl-fantasy --file=../data_pipeline/draft_results/schema.sql --remote
# Import draft data:
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/draft_*.sql --remote
```

#### Automated Production Updates (GitHub Actions)
```bash
# GitHub Actions runs automatically 3x daily:
# - 6:00 AM ET: 7-day lookback for corrections
# - 1:00 PM ET: 3-day lookback for recent changes
# - 10:00 PM ET: 3-day lookback for end-of-day sync

# Manual workflow trigger:
gh workflow run data-refresh.yml --input refresh_type=manual --input environment=production

# Monitor workflow status:
gh run list --workflow=data-refresh.yml --limit=5
```

**Foreign Key Constraints:**
- All data tables reference job_log.job_id
- GitHub Actions handle dependencies automatically with D1 direct writes
- Manual imports: job_logs FIRST to avoid FOREIGN KEY errors
- Use INSERT OR IGNORE for job_logs to handle duplicates
- Use REPLACE for data tables to handle updates

### Deployment

#### Production Deployment Standards (CRITICAL - Added after Aug 5, 2025 outage)

**MANDATORY Pre-Deployment Checklist:**
1. **Git Status Check**: Run `git status` - must show "nothing to commit, working tree clean"
2. **All Changes Committed**: NEVER deploy uncommitted code to production
3. **Remove .env.local**: Temporarily rename to prevent development settings in production builds
4. **Verify Build Output**: Check that JS bundle hash changes when expected
5. **Test on Staging**: Deploy to a test URL first when possible

**PROHIBITED Actions:**
- ❌ NEVER use `--commit-dirty=true` for production deployments
- ❌ NEVER build production locally with `.env.local` present
- ❌ NEVER deploy without a corresponding git commit
- ❌ NEVER skip the pre-deployment checklist

#### Correct Production Deployment Process

```bash
# 1. Ensure all changes are committed
git add .
git commit -m "Clear description of changes"
git push origin main

# 2. Deploy API to Cloudflare Workers
cd cloudflare-production
npm run deploy

# 3. Deploy frontend to Cloudflare Pages
cd web-ui/frontend

# CRITICAL: Handle .env.local for production builds
mv .env.local .env.local.backup  # Temporarily remove
npm run build                     # Build will use .env.production
npx wrangler pages deploy build --project-name gkl-fantasy-frontend
mv .env.local.backup .env.local  # Restore for development

# 4. Verify deployment
# - Check browser console for errors
# - Verify API endpoints are accessible
# - Test core functionality
```

#### Environment File Hierarchy (React)
1. `.env.local` - HIGHEST PRIORITY (development only)
2. `.env.production` - Production settings
3. `.env` - Shared settings
4. Hardcoded fallbacks in code

**Warning**: `.env.local` will override `.env.production` even in production builds!

### Feature Branch Workflow (Required for all new features)

**Never develop features directly on main branch**. Use this workflow:

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/descriptive-name

# 2. Develop and test locally
# Make changes, test thoroughly
git add .
git commit -m "feat: clear description of changes"

# 3. Deploy to test environment (optional)
# Can deploy to a test Pages URL for validation

# 4. Merge to main when ready
git checkout main
git pull origin main
git merge feature/descriptive-name
git push origin main

# 5. Deploy to production from main
# Follow production deployment process above

# 6. Delete feature branch
git branch -d feature/descriptive-name
git push origin --delete feature/descriptive-name
```

## Recent Improvements (August 2025)

### Data Pipeline Consolidation
Both `league_transactions` and `daily_lineups` modules have been consolidated:
- **From**: 10+ scripts per module with overlapping functionality
- **To**: 2 main scripts per module (backfill + update) plus data quality validation
- **Benefits**: Cleaner code, consistent patterns, better maintainability
- **Pattern**: Each module now has:
  - `backfill_*.py` - Bulk historical data with parallel processing
  - `update_*.py` - Incremental updates for automation
  - `data_quality_check.py` - Comprehensive validation

### Draft Results Pipeline (New)
Added `draft_results` module for annual draft data collection:
- **One-time collection**: Runs once per season after draft completes
- **Features**: Automatic draft type detection, player enrichment, keeper support
- **D1 Integration**: Uses sync_to_production pattern for manual push
- **Manual Process**: Keeper designation requires post-collection SQL updates

### Player Stats Pipeline (August 2025)
Comprehensive MLB player statistics collection now in production:
- **Scope**: All ~750+ active MLB players daily (not limited to fantasy rosters)
- **Data Source**: MLB Stats API via PyBaseball (real-time game data)
- **Yahoo Integration**: 1,583 players mapped (79% coverage) with fuzzy matching
- **Features**: Daily batting/pitching stats, health scoring (A-F grades), rate calculations
- **Architecture**: Follows established pattern (backfill + update + data quality)
- **Automation**: GitHub Actions 3x daily (6 AM, 1 PM, 10 PM ET)
- **Special Handling**: Jr./Sr./III suffix matching, production column name differences

### Key Fixes
- League key for 2025: `458.l.6966` (not 449 or mlb prefixes)
- Complete data extraction for all add/drop transaction movements
- Full roster data for all 18 teams in daily lineups
- Proper date handling using transaction timestamps
- Draft type detection via `is_auction_draft` field

## Project Architecture

### Directory Structure
```
gkl-league-analytics/
├── auth/                          # OAuth2 authentication
├── data_pipeline/                 # Python data collection
│   ├── league_transactions/       # Transaction processing
│   ├── daily_lineups/            # Lineup collection
│   ├── draft_results/            # Draft data collection
│   ├── player_stats/             # MLB stats integration (PyBaseball-based)
│   └── common/                   # Shared utilities
├── cloudflare-production/        # Production deployment
│   ├── src/                      # Workers API code
│   ├── d1-schema.sql            # Database schema
│   └── wrangler.toml            # Cloudflare config
├── cloudflare-scheduled-worker/  # Automated refresh triggers
├── web-ui/                       # Frontend application
│   └── frontend/                 # React application
├── database/                     # SQLite local database
├── scripts/                      # Utility scripts
└── docs/                         # Documentation
    ├── permanent-docs/           # Architecture documentation
    └── development-docs/         # Development artifacts
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React 18, Tailwind CSS | User interface |
| **API** | Cloudflare Workers | Edge API endpoints |
| **Database** | Cloudflare D1 (SQLite) | Production data storage |
| **Cache** | Cloudflare KV | API response caching |
| **Data Pipeline** | Python 3.11+ | Yahoo API integration |
| **Authentication** | OAuth2 | Yahoo API access |

### Data Flow Architecture

```
Yahoo API → Python Pipeline → SQLite (local) → Export Scripts → D1 (production)
                                ↓
                        Job Logging & Audit Trail
```

**Production API Flow**:
```
User Request → Cloudflare Edge → Workers API → D1/KV → Response
```

## Critical Implementation Standards

### Job Logging Requirements

**MANDATORY for ALL data processing scripts**:

```python
from job_manager import start_job_log, update_job_log

# Start job with comprehensive logging
job_id = start_job_log(
    job_type="transaction_collection",
    environment="test",  # or "production"
    date_range_start="2025-07-01",
    date_range_end="2025-07-31",
    league_key="458.l.6966",  # 2025 league key
    metadata="additional context"
)

# Include job_id in all data operations
process_data(job_id=job_id)

# Update on completion
update_job_log(job_id, 'completed', records_processed=N, records_inserted=M)
```

### API Performance Standards

- **Response Time**: < 200ms p95
- **Cache TTL**: 5 minutes for dynamic data
- **Rate Limiting**: 1 req/sec to Yahoo API
- **Concurrent Workers**: Maximum 2 for data collection
- **Database Connections**: Connection pooling required

### Security Requirements

1. **Never commit credentials** - Use environment variables
2. **OAuth tokens** - Auto-refresh before expiration
3. **SQL injection** - Use prepared statements only
4. **CORS** - Configure for production domain only
5. **Secrets management** - Use Cloudflare secrets for production

### Database Standards

1. **Schema changes** - Require migration scripts
2. **Indexes** - Performance test before adding
3. **Transactions** - Use for multi-table updates
4. **Backup** - Before any destructive operations
5. **SQL Compatibility** - Test all SQL in D1 before deployment
   - Avoid SQLite-specific functions like `strftime('%s', date)`
   - Use ANSI-standard SQL when possible
   - Test with: `npx wrangler d1 execute gkl-fantasy --command "SQL" --remote`

### Automation Patterns

1. **Incremental Updates** - Use `update_transactions.py` for scheduled tasks
   ```bash
   # Crontab example for daily updates at 6 AM
   0 6 * * * cd /path/to/data_pipeline/league_transactions && python update_transactions.py --quiet
   ```

2. **Bulk Backfill** - Use `backfill_transactions.py` for historical data
   - Supports parallel processing (up to 4 workers)
   - Resume capability for interrupted jobs
   - Multi-season support

3. **Scheduled Workers** - Cloudflare scheduled triggers for production
   - Morning: Previous day's lineups
   - Afternoon: Morning transactions  
   - Evening: Full synchronization
5. **Job tracking** - Include job_id in all records

## Environment Configuration

### Local Development Environment
- **Frontend**: React app on http://localhost:3000
- **Backend API**: Express server on http://localhost:3001
- **Database**: Local SQLite (database/league_analytics.db)
- **Configuration**: `.env.local` for frontend, `.env` for backend

### Production Environment
- **Frontend**: Cloudflare Pages (goldenknightlounge.com)
- **API**: Cloudflare Workers (gkl-fantasy-api.services-403.workers.dev)
- **Database**: Cloudflare D1
- **Cache**: Cloudflare KV

### Environment Separation
```
Local:    Frontend → Backend API (3001) → SQLite
Production: Frontend → Workers API → D1
```

### Environment Variables
```bash
# Yahoo API (required)
YAHOO_CLIENT_ID=xxx
YAHOO_CLIENT_SECRET=xxx
YAHOO_AUTHORIZATION_CODE=xxx

# Cloudflare (deployment)
CLOUDFLARE_ACCOUNT_ID=xxx
CLOUDFLARE_API_TOKEN=xxx

# Database
DATABASE_URL=./database/league_analytics.db
D1_DATABASE_ID=xxx
```

## Documentation Standards

### Documentation Hierarchy

1. **`/docs/permanent-docs/`** - Architecture and system documentation
   - Updated after releases
   - Authoritative reference
   - System design and capabilities

2. **`/docs/development-docs/`** - Development artifacts
   - Implementation plans
   - Session-specific documentation
   - Work-in-progress notes

3. **Module READMEs** - Component-specific documentation
   - Quick reference
   - API documentation
   - Usage examples

### Documentation Requirements

- **Before Development**: Create implementation plan
- **During Development**: Update progress in dev-docs
- **After Development**: Update permanent-docs
- **On Release**: Archive old dev-docs

## Testing Requirements

### Data Collection Testing
1. Test with small date ranges first
2. Verify job logging works correctly
3. Check data quality before bulk operations
4. Validate against Yahoo API responses

### API Testing
```bash
# Local testing
curl http://localhost:8787/api/health

# Production testing
curl https://gkl-fantasy-api.services-403.workers.dev/api/health
```

### Database Testing
1. Backup before schema changes
2. Test migrations on local D1 first
3. Verify indexes improve performance
4. Check foreign key constraints

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Environment variables set
- [ ] Database migrations ready
- [ ] Backup created

### Deployment Steps
1. Deploy API to Workers
2. Run database migrations
3. Deploy frontend to Pages
4. Verify health endpoints
5. Test critical paths

### Post-Deployment
- [ ] Monitor error logs
- [ ] Check performance metrics
- [ ] Verify data collection
- [ ] Update documentation
- [ ] Communicate changes

## Common Issues & Solutions

### Local Development Issues

#### Frontend Shows Old/Production Data
**Problem**: Frontend at localhost:3000 shows outdated data or production data
**Solution**: 
1. Ensure `.env.local` exists in `web-ui/frontend/` with `REACT_APP_API_URL=http://localhost:3001/api`
2. Restart frontend after creating/modifying `.env.local`
3. Clear browser cache and refresh

#### Backend Not Starting
**Problem**: Port 3001 already in use
**Solution**: Backend is likely already running. Check with:
```bash
curl http://localhost:3001/health
```

#### CORS Errors
**Problem**: Frontend can't connect to backend
**Solution**: Verify backend `.env` has `CORS_ORIGIN=http://localhost:3000`

### OAuth Token Expiration
```bash
# Tokens expire hourly, refresh with:
python auth/initialize_tokens.py
```

### Database Issues

#### Foreign Key Constraint Failed
**Problem**: Error "FOREIGN KEY constraint failed" when importing to D1
**Solution**: 
1. Import job_logs FIRST before any data tables
2. Use the sync_to_production.py script which handles dependencies
3. Follow the exact import order shown by the script
4. Check that all job_ids in data exports exist in job_log

#### Local Database Not Found
**Problem**: Backend can't find SQLite database
**Solution**: Check `DB_PATH` in backend `.env` points to correct location

#### Database Size Limits
- D1 has 500MB limit
- Use data retention policies
- Archive old seasons

#### D1 API Connection Issues
**Problem**: "Route not found" or 404 errors from D1 API
**Solution**: 
1. Verify environment variables: `CLOUDFLARE_ACCOUNT_ID`, `D1_DATABASE_ID`, `CLOUDFLARE_API_TOKEN`
2. Check API token has D1 permissions
3. Current implementation uses individual queries (not batch) as workaround
4. Enable debug logging with `logger.setLevel(logging.DEBUG)` to see exact URLs

**Problem**: "List object has no attribute 'get'" errors
**Solution**: Fixed in current implementation - D1 API response format handled correctly

### API Rate Limiting
- Yahoo: 1 request/second
- Implement exponential backoff
- Use job queue for large operations

### Deployment Failures
1. Check wrangler.toml configuration
2. Verify Cloudflare credentials
3. Review build logs
4. Test locally first

## Support Resources

- **GitHub Issues**: Bug reports and feature requests
- **Cloudflare Docs**: https://developers.cloudflare.com
- **Yahoo API Docs**: https://developer.yahoo.com/fantasysports
- **Project Docs**: `/docs/permanent-docs/`

---

*Last Updated: August 2025*  
*Version: 2.0.0 - Production on Cloudflare Edge*