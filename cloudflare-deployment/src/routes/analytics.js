/**
 * Analytics route handler for Cloudflare Workers
 */

import { D1Client } from '../db/d1-client.js';

export async function handleAnalytics(request, env, action) {
  const db = new D1Client(env.DB);
  const { query } = request;
  
  try {
    switch (action) {
      case 'overview':
        return await getAnalyticsOverview(db, query);
      case 'trends':
        return await getAnalyticsTrends(db, query);
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    console.error('Analytics route error:', error);
    throw error;
  }
}

async function getAnalyticsOverview(db, query) {
  const season = query.season || new Date().getFullYear();
  
  // Get transaction stats
  const transactionStats = await db.first(`
    SELECT 
      COUNT(*) as total_transactions,
      COUNT(DISTINCT team_key) as active_teams,
      COUNT(DISTINCT DATE(transaction_date)) as active_days
    FROM transactions
    WHERE strftime('%Y', transaction_date) = ?
  `, [season.toString()]);
  
  // Get transaction breakdown by type
  const transactionTypes = await db.all(`
    SELECT 
      type,
      COUNT(*) as count
    FROM transactions
    WHERE strftime('%Y', transaction_date) = ?
    GROUP BY type
    ORDER BY count DESC
  `, [season.toString()]);
  
  // Get most active teams
  const activeTeams = await db.all(`
    SELECT 
      team_key,
      team_name,
      COUNT(*) as transaction_count
    FROM transactions
    WHERE strftime('%Y', transaction_date) = ?
    GROUP BY team_key, team_name
    ORDER BY transaction_count DESC
    LIMIT 10
  `, [season.toString()]);
  
  // Get most moved players
  const movedPlayers = await db.all(`
    SELECT 
      tp.player_name,
      COUNT(DISTINCT t.transaction_id) as move_count
    FROM transaction_players tp
    JOIN transactions t ON tp.transaction_id = t.transaction_id
    WHERE strftime('%Y', t.transaction_date) = ?
    GROUP BY tp.player_name
    ORDER BY move_count DESC
    LIMIT 20
  `, [season.toString()]);
  
  return new Response(JSON.stringify({
    overview: transactionStats,
    transactionTypes,
    activeTeams,
    movedPlayers,
    season
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getAnalyticsTrends(db, query) {
  const season = query.season || new Date().getFullYear();
  const groupBy = query.groupBy || 'week';
  
  let dateFormat;
  switch (groupBy) {
    case 'day':
      dateFormat = '%Y-%m-%d';
      break;
    case 'week':
      dateFormat = '%Y-W%W';
      break;
    case 'month':
      dateFormat = '%Y-%m';
      break;
    default:
      dateFormat = '%Y-W%W';
  }
  
  const trends = await db.all(`
    SELECT 
      strftime('${dateFormat}', transaction_date) as period,
      COUNT(*) as transaction_count,
      COUNT(DISTINCT team_key) as active_teams
    FROM transactions
    WHERE strftime('%Y', transaction_date) = ?
    GROUP BY period
    ORDER BY period
  `, [season.toString()]);
  
  return new Response(JSON.stringify({
    trends,
    season,
    groupBy
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}