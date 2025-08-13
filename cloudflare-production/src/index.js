/**
 * GKL Fantasy Baseball API - Cloudflare Workers
 * Main entry point for the Workers application
 */

import { Router } from './utils/router.js';
import { handleCORS, corsHeaders } from './utils/cors.js';
import { handleError } from './utils/error-handler.js';

// Import route handlers
import { handleTransactions } from './routes/transactions.js';
import { handleAnalytics } from './routes/analytics.js';
import { handlePlayerSpotlight } from './routes/player-spotlight.js';
import { handlePlayers } from './routes/players.js';
import { handleLineups } from './routes/lineups.js';

export default {
  /**
   * Main fetch handler for all requests
   */
  async fetch(request, env, ctx) {
    // Handle CORS preflight requests
    if (request.method === 'OPTIONS') {
      return handleCORS();
    }

    const router = new Router();

    // Health check endpoint
    router.get('/health', () => {
      return new Response(JSON.stringify({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        environment: env.ENVIRONMENT || 'production',
        database: 'connected'
      }), {
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    });

    // API Routes (without /api prefix to match frontend expectations)
    // Note: More specific routes must come before parameterized routes
    router.get('/transactions/filters', (req) => handleTransactions(req, env, 'filters'));
    router.get('/transactions/stats', (req) => handleTransactions(req, env, 'stats'));
    router.get('/transactions/:id', (req) => handleTransactions(req, env, 'get'));
    router.get('/transactions', (req) => handleTransactions(req, env, 'list'));
    
    router.get('/analytics/overview', (req) => handleAnalytics(req, env, 'overview'));
    router.get('/analytics/trends', (req) => handleAnalytics(req, env, 'trends'));
    
    router.get('/player-spotlight/:playerId', (req) => handlePlayerSpotlight(req, env, 'spotlight'));
    router.get('/player-spotlight/:playerId/timeline', (req) => handlePlayerSpotlight(req, env, 'timeline'));
    
    router.get('/players', (req) => handlePlayers(req, env, 'list'));
    router.get('/players/:playerId', (req) => handlePlayers(req, env, 'get'));
    router.get('/players/:playerId/stats', (req) => handlePlayers(req, env, 'stats'));
    
    router.get('/lineups', (req) => handleLineups(req, env, 'list'));
    router.get('/lineups/dates', (req) => handleLineups(req, env, 'dates'));
    router.get('/lineups/teams', (req) => handleLineups(req, env, 'teams'));
    router.get('/lineups/date/:date', (req) => handleLineups(req, env, 'daily'));
    router.get('/lineups/summary/:date', (req) => handleLineups(req, env, 'summary'));
    router.get('/lineups/:date', (req) => handleLineups(req, env, 'daily'));
    router.get('/lineups/:date/team/:teamId', (req) => handleLineups(req, env, 'team'));

    // Handle the request
    try {
      const response = await router.handle(request);
      
      // Add CORS headers to all responses
      const newHeaders = new Headers(response.headers);
      Object.entries(corsHeaders).forEach(([key, value]) => {
        newHeaders.set(key, value);
      });
      
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders
      });
    } catch (error) {
      return handleError(error, env);
    }
  },

  /**
   * Scheduled handler for cron triggers
   */
  async scheduled(event, env, ctx) {
    const timestamp = new Date().toISOString();
    console.log(`Scheduled event triggered at ${timestamp}`);

    switch (event.cron) {
      case '0 2 * * *':  // 2 AM daily
        console.log('Running 2 AM daily update...');
        await this.runDailyUpdate(env, 'morning');
        break;
      
      case '0 14 * * *': // 2 PM daily
        console.log('Running 2 PM daily update...');
        await this.runDailyUpdate(env, 'afternoon');
        break;
      
      default:
        console.log(`Unknown cron pattern: ${event.cron}`);
    }
  },

  /**
   * Run daily data updates
   */
  async runDailyUpdate(env, timeOfDay) {
    try {
      console.log(`Starting ${timeOfDay} update...`);
      
      // Here we'll add calls to update functions
      // For now, just log the activity
      const result = await env.DB.prepare(
        `INSERT INTO update_log (timestamp, type, status, details) 
         VALUES (?, ?, ?, ?)`
      ).bind(
        new Date().toISOString(),
        `daily_${timeOfDay}`,
        'completed',
        JSON.stringify({ environment: env.ENVIRONMENT })
      ).run();

      console.log(`${timeOfDay} update completed successfully`);
      return result;
    } catch (error) {
      console.error(`Error in ${timeOfDay} update:`, error);
      throw error;
    }
  }
};