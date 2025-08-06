# How to Enable and Test GitHub Actions

## Step 1: Commit the Workflow File

First, make sure the workflow file is committed to your repository:

```bash
# Check git status
git status

# If .github/workflows/data-refresh.yml is untracked or modified:
git add .github/workflows/data-refresh.yml
git commit -m "Add automated data refresh workflow"
git push origin main
```

## Step 2: Enable GitHub Actions

GitHub Actions should be enabled by default, but let's verify:

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/gkl-league-analytics`
2. Click on **Settings** tab (same place where you added secrets)
3. In the left sidebar, scroll down to **Actions** → **General**
4. Make sure **Actions permissions** is set to:
   - ✅ **Allow all actions and reusable workflows**
   - OR at minimum: **Allow YOUR_USERNAME actions and reusable workflows**
5. Click **Save** if you made any changes

## Step 3: Navigate to Actions Tab

1. Go back to your repository main page
2. Click on the **Actions** tab (should be between "Pull requests" and "Projects")
3. If this is your first time:
   - You might see "Get started with GitHub Actions"
   - Click **Skip this and set up a workflow yourself** (if shown)
   - OR you should see your workflow listed

## Step 4: Find Your Workflow

After the workflow file is pushed and Actions is enabled:

1. In the Actions tab, look at the left sidebar
2. You should see **"Scheduled Data Refresh"** listed under "All workflows"
3. Click on **"Scheduled Data Refresh"**

## Step 5: Run the Workflow Manually

1. On the workflow page, you'll see a blue banner or button: **"Run workflow"**
2. Click **Run workflow**
3. A dropdown will appear with options:
   - **Use workflow from**: Select `main` (or your default branch)
   - **Type of refresh**: Select `manual`
   - **Environment**: Select `test`
   - **Date range**: Enter `2025-08-01,2025-08-04` (or leave blank for defaults)
4. Click the green **Run workflow** button

## Step 6: Monitor the Run

1. After clicking Run workflow, refresh the page
2. You should see a new workflow run starting (yellow circle spinning)
3. Click on the workflow run to see details
4. You'll see jobs:
   - `Determine Refresh Parameters`
   - `Refresh Transactions`
   - `Refresh Daily Lineups`
   - `Refresh Player Stats`
   - `Send Notifications`

## What If You Don't See the Actions Tab?

If there's no Actions tab:

### Option A: Actions is Disabled at Repository Level
1. Go to Settings → Actions → General
2. Under "Actions permissions", select **Allow all actions**
3. Click Save
4. Go back to main repo page - Actions tab should appear

### Option B: Actions is Disabled at Organization Level
If this repo is in an organization:
1. Check organization settings
2. Or create a personal fork to test

### Option C: The Workflow File Isn't Pushed
1. Make sure you've committed and pushed the workflow file:
   ```bash
   git add .github/workflows/data-refresh.yml
   git commit -m "Add GitHub Actions workflow"
   git push
   ```

## Troubleshooting

### "Workflow not found" Error
- Make sure the file is named exactly: `.github/workflows/data-refresh.yml`
- Ensure it's in the default branch (usually `main` or `master`)
- Check that the YAML syntax is valid

### "Bad credentials" Error
- Your YAHOO_REFRESH_TOKEN secret might be wrong
- Double-check all 4 secrets are set correctly
- Make sure you used YAHOO_REFRESH_TOKEN, not YAHOO_AUTHORIZATION_CODE

### Workflow Doesn't Appear
- The workflow file must be in the default branch
- Try refreshing the page or clearing browser cache
- Check that the file has `.yml` extension (not `.yaml`)

## Quick Test Script

Run this locally to verify your setup before GitHub:

```bash
# Test that your tokens work
python auth/test_token_refresh.py

# Test the incremental update scripts
python league_transactions/incremental_update.py --start-date 2025-08-03 --end-date 2025-08-04 --environment test
```

## Success Indicators

When it works, you'll see:
1. ✅ Green checkmarks next to each job
2. Logs showing data being processed
3. Database updates (if you download artifacts)
4. Completion notification (if configured)

## Next Steps

Once the manual test works:
1. The scheduled runs will happen automatically (6 AM, 1 PM, 10 PM ET)
2. Proceed with CloudFlare Worker setup for redundancy
3. Monitor the first few scheduled runs