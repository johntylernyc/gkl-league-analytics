# GitHub Secrets Setup Guide

## Required Secrets for GitHub Actions

You need to add these secrets to your GitHub repository for the automated data refresh to work.

### How to Add Secrets to GitHub

1. Go to your GitHub repository: https://github.com/YOUR_USERNAME/gkl-league-analytics
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** for each secret below

### Required Secrets

Add each of these secrets with the exact name and value:

#### 1. YAHOO_CLIENT_ID
**Name:** `YAHOO_CLIENT_ID`  
**Value:** `dj0yJmk9TUVsalowTUlwMGEzJmQ9WVdrOU9YUTBlV3hzT1RRbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWY4`

#### 2. YAHOO_CLIENT_SECRET
**Name:** `YAHOO_CLIENT_SECRET`  
**Value:** `ba50f46b8e684dbe8af283aadcfa209d5f79ebfe`

#### 3. YAHOO_REDIRECT_URI
**Name:** `YAHOO_REDIRECT_URI`  
**Value:** `https://createdbydata.com`

#### 4. YAHOO_REFRESH_TOKEN
**Name:** `YAHOO_REFRESH_TOKEN`  
**Value:** `ABl7j2hSagqnPdj8EfXtUVJcg5W7~001~Jub6gbTt3pfS.u.npRjkXCRLWuI-`

**Important:** Use the refresh_token from your `auth/tokens.json` file (line 3), NOT the authorization code from `.env`. The authorization code is one-time use only.

### Optional Secrets (for notifications)

#### 5. SLACK_WEBHOOK_URL (Optional)
**Name:** `SLACK_WEBHOOK_URL`  
**Value:** Your Slack incoming webhook URL (if you want Slack notifications)

To get a Slack webhook:
1. Go to https://api.slack.com/apps
2. Create a new app or select existing
3. Go to "Incoming Webhooks"
4. Add new webhook to workspace
5. Copy the webhook URL

#### 6. DISCORD_WEBHOOK_URL (Optional)
**Name:** `DISCORD_WEBHOOK_URL`  
**Value:** Your Discord webhook URL (if you want Discord notifications)

To get a Discord webhook:
1. Open Discord, go to your server
2. Right-click the channel → Edit Channel
3. Go to Integrations → Webhooks
4. Create New Webhook
5. Copy the webhook URL

## Verify Secrets Are Set

After adding all secrets, you should see them listed in:
**Settings** → **Secrets and variables** → **Actions** → **Repository secrets**

You should see at minimum:
- YAHOO_CLIENT_ID
- YAHOO_CLIENT_SECRET  
- YAHOO_REDIRECT_URI
- YAHOO_AUTHORIZATION_CODE

## Test the GitHub Action

Once secrets are set, you can test the workflow:

### Option 1: Via GitHub UI
1. Go to **Actions** tab in your repository
2. Click on "Scheduled Data Refresh" workflow
3. Click "Run workflow" button
4. Select:
   - Branch: `main`
   - Refresh type: `manual`
   - Environment: `test`
   - Date range: `2025-08-01,2025-08-04` (optional)
5. Click "Run workflow"

### Option 2: Via GitHub CLI
```bash
gh workflow run data-refresh.yml \
  -f refresh_type=manual \
  -f environment=test \
  -f date_range="2025-08-01,2025-08-04"
```

## Next Step

Once GitHub secrets are configured and tested, proceed to CloudFlare Worker deployment.