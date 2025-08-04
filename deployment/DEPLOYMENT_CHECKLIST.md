# 🚀 Deployment Checklist

Follow this checklist to deploy the automated data refresh system.

## Phase 1: GitHub Setup (15 minutes)

### 1.1 Add GitHub Secrets
Go to: **Settings** → **Secrets and variables** → **Actions**

- [x] Add `YAHOO_CLIENT_ID`
- [x] Add `YAHOO_CLIENT_SECRET`
- [x] Add `YAHOO_REDIRECT_URI`
- [x] Add `YAHOO_AUTHORIZATION_CODE`
- [-] (Optional) Add `SLACK_WEBHOOK_URL`
- [-] (Optional) Add `DISCORD_WEBHOOK_URL`

### 1.2 Test GitHub Actions
- [ ] Go to Actions tab
- [ ] Run "Scheduled Data Refresh" workflow manually
- [ ] Verify all jobs complete (green checkmarks)

**✅ Checkpoint:** GitHub Actions runs successfully

---

## Phase 2: CloudFlare Setup (20 minutes)

### 2.1 Prerequisites
- [ ] Install Wrangler: `npm install -g wrangler`
- [ ] Get CloudFlare Account ID from dashboard
- [ ] Create GitHub Personal Access Token with `workflow` scope

### 2.2 Configure Files
- [ ] Update `cloudflare/wrangler.toml` with your Account ID
- [ ] Update `cloudflare/worker.js` with your GitHub username

### 2.3 Deploy Worker
```bash
cd cloudflare
```
- [ ] Login: `wrangler login`
- [ ] Deploy: `wrangler deploy`
- [ ] Note your worker URL: `https://gkl-fantasy-analytics._______.workers.dev`

### 2.4 Set CloudFlare Secrets
- [ ] Set GitHub token: `wrangler secret put GITHUB_TOKEN`
- [ ] Set auth token: `wrangler secret put AUTH_TOKEN` (generate random string)
- [ ] Verify: `wrangler secret list`

**✅ Checkpoint:** Worker deployed and secrets configured

---

## Phase 3: Integration Testing (10 minutes)

### 3.1 Test Worker Health
- [ ] Test health endpoint:
```bash
curl https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/health
```

### 3.2 Test Manual Trigger
- [ ] Trigger workflow from CloudFlare:
```bash
curl -X POST https://gkl-fantasy-analytics.YOUR-SUBDOMAIN.workers.dev/trigger \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshType": "manual"}'
```
- [ ] Verify new workflow appears in GitHub Actions

### 3.3 Verify Scheduled Triggers
- [ ] Check CloudFlare Dashboard → Workers → Triggers
- [ ] Confirm 3 cron schedules are active

**✅ Checkpoint:** CloudFlare successfully triggers GitHub Actions

---

## Phase 4: Data Verification (5 minutes)

### 4.1 Check Database Updates
- [ ] Run test script to verify job logs:
```bash
python deployment/verify_deployment.py
```

### 4.2 Monitor First Scheduled Run
- [ ] Note next scheduled time (6 AM, 1 PM, or 10 PM ET)
- [ ] Start log monitoring: `wrangler tail`
- [ ] Verify trigger executes at scheduled time

**✅ Checkpoint:** Data updates successfully

---

## Phase 5: Production Readiness (Optional)

### 5.1 Notifications
- [ ] Test Slack webhook (if configured)
- [ ] Test Discord webhook (if configured)

### 5.2 Monitoring
- [ ] Set up uptime monitoring for worker health endpoint
- [ ] Create dashboard for job success metrics
- [ ] Configure alerts for failures

### 5.3 Documentation
- [ ] Document your specific configuration
- [ ] Share worker URL with team
- [ ] Create runbook for troubleshooting

---

## 🎉 Deployment Complete!

### Your Endpoints
- **Worker URL:** `https://gkl-fantasy-analytics._______.workers.dev`
- **Health Check:** `/health`
- **Status Check:** `/status`
- **Manual Trigger:** `/trigger` (requires auth)

### Schedule (ET)
- **6:00 AM** - Full refresh (7-day lookback)
- **1:00 PM** - Incremental (3-day lookback)
- **10:00 PM** - Incremental (3-day lookback)

### Monitoring Commands
```bash
# Watch CloudFlare logs
wrangler tail

# Check GitHub workflows
gh run list --workflow=data-refresh.yml

# View recent database jobs
python deployment/check_jobs.py
```

### Quick Actions
```bash
# Trigger manual refresh
curl -X POST YOUR_WORKER_URL/trigger \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refreshType": "manual"}'

# Check system health
curl YOUR_WORKER_URL/health

# View workflow status
curl YOUR_WORKER_URL/status
```

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| GitHub Action fails | Check secrets in Settings → Secrets |
| Worker won't deploy | Verify account ID and login with `wrangler login` |
| Manual trigger 401 | Set AUTH_TOKEN secret in CloudFlare |
| No scheduled runs | Check CloudFlare Dashboard → Triggers |
| Data not updating | Verify Yahoo OAuth tokens are valid |

---

## Time Estimate

- **Total Setup Time:** ~50 minutes
- **GitHub Setup:** 15 minutes
- **CloudFlare Setup:** 20 minutes
- **Testing:** 10 minutes
- **Verification:** 5 minutes

## Support Files

- `deployment/setup_github_secrets.md` - Detailed GitHub setup
- `deployment/setup_cloudflare.md` - Detailed CloudFlare setup
- `deployment/test_deployment.md` - Comprehensive testing guide
- `cloudflare/README.md` - CloudFlare Worker documentation