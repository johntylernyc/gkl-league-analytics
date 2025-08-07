# Cloudflare Workers Deployment Guide

## Prerequisites

Before starting, ensure you have:
- Node.js 16+ installed
- A Cloudflare account (free tier is fine)
- Git installed

## Step 1: Initial Setup

### 1.1 Install Wrangler CLI

Open a terminal and run:
```bash
npm install -g wrangler
```

### 1.2 Authenticate with Cloudflare

```bash
wrangler login
```

This will open your browser. Log in to your Cloudflare account and authorize Wrangler.

### 1.3 Navigate to the deployment directory

```bash
cd cloudflare-deployment
```

### 1.4 Install dependencies

```bash
npm install
```

## Step 2: Database Migration

### 2.1 Export existing SQLite database

```bash
npm run export-db
```

This creates SQL files in the `sql/` directory.

### 2.2 Create and import to D1 database

```bash
npm run import-db
```

Follow the prompts:
- Press Enter to use default database name "gkl-fantasy"
- Type 'y' to proceed with import

**Important:** Note the database ID that's displayed. You'll need it for the next step.

### 2.3 Update wrangler.toml

Open `wrangler.toml` and update the database_id:

```toml
[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "YOUR_DATABASE_ID_HERE"  # <-- Add the ID from step 2.2
```

## Step 3: Create KV Namespace (for caching)

```bash
wrangler kv:namespace create "CACHE"
```

Note the ID and update `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "CACHE"
id = "YOUR_KV_ID_HERE"  # <-- Add the ID here
```

## Step 4: Test Locally

```bash
npm run dev
```

This starts a local development server. Test the API:
- Open: http://localhost:8787/health
- You should see a JSON response with status "healthy"

Test other endpoints:
- http://localhost:8787/api/transactions
- http://localhost:8787/api/players
- http://localhost:8787/api/analytics/overview

## Step 5: Deploy to Cloudflare

### 5.1 Deploy to Workers

```bash
npm run deploy
```

This deploys to your workers.dev subdomain. Note the URL that's displayed.

### 5.2 Update Frontend Configuration

Navigate to the frontend directory:
```bash
cd ../web-ui/frontend
```

Create `.env.production`:
```env
REACT_APP_API_URL=https://gkl-fantasy-api.YOUR-SUBDOMAIN.workers.dev
```

Build the frontend:
```bash
npm run build
```

## Step 6: Deploy Frontend to Cloudflare Pages

### 6.1 Create Pages project

```bash
cd web-ui/frontend
wrangler pages deploy build/ --project-name gkl-fantasy-frontend
```

Follow the prompts and note the Pages URL.

### 6.2 Configure custom domain (optional)

1. Go to Cloudflare Dashboard > Pages > Your Project > Custom domains
2. Add your domain
3. Follow DNS configuration instructions

## Step 7: Set Up Scheduled Updates

The Workers are configured with cron triggers for 2 AM and 2 PM daily updates.

To verify they're working:
```bash
wrangler tail
```

This shows real-time logs from your Worker.

## Step 8: Production Deployment

### 8.1 Update environment variables

Edit `wrangler.toml` for production:

```toml
[env.production]
name = "gkl-fantasy-api-prod"
vars = { ENVIRONMENT = "production" }
routes = [
  { pattern = "api.yourdomain.com/*", zone_name = "yourdomain.com" }
]
```

### 8.2 Deploy to production

```bash
npm run deploy:prod
```

## Troubleshooting

### Database Issues

If you see database errors:
1. Check the database ID in wrangler.toml
2. Verify tables were created: `wrangler d1 execute gkl-fantasy --command="SELECT name FROM sqlite_master WHERE type='table'"`

### API Not Responding

1. Check Worker logs: `wrangler tail`
2. Verify deployment: `wrangler deployments list`

### Frontend Can't Connect to API

1. Check CORS settings in src/utils/cors.js
2. Verify API URL in frontend .env file
3. Check browser console for errors

## Monitoring

### View logs
```bash
wrangler tail
```

### Check metrics
Go to Cloudflare Dashboard > Workers & Pages > Your Worker > Metrics

### Database queries
```bash
wrangler d1 execute gkl-fantasy --command="SELECT COUNT(*) FROM transactions"
```

## Rollback

If something goes wrong:

```bash
wrangler rollback --message "Reverting to previous version"
```

## Cost Estimation

With Cloudflare's free tier:
- Workers: 100,000 requests/day free
- D1: 5GB storage free
- Pages: Unlimited sites

Estimated monthly cost for typical usage: **$0 - $5**

## Support

For issues or questions:
1. Check Worker logs: `wrangler tail`
2. Review Cloudflare documentation: https://developers.cloudflare.com/workers/
3. Check the error_log table in D1 database

## Next Steps

After successful deployment:
1. Set up monitoring alerts
2. Configure custom domain
3. Enable Cloudflare Analytics
4. Set up backup automation
5. Configure rate limiting

---

Deployment typically takes 30-45 minutes total.