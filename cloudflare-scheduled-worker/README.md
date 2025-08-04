# CloudFlare Worker Setup

This directory contains the CloudFlare Worker that handles scheduled data refreshes for the GKL Fantasy Baseball Analytics system.

## Overview

The CloudFlare Worker runs on a schedule to trigger GitHub Actions workflows that refresh fantasy baseball data at three times daily:
- **6 AM ET**: Full refresh (7-day lookback for stat corrections)
- **1 PM ET**: Incremental refresh (3-day lookback for lineup changes)
- **10 PM ET**: Incremental refresh (3-day lookback for final lineup changes)

## Setup Instructions

### 1. Prerequisites

- CloudFlare account with Workers enabled
- GitHub repository with Actions enabled
- GitHub Personal Access Token with `workflow` permissions
- Wrangler CLI installed (`npm install -g wrangler`)

### 2. Configuration

1. **Update Configuration Files**:
   ```bash
   # Edit wrangler.toml
   - Replace YOUR_CLOUDFLARE_ACCOUNT_ID with your account ID
   
   # Edit worker.js
   - Replace 'your-github-username' with your GitHub username
   ```

2. **Set Environment Variables**:
   ```bash
   # Required
   wrangler secret put GITHUB_TOKEN
   # Enter your GitHub Personal Access Token when prompted
   
   # Optional (for notifications)
   wrangler secret put SLACK_WEBHOOK_URL
   wrangler secret put DISCORD_WEBHOOK_URL
   ```

### 3. Deployment

1. **Login to CloudFlare**:
   ```bash
   wrangler login
   ```

2. **Deploy the Worker**:
   ```bash
   wrangler deploy
   ```

3. **Verify Deployment**:
   ```bash
   # Check worker status
   wrangler tail
   
   # Test health endpoint
   curl https://gkl-fantasy-analytics.<your-subdomain>.workers.dev/health
   ```

## Manual Triggers

You can manually trigger the refresh process:

```bash
# Via CloudFlare Worker
curl -X POST https://gkl-fantasy-analytics.<your-subdomain>.workers.dev/trigger \
  -H "Authorization: Bearer YOUR_SECRET_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshType": "manual"}'

# Via GitHub Actions (directly)
gh workflow run data-refresh.yml \
  -f refresh_type=manual \
  -f environment=production \
  -f date_range="2025-08-01,2025-08-04"
```

## Monitoring

### Check Worker Status
```bash
# View recent executions
wrangler tail

# Check workflow status
curl https://gkl-fantasy-analytics.<your-subdomain>.workers.dev/status
```

### CloudFlare Dashboard
1. Go to CloudFlare Dashboard > Workers & Pages
2. Select `gkl-fantasy-analytics`
3. View metrics, logs, and scheduled triggers

### GitHub Actions
1. Go to GitHub repository > Actions tab
2. View `Scheduled Data Refresh` workflow runs
3. Check logs for each job

## Troubleshooting

### Worker Not Triggering
1. Check cron expressions in `wrangler.toml`
2. Verify timezone settings (uses UTC)
3. Check CloudFlare dashboard for errors

### GitHub Actions Not Running
1. Verify GitHub token has `workflow` permissions
2. Check workflow file exists at `.github/workflows/data-refresh.yml`
3. Ensure Actions are enabled in repository settings

### Notifications Not Working
1. Verify webhook URLs are correctly set as secrets
2. Test webhooks manually with curl
3. Check worker logs for notification errors

## Schedule Reference

| Time (ET) | Time (UTC) | Refresh Type | Lookback Period |
|-----------|------------|--------------|-----------------|
| 6:00 AM   | 10:00 AM*  | Full         | 7 days          |
| 1:00 PM   | 5:00 PM*   | Incremental  | 3 days          |
| 10:00 PM  | 2:00 AM**  | Incremental  | 3 days          |

\* During EST (winter)  
\** Next day UTC

## Cost Considerations

CloudFlare Workers Free Tier includes:
- 100,000 requests per day
- 10ms CPU time per invocation
- Unlimited scheduled triggers

Our usage (3 triggers/day + occasional manual) fits well within free tier limits.

## Security Notes

1. **GitHub Token**: Store securely as CloudFlare secret, never commit to code
2. **Authorization**: Manual trigger endpoint requires Bearer token
3. **CORS**: Worker doesn't enable CORS by default for security
4. **Rate Limiting**: Consider adding rate limiting for manual triggers

## Development

### Local Testing
```bash
# Start local development server
wrangler dev

# Test locally
curl http://localhost:8787/health
```

### Update Worker
```bash
# Make changes to worker.js
# Deploy updates
wrangler deploy

# View deployment logs
wrangler tail
```

## Integration with GitHub Actions

The worker triggers the GitHub Actions workflow with these inputs:
- `refresh_type`: morning/afternoon/night/manual
- `environment`: production/test
- `date_range`: Calculated based on refresh type

The workflow then:
1. Determines parameters based on refresh type
2. Runs three parallel jobs: transactions, lineups, stats
3. Creates database backup (production only)
4. Sends completion notifications

## Monitoring Dashboard

Consider setting up a monitoring dashboard using:
- CloudFlare Analytics API
- GitHub Actions API
- Custom metrics in CloudFlare KV or Durable Objects

Example metrics to track:
- Successful/failed refreshes per day
- Average refresh duration
- Data changes detected
- Error rates by job type