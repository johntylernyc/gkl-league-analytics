# Safe Credential Setup Guide

## Where Credentials Should Be Stored

### ✅ ONLY Store Credentials In These Two Places:

1. **Local Development**: `.env` file (never committed)
2. **GitHub Actions**: Repository Secrets (encrypted by GitHub)

### ❌ NEVER Store Credentials In:
- Any `.md` files
- Any documentation
- Any code files
- Any configuration files that get committed
- Any examples or templates

## Setting Up Credentials Safely

### Step 1: Create Yahoo App

1. Go to https://developer.yahoo.com/apps/
2. Create a new app
3. Note down your credentials (don't paste them anywhere yet)

### Step 2: Local Setup (.env file)

Create or update `.env` in your project root:

```env
# .env - This file is gitignored and safe for secrets
YAHOO_CLIENT_ID=paste_your_client_id_here
YAHOO_CLIENT_SECRET=paste_your_client_secret_here  
YAHOO_REDIRECT_URI=https://localhost:8080
```

**IMPORTANT**: 
- This file should NEVER be committed
- Verify it's in `.gitignore` (it already is)
- This is the ONLY place to store credentials locally

### Step 3: Generate OAuth Tokens

```bash
# 1. Generate authorization URL
python auth/generate_auth_url.py

# 2. Visit the URL and authorize

# 3. Copy the code from redirect URL

# 4. Temporarily add to .env:
# YAHOO_AUTHORIZATION_CODE=code_from_redirect

# 5. Exchange for tokens
python auth/initialize_tokens.py

# 6. Remove the authorization code from .env (it's one-time use)
```

This creates `auth/tokens.json` with your refresh token.

### Step 4: GitHub Secrets Setup

1. Go to your GitHub repository
2. Navigate to: Settings → Secrets and variables → Actions
3. Add these secrets:

| Secret Name | Value Source |
|------------|--------------|
| `YAHOO_CLIENT_ID` | From your Yahoo app |
| `YAHOO_CLIENT_SECRET` | From your Yahoo app |
| `YAHOO_REDIRECT_URI` | Your redirect URI |
| `YAHOO_REFRESH_TOKEN` | From `auth/tokens.json` line 3 |

**NEVER** paste the actual values in any documentation!

## Verifying Your Setup

### Test Locally
```bash
python auth/test_token_refresh.py
```

### Test GitHub Actions
1. Commit your code (WITHOUT any secrets)
2. Push to GitHub
3. Go to Actions tab
4. Run workflow manually

## Security Checklist

Before every commit:
- [ ] No actual credentials in any files
- [ ] `.env` is NOT being committed
- [ ] `tokens.json` is NOT being committed  
- [ ] Documentation uses placeholders only
- [ ] Run `git status` to verify

## If You Make a Mistake

If you accidentally commit credentials:
1. Remove the file immediately
2. Rotate credentials (create new Yahoo app)
3. Clean git history
4. Update `.env` and GitHub Secrets with new credentials

## Quick Reference

### Safe Example (Use This)
```markdown
Set YAHOO_CLIENT_ID to your client ID from Yahoo
```

### Unsafe Example (Never Do This)
```markdown
Set YAHOO_CLIENT_ID to dj0yJmk9TUVs... [NEVER PUT REAL VALUES]
```

## Remember

- **Local secrets**: Only in `.env`
- **CI/CD secrets**: Only in GitHub Secrets
- **Documentation**: Only placeholders
- **Commits**: Never include secrets
- **Reviews**: Always check before pushing