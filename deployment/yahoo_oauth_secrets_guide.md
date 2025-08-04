# Yahoo OAuth Secrets - Complete Guide

## Important: Understanding Yahoo OAuth Flow

The Yahoo Fantasy API uses OAuth 2.0, which involves:
1. **One-time authorization code** - Used ONCE to get initial tokens (expires quickly)
2. **Access token** - Valid for 1 hour, used for API calls
3. **Refresh token** - Long-lived, used to get new access tokens

## What You Actually Need in GitHub Secrets

You have two options for setting up Yahoo OAuth in GitHub Actions:

### Option 1: Use Refresh Token (Recommended)

Since you already have `tokens.json` with a valid refresh token, use this approach:

#### GitHub Secrets to Create:

1. **YAHOO_CLIENT_ID**  
   Value: `dj0yJmk9TUVsalowTUlwMGEzJmQ9WVdrOU9YUTBlV3hzT1RRbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWY4`

2. **YAHOO_CLIENT_SECRET**  
   Value: `ba50f46b8e684dbe8af283aadcfa209d5f79ebfe`

3. **YAHOO_REDIRECT_URI**  
   Value: `https://createdbydata.com`

4. **YAHOO_REFRESH_TOKEN** (not AUTHORIZATION_CODE!)  
   Value: `ABl7j2hSagqnPdj8EfXtUVJcg5W7~001~Jub6gbTt3pfS.u.npRjkXCRLWuI-`
   (This is from your tokens.json file, line 3)

### Option 2: Generate Fresh Authorization Code

If the refresh token expires or stops working:

1. **Generate new auth URL:**
   ```bash
   python auth/generate_auth_url.py
   ```

2. **Visit the URL** in your browser and authorize the app

3. **Copy the authorization code** from the redirect URL:
   - After authorizing, you'll be redirected to something like:
   - `https://createdbydata.com?code=NEW_AUTH_CODE_HERE`
   - Copy the `code` parameter value

4. **Get new tokens:**
   ```bash
   # First update auth/config.py with the new auth code
   # Then run:
   python auth/initialize_tokens.py
   ```

5. **Use the new refresh token** from the generated tokens.json

## Updated Scripts for GitHub Actions

We need to update the incremental update scripts to use the refresh token properly:

### Create a Token Manager

Create `auth/token_manager.py`: