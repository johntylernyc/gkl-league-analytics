# 🔴 CRITICAL SECURITY ACTION PLAN

## Immediate Actions (Do RIGHT NOW)

### 1. Remove Exposed Files from Git
```bash
# Run this immediately
remove_exposed_secrets.bat

# Then commit and push
git add .gitignore
git commit -m "SECURITY: Remove exposed credentials and update gitignore"
git push origin main
```

### 2. Invalidate Exposed Credentials

#### Yahoo OAuth App
1. Go to: https://developer.yahoo.com/apps/
2. Find your current app
3. **Create a NEW app first** (so you have new credentials ready)
   - App Name: GKL Fantasy Analytics (NEW)
   - Description: Fantasy baseball analytics
   - Redirect URI: https://localhost:8080 (or your preferred)
   - API Permissions: Fantasy Sports
4. **Copy the new credentials** (keep them safe, don't put in any file yet)
5. **Delete the OLD app** to invalidate exposed credentials

### 3. Clean Git History

Since secrets are already pushed, they're in Git history. You need to clean them:

```bash
# Option 1: If repo is PRIVATE and you're the only user
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch deployment/YAHOO_OAUTH_SETUP.md deployment/setup_github_secrets.md deployment/yahoo_oauth_secrets_guide.md" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

```bash
# Option 2: Nuclear option - create new repo
# - Create new private repo
# - Copy code WITHOUT deployment folder
# - Start fresh with clean history
```

## After Emergency Actions

### 4. Set Up New Credentials Safely

#### Update Local .env
```env
# .env file (NEVER COMMIT THIS)
YAHOO_CLIENT_ID=your_new_client_id_here
YAHOO_CLIENT_SECRET=your_new_client_secret_here
YAHOO_REDIRECT_URI=https://localhost:8080
```

#### Re-run OAuth Flow
```bash
# 1. Generate new auth URL with NEW credentials
python auth/generate_auth_url.py

# 2. Visit URL, authorize

# 3. Get code from redirect URL

# 4. Update .env with authorization code
# YAHOO_AUTHORIZATION_CODE=new_code_here

# 5. Get new tokens
python auth/initialize_tokens.py

# 6. Test it works
python auth/test_token_refresh.py
```

### 5. Update GitHub Secrets

1. Go to GitHub → Settings → Secrets → Actions
2. **Delete** all old Yahoo secrets
3. **Add** new secrets with NEW credentials:
   - YAHOO_CLIENT_ID (new)
   - YAHOO_CLIENT_SECRET (new)
   - YAHOO_REDIRECT_URI
   - YAHOO_REFRESH_TOKEN (from new tokens.json)

## Prevention Checklist

### Files That Should NEVER Be Committed:
- ❌ `.env` files
- ❌ `tokens.json`
- ❌ Any file with actual API keys
- ❌ Any file with real OAuth tokens
- ❌ Documentation with real credentials

### Safe Practices:
- ✅ Use placeholders in docs: `YOUR_CLIENT_ID`
- ✅ Store secrets only in: `.env` (local) and GitHub Secrets (CI/CD)
- ✅ Always check `git status` before committing
- ✅ Review files before pushing
- ✅ Keep `.gitignore` updated

## Monitoring

### Check for Unauthorized Access:
1. Yahoo Developer Console → Your App → Usage Statistics
2. Look for unexpected API calls
3. Check if anyone forked your repo while secrets were exposed

### Search Your Repo:
```bash
# Make sure no secrets remain
git grep -i "client_secret"
git grep -i "refresh_token" 
git grep -i "access_token"
git grep "client_id"    # Search for client ID
git grep "client_secret" # Search for client secret  
git grep "refresh_token" # Search for refresh token
```

## Timeline

- **0-5 minutes**: Remove files, update .gitignore, push
- **5-15 minutes**: Create new Yahoo app, get new credentials
- **15-30 minutes**: Clean git history
- **30-45 minutes**: Update local environment with new credentials
- **45-60 minutes**: Update GitHub Secrets, test everything works

## If Repository Was Public

If your repository was/is public:
1. **Assume credentials are compromised**
2. **Rotate immediately** (already doing this)
3. **Monitor for abuse** in Yahoo Developer Console
4. **Consider** contacting GitHub Support about removing cached views
5. **Check** if repo was forked while secrets were exposed

## Lessons Learned

1. **Never** put real credentials in markdown files
2. **Always** use template files with placeholders
3. **Review** every file before committing
4. **Test** .gitignore is working: `git status`
5. **Use** secret scanning tools before pushing

## Final Verification

After completing all steps:
```bash
# Verify no secrets in current files
git grep -i secret
git grep -i token
git grep -i "client_"

# Verify .gitignore is working
touch deployment/test_SETUP.md
git status  # Should NOT show the file

# Test new credentials work
python auth/test_token_refresh.py
```

## Need Help?

- GitHub's guide on removing sensitive data: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- Yahoo Developer Support: https://developer.yahoo.com/support/
- BFG Repo-Cleaner: https://rtyley.github.io/bfg-repo-cleaner/