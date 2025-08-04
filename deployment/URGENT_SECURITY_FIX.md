# 🚨 URGENT: Security Fix Required

## Exposed Secrets in Repository

The following files contain sensitive information and need immediate action:

### Files with Exposed Secrets:
- `deployment/YAHOO_OAUTH_SETUP.md` - Contains actual OAuth tokens
- `deployment/setup_github_secrets.md` - Contains client ID and secret
- Any other deployment guides with real credentials

## Immediate Actions Required

### Step 1: Remove Sensitive Files from Repository (Do This First!)

```bash
# Remove files with secrets from the repository
git rm deployment/YAHOO_OAUTH_SETUP.md
git rm deployment/setup_github_secrets.md
git rm deployment/yahoo_oauth_secrets_guide.md

# Commit the removal
git commit -m "Remove files containing sensitive credentials"
git push origin main
```

### Step 2: Rotate Yahoo OAuth Credentials

Since your credentials are exposed, you need to:

1. **Go to Yahoo Developer Console**: https://developer.yahoo.com/apps/
2. **Find your app** (or create a new one if needed)
3. **Generate new credentials**:
   - Get new Client ID
   - Get new Client Secret
   - Update redirect URI if needed
4. **Delete the old app** to invalidate the exposed credentials

### Step 3: Update .gitignore

```bash
# Add these lines to .gitignore
echo "# Security - Never commit credentials" >> .gitignore
echo "deployment/*_SETUP.md" >> .gitignore
echo "deployment/*_secrets*.md" >> .gitignore
echo "auth/tokens.json" >> .gitignore
echo "*.env" >> .gitignore
echo ".env.*" >> .gitignore
echo "**/tokens.json" >> .gitignore
echo "**/*secret*" >> .gitignore
echo "**/*credential*" >> .gitignore

# Commit the updated .gitignore
git add .gitignore
git commit -m "Update .gitignore to prevent credential exposure"
git push origin main
```

### Step 4: Clean Git History (Nuclear Option)

Since the secrets are in git history, you need to remove them completely:

#### Option A: Using BFG Repo-Cleaner (Easier)
```bash
# Download BFG from https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files YAHOO_OAUTH_SETUP.md
java -jar bfg.jar --delete-files setup_github_secrets.md
git push --force
```

#### Option B: Using git filter-branch (Built-in)
```bash
# Remove files from all history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch deployment/YAHOO_OAUTH_SETUP.md deployment/setup_github_secrets.md" \
  --prune-empty --tag-name-filter cat -- --all

# Force push the cleaned history
git push origin --force --all
git push origin --force --tags
```

### Step 5: Create New Secure Documentation

After rotating credentials, create new documentation WITHOUT actual secrets:

```bash
# Create secure templates
echo "Use placeholders like YOUR_CLIENT_ID instead of actual values" > deployment/README_SECURITY.md
```

## After Fixing

### 1. New OAuth Setup Process
- Create new Yahoo app
- Generate new credentials
- Store them ONLY in:
  - Local `.env` file (never commit)
  - GitHub Secrets (secure)
  
### 2. Update GitHub Secrets
- Delete old secrets
- Add new secrets with rotated credentials

### 3. Update Local Environment
- Update `.env` with new credentials
- Delete old `tokens.json`
- Re-run OAuth flow with new credentials

## Prevention for Future

### Never Commit:
- Actual API keys
- OAuth tokens  
- Client secrets
- Refresh tokens
- Any real credentials

### Always Use:
- Placeholders in documentation (YOUR_CLIENT_ID)
- Environment variables
- GitHub Secrets for CI/CD
- `.gitignore` for sensitive files

## Check What's Exposed

```bash
# Search for exposed secrets in your repo
git grep -i "client_secret"
git grep -i "refresh_token"
git grep -i "access_token"
git grep "YOUR_CLIENT"  # Search for client ID patterns
git grep "YOUR_TOKEN"  # Search for token patterns
```

## Contact GitHub Support

If the repository was public, consider:
1. Contact GitHub Support to purge cached views
2. Check if the repo was forked (exposed secrets might be in forks)
3. Monitor for unauthorized use of your Yahoo API

## Timeline

1. **NOW**: Remove files and push changes
2. **IMMEDIATELY AFTER**: Rotate Yahoo credentials  
3. **WITHIN 1 HOUR**: Clean git history
4. **TODAY**: Update all documentation with placeholders
5. **ONGOING**: Monitor for any unauthorized API usage