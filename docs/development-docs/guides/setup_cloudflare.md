# CloudFlare Worker Deployment Guide

## Prerequisites

### 1. Install Wrangler CLI
```bash
npm install -g wrangler
```

Verify installation:
```bash
wrangler --version
```

### 2. Get Your CloudFlare Account ID

1. Log in to CloudFlare Dashboard: https://dash.cloudflare.com
2. Select any domain (or Workers & Pages)
3. On the right sidebar, find your **Account ID**
4. Copy the Account ID (looks like: `a1b2c3d4e5f6...`)

## Step 1: Update Configuration

### Edit `cloudflare/wrangler.toml`

```toml
# Replace this line:
account_id = "YOUR_CLOUDFLARE_ACCOUNT_ID"
# With your actual account ID:
account_id = "a1b2c3d4e5f6..."  # Your actual account ID
```

### Edit `cloudflare/worker.js`

```javascript
// Replace this line:
const GITHUB_OWNER = 'your-github-username';
// With your GitHub username:
const GITHUB_OWNER = 'YOUR_ACTUAL_GITHUB_USERNAME';
```

## Step 2: Login to CloudFlare

```bash
cd cloudflare
wrangler login
```

This will open a browser window. Log in and authorize Wrangler.

## Step 3: Create GitHub Personal Access Token

You need a GitHub token with `workflow` permissions:

1. Go to GitHub Settings: https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Give it a name: `CloudFlare Worker - GKL Analytics`
4. Select scopes:
   - ✅ `repo` (full control)
   - ✅ `workflow` (update GitHub Actions)
5. Click **Generate token**
6. **COPY THE TOKEN NOW** (you won't see it again!)

## Step 4: Deploy the Worker

### First Deployment
```bash
cd cloudflare
wrangler deploy
```

You should see output like:
```
Uploading... 
Deployed gkl-fantasy-analytics
  https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev
```

Save this URL - you'll need it for testing!

## Step 5: Set CloudFlare Secrets

### Required Secret: GitHub Token
```bash
wrangler secret put GITHUB_TOKEN
```
When prompted, paste your GitHub Personal Access Token.

### Optional: Slack Notifications
```bash
wrangler secret put SLACK_WEBHOOK_URL
```
Enter your Slack webhook URL when prompted.

### Optional: Discord Notifications
```bash
wrangler secret put DISCORD_WEBHOOK_URL
```
Enter your Discord webhook URL when prompted.

### Verify Secrets
```bash
wrangler secret list
```

You should see:
```
[
  {
    "name": "GITHUB_TOKEN",
    "type": "secret_text"
  }
]
```

## Step 6: Test the Deployment

### Test Health Endpoint
```bash
# Replace YOUR-SUBDOMAIN with your actual subdomain
curl https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-04T...",
  "timezone": "America/New_York"
}
```

### Test Status Endpoint
```bash
curl https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/status
```

### Manual Trigger Test (Requires Auth Token)

First, let's create a simple auth token for testing:

```bash
# Add an auth token secret
wrangler secret put AUTH_TOKEN
# Enter a secure random string (e.g., generate with: openssl rand -hex 32)
```

Then update `cloudflare/worker.js` to check this token:
```javascript
// In handleRequest function, update the authorization check:
const authHeader = request.headers.get('Authorization');
const expectedToken = `Bearer ${AUTH_TOKEN}`; // Use the secret
if (authHeader !== expectedToken) {
  return new Response('Unauthorized', { status: 401 });
}
```

Redeploy:
```bash
wrangler deploy
```

Test manual trigger:
```bash
curl -X POST https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/trigger \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshType": "manual"}'
```

## Step 7: Verify Scheduled Triggers

Check the CloudFlare Dashboard:

1. Go to **Workers & Pages** in CloudFlare Dashboard
2. Click on `gkl-fantasy-analytics`
3. Go to **Triggers** tab
4. You should see 3 cron triggers:
   - `0 10 * * *` (6 AM ET)
   - `0 17 * * *` (1 PM ET)
   - `0 2 * * *` (10 PM ET)

## Step 8: Monitor Logs

### Real-time Logs
```bash
wrangler tail
```

This shows live logs as the worker executes.

### CloudFlare Dashboard Logs
1. Go to Workers & Pages → gkl-fantasy-analytics
2. Click on **Logs** tab
3. View recent executions and any errors

## Troubleshooting

### Worker Not Deploying
- Check your account ID is correct
- Ensure you're logged in: `wrangler login`
- Try: `wrangler deploy --compatibility-date 2024-01-01`

### GitHub Workflow Not Triggering
- Verify GITHUB_TOKEN secret is set
- Check token has `workflow` permissions
- Ensure workflow file exists in `.github/workflows/`
- Check GitHub Actions is enabled in repo settings

### Scheduled Triggers Not Running
- Remember times are in UTC
- Check CloudFlare Dashboard → Workers → Triggers
- View logs: `wrangler tail`

### Test GitHub Token
```bash
# Test your GitHub token works
curl -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user
```

## Success Checklist

- [ ] Wrangler CLI installed
- [ ] CloudFlare account ID updated in wrangler.toml
- [ ] GitHub username updated in worker.js
- [ ] Worker deployed successfully
- [ ] GitHub token secret set
- [ ] Health endpoint returns 200 OK
- [ ] Scheduled triggers visible in dashboard
- [ ] Test manual trigger works

## Next Steps

1. Wait for next scheduled run (6 AM, 1 PM, or 10 PM ET)
2. Monitor GitHub Actions tab for workflow runs
3. Check CloudFlare logs: `wrangler tail`
4. Set up notifications (Slack/Discord) if desired

## Useful Commands

```bash
# View worker details
wrangler deploy --dry-run

# Update worker
wrangler deploy

# Delete worker (if needed)
wrangler delete

# View secrets
wrangler secret list

# Remove a secret
wrangler secret delete SECRET_NAME

# View real-time logs
wrangler tail

# Run locally for testing
wrangler dev
```