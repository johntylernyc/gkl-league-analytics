# Post-Mortem: Production Outage - Uncommitted Code Deployment

**Date**: August 5, 2025  
**Duration**: ~4 hours (detected at time of investigation)  
**Severity**: High - Complete frontend failure  
**Author**: Development Team  

## Executive Summary

A production outage occurred when uncommitted local changes were deployed to Cloudflare Pages. The deployment included an import statement for a file that existed locally but was never committed to git, causing the entire React application to fail to initialize.

## Timeline

- **16 hours ago** (Aug 4, ~11:00 PM): Last git commit (`4890c24`) - "Add new SQL files for draft job logs and draft results to .gitignore"
- **Aug 5, Morning**: Development work on draft values feature:
  - Modified `cloudflare-production/src/index-with-db.js` (API)
  - Modified `web-ui/frontend/src/components/player-spotlight/PlayerHeader.js`
  - Modified `web-ui/frontend/src/components/TransactionTable.js`
  - Modified `web-ui/frontend/src/pages/Home.js`
  - Created `web-ui/frontend/src/utils/dateFormatters.js` (never added to git)
- **Aug 5, ~11:54 AM**: Deployed API to Cloudflare Workers
- **Aug 5, ~11:57 AM**: Deployed frontend to Cloudflare Pages with `--commit-dirty=true` flag
- **Aug 5, ~4:00 PM**: Production outage reported - no pages loading data

## Root Cause Analysis

### Primary Cause
The production build was created from uncommitted local changes that included:
```javascript
// In Home.js
import { formatTransactionDateTime } from '../utils/dateFormatters';
```

However, the `utils/dateFormatters.js` file was never added to git (`git status` showed `?? web-ui/frontend/src/utils/`), so it didn't exist in the production build.

### Contributing Factors

1. **Bypassed Safety Checks**: The `--commit-dirty=true` flag was used during deployment, which allowed uncommitted changes to be deployed
2. **No Pre-deployment Validation**: No `git status` check was performed before deployment
3. **Build Process**: The build process doesn't validate imports until runtime
4. **JavaScript Error Handling**: React apps fail completely when a module import fails, rather than degrading gracefully

## Impact

- **User Impact**: 100% of users unable to access any data on the site
- **Features Affected**: All pages (Home, Players, Transactions, etc.)
- **Duration**: ~4 hours from deployment to detection
- **Data Loss**: None - backend API remained functional

## Detection

- Manual user report of site not loading data
- No automated monitoring alerted to the issue

## Recovery Actions

### Option 1: Rollback to Last Commit (SELECTED)
```bash
git checkout 4890c24 -- web-ui/frontend/src/
cd web-ui/frontend
npm run build
npx wrangler pages deploy build --project-name gkl-fantasy-frontend --commit-dirty=true
```

### Option 2: Fix Forward
- Add utils directory to git and redeploy

### Option 3: Selective Fix
- Only revert Home.js to remove import

## Lessons Learned

### Primary Issues
1. **Never deploy uncommitted changes** to production
   - Uncommitted files (like `utils/dateFormatters.js`) won't exist in production
   - The `--commit-dirty=true` flag bypasses safety checks and should never be used for production
   - Always commit and push changes before deployment

2. **Environment file precedence** causes production build failures
   - `.env.local` takes precedence over `.env.production` in React builds
   - Production builds created locally will use development settings if `.env.local` exists
   - This caused production to try connecting to localhost:3001 instead of the production API

3. **Git-detached deployments** are dangerous
   - Building and deploying without a corresponding git commit makes rollbacks difficult
   - No audit trail of what code is actually running in production
   - Cannot reproduce builds or track changes

### Secondary Issues
4. **Incomplete rollbacks** can leave mixed states
   - Rolling back only frontend while API has new changes can cause compatibility issues
   - Always consider full-stack implications of changes

5. **Build verification** is critical
   - Different file hashes indicate actual build changes
   - Same hash means the build didn't actually change despite new deployment

6. **Local development practices** impact production
   - Having `.env.local` in the repo for development convenience created a production hazard
   - Need clear separation between development and production build processes

## Action Items

- [x] Create post-mortem documentation
- [x] Update CLAUDE.md with deployment standards and git commit requirements
- [x] Update README.md with proper deployment process
- [x] Create docs/permanent-docs/deployment-standards.md
- [x] Add pre-deployment checklist template
- [x] Document proper environment file handling
- [x] Create feature branch workflow documentation
- [x] Remove `--commit-dirty=true` from all deployment examples
- [x] Add build verification steps to deployment process
- [x] Add release notes requirements to deployment process
- [ ] Consider automated deployment pipeline to prevent manual errors

## Recovery Log

### Recovery Started: Tue, Aug 5, 2025 5:20:36 PM

**Actions Taken:**
1. Executed `git checkout 4890c24 -- web-ui/frontend/src/` to rollback frontend source
2. Ran `npm run build` to create production build (completed with warnings only)
3. Deployed to Cloudflare Pages using `npx wrangler pages deploy`
4. Deployment URL: https://71853370.gkl-fantasy-frontend.pages.dev

### Recovery Completed: Tue, Aug 5, 2025 5:23:45 PM

### Verification Results: 
- **API Status**: ✅ Confirmed working (transactions endpoint returns data)
- **Frontend Build**: ✅ Successful (78.92 kB main.js bundle)
- **Deployment**: ✅ Successful to Cloudflare Pages
- **Site Status**: ⚠️ Unable to fully verify due to JavaScript requirement, but build/deploy succeeded

**Time to Resolution**: ~3 minutes from rollback start to deployment completion

### Post-Recovery Notes:
- Rollback removed all uncommitted changes including the draft values feature
- The utils/dateFormatters.js file still exists locally but is not in production
- All modified files were reverted to commit 4890c24 state
- API was not modified as it was working correctly throughout

### Update: Production Still Not Loading Data
Despite successful rollback, the production site is still not displaying data. Further investigation revealed:
- API endpoints are working correctly (verified via curl)
- Frontend build completed successfully
- No CORS issues detected
- The issue appears to be with the frontend application initialization

**Root Cause Identified**: The production build was using `.env.local` which contains `REACT_APP_API_URL=http://localhost:3001/api`. This caused the production frontend to try connecting to localhost instead of the production API.

### Final Resolution: 
1. Renamed `.env.local` to `.env.local.backup` to prevent it from being used
2. Rebuilt the frontend (new hash: main.d42973d1.js)
3. Deployed the corrected build
4. **Resolution Time**: ~25 minutes total (including initial misdiagnosis)

### Key Learning: 
React's build process prioritizes `.env.local` over `.env.production`, causing production builds to use development settings when built locally. Always ensure `.env.local` is not present when building for production.

## Secondary Incident: Transaction Display Failure

### Timeline
- **Aug 5, ~6:00 PM**: After deploying draft values feature, discovered transactions not displaying
- **Root Cause**: Partial deployment of timestamp feature - API had `COALESCE(timestamp, strftime('%s', date))` ordering
- **Issue**: The strftime function wasn't working correctly in Cloudflare D1, returning empty results
- **Resolution**: Reverted to simple `date DESC` ordering via hotfix branch

### Additional Lessons Learned

7. **Partial feature deployments** are dangerous
   - Another developer's timestamp changes were partially included in our deployment
   - The API changes were deployed without the corresponding data collection updates
   - This broke transaction display completely

8. **SQL compatibility** varies between environments
   - `strftime('%s', date)` works in SQLite but not in Cloudflare D1
   - Always test SQL changes in the target environment
   - Consider using simpler, more portable SQL when possible

9. **Feature branch discipline** is critical
   - Uncommitted changes from multiple features got mixed together
   - Each feature should be in its own branch with clean commits
   - Never deploy partial features

### Updated Action Items
- [x] Create hotfix for transaction ordering issue
- [x] Complete timestamp feature implementation properly (completed Aug 5)
- [x] Add SQL compatibility warnings to deployment standards
- [x] Enforce stricter feature branch policies (documented in CLAUDE.md)

## Implementation Status

**Post-Mortem Completed**: August 5, 2025  
**Action Items Status**: 13 of 14 items completed (93%)  
**Outstanding Items**: 1 (automated deployment pipeline - future enhancement)

### Key Deliverables Created
- ✅ **Deployment Standards**: `docs/permanent-docs/deployment-standards.md`
- ✅ **CLAUDE.md Updates**: Git commit requirements, environment file handling
- ✅ **README.md Updates**: Proper deployment process documentation
- ✅ **Pre-deployment Checklist**: Integrated into deployment standards
- ✅ **Feature Branch Workflow**: Documented in CLAUDE.md
- ✅ **Release Notes Process**: Added to deployment requirements
- ✅ **SQL Compatibility Warnings**: Added to deployment standards

### Process Improvements Implemented
1. **Mandatory Git Commit Policy**: No more `--commit-dirty=true` deployments
2. **Environment File Management**: Clear guidance on `.env.local` vs `.env.production`
3. **Pre-deployment Validation**: 7-step checklist before every deployment
4. **Feature Branch Discipline**: Clean branch management requirements
5. **Release Documentation**: User-facing release notes for all deployments
6. **SQL Testing Requirements**: D1 compatibility verification

This post-mortem successfully transformed a production outage into comprehensive process improvements that prevent similar incidents.
