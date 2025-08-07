# CloudFlare Secrets Setup

## 🎯 Problem Solved

Your GitHub Actions were updating a temporary database, but your website at https://goldenknightlounge.com uses CloudFlare D1 database. Now GitHub Actions will sync data to CloudFlare D1 automatically!

## 🔑 Required GitHub Secrets

You need to add 2 more secrets to your GitHub repository:

### 1. Get CloudFlare Account ID

1. Go to https://dash.cloudflare.com/
2. Login to your CloudFlare account
3. On the right sidebar, you'll see your **Account ID**
4. Copy this ID (looks like: `a1b2c3d4e5f6...`)

### 2. Get CloudFlare API Token

1. In CloudFlare Dashboard, click your profile icon (top right)
2. Click **"My Profile"**
3. Go to **"API Tokens"** tab
4. Click **"Create Token"**
5. Use **"Custom token"** template
6. Set these permissions:
   - **Account**: `Cloudflare D1:Edit`
   - **Zone Resources**: `Include - All zones`
7. Click **"Continue to summary"**
8. Click **"Create Token"**
9. **Copy the token** (you won't see it again!)

### 3. Add Secrets to GitHub

Go to your GitHub repository:
1. **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"**

Add these 2 secrets:

#### CLOUDFLARE_ACCOUNT_ID
- **Name**: `CLOUDFLARE_ACCOUNT_ID`
- **Value**: Your account ID from step 1

#### CLOUDFLARE_API_TOKEN  
- **Name**: `CLOUDFLARE_API_TOKEN`
- **Value**: Your API token from step 2

## ✅ What This Enables

After adding these secrets:
1. **GitHub Actions** will collect data from Yahoo API
2. **Export script** will generate SQL with recent changes
3. **Wrangler CLI** will push changes to CloudFlare D1
4. **Your website** will show updated data immediately

## 🧪 Test the Full Pipeline

After adding the secrets:
1. Run another **production test** in GitHub Actions
2. This time you should see a new job: **"Sync to CloudFlare D1"**
3. After it completes, check https://goldenknightlounge.com
4. You should see the updated data!

## 🚀 Automatic Updates

Once working, your website will update automatically:
- **6:00 AM ET**: Full data refresh
- **1:00 PM ET**: Incremental updates  
- **10:00 PM ET**: Incremental updates

Data flows: **Yahoo API** → **GitHub Actions** → **CloudFlare D1** → **Your Website**

## 🔍 Troubleshooting

### If CloudFlare sync fails:
- Check your API token has D1 edit permissions
- Verify the account ID is correct
- Ensure your D1 database is named `fantasy-baseball-db`

### If data still doesn't appear:
- Check CloudFlare D1 console to verify data was inserted
- Clear your browser cache
- Check website logs for database connection issues

This will connect your automated data collection to your live website! 🎉