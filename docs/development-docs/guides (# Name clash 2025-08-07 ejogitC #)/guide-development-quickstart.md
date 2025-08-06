# 🚀 Quick Start - Enable GitHub Actions

## Your Current Status
✅ GitHub Secrets are configured  
❌ GitHub Actions workflow not yet committed  

## Next Steps (5 minutes)

### 1. Commit the Workflow File

Run this in your terminal:

```bash
# Option A: Use the batch script (Windows)
deployment\commit_deployment_files.bat

# Option B: Manual commands
git add .github/workflows/data-refresh.yml
git commit -m "Add automated data refresh workflow"
git push origin main
```

### 2. Check GitHub Actions

After pushing:
1. Go to your repository on GitHub
2. You should now see an **Actions** tab
3. Click on **Actions**
4. You should see "Scheduled Data Refresh" in the left sidebar

### 3. Run Your First Test

1. Click on **"Scheduled Data Refresh"**
2. Click **"Run workflow"** button
3. Select:
   - Branch: `main`
   - Refresh type: `manual`
   - Environment: `test`
4. Click green **"Run workflow"** button

### 4. Watch It Run

1. Refresh the page
2. Click on the new workflow run
3. Watch the jobs execute
4. All should show green checkmarks ✅

## If Actions Tab Doesn't Appear

Go to: **Settings** → **Actions** → **General**
- Set **Actions permissions** to "Allow all actions"
- Save
- Refresh the page

## What You'll See When It Works

```
✅ Determine Refresh Parameters (10 seconds)
✅ Refresh Transactions (30 seconds)  
✅ Refresh Daily Lineups (30 seconds)
✅ Refresh Player Stats (30 seconds)
✅ Send Notifications (5 seconds)
```

## Troubleshooting

### No Actions Tab?
- The workflow file must be committed and pushed first
- Actions must be enabled in Settings

### Workflow Fails?
- Check the logs - click on the failed job
- Most likely issue: Wrong YAHOO_REFRESH_TOKEN
- Verify your secrets are set correctly

### "Waiting for a runner"?
- This is normal - GitHub is allocating resources
- Usually takes 10-30 seconds

## Quick Test Before GitHub

Test locally first:
```bash
python auth/test_token_refresh.py
```

If this works, GitHub Actions should work too!

## Success! 🎉

Once the workflow runs successfully:
- Scheduled runs will happen automatically at 6 AM, 1 PM, and 10 PM ET
- You can proceed with CloudFlare setup for extra reliability
- Monitor the first few scheduled runs to ensure stability

## Need Help?

Check the detailed guides:
- `deployment/enable_github_actions.md` - Full GitHub Actions setup
- `deployment/YAHOO_OAUTH_SETUP.md` - OAuth troubleshooting
- `deployment/test_deployment.md` - Complete testing guide