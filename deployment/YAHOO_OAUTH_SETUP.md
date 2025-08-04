# Yahoo OAuth Setup - Complete Guide

## ✅ Your Current Status

Your Yahoo OAuth is **working correctly**! The refresh token successfully obtained a new access token.

## GitHub Secrets You Need to Create

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these **4 secrets** exactly as shown:

### 1. YAHOO_CLIENT_ID
```
dj0yJmk9TUVsalowTUlwMGEzJmQ9WVdrOU9YUTBlV3hzT1RRbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWY4
```

### 2. YAHOO_CLIENT_SECRET
```
ba50f46b8e684dbe8af283aadcfa209d5f79ebfe
```

### 3. YAHOO_REDIRECT_URI
```
https://createdbydata.com
```

### 4. YAHOO_REFRESH_TOKEN
```
ABl7j2hSagqnPdj8EfXtUVJcg5W7~001~Jub6gbTt3pfS.u.npRjkXCRLWuI-
```

## Important Notes

### About the Tokens

- **Access Token**: Expires every hour, automatically refreshed by our scripts
- **Refresh Token**: Long-lived (~6 months), used to get new access tokens
- **Authorization Code**: One-time use only, already used to get your tokens

### What Happens in GitHub Actions

1. The workflow uses `YAHOO_REFRESH_TOKEN` to get a fresh access token
2. The token manager (`auth/token_manager.py`) handles this automatically
3. Each incremental update script uses the token manager for API calls

### If Tokens Stop Working

If after ~6 months the refresh token expires:

1. **Generate new authorization URL:**
   ```bash
   python auth/generate_auth_url.py
   ```

2. **Visit the URL** in your browser and authorize

3. **Copy the code** from the redirect URL:
   - You'll be redirected to: `https://createdbydata.com?code=NEW_CODE_HERE`
   - Copy the `code` value

4. **Update `.env`** with the new code:
   ```
   YAHOO_AUTHORIZATION_CODE=NEW_CODE_HERE
   ```

5. **Get new tokens:**
   ```bash
   python auth/initialize_tokens.py
   ```

6. **Update GitHub secret** with the new refresh token from `auth/tokens.json`

## Testing Your Setup

### Local Test (Already Working ✅)
```bash
python auth/test_token_refresh.py
```

### GitHub Actions Test
After adding the secrets:
1. Go to Actions tab
2. Run "Scheduled Data Refresh" workflow manually
3. Check the logs - it should successfully authenticate

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Bad credentials" in GitHub Actions | Check YAHOO_REFRESH_TOKEN secret is set correctly |
| "Token expired" after 6 months | Re-run OAuth flow (steps above) |
| "Invalid grant" error | The refresh token is invalid, re-run OAuth flow |
| Local works but GitHub fails | Ensure all 4 secrets are set in GitHub |

## Security Best Practices

1. **Never commit tokens** to your repository
2. **Use GitHub Secrets** for production deployments
3. **Rotate tokens** every 6 months proactively
4. **Keep `tokens.json`** in `.gitignore` (already done)

## Summary

✅ Your Yahoo OAuth is configured and working locally  
✅ You have a valid refresh token that successfully gets new access tokens  
📋 Just add the 4 secrets to GitHub as shown above  
🚀 Then your automated refreshes will work!