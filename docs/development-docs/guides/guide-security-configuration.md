# Security Setup Guide

## Overview
This project uses sensitive configurations that must be properly secured before deployment.

## Required Environment Variables

### Yahoo Fantasy API (.env file in project root)
```
YAHOO_CLIENT_ID=your_yahoo_client_id
YAHOO_CLIENT_SECRET=your_yahoo_client_secret
YAHOO_AUTHORIZATION_CODE=your_auth_code
YAHOO_REDIRECT_URI=https://yourdomain.com
```

### CloudFlare Workers Setup

1. **Copy Configuration Template**
   ```bash
   cp cloudflare-deployment/wrangler.toml.example cloudflare-deployment/wrangler.toml
   ```

2. **Update wrangler.toml with your values:**
   - Replace `YOUR_D1_DATABASE_ID` with your CloudFlare D1 database ID
   - Replace `YOUR_KV_NAMESPACE_ID` with your KV namespace ID
   - Update domain routes to match your domain

3. **Get CloudFlare Resource IDs:**
   ```bash
   # List D1 databases
   wrangler d1 list
   
   # List KV namespaces
   wrangler kv:namespace list
   ```

## Security Checklist

- [ ] Environment variables configured in `.env` file
- [ ] `wrangler.toml` copied from example and configured
- [ ] OAuth tokens regenerated (if `auth/tokens.json` was previously committed)
- [ ] No sensitive data committed to git repository
- [ ] CloudFlare wrangler.toml excluded from git tracking

## OAuth Token Security

If `auth/tokens.json` was previously committed:
1. Revoke current tokens in Yahoo Developer Console
2. Generate new OAuth authorization code
3. Update environment variables
4. Run token initialization script

## File Permissions

Ensure these files have restricted permissions:
- `.env` (readable only by owner)
- `auth/tokens.json` (readable only by owner)
- `cloudflare-deployment/wrangler.toml` (readable only by owner)

## Production Deployment

Never commit the following to version control:
- Actual database IDs
- KV namespace IDs  
- OAuth tokens or secrets
- API keys or credentials
- Production configuration files