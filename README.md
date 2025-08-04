# GKL League Analytics

A comprehensive fantasy baseball analytics platform that transforms Yahoo Fantasy Sports data into actionable insights through modern edge computing infrastructure.

## 🌟 Overview

GKL League Analytics is a production-ready system that collects, processes, and visualizes fantasy baseball league data. Built on Cloudflare's global edge network, it provides real-time analytics for player usage patterns, transaction analysis, and team management strategies.

### Live Application
- **Web Application**: [https://goldenknightlounge.com](https://goldenknightlounge.com)
- **API Endpoint**: [https://gkl-fantasy-api.services-403.workers.dev](https://gkl-fantasy-api.services-403.workers.dev)

## ✨ Key Features

### Analytics Dashboard
- **Transaction Explorer** - Track all adds, drops, and trades with advanced filtering
- **Player Spotlight** - Deep analysis of individual player usage and performance
- **Daily Lineups** - Historical roster decisions and position utilization
- **Manager Analytics** - Compare strategies across teams
- **Performance Timeline** - Visualize ownership patterns over time

### Technical Capabilities
- Real-time data synchronization with Yahoo Fantasy Sports API
- Edge-powered API with sub-200ms response times globally
- Comprehensive job logging and audit trails
- Automated data collection with error recovery
- Mobile-responsive interface

## 🏗️ Architecture

### High-Level System Design

```
Users → Cloudflare Edge Network → React Frontend
                ↓
        Cloudflare Workers API
                ↓
        Cloudflare D1 Database
                ↑
    Python Data Pipeline ← Yahoo Fantasy API
```

### Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, Tailwind CSS, React Router |
| **API** | Cloudflare Workers, JavaScript/Node.js |
| **Database** | Cloudflare D1 (SQLite), KV Cache |
| **Data Pipeline** | Python 3.11+, OAuth2, Job Management |
| **Infrastructure** | Cloudflare Pages, GitHub Actions |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 18+ and npm
- Cloudflare account (free tier works)
- Yahoo Developer account

### Local Development

1. **Clone and Configure**
```bash
git clone https://github.com/[username]/gkl-league-analytics.git
cd gkl-league-analytics

# Set up Yahoo API credentials
cp .env.example .env
# Edit .env with your Yahoo API credentials
```

2. **Initialize Authentication**
```bash
# Generate OAuth URL
python auth/generate_auth_url.py

# Visit URL and authorize, then:
python auth/initialize_tokens.py
```

3. **Configure Local Environment**
```bash
# Frontend configuration (uses local backend)
cd web-ui/frontend
cp .env.example .env.local
# .env.local will contain: REACT_APP_API_URL=http://localhost:3001/api

# Backend configuration (already set)
cd web-ui/backend
# Check .env has: PORT=3001, CORS_ORIGIN=http://localhost:3000
```

4. **Start Development Servers**
```bash
# Backend API (Terminal 1) - Port 3001
cd web-ui/backend
npm install  # First time only
npm start

# Frontend (Terminal 2) - Port 3000
cd web-ui/frontend
npm install  # First time only
npm start
```

## 📊 Data Management

### Data Collection Pipeline

The system uses a Python-based pipeline for data collection:

```bash
# Bulk backfill historical transactions
cd data_pipeline
python league_transactions/backfill_transactions.py --season 2025

# Incremental transaction updates (for automation)
python league_transactions/update_transactions.py --days 7

# Bulk backfill historical lineups
python daily_lineups/backfill_lineups.py --season 2025

# Incremental lineup updates (for automation)
python daily_lineups/update_lineups.py --days 7

# Update player statistics
python player_stats/incremental_update.py
```

### Database Synchronization

#### Local Development
Local development uses SQLite database directly:
- Frontend (localhost:3000) → Backend API (localhost:3001) → SQLite (database/league_analytics.db)

#### Production Deployment  
Production uses Cloudflare D1 with **direct writes from GitHub Actions**:
- Frontend (goldenknightlounge.com) → Cloudflare Workers → D1 Database
- GitHub Actions → D1 Database (scheduled data refresh)

#### Local to Production Data Flow

**For Manual Updates** (Development/Testing):
```bash
# Export recent data from local SQLite with dependencies
python scripts/sync_to_production.py

# The script will output commands in the CORRECT ORDER - follow exactly!
cd cloudflare-production

# Import in this order to satisfy foreign key constraints:
# 1. Job logs (referenced by all data tables)
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/job_logs_*.sql --remote

# 2. Transactions
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/transactions_*.sql --remote

# 3. Lineups (depends on job_log)
npx wrangler d1 execute gkl-fantasy --file=./sql/incremental/lineups_*.sql --remote
```

**For Production Updates** (Automated):
```bash
# GitHub Actions runs automatically 3x daily with direct D1 writes:
# NO local database required - writes directly to production D1
# Handles foreign key dependencies automatically
# Comprehensive job logging and error handling included
```

**⚠️ Important**: Manual import order matters! Always import `job_logs` first to avoid foreign key errors. Automated GitHub Actions handle this automatically.

### Automated Updates

The system includes GitHub Actions scheduled workflows for automatic data refresh with direct Cloudflare D1 writes:
- **Morning Update** (6 AM ET): 7-day lookback for transaction corrections and lineup updates
- **Afternoon Update** (1 PM ET): 3-day lookback for recent transactions and lineup changes  
- **Evening Update** (10 PM ET): 3-day lookback for end-of-day synchronization

**Key Features:**
- Direct D1 database writes (no local SQLite sync required)
- Automatic foreign key dependency management
- Comprehensive job logging and audit trails
- Sub-2-minute execution times
- 99%+ successful write rate

## 🔐 Environment Configuration

### Frontend Environment Files
- `.env.local` - Local development (points to localhost:3001)
- `.env.production` - Production build (points to Cloudflare Workers)
- `.env.example` - Template with all required variables

### Backend Environment Files
- `.env` - Backend configuration (port, database path, CORS settings)

### Environment Variables
```bash
# Frontend (.env.local)
REACT_APP_API_URL=http://localhost:3001/api  # Local backend
REACT_APP_ENV=local

# Backend (.env)
PORT=3001
NODE_ENV=development
DB_PATH=../../database/league_analytics.db
CORS_ORIGIN=http://localhost:3000

# Yahoo API (.env in root)
YAHOO_CLIENT_ID=your_client_id
YAHOO_CLIENT_SECRET=your_client_secret
```

## 🔧 API Reference

### Core Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/transactions` | Transaction history with filtering |
| `GET /api/players/:id/spotlight` | Player analytics and usage |
| `GET /api/lineups/date/:date` | Daily lineup data |
| `GET /api/analytics/managers` | Manager statistics |
| `GET /api/teams` | Team information |

### Example Usage

```javascript
// Fetch player spotlight data
fetch('https://gkl-fantasy-api.services-403.workers.dev/api/players/12345/spotlight')
  .then(res => res.json())
  .then(data => console.log(data));
```

## 📁 Project Structure

```
gkl-league-analytics/
├── data_pipeline/           # Python data collection
│   ├── league_transactions/ # Transaction processing
│   ├── daily_lineups/      # Lineup collection
│   ├── player_stats/       # Statistics integration
│   └── common/             # Shared utilities
├── cloudflare-production/  # Production deployment
│   ├── src/               # Workers API code
│   ├── d1-schema.sql      # Database schema
│   └── wrangler.toml      # Cloudflare config
├── web-ui/                # Frontend application
│   └── frontend/          # React application
├── auth/                  # OAuth authentication
├── scripts/               # Utility scripts
└── docs/                  # Documentation
    └── permanent-docs/    # Architecture docs
```

## 🚢 Deployment

### Deploy to Production

1. **Configure Cloudflare**
```bash
cd cloudflare-production
npx wrangler login
```

2. **Create Resources**
```bash
# Create production database
npx wrangler d1 create gkl-fantasy

# Create KV namespace for caching
npx wrangler kv namespace create CACHE

# Update wrangler.toml with returned IDs
```

3. **Deploy API**
```bash
npm run deploy
```

4. **Deploy Frontend**
```bash
cd ../web-ui/frontend
npm run build
npx wrangler pages deploy build --project-name gkl-fantasy
```

## 📈 Performance

### System Metrics
- **API Response**: < 200ms p95 globally
- **Database Queries**: < 50ms average
- **Cache Hit Rate**: > 80%
- **Availability**: 99.9% uptime target

### Optimization Features
- Edge computing at 200+ locations
- Intelligent caching strategies
- Database query optimization
- Code splitting and lazy loading

## 🔒 Security

### Implementation
- OAuth2 authentication for Yahoo API
- Environment-based secrets management
- SQL injection prevention
- HTTPS enforcement
- CORS configuration
- Rate limiting

### Best Practices
- Never commit credentials
- Use environment variables
- Regular token rotation
- Audit logging enabled

## 📚 Documentation

### Architecture Documentation
- [System Architecture Overview](docs/permanent-docs/system-architecture-overview.md)
- [Data Pipeline Architecture](docs/permanent-docs/data-pipeline-architecture.md)
- [Application Infrastructure](docs/permanent-docs/application-infrastructure.md)
- [Database Infrastructure](docs/permanent-docs/database-infrastructure.md)
- [Deployment Infrastructure](docs/permanent-docs/deployment-infrastructure.md)

### Development Guides
- [CLAUDE.md](CLAUDE.md) - AI assistant context and development workflow
- [Local Development Setup](docs/development-docs/LOCAL_DEVELOPMENT_SETUP.md) - Complete local environment guide
- [Development Documentation](docs/development-docs/) - Implementation guides

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow existing patterns and standards
4. Include job logging for data operations
5. Test thoroughly
6. Submit pull request

### Development Standards
- Comprehensive job logging for data operations
- Test coverage for critical paths
- Documentation for new features
- Performance considerations

## 📊 Project Status

### Current Implementation
✅ Transaction data collection and analysis (consolidated Aug 2025)  
✅ Daily lineup tracking (consolidated Aug 2025)  
✅ Player spotlight features  
✅ Manager analytics  
✅ Production deployment on Cloudflare  
✅ Automated data refresh  
✅ Mobile-responsive interface  
✅ Data quality validation for all pipelines  

### Roadmap
🔄 MLB statistics integration (PyBaseball)  
📱 Native mobile applications  
📈 Advanced predictive analytics  
🔔 Real-time notifications  
👥 Multi-league support  

## 📄 License

This project is proprietary software developed for the GKL Fantasy Baseball League. Usage must comply with Yahoo Fantasy Sports API Terms of Service.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/[username]/gkl-league-analytics/issues)
- **Documentation**: [Permanent Docs](docs/permanent-docs/)
- **API Status**: Check `/api/health` endpoint

---

**Version**: 2.0.0  
**Last Updated**: August 2025  
**Status**: Production