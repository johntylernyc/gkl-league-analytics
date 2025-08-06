# Local Development Environment Setup

## Overview
This guide explains how to run the GKL League Analytics application locally with proper separation between local and production environments.

## Architecture

```
Local Development:
Frontend (localhost:3000) → Backend API (localhost:3001) → SQLite (local database)

Production:
Frontend (goldenknightlounge.com) → Cloudflare Workers API → Cloudflare D1
```

## Setup Instructions

### 1. Backend Setup

The backend serves the API locally from your SQLite database.

```bash
cd web-ui/backend
npm install  # First time only
npm start    # Runs on port 3001
```

**Configuration** (already set in `.env`):
- Port: 3001
- Database: `database/league_analytics.db`
- CORS: Allows localhost:3000

### 2. Frontend Setup

The frontend React app needs to point to the local backend.

```bash
cd web-ui/frontend
npm install  # First time only
npm start    # Runs on port 3000
```

**Configuration** (`.env.local`):
```
REACT_APP_API_URL=http://localhost:3001/api
REACT_APP_ENV=local
```

**Note**: After creating or modifying `.env.local`, you must restart the frontend for changes to take effect.

### 3. Verify Setup

1. **Backend Health Check**: http://localhost:3001/health
   - Should return: `{"status":"healthy","database":"connected"}`

2. **Frontend**: http://localhost:3000
   - Should display data from your local database
   - Check transactions page for latest entries

3. **API Test**:
   ```bash
   curl http://localhost:3001/api/transactions?limit=1
   ```

## Environment Files

### Frontend
- `.env.local` - Local development (uses local backend)
- `.env.production` - Production build (uses Cloudflare API)
- `.env.example` - Template for developers

### Backend
- `.env` - Backend configuration (port, database path, CORS)

## Data Flow

### Local Development
1. User accesses http://localhost:3000
2. React app makes API calls to http://localhost:3001/api
3. Backend queries local SQLite database
4. Data returned to frontend

### Production
1. User accesses https://goldenknightlounge.com
2. React app makes API calls to Cloudflare Workers
3. Workers query Cloudflare D1 database
4. Data returned to frontend

## Troubleshooting

### Frontend shows old data
- **Issue**: Frontend is using production API instead of local
- **Solution**: 
  1. Check `.env.local` exists with correct API URL
  2. Restart frontend: Stop (Ctrl+C) and run `npm start` again
  3. Clear browser cache

### Backend not starting
- **Issue**: Port 3001 already in use
- **Solution**: Backend is already running, check with `curl http://localhost:3001/health`

### CORS errors
- **Issue**: Frontend can't connect to backend
- **Solution**: Verify backend `.env` has `CORS_ORIGIN=http://localhost:3000`

### Database not found
- **Issue**: Backend can't find SQLite database
- **Solution**: Check `DB_PATH` in backend `.env` points to correct location

## Updating Data

### Local Database Update
```bash
cd data_pipeline
python league_transactions/backfill_transactions_optimized.py
python daily_lineups/collector.py
```

### Sync to Production
```bash
# Export from local SQLite
python scripts/export_to_cloudflare.py

# Import to Cloudflare D1
cd cloudflare-production
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/transactions.sql --remote
```

## Development Workflow

1. **Make changes locally**
2. **Test with local database**
3. **Verify all features work**
4. **Sync to production when ready**

## Key Differences: Local vs Production

| Aspect | Local | Production |
|--------|-------|------------|
| Frontend URL | http://localhost:3000 | https://goldenknightlounge.com |
| API URL | http://localhost:3001/api | https://gkl-fantasy-api.services-403.workers.dev |
| Database | SQLite (local file) | Cloudflare D1 |
| Data Updates | Python scripts | GitHub Actions + Cloudflare Workers |
| Environment | Development | Production |

## Best Practices

1. **Always test locally first** before deploying to production
2. **Keep local database updated** for accurate testing
3. **Use `.env.local`** for local configuration, never commit it
4. **Document API changes** that affect both environments
5. **Verify both environments** after major changes

---

*Last Updated: August 2025*