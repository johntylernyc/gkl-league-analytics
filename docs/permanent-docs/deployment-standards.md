# Deployment Standards and Best Practices

**Last Updated**: August 5, 2025  
**Status**: Mandatory for all deployments  
**Context**: Created after production outage caused by deploying uncommitted code

## Executive Summary

This document defines mandatory deployment standards for the GKL League Analytics platform. These standards were established after a production outage on August 5, 2025, caused by deploying uncommitted code with missing dependencies.

## Critical Rules

### 1. Git-Based Deployments Only

**All production deployments MUST be from committed code.**

- ✅ DO: Deploy from clean git state
- ❌ DON'T: Deploy with uncommitted changes
- ❌ DON'T: Use `--commit-dirty=true` flag
- ❌ DON'T: Deploy without pushing to GitHub first

### 2. Environment File Management

**Production builds must not use development environment files.**

React's environment file precedence (highest to lowest):
1. `.env.local` - Development only
2. `.env.production` - Production settings
3. `.env` - Shared settings
4. Hardcoded defaults

**Critical Issue**: `.env.local` overrides `.env.production` even in production builds!

### 3. Release Documentation

**Qualifying production deployments MUST include user-facing release notes.**

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
- ❌ Minor bug fixes or hotfixes (unless specifically requested)

**Release Notes Format**:
- Stored in `docs/release-notes/` with format `YYYY-MM-DD-feature-name.md`
- Written in user-friendly language (not technical jargon)
- Include screenshots for UI changes when applicable
- **Required documentation links**:
  - Link to related PRD in `docs/prds/`
  - Link to implementation plan in `docs/development-docs/implemented/`
- Follow template structure in `docs/release-notes/TEMPLATE.md`

### 4. Pre-Deployment Checklist

Execute these commands before EVERY deployment:

```bash
# 1. Verify clean git state
git status
# Expected: "nothing to commit, working tree clean"

# 2. Verify latest commit
git log -1
# Confirm this is the code you want to deploy

# 3. Check for uncommitted files
git ls-files --others --exclude-standard
# Should return empty or only expected files

# 4. Verify environment files
ls -la web-ui/frontend/.env*
# Ensure .env.local exists for development

# 5. Check for partial features
git diff main --name-only
# Ensure no unrelated changes are included

# 6. Test SQL compatibility
# If SQL changes, test in D1 first:
# npx wrangler d1 execute gkl-fantasy --command "YOUR SQL HERE" --local

# 7. Create release notes
# Write user-facing release notes in docs/release-notes/
# Format: YYYY-MM-DD-feature-name.md
```

## Deployment Process

### Frontend Deployment (Cloudflare Pages)

```bash
cd web-ui/frontend

# Step 1: Temporarily remove .env.local
mv .env.local .env.local.backup

# Step 2: Build for production
npm run build

# Step 3: Verify build output
# - Check that main.[hash].js hash changed if code changed
# - Verify build size is reasonable (~80KB gzipped)

# Step 4: Deploy to Cloudflare Pages
npx wrangler pages deploy build --project-name gkl-fantasy-frontend

# Step 5: Restore .env.local
mv .env.local.backup .env.local
```

### API Deployment (Cloudflare Workers)

```bash
cd cloudflare-production

# Step 1: Verify wrangler.toml is correct
cat wrangler.toml | grep name

# Step 2: Deploy
npm run deploy

# Step 3: Verify deployment
curl https://gkl-fantasy-api.services-403.workers.dev/health
```

## Feature Branch Workflow

### Creating a Feature Branch

```bash
# 1. Start from clean main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/descriptive-name

# 3. Develop and commit
git add .
git commit -m "feat: clear description"
git push origin feature/descriptive-name
```

### Merging to Production

```bash
# 1. Update main
git checkout main
git pull origin main

# 2. Merge feature
git merge feature/descriptive-name

# 3. Push to GitHub
git push origin main

# 4. Deploy from main branch
# Follow deployment process above

# 5. Clean up
git branch -d feature/descriptive-name
git push origin --delete feature/descriptive-name
```

## Rollback Procedures

### Frontend Rollback

```bash
# 1. Identify last good commit
git log --oneline -10

# 2. Checkout frontend at that commit
git checkout <commit-hash> -- web-ui/frontend/src/

# 3. Rebuild and deploy
cd web-ui/frontend
mv .env.local .env.local.backup
npm run build
npx wrangler pages deploy build --project-name gkl-fantasy-frontend
mv .env.local.backup .env.local
```

### API Rollback

```bash
# 1. Checkout API at last good commit
git checkout <commit-hash> -- cloudflare-production/src/

# 2. Redeploy
cd cloudflare-production
npm run deploy
```

## Verification Steps

### Post-Deployment Verification

1. **Browser Console Check**
   - Open https://goldenknightlounge.com
   - Press F12 to open DevTools
   - Check Console tab for errors
   - Look for failed API calls

2. **API Health Check**
   ```bash
   curl https://gkl-fantasy-api.services-403.workers.dev/health
   # Expected: {"status":"healthy",...}
   ```

3. **Data Loading Test**
   ```bash
   curl https://gkl-fantasy-api.services-403.workers.dev/transactions?limit=1
   # Should return transaction data
   ```

4. **Frontend Functionality**
   - Navigate to /transactions
   - Verify data loads
   - Check player search works

## Common Issues and Solutions

### Issue: Frontend Connects to Localhost in Production

**Symptoms**: 
- Console shows requests to `http://localhost:3001`
- CORS errors in browser console

**Cause**: `.env.local` was present during build

**Solution**:
1. Remove `.env.local` before building
2. Rebuild frontend
3. Redeploy

### Issue: Missing Module Errors

**Symptoms**:
- "Cannot find module" errors
- White screen in production

**Cause**: Uncommitted files deployed

**Solution**:
1. Commit all changes
2. Push to GitHub
3. Redeploy from clean state

### Issue: Build Doesn't Update

**Symptoms**:
- Changes don't appear in production
- Same JS file hash after rebuild

**Cause**: Build cache or environment issues

**Solution**:
1. Delete `build/` folder
2. Clear npm cache: `npm cache clean --force`
3. Rebuild and redeploy

### Issue: SQL Works Locally but Not in D1

**Symptoms**:
- Queries return empty results in production
- Same query works in local SQLite

**Cause**: D1 SQL compatibility differences

**Common Issues**:
- `strftime('%s', date)` - doesn't work in D1
- Complex date functions may behave differently
- Some SQLite-specific functions not supported

**Solution**:
1. Test SQL in D1 before deployment
2. Use simpler, ANSI-standard SQL when possible
3. Avoid SQLite-specific functions
4. Test with: `npx wrangler d1 execute gkl-fantasy --command "SQL" --remote`

## Monitoring and Alerts

### Manual Monitoring

Until automated monitoring is implemented:

1. **Daily Checks**
   - Visit production site
   - Verify data is current
   - Check browser console

2. **Post-Deployment**
   - Monitor for 15 minutes
   - Check error rates
   - Verify core functions

### Future Improvements

- [ ] Implement Sentry for error tracking
- [ ] Add synthetic monitoring
- [ ] Create deployment automation
- [ ] Add pre-deployment tests
- [ ] Implement blue-green deployments

## Emergency Contacts

- **Cloudflare Status**: https://www.cloudflarestatus.com/
- **GitHub Status**: https://www.githubstatus.com/
- **Team Escalation**: [Define escalation path]

## Appendix: Incident Timeline (Aug 5, 2025)

### Incident 1: Uncommitted Code Deployment
1. **~11:50 AM**: Uncommitted code deployed with `--commit-dirty=true`
2. **~11:57 AM**: Frontend deployed with missing `utils/dateFormatters.js`
3. **~4:00 PM**: Production outage detected
4. **~5:20 PM**: Rollback initiated
5. **~5:23 PM**: Initial fix failed - `.env.local` issue discovered
6. **~5:45 PM**: Correct build deployed
7. **~5:46 PM**: Service restored

**Total Downtime**: ~4 hours  
**Root Causes**: 
1. Uncommitted code deployed
2. `.env.local` used in production build

### Incident 2: Transaction Display Failure
1. **~6:00 PM**: Deployed draft values feature successfully
2. **~6:05 PM**: Discovered transactions not displaying
3. **~6:10 PM**: Identified partial timestamp feature deployment
4. **~6:15 PM**: Created hotfix branch
5. **~6:20 PM**: Deployed fix reverting to simple date ordering
6. **~6:22 PM**: Service fully restored

**Total Downtime**: ~20 minutes  
**Root Cause**: SQL compatibility issue with D1 (`strftime` function not supported)

---

This document is mandatory reading for anyone deploying to production.