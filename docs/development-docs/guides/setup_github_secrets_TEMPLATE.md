# GitHub Secrets Setup Guide (TEMPLATE)

## Required Secrets for GitHub Actions

You need to add these secrets to your GitHub repository for the automated data refresh to work.

### How to Add Secrets to GitHub

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** for each secret below

### Required Secrets

Add each of these secrets with the exact name and your actual values:

#### 1. YAHOO_CLIENT_ID
**Name:** `YAHOO_CLIENT_ID`  
**Value:** `YOUR_YAHOO_CLIENT_ID_HERE`

#### 2. YAHOO_CLIENT_SECRET
**Name:** `YAHOO_CLIENT_SECRET`  
**Value:** `YOUR_YAHOO_CLIENT_SECRET_HERE`

#### 3. YAHOO_REDIRECT_URI
**Name:** `YAHOO_REDIRECT_URI`  
**Value:** `YOUR_REDIRECT_URI_HERE`

#### 4. YAHOO_REFRESH_TOKEN
**Name:** `YAHOO_REFRESH_TOKEN`  
**Value:** `YOUR_REFRESH_TOKEN_FROM_TOKENS_JSON`

**Important:** Use the refresh_token from your `auth/tokens.json` file, NOT an authorization code.

### Optional Secrets (for notifications)

#### 5. SLACK_WEBHOOK_URL (Optional)
**Name:** `SLACK_WEBHOOK_URL`  
**Value:** Your Slack incoming webhook URL

#### 6. DISCORD_WEBHOOK_URL (Optional)
**Name:** `DISCORD_WEBHOOK_URL`  
**Value:** Your Discord webhook URL

## Getting Your Credentials

### Yahoo OAuth Credentials
1. Go to https://developer.yahoo.com/apps/
2. Create a new app or use existing
3. Copy the Client ID and Client Secret
4. Set redirect URI (e.g., https://localhost:8080 or your domain)

### Generate Refresh Token
1. Run `python auth/generate_auth_url.py`
2. Visit the URL and authorize
3. Copy the code from redirect URL
4. Run `python auth/initialize_tokens.py`
5. Get refresh_token from `auth/tokens.json`

## Security Notes

⚠️ **NEVER commit actual credentials to your repository**
- Use placeholders in documentation
- Store real values only in GitHub Secrets
- Keep `tokens.json` in `.gitignore`

## Verify Secrets Are Set

After adding all secrets, you should see them listed in:
**Settings** → **Secrets and variables** → **Actions** → **Repository secrets**

## Test the GitHub Action

Once secrets are set, test the workflow:
1. Go to **Actions** tab
2. Run "Scheduled Data Refresh" workflow manually
3. Check logs for authentication success