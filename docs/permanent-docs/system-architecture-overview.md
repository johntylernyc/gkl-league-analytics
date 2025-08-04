# System Architecture Overview

## Executive Summary

GKL League Analytics is a comprehensive fantasy baseball analytics platform that collects, processes, and visualizes data from Yahoo Fantasy Sports leagues. The system provides real-time insights into player usage, transaction patterns, and team management strategies through a modern web interface powered by edge computing infrastructure.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          End Users                              │
│                   (Web Browsers / Mobile)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Edge Network                      │
│  ┌─────────────────────────────────┬──────────────────────┐    │
│  │   Cloudflare Pages              │  Cloudflare Workers  │    │
│  │   (React Frontend)              │  (API Backend)       │    │
│  │   goldenknightlounge.com        │  api.*.com           │    │
│  └─────────────────────────────────┴──────────────────────┘    │
│                      │                        │                 │
│                      ▼                        ▼                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │           Cloudflare D1 Database (SQLite)            │      │
│  └──────────────────────────────────────────────────────┘      │
│                              ▲                                  │
│  ┌───────────────────────────┴──────────────────────────┐      │
│  │        Cloudflare KV (Cache Layer)                   │      │
│  └───────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                      ▲
                      │ Data Sync
┌─────────────────────┴───────────────────────────────────────────┐
│                 Data Collection Infrastructure                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │          Cloudflare Scheduled Worker                     │   │
│  │            (Cron: 6AM, 1PM, 10PM ET)                    │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │ Triggers                               │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │              GitHub Actions Workflows                    │   │
│  │         (Automated Data Collection Scripts)              │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │ Executes                               │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │              Python Data Pipeline                        │   │
│  │   • Transaction Collection  • Daily Lineups              │   │
│  │   • Player Statistics      • MLB Data Integration        │   │
│  └─────────────────────┬───────────────────────────────────┘   │
│                        │ API Calls                              │
│  ┌─────────────────────▼───────────────────────────────────┐   │
│  │            Yahoo Fantasy Sports API                      │   │
│  │              (OAuth2 Authentication)                     │   │
│  └───────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

## Core System Components

### 1. Data Sources

#### Yahoo Fantasy Sports API
- **Purpose**: Primary data source for fantasy league information
- **Authentication**: OAuth2 with automatic token refresh
- **Data Types**: Transactions, lineups, players, teams, leagues
- **Rate Limits**: 1 request/second, managed through queuing

#### MLB Data Sources (via PyBaseball)
- **Purpose**: Enrich fantasy data with real MLB statistics
- **Sources**: Baseball Reference, Fangraphs, Statcast
- **Integration**: Player ID mapping system
- **Update Frequency**: Daily synchronization

### 2. Data Collection Layer

#### Python Data Pipeline (`data_pipeline/`)
**Components:**
- Transaction collector with job logging
- Daily lineup tracker with position analysis
- Player statistics aggregator
- Season manager for multi-year support

**Processing Flow:**
1. Scheduled trigger initiates collection
2. OAuth token validation and refresh
3. Parallel API requests with rate limiting
4. XML parsing and data transformation
5. Database storage with transaction management

#### Job Management System
**Features:**
- Unique job ID generation
- Progress tracking and monitoring
- Error handling and recovery
- Audit trail for all operations

### 3. Storage Layer

#### Primary Database (Cloudflare D1)
**Characteristics:**
- Globally distributed SQLite
- ACID compliance
- Automatic replication
- Sub-millisecond read latency

**Schema Design:**
- Normalized structure for data integrity
- Optimized indexes for query performance
- Partitioning strategy for large tables
- Audit columns for tracking

#### Cache Layer (Cloudflare KV)
**Usage:**
- API response caching (5-minute TTL)
- Static data caching (24-hour TTL)
- Session storage
- Rate limiting counters

### 4. Application Layer

#### API Backend (Cloudflare Workers)
**Architecture:**
- Serverless edge functions
- Request routing and validation
- Database query execution
- Response transformation and caching

**Endpoints:**
```
GET /api/players           # Player listings
GET /api/transactions      # Transaction history
GET /api/lineups          # Daily lineups
GET /api/analytics        # Statistical analysis
GET /api/teams            # Team information
```

#### Frontend Application (React)
**Architecture:**
- Single-page application (SPA)
- Component-based architecture
- Client-side routing
- Responsive design

**Key Features:**
- Real-time data visualization
- Advanced filtering and search
- Interactive charts and timelines
- Export capabilities

### 5. Infrastructure Layer

#### Cloudflare Edge Network
**Benefits:**
- Global distribution (200+ locations)
- Automatic scaling
- DDoS protection
- SSL/TLS termination

#### Deployment Pipeline
**Process:**
1. Code push to GitHub
2. Automated testing
3. Build optimization
4. Deployment to Cloudflare
5. Health check verification

## Data Flow Architecture

### 1. Data Collection Flow

```
Yahoo API → Data Pipeline → Local SQLite → Export Scripts → D1 Database
    ↑                                                           ↓
OAuth Token ←────────────────────────────────────────→ API Responses
```

**Steps:**
1. Scheduled worker triggers collection
2. Python scripts fetch data from Yahoo
3. Data processed and stored locally
4. Export scripts generate SQL files
5. Import to production D1 database

### 2. User Request Flow

```
User → CDN → Worker → D1/KV → Worker → CDN → User
         ↓                        ↑
      Cache Hit ──────────────────┘
```

**Steps:**
1. User makes request
2. CDN checks edge cache
3. Worker processes request
4. Database/cache query
5. Response transformation
6. Client receives data

## Security Architecture

### Authentication & Authorization
- Yahoo OAuth2 for API access
- Environment-based secrets management
- Token encryption at rest
- Secure credential storage

### Network Security
- HTTPS enforcement
- CORS policy configuration
- Rate limiting implementation
- DDoS protection via Cloudflare

### Data Security
- SQL injection prevention
- Input validation and sanitization
- Prepared statement usage
- Audit logging for compliance

## Performance Architecture

### Optimization Strategies

#### Frontend Performance
- Code splitting and lazy loading
- Asset compression and minification
- Browser caching strategies
- CDN distribution

#### Backend Performance
- Edge computing for low latency
- Query optimization and indexing
- Result caching strategies
- Connection pooling

#### Database Performance
- Index optimization
- Query plan analysis
- Batch operations
- Read replica distribution (future)

### Scalability Design

#### Horizontal Scaling
- Stateless application design
- Distributed caching layer
- Load balancing across edges
- Database sharding (future)

#### Vertical Scaling
- Worker resource allocation
- Database connection limits
- Cache size management
- Query complexity limits

## Monitoring & Observability

### Metrics Collection
- Application performance metrics
- Infrastructure health metrics
- Business metrics tracking
- User behavior analytics

### Logging Strategy
- Structured JSON logging
- Centralized log aggregation
- Log retention policies
- Search and analysis capabilities

### Alerting System
- Performance degradation alerts
- Error rate monitoring
- Availability monitoring
- Capacity planning alerts

## Disaster Recovery

### Backup Strategy
- Daily automated backups
- Point-in-time recovery
- Cross-region replication
- Backup verification testing

### Recovery Procedures
- Rollback capabilities
- Data restoration process
- Service degradation handling
- Communication protocols

## System Integration Points

### External Systems
1. **Yahoo Fantasy Sports API**
   - OAuth2 integration
   - Rate limit management
   - Error handling

2. **GitHub Actions**
   - CI/CD pipeline
   - Automated testing
   - Deployment automation

3. **PyBaseball Libraries**
   - MLB data integration
   - Statistical enrichment
   - Player mapping

### Internal Integration
1. **Frontend ↔ API**
   - RESTful communication
   - Error handling
   - Response caching

2. **API ↔ Database**
   - Connection pooling
   - Transaction management
   - Query optimization

3. **Pipeline ↔ Database**
   - Batch operations
   - Job tracking
   - Error recovery

## Technology Stack

### Frontend
- React 18.x
- Tailwind CSS
- React Router
- Axios/Fetch API

### Backend
- Cloudflare Workers
- Node.js runtime
- Wrangler CLI
- JavaScript/TypeScript

### Database
- Cloudflare D1 (SQLite)
- Cloudflare KV
- Local SQLite (dev)

### Data Pipeline
- Python 3.11+
- Requests library
- PyBaseball
- SQLite3

### Infrastructure
- Cloudflare Pages
- Cloudflare Workers
- GitHub Actions
- Git version control

## Future Architecture Evolution

### Short-term Enhancements
1. GraphQL API layer
2. WebSocket support for real-time
3. Mobile application
4. Advanced caching strategies
5. Performance monitoring dashboard

### Long-term Vision
1. Microservices architecture
2. Machine learning integration
3. Multi-league support
4. Social features
5. Predictive analytics

## Architectural Principles

### Design Principles
- **Scalability**: Design for 10x growth
- **Reliability**: 99.9% uptime target
- **Performance**: Sub-second response times
- **Security**: Defense in depth
- **Maintainability**: Clear separation of concerns

### Development Principles
- **CI/CD**: Automated deployment pipeline
- **Testing**: Comprehensive test coverage
- **Documentation**: Self-documenting code
- **Monitoring**: Observable systems
- **Version Control**: Git-based workflow

## Conclusion

The GKL League Analytics system architecture provides a robust, scalable, and performant platform for fantasy baseball analytics. By leveraging modern edge computing, serverless functions, and distributed databases, the system delivers real-time insights with global availability and minimal latency. The architecture supports future growth while maintaining operational simplicity and cost efficiency.