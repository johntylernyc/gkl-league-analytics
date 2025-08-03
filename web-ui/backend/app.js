require('dotenv').config();
const express = require('express');
const cors = require('cors');
const database = require('./services/database');

// Import routes
const transactionsRoutes = require('./routes/transactions');
const analyticsRoutes = require('./routes/analytics');
const playerSpotlightRoutes = require('./routes/playerSpotlight');

let lineupsRoutes;
try {
  lineupsRoutes = require('./routes/lineups');
  console.log('✅ Lineups routes loaded successfully');
} catch (error) {
  console.error('❌ Failed to load lineups routes:', error.message);
  lineupsRoutes = null;
}

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    database: 'connected'
  });
});

// API routes
app.use('/api/transactions', transactionsRoutes);
app.use('/api/analytics', analyticsRoutes);
app.use('/api/players', playerSpotlightRoutes);

if (lineupsRoutes) {
  app.use('/api/lineups', lineupsRoutes);
  console.log('✅ Lineups routes registered at /api/lineups');
} else {
  console.log('❌ Lineups routes not available');
}

// Default route
app.get('/', (req, res) => {
  res.json({
    message: 'GKL League Analytics API',
    version: '1.0.0',
    endpoints: {
      health: '/health',
      transactions: '/api/transactions',
      transactionStats: '/api/transactions/stats',
      transactionFilters: '/api/transactions/filters',
      playerSearch: '/api/transactions/players/search',
      analytics: '/api/analytics/summary',
      managers: '/api/analytics/managers',
      lineupDates: '/api/lineups/dates',
      lineupTeams: '/api/lineups/teams',
      lineupsByDate: '/api/lineups/date/{date}',
      teamLineup: '/api/lineups/team/{teamKey}/date/{date}',
      playerHistory: '/api/lineups/player/{playerId}/history',
      playerSpotlight: '/api/players/{playerId}/spotlight',
      playerTimeline: '/api/players/{playerId}/timeline',
      playerSeasons: '/api/players/{playerId}/seasons',
      playerSearch: '/api/players/search'
    }
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    path: req.originalUrl
  });
});

// Initialize database and start server
async function startServer() {
  try {
    await database.connect();
    
    app.listen(PORT, () => {
      console.log(`GKL Analytics API server running on port ${PORT}`);
      console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
      console.log(`CORS enabled for: ${process.env.CORS_ORIGIN || 'http://localhost:3000'}`);
      console.log('API endpoints available:');
      console.log(`  Health check: http://localhost:${PORT}/health`);
      console.log(`  Transactions: http://localhost:${PORT}/api/transactions`);
      console.log(`  Analytics: http://localhost:${PORT}/api/analytics/summary`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down gracefully...');
  await database.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('Shutting down gracefully...');
  await database.close();
  process.exit(0);
});

startServer();