# PRD: Cloudflare Workers Deployment Guide for Fantasy Baseball Application

*Synced from Notion on 2025-08-04 23:01:27*

*Page ID: 2441a736-211e-81c1-b6b2-f8452537971e*

---

# Cloudflare Workers Deployment Guide for Fantasy Baseball Application

**Author:** Senior Product Manager

**Date:** August 3, 2025

**Status:** Draft

**Version:** 1.0

---

## Executive Summary

This guide provides a comprehensive deployment strategy for migrating the GKL Fantasy Baseball Analytics application from local development to production deployment on Cloudflare Workers. The deployment involves significant architectural changes to transform a traditional Node.js/Python application into a serverless architecture suitable for Cloudflare's edge computing platform.

## Current Architecture Analysis

### Backend Components

- **Node.js Express API Server** (port 3001)

### Frontend Components

- **React Application** (port 3000)

### Data Layer

- **SQLite Databases**

- **Python Data Collection Scripts**

## Cloudflare Workers Architecture Requirements

### Key Limitations to Address

1. **No Node.js Runtime**

1. **No File System Access**

1. **Request Duration Limits**

1. **Memory Constraints**

## Deployment Strategy

### Phase 1: Database Migration

### Option 1: Cloudflare D1 (Recommended)

```javascript
// wrangler.toml configuration
name = "gkl-fantasy-api"
main = "src/index.js"
compatibility_date = "2024-01-01"

[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "<your-database-id>"
```

**Migration Steps:**

1. Export SQLite data to SQL dump

1. Create D1 database via Wrangler CLI

1. Import data into D1

1. Update connection strings

### Option 2: External Database (Alternative)

- Planetscale (MySQL-compatible)

- Neon (Postgres-compatible)

- Turso (SQLite-compatible edge database)

### Phase 2: API Migration

### Transform Express Routes to Workers Format

**Before (Express):**

```javascript
app.get('/api/transactions', async (req, res) => {
  const { page, limit } = req.query;
  const transactions = await getTransactions(page, limit);
  res.json(transactions);
});
```

**After (Workers):**

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    if (url.pathname === '/api/transactions' && request.method === 'GET') {
      const page = url.searchParams.get('page') || 1;
      const limit = url.searchParams.get('limit') || 20;
      const transactions = await getTransactions(env.DB, page, limit);
      
      return new Response(JSON.stringify(transactions), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response('Not Found', { status: 404 });
  }
};
```

### Phase 3: Frontend Deployment

### Static Asset Configuration

```toml
# wrangler.toml
[site]
bucket = "./build"

[build]
command = "npm run build"
```

### Environment Variables

```javascript
// Use Cloudflare environment variables
const API_URL = env.API_URL || '[https://api.yourdomain.com](https://api.yourdomain.com/)';
```

### Phase 4: Python Scripts Migration

### Option 1: Cloudflare Cron Triggers

```toml
# wrangler.toml
[triggers]
crons = ["0 2 * * *"] # Run at 2 AM daily
```

### Option 2: External Scheduler

- GitHub Actions

- [Render.com](http://render.com/) cron jobs

- AWS Lambda with EventBridge

## Technical Requirements Document

### 1. Database Schema Modifications

```sql
-- Add edge-optimized indexes
CREATE INDEX idx_transactions_date_desc ON transactions(date DESC);
CREATE INDEX idx_lineups_composite ON daily_lineups(date, team_key, player_id);

-- Denormalize for performance
CREATE TABLE transaction_summaries AS
SELECT 
  DATE(date) as summary_date,
  COUNT(*) as transaction_count,
  COUNT(DISTINCT team_key) as active_teams
FROM transactions
GROUP BY DATE(date);
```

### 2. API Endpoint Refactoring

```javascript
// src/handlers/transactions.js
export async function handleTransactions(request, env) {
  const { searchParams } = new URL(request.url);
  
  const query = searchParams.get('q');
  const page = parseInt(searchParams.get('page') || '1');
  const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 100);
  
  const stmt = env.DB.prepare(`
    SELECT * FROM transactions
    WHERE player_name LIKE ?1
    ORDER BY date DESC
    LIMIT ?2 OFFSET ?3
  `);
  
  const results = await stmt.bind(
    `%${query || ''}%`,
    limit,
    (page - 1) * limit
  ).all();
  
  return new Response(JSON.stringify(results), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'max-age=60'
    }
  });
}
```

### 3. Frontend Build Optimization

```javascript
// webpack.config.js modifications
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        }
      }
    }
  },
  output: {
    filename: '[name].[contenthash].js',
    publicPath: '/'
  }
};
```

### 4. Environment Configuration

```javascript
// src/config.js
export const config = {
  development: {
    apiUrl: '[http://localhost:8787](http://localhost:8787/)',
    debug: true
  },
  production: {
    apiUrl: '[https://api.gkl-fantasy.com](https://api.gkl-fantasy.com/)',
    debug: false
  }
};
```

## Deployment Steps

### Prerequisites

1. Cloudflare account with Workers enabled

1. Wrangler CLI installed (`npm install -g wrangler`)

1. Domain configured in Cloudflare

1. GitHub repository connected

### Step-by-Step Deployment

### 1. Initialize Workers Project

```bash
wrangler init gkl-fantasy-workers
cd gkl-fantasy-workers
```

### 2. Configure wrangler.toml

```toml
name = "gkl-fantasy"
main = "src/index.js"
compatibility_date = "2024-01-01"
workers_dev = true

[env.production]
route = "[api.gkl-fantasy.com/*](http://api.gkl-fantasy.com/*)"

[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "<your-d1-database-id>"

[site]
bucket = "./dist"

[[kv_namespaces]]
binding = "CACHE"
id = "<your-kv-namespace-id>"
```

### 3. Create Database Migration Script

```javascript
// scripts/migrate-to-d1.js
import { readFileSync } from 'fs';
import { $ } from 'execa';

const sqlDump = readFileSync('./database/league_analytics.sql', 'utf8');
const statements = sqlDump.split(';').filter(s => s.trim());

for (const statement of statements) {
  await $`wrangler d1 execute gkl-fantasy --sql="${statement}"`;
}
```

### 4. Deploy API Worker

```bash
# Development
wrangler dev

# Production
wrangler publish --env production
```

### 5. Deploy Frontend Assets

```bash
# Build React app
cd web-ui/frontend
npm run build

# Deploy to Workers Sites
wrangler pages deploy build/
```

## Monitoring & Operations

### 1. Logging Configuration

```javascript
// Structured logging for Workers
export function log(level, message, data = {}) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    message,
    ...data
  }));
}
```

### 2. Error Handling

```javascript
export async function handleRequest(request, env) {
  try {
    return await router(request, env);
  } catch (error) {
    log('error', 'Request failed', { 
      error: error.message,
      stack: error.stack,
      url: request.url 
    });
    
    return new Response('Internal Server Error', { 
      status: 500 
    });
  }
}
```

### 3. Performance Monitoring

```javascript
// Track API performance
export async function trackPerformance(request, handler) {
  const start = [Date.now](http://date.now/)();
  const response = await handler(request);
  const duration = [Date.now](http://date.now/)() - start;
  
  // Log to Workers Analytics
  [request.cf](http://request.cf/).analyticsEngine?.writeDataPoint({
    blobs: [request.url],
    doubles: [duration],
    indexes: ['api-performance']
  });
  
  return response;
}
```

## Cost Optimization

### Workers Pricing Considerations

- **Free Tier**: 100,000 requests/day

- **Paid Tier**: $5/month + $0.50/million requests

- **D1 Database**: 5GB free, then $0.75/GB

### Optimization Strategies

1. **Cache Aggressively**

1. **Minimize Database Queries**

1. **Optimize Asset Delivery**

## Security Considerations

### 1. API Authentication

```javascript
// Implement JWT validation
export async function authenticate(request, env) {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '');
  
  if (!token) {
    return new Response('Unauthorized', { status: 401 });
  }
  
  try {
    const payload = await verifyJWT(token, env.JWT_SECRET);
    return { authenticated: true, user: payload };
  } catch {
    return new Response('Invalid token', { status: 401 });
  }
}
```

### 2. CORS Configuration

```javascript
const corsHeaders = {
  'Access-Control-Allow-Origin': env.FRONTEND_URL,
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization'
};
```

### 3. Rate Limiting

```javascript
// Use Cloudflare Rate Limiting or implement custom
export async function rateLimit(request, env) {
  const ip = request.headers.get('CF-Connecting-IP');
  const key = `rate-limit:${ip}`;
  
  const count = await env.CACHE.get(key) || 0;
  if (count > 100) {
    return new Response('Rate limit exceeded', { status: 429 });
  }
  
  await env.CACHE.put(key, count + 1, { expirationTtl: 3600 });
}
```

## Rollback Strategy

### Version Management

```bash
# Tag deployments
wrangler publish --env production --tag v1.0.0

# Rollback to previous version
wrangler rollback --env production --tag v0.9.0
```

### Database Backups

```bash
# Export D1 database
wrangler d1 export gkl-fantasy --output backup.sql

# Store in R2 bucket
wrangler r2 object put backups/$(date +%Y%m%d).sql --file backup.sql
```

## Success Metrics

### Performance Targets

- API Response Time: < 200ms (p95)

- Frontend Load Time: < 2s (p90)

- Database Query Time: < 50ms (p95)

- Uptime: 99.9%

### Monitoring Dashboard

- Cloudflare Analytics

- Custom Workers Analytics

- Error rate tracking

- User engagement metrics

## Next Steps

1. **Immediate Actions**

1. **Week 1-2: Core Migration**

1. **Week 3-4: Frontend & Integration**

1. **Week 5-6: Optimization & Launch**

---

*This deployment guide provides a comprehensive roadmap for migrating the GKL Fantasy Baseball application to Cloudflare Workers. Regular updates to this document should reflect implementation progress and lessons learned.*
