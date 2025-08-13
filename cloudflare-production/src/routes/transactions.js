/**
 * Transactions route handler for Cloudflare Workers
 */

import { D1Client } from '../db/d1-client.js';

export async function handleTransactions(request, env, action) {
  const db = new D1Client(env.DB);
  const { query, params } = request;
  
  try {
    switch (action) {
      case 'list':
        return await getTransactionsList(db, query);
      case 'get':
        return await getTransaction(db, params.id);
      case 'filters':
        return await getTransactionFilters(db);
      case 'stats':
        return await getTransactionStats(db);
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    console.error('Transactions route error:', error);
    throw error;
  }
}

async function getTransactionsList(db, query) {
  const page = parseInt(query.page) || 1;
  const limit = Math.min(parseInt(query.limit) || 20, 100);
  const searchTerm = query.search || '';
  const teamKey = query.team_key;
  const transactionType = query.type;
  const startDate = query.start_date;
  const endDate = query.end_date;

  // Build query - simplified for current production schema
  let sql = `
    SELECT *
    FROM transactions
    WHERE 1=1
  `;
  
  const params = [];
  
  if (searchTerm) {
    sql += ` AND (player_name LIKE ? OR transaction_id LIKE ?)`;
    params.push(`%${searchTerm}%`, `%${searchTerm}%`);
  }
  
  if (teamKey) {
    sql += ` AND (source_team_key = ? OR destination_team_key = ?)`;
    params.push(teamKey, teamKey);
  }
  
  if (transactionType) {
    sql += ` AND transaction_type = ?`;
    params.push(transactionType);
  }
  
  if (startDate) {
    sql += ` AND date >= ?`;
    params.push(startDate);
  }
  
  if (endDate) {
    sql += ` AND date <= ?`;
    params.push(endDate);
  }
  
  sql += ` ORDER BY date DESC, timestamp DESC`;
  
  // Get paginated results
  const result = await db.paginate(sql, page, limit, params);
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getTransaction(db, id) {
  // For the current production schema, we get all rows for a transaction_id
  const transactions = await db.all(
    `SELECT * FROM transactions WHERE transaction_id = ?`,
    [id]
  );
  
  if (!transactions || transactions.length === 0) {
    throw new Error('Transaction not found');
  }
  
  // Return the first transaction record with all related records
  const result = {
    ...transactions[0],
    movements: transactions // Include all movements for this transaction
  };
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getTransactionFilters(db) {
  try {
    // Get unique teams from both source and destination
    const teams = await db.all(`
      WITH all_teams AS (
        SELECT DISTINCT source_team_key as team_key, source_team_name as team_name 
        FROM transactions 
        WHERE source_team_key != '' AND source_team_name != ''
        UNION
        SELECT DISTINCT destination_team_key as team_key, destination_team_name as team_name 
        FROM transactions 
        WHERE destination_team_key != '' AND destination_team_name != ''
      )
      SELECT * FROM all_teams
      ORDER BY team_name
    `);
    
    // Get transaction types
    const types = await db.all(`
      SELECT DISTINCT transaction_type as type
      FROM transactions 
      WHERE transaction_type IS NOT NULL 
      ORDER BY transaction_type
    `);
    
    // Get date range
    const dateRange = await db.first(`
      SELECT 
        MIN(date) as min_date,
        MAX(date) as max_date
      FROM transactions
    `);
    
    return new Response(JSON.stringify({
      teams: teams || [],
      types: types?.map(t => t.type) || [],
      dateRange: dateRange || { min_date: null, max_date: null }
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error getting filters:', error);
    return new Response(JSON.stringify({
      teams: [],
      types: [],
      dateRange: { min_date: null, max_date: null }
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function getTransactionStats(db) {
  try {
    // Get overview stats
    const overview = await db.first(`
      SELECT 
        COUNT(*) as total_transactions,
        COUNT(DISTINCT CASE 
          WHEN destination_team_key != '' THEN destination_team_key 
          WHEN source_team_key != '' THEN source_team_key 
        END) as total_teams,
        COUNT(DISTINCT yahoo_player_id) as unique_players
      FROM transactions
    `);
    
    // Get manager stats - count all transactions where team is involved
    const managerStats = await db.all(`
      WITH team_transactions AS (
        SELECT destination_team_key as team_key, destination_team_name as team_name
        FROM transactions
        WHERE destination_team_key != '' AND destination_team_name != ''
        UNION ALL
        SELECT source_team_key as team_key, source_team_name as team_name
        FROM transactions
        WHERE source_team_key != '' AND source_team_name != ''
      )
      SELECT 
        team_name,
        team_key,
        COUNT(*) as transaction_count
      FROM team_transactions
      GROUP BY team_key, team_name
      ORDER BY transaction_count DESC
    `);
    
    // Get recent activity - D1 compatible date arithmetic
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoStr = thirtyDaysAgo.toISOString().split('T')[0];
    
    const recentActivity = await db.all(`
      SELECT 
        date,
        COUNT(*) as count
      FROM transactions
      WHERE date >= ?
      GROUP BY date
      ORDER BY date DESC
      LIMIT 30
    `, [thirtyDaysAgoStr]);
    
    return new Response(JSON.stringify({
      overview: overview || {},
      managerStats: managerStats || [],
      recentActivity: recentActivity || []
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error getting stats:', error);
    return new Response(JSON.stringify({
      overview: {},
      managerStats: [],
      recentActivity: []
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
}