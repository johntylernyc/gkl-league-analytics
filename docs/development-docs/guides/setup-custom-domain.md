# Setting Up Custom Domain for GKL Fantasy Baseball

## Configure via Cloudflare Dashboard

### 1. Frontend - Cloudflare Pages
1. Go to https://dash.cloudflare.com
2. Navigate to **Pages** → **gkl-fantasy-frontend**
3. Click **Custom domains** tab
4. Click **Set up a custom domain**
5. Enter `goldenknightlounge.com` (for root) or `www.goldenknightlounge.com`
6. Cloudflare will automatically add the DNS records

### 2. API - Cloudflare Workers
1. In Cloudflare Dashboard, go to **Workers & Pages**
2. Select your worker **gkl-fantasy-api**
3. Go to **Settings** → **Triggers**
4. Add a custom domain:
   - Click **Add Custom Domain**
   - Enter `api.goldenknightlounge.com`
   - Save

### 3. Update wrangler.toml for Workers
Add the route to your worker configuration:

```toml
routes = [
  { pattern = "api.goldenknightlounge.com/*", zone_name = "goldenknightlounge.com" }
]
```

Then redeploy:
```bash
cd cloudflare-deployment
wrangler deploy
```

### 4. Update Frontend API Endpoint
The frontend needs to know about the new API domain:

```bash
cd web-ui/frontend
# Update .env.production
echo "REACT_APP_API_URL=https://api.goldenknightlounge.com" > .env.production

# Rebuild and deploy
npm run build
wrangler pages deploy build --project-name gkl-fantasy-frontend
```

## DNS Configuration (Automatic)
Cloudflare will automatically configure these DNS records:
- `A` record for `goldenknightlounge.com` → Cloudflare Pages
- `CNAME` record for `www` → goldenknightlounge.com
- `CNAME` record for `api` → Your Workers deployment

## Verify Setup
After configuration:
1. Frontend: https://goldenknightlounge.com
2. API: https://api.goldenknightlounge.com
3. Test API: https://api.goldenknightlounge.com/api/transactions

## SSL/TLS
SSL certificates are automatically provisioned by Cloudflare - no action needed!