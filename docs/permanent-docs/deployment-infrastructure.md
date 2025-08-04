# Deployment Infrastructure

## Overview

The GKL League Analytics deployment infrastructure leverages Cloudflare's edge computing platform for global distribution, automatic scaling, and high availability. The system employs a multi-environment strategy with automated deployment pipelines.

## Deployment Architecture

### Environment Structure

#### Production Environment
- **URL**: https://goldenknightlounge.com
- **API**: https://api.goldenknightlounge.com
- **Infrastructure**: Cloudflare Workers + Pages
- **Database**: Cloudflare D1
- **Cache**: Cloudflare KV

#### Development Environment
- **Local Frontend**: http://localhost:3000
- **Local Backend API**: http://localhost:3001/api
- **Database**: Local SQLite (database/league_analytics.db)
- **Hot Reload**: Enabled for rapid development
- **Environment Config**: `.env.local` for frontend, `.env` for backend

### Cloudflare Infrastructure Components

#### 1. Cloudflare Workers (`cloudflare-production/`)

**Production API Worker**
```toml
name = "gkl-fantasy-api-prod"
main = "src/index-with-db.js"
compatibility_date = "2024-01-02"
compatibility_flags = ["nodejs_compat"]

[[d1_databases]]
binding = "DB"
database_name = "gkl-fantasy"
database_id = "f541fa7b-9356-4a96-a24e-3b7cd06e9cfa"

[[kv_namespaces]]
binding = "CACHE"
id = "27f3df3708b84a6f8d57a0753057ef9f"
```

**Worker Capabilities:**
- Request routing and handling
- Database query execution
- Response caching
- CORS management
- Error handling

#### 2. Cloudflare Pages

**Frontend Hosting**
- Automatic deployments from Git
- Global CDN distribution
- SSL/TLS certificates
- Custom domain support
- Preview deployments for branches

**Deployment Configuration:**
```yaml
Build Settings:
  Framework: Create React App
  Build Command: npm run build
  Output Directory: build
  Node Version: 18.x
```

#### 3. Cloudflare D1 Database

**Production Database**
- Globally distributed SQLite
- Automatic replication
- Point-in-time recovery
- SQL console access
- Export/Import capabilities

**Database Management:**
```bash
# Create database
wrangler d1 create gkl-fantasy

# Execute migrations
wrangler d1 execute gkl-fantasy --file schema.sql

# Import data
wrangler d1 execute gkl-fantasy --file data.sql
```

#### 4. Cloudflare KV Storage

**Caching Layer**
- Key-value storage
- Global replication
- TTL support
- Atomic operations
- 25 MB value size limit

**Usage Patterns:**
- API response caching
- Session storage
- Configuration management
- Rate limiting counters

### Scheduled Workers (`cloudflare-scheduled-worker/`)

**Data Refresh Scheduler**
```javascript
Schedule Configuration:
- 6:00 AM ET: Full refresh (7-day lookback)
- 1:00 PM ET: Incremental update (3-day lookback)
- 10:00 PM ET: Final daily update (3-day lookback)
```

**Trigger Mechanism:**
1. Cron trigger activates worker
2. Worker calls GitHub Actions API
3. GitHub Actions runs data collection
4. Data syncs to production database

## Deployment Pipeline

### 1. Local Development

**Environment Setup:**
```bash
# Configure frontend to use local API
cd web-ui/frontend
cp .env.example .env.local
# Edit .env.local: REACT_APP_API_URL=http://localhost:3001/api
```

**Development Workflow:**
```bash
# Start backend server (port 3001)
cd web-ui/backend
npm install
npm start

# Start frontend development (port 3000)
cd web-ui/frontend
npm install
npm start

# Run data pipeline to update local database
cd data_pipeline
python league_transactions/backfill_transactions_optimized.py
python daily_lineups/collector.py
```

**Local to Production Sync:**
```bash
# Export recent data from local database with foreign key dependencies
python scripts/sync_to_production.py

# Import to Cloudflare D1 - ORDER IS CRITICAL!
cd cloudflare-production

# 1. Import job_log entries FIRST (foreign key dependencies)
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/job_logs_*.sql --remote

# 2. Import transactions (independent table)
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/transactions_*.sql --remote

# 3. Import lineups (depends on job_log)
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/lineups_*.sql --remote
```

**Foreign Key Management:**
- The sync script automatically extracts referenced job_ids
- Creates job_log export with all required entries
- Provides commands in correct dependency order
- Failure to follow order results in FOREIGN KEY constraint errors

### 2. Build Process

**Frontend Build:**
```bash
cd web-ui/frontend
npm run build
# Output: build/ directory with optimized assets
```

**Worker Build:**
```bash
cd cloudflare-production
npm run build
# Bundles worker code with dependencies
```

### 3. Deployment Process

#### Manual Deployment

**Frontend Deployment:**
```bash
cd web-ui/frontend/build
wrangler pages deploy . --project-name gkl-fantasy-frontend
```

**API Worker Deployment:**
```bash
cd cloudflare-production
wrangler deploy --env production
```

**Database Migration:**
```bash
# Export from local
python scripts/export_to_cloudflare.py

# Import to D1
wrangler d1 execute gkl-fantasy --file incremental.sql
```

#### Automated Deployment (CI/CD)

**GitHub Actions Workflow:**
```yaml
name: Deploy to Production
on:
  push:
    branches: [main]

jobs:
  deploy:
    steps:
      - Build frontend
      - Deploy to Cloudflare Pages
      - Deploy Worker
      - Run database migrations
      - Verify deployment
```

**D1 Direct Write Implementation:**
GitHub Actions workflows include automated data refresh with direct D1 database writes:

- **Resilient Connection**: Automatic retry logic for API failures
- **Individual Query Execution**: Workaround for D1 batch endpoint issues  
- **Response Format Handling**: Proper parsing of D1 API result structures
- **Error Recovery**: Graceful handling of individual query failures
- **Debug Capabilities**: Comprehensive logging for troubleshooting

### 4. Deployment Verification

**Health Checks:**
```python
# cloudflare-deployment-tools/verify_deployment.py
- Database connectivity
- API endpoint availability
- Frontend asset loading
- Cache functionality
- Worker status
```

## Infrastructure as Code

### Wrangler Configuration

**Worker Configuration (`wrangler.toml`):**
```toml
# Base configuration
name = "gkl-fantasy-api"
main = "src/index-with-db.js"
compatibility_date = "2024-01-02"

# Environment-specific settings
[env.production]
name = "gkl-fantasy-api-prod"
vars = { ENVIRONMENT = "production" }
routes = [
  { pattern = "api.goldenknightlounge.com/*", zone_name = "goldenknightlounge.com" }
]

[env.development]
name = "gkl-fantasy-api-dev"
vars = { ENVIRONMENT = "development" }
```

### Database Schema Management

**Migration Strategy:**
1. Version-controlled schema files
2. Incremental migration scripts
3. Rollback procedures
4. Data validation checks

**Schema Deployment:**
```sql
-- migrations/001_initial_schema.sql
CREATE TABLE IF NOT EXISTS transactions ...
CREATE TABLE IF NOT EXISTS daily_lineups ...
CREATE TABLE IF NOT EXISTS players ...

-- migrations/002_add_indexes.sql
CREATE INDEX idx_transactions_date ...
CREATE INDEX idx_players_yahoo_id ...
```

## Monitoring and Observability

### Cloudflare Analytics

**Metrics Tracked:**
- Request volume and patterns
- Response time percentiles
- Error rates and types
- Bandwidth usage
- Cache hit ratios

### Worker Analytics

**Performance Metrics:**
- CPU time per request
- Subrequest counts
- Memory usage
- Cold start frequency

### Custom Monitoring

**Application Metrics:**
```javascript
// Log custom metrics
console.log(JSON.stringify({
  type: 'metric',
  name: 'api_request',
  value: responseTime,
  tags: { endpoint, method, status }
}));
```

### Alerting Configuration

**Alert Rules:**
- Error rate > 1%
- Response time > 1000ms (p95)
- Database connection failures
- Worker CPU limit approached
- Cache miss rate > 50%

## Security Configuration

### SSL/TLS Configuration

**Certificate Management:**
- Automatic SSL provisioning
- TLS 1.3 support
- HSTS enforcement
- Certificate transparency

### Access Control

**Cloudflare Access Policies:**
- API key authentication
- IP allowlisting (admin endpoints)
- Rate limiting rules
- DDoS protection

### Secret Management

**Environment Variables:**
```bash
# Set via Wrangler
wrangler secret put API_KEY
wrangler secret put GITHUB_TOKEN
wrangler secret put DATABASE_URL
```

## Backup and Recovery

### Database Backups

**Backup Strategy:**
1. Daily automated exports
2. Weekly full backups
3. Transaction log archival
4. Cross-region replication

**Recovery Procedures:**
```bash
# Export current state
wrangler d1 export gkl-fantasy --output backup.sql

# Restore from backup
wrangler d1 execute gkl-fantasy --file backup.sql
```

### Code Backups

**Version Control:**
- Git repository (GitHub)
- Tagged releases
- Branch protection rules
- Automated backups to S3 (future)

## Performance Optimization

### CDN Configuration

**Caching Rules:**
```
Static Assets: Cache-Control: public, max-age=31536000
API Responses: Cache-Control: public, max-age=300
Dynamic Content: Cache-Control: no-cache
```

### Edge Optimization

**Worker Optimization:**
- Minimize cold starts
- Efficient routing logic
- Optimized bundle size
- Strategic subrequest usage

### Database Optimization

**D1 Performance:**
- Prepared statements
- Index optimization
- Query result caching
- Connection pooling

## Cost Management

### Resource Monitoring

**Usage Tracking:**
- Worker invocations
- D1 queries
- KV operations
- Bandwidth consumption
- Storage usage

### Cost Optimization

**Strategies:**
1. Aggressive caching
2. Query optimization
3. Asset compression
4. Conditional requests
5. Resource quotas

## Disaster Recovery

### Incident Response

**Response Plan:**
1. Detection and alerting
2. Initial assessment
3. Mitigation actions
4. Root cause analysis
5. Post-mortem review

### Recovery Procedures

**Rollback Strategy:**
```bash
# Rollback worker deployment
wrangler rollback --env production

# Restore database
wrangler d1 restore gkl-fantasy --timestamp "2024-01-01T00:00:00Z"

# Revert frontend
wrangler pages rollback --project gkl-fantasy-frontend
```

## Scaling Strategy

### Automatic Scaling

**Cloudflare Workers:**
- Automatic global distribution
- Unlimited scaling capability
- No cold start penalties
- Automatic load balancing

### Manual Scaling

**Capacity Planning:**
- Monitor usage trends
- Predict growth patterns
- Optimize before scaling
- Cost-benefit analysis

## Future Infrastructure Plans

### Short-term Improvements
1. Implement blue-green deployments
2. Add staging environment
3. Enhance monitoring dashboards
4. Automate backup procedures
5. Implement canary deployments

### Long-term Evolution
1. Multi-region active-active setup
2. Kubernetes migration option
3. Service mesh implementation
4. Advanced observability platform
5. Infrastructure automation with Terraform