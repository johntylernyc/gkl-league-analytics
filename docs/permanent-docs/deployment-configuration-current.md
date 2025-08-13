# Deployment and Configuration - Current State
*Last Updated: August 13, 2025*

## Deployment Overview

The GKL League Analytics platform is deployed across multiple Cloudflare services with a Python data pipeline running via GitHub Actions.

## Production Infrastructure

### Cloudflare Workers (API)
- **URL**: `https://gkl-fantasy-api.services-403.workers.dev`
- **Entry Point**: `src/index-with-db.js` (NOT the modular index.js)
- **Account ID**: Retrieved from environment
- **Deployment Command**: `npx wrangler deploy`

### Cloudflare Pages (Frontend)
- **URL**: `https://goldenknightlounge.com`
- **Project**: `gkl-fantasy-frontend`
- **Build Directory**: `web-ui/frontend/build`
- **Framework**: React 18

### Cloudflare D1 (Database)
- **Database Name**: `gkl-fantasy`
- **Database ID**: `f541fa7b-9356-4a96-a24e-3b7cd06e9cfa`
- **Binding**: `DB`
- **Size Limit**: 500MB

### Cloudflare KV (Cache)
- **Namespace ID**: `27f3df3708b84a6f8d57a0753057ef9f`
- **Binding**: `CACHE`
- **Purpose**: API response caching

## Configuration Files

### wrangler.toml (Current Production)
```toml
name = "gkl-fantasy-api"
main = "src/index-with-db.js"  # CRITICAL: Not using modular system
compatibility_date = "2024-01-02"
compatibility_flags = ["nodejs_compat"]

# Development environment
[env.development]
name = "gkl-fantasy-api-dev"
vars = { ENVIRONMENT = "development" }

# Production environment
[env.production]
name = "gkl-fantasy-api-prod"
vars = { ENVIRONMENT = "production" }

# D1 Database binding
[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "f541fa7b-9356-4a96-a24e-3b7cd06e9cfa"

# KV namespace for caching
[[kv_namespaces]]
binding = "CACHE"
id = "27f3df3708b84a6f8d57a0753057ef9f"

# Production-specific bindings
[[env.production.d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "f541fa7b-9356-4a96-a24e-3b7cd06e9cfa"

[[env.production.kv_namespaces]]
binding = "CACHE"
id = "27f3df3708b84a6f8d57a0753057ef9f"
```

### package.json Scripts (cloudflare-production)
```json
{
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "deploy:prod": "wrangler deploy --env production",
    "tail": "wrangler tail"
  }
}
```

### Frontend Environment Files

**web-ui/frontend/.env.production**
```
REACT_APP_API_URL=https://gkl-fantasy-api.services-403.workers.dev
```

**web-ui/frontend/.env.local** (Development)
```
REACT_APP_API_URL=http://localhost:3001/api
```

⚠️ **Critical Issue**: `.env.local` overrides production settings even in production builds!

## GitHub Actions Configuration

### Workflow: data-refresh.yml
```yaml
name: Data Refresh
on:
  schedule:
    - cron: '0 10 * * *'  # 6 AM ET
    - cron: '0 17 * * *'  # 1 PM ET
    - cron: '0 2 * * *'   # 10 PM ET
  workflow_dispatch:
    inputs:
      refresh_type:
        description: 'Type of refresh'
        required: true
        default: 'incremental'
        type: choice
        options:
          - incremental
          - full
          - manual
```

### Environment Secrets (GitHub)
```
YAHOO_CLIENT_ID
YAHOO_CLIENT_SECRET
YAHOO_AUTHORIZATION_CODE
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
D1_DATABASE_ID
```

## Deployment Process

### API Deployment (Manual)
```bash
cd cloudflare-production
npm run deploy  # Deploys to default environment

# Or with explicit environment:
npx wrangler deploy --env production
```

### Frontend Deployment (Manual)
```bash
cd web-ui/frontend

# CRITICAL: Remove .env.local before building for production
mv .env.local .env.local.backup
npm run build
npx wrangler pages deploy build --project-name gkl-fantasy-frontend
mv .env.local.backup .env.local
```

### Database Migrations
```bash
# Apply schema changes to D1
npx wrangler d1 execute gkl-fantasy --file=migration.sql --remote

# Import data (order matters!)
npx wrangler d1 execute gkl-fantasy --file=job_logs.sql --remote  # FIRST
npx wrangler d1 execute gkl-fantasy --file=transactions.sql --remote
npx wrangler d1 execute gkl-fantasy --file=lineups.sql --remote
```

## Local Development Setup

### Backend API
```bash
cd web-ui/backend
npm install
npm start  # Runs on port 3001
```

### Frontend
```bash
cd web-ui/frontend
npm install
npm start  # Runs on port 3000
```

### Workers Development
```bash
cd cloudflare-production
npx wrangler dev  # Local Workers environment on 8787
```

## Common Deployment Issues

### 1. Wrong Entry Point
**Problem**: Changes to route files have no effect
**Cause**: `wrangler.toml` uses `index-with-db.js` not modular `index.js`
**Solution**: Either update index-with-db.js or change entry point

### 2. Environment Variable Override
**Problem**: Production build uses development API URL
**Cause**: `.env.local` overrides `.env.production`
**Solution**: Remove .env.local before production build

### 3. Deployment Not Updating
**Problem**: Old code still running after deployment
**Cause**: Cloudflare caching or version not deployed
**Solution**: 
```bash
npx wrangler rollback  # Rollback first
npx wrangler deploy    # Then redeploy
```

### 4. Foreign Key Constraints
**Problem**: D1 import fails with foreign key errors
**Cause**: Wrong import order
**Solution**: Always import job_logs first

### 5. Column Name Mismatches
**Problem**: 500 errors with "no such column"
**Cause**: Code references old column names
**Solution**: Update queries to use correct column names

## Monitoring and Debugging

### View Worker Logs
```bash
npx wrangler tail gkl-fantasy-api --format pretty
```

### Check Deployment Status
```bash
npx wrangler deployments list
npx wrangler versions list
```

### Test API Endpoints
```bash
# Health check
curl https://gkl-fantasy-api.services-403.workers.dev/health

# With specific date
curl https://gkl-fantasy-api.services-403.workers.dev/lineups/date/2025-08-13
```

## Version Management

### Current Deployment Versions
- **Worker**: Version changes with each deployment
- **Frontend**: Deployed via Pages, no explicit versioning
- **Database Schema**: Manual migration tracking needed

### Rollback Procedures
```bash
# Workers rollback
npx wrangler rollback

# Frontend rollback (manual)
# Redeploy previous commit via Pages dashboard

# Database rollback
# No automated rollback - requires manual SQL
```

## Security Configuration

### API CORS Settings
```javascript
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',  // Should restrict in production
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};
```

### Authentication
- Yahoo OAuth2 for data collection
- No user authentication on frontend (public data)
- API tokens stored in GitHub Secrets

## Performance Configuration

### Worker Limits
- CPU: 10ms (free tier)
- Memory: 128MB
- Request size: 100MB
- Subrequests: 50

### D1 Limits
- Database size: 500MB
- Query time: 30s max
- Batch size: 100 statements

### KV Cache Settings
- TTL: 300 seconds (5 minutes) for most data
- Namespace: Single namespace for all cache

## Recommended Configuration Changes

1. **Switch to Modular System**: Update wrangler.toml to use index.js
2. **Restrict CORS**: Limit to goldenknightlounge.com domain
3. **Add Environment Detection**: Properly detect and use environment configs
4. **Implement Cache Strategy**: Different TTLs for different data types
5. **Add Error Tracking**: Integrate Sentry or similar service
6. **Version Database Schema**: Track migrations properly
7. **Automate Deployments**: CD pipeline for automatic deployments