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

  // Build query
  let sql = `
    SELECT 
      t.*,
      GROUP_CONCAT(
        json_object(
          'player_name', tp.player_name,
          'player_key', tp.player_key,
          'source_type', tp.source_type,
          'destination_type', tp.destination_type
        )
      ) as players_json
    FROM transactions t
    LEFT JOIN transaction_players tp ON t.transaction_id = tp.transaction_id
    WHERE 1=1
  `;
  
  const params = [];
  
  if (searchTerm) {
    sql += ` AND (tp.player_name LIKE ? OR t.transaction_key LIKE ?)`;
    params.push(`%${searchTerm}%`, `%${searchTerm}%`);
  }
  
  if (teamKey) {
    sql += ` AND t.team_key = ?`;
    params.push(teamKey);
  }
  
  if (transactionType) {
    sql += ` AND t.type = ?`;
    params.push(transactionType);
  }
  
  if (startDate) {
    sql += ` AND DATE(t.transaction_date) >= ?`;
    params.push(startDate);
  }
  
  if (endDate) {
    sql += ` AND DATE(t.transaction_date) <= ?`;
    params.push(endDate);
  }
  
  sql += ` GROUP BY t.transaction_id ORDER BY t.transaction_date DESC, t.timestamp DESC`;
  
  // Get paginated results
  const result = await db.paginate(sql, page, limit, params);
  
  // Parse players JSON
  result.data = result.data.map(transaction => ({
    ...transaction,
    players: transaction.players_json ? JSON.parse(`[${transaction.players_json}]`) : []
  }));
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getTransaction(db, id) {
  const transaction = await db.first(
    `SELECT * FROM transactions WHERE transaction_id = ?`,
    [id]
  );
  
  if (!transaction) {
    throw new Error('Transaction not found');
  }
  
  // Get associated players
  const players = await db.all(
    `SELECT * FROM transaction_players WHERE transaction_id = ?`,
    [id]
  );
  
  transaction.players = players;
  
  return new Response(JSON.stringify(transaction), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getTransactionFilters(db) {
  try {
    // Get unique teams
    const teams = await db.all(`
      SELECT DISTINCT team_key, team_name 
      FROM transactions 
      WHERE team_name IS NOT NULL 
      ORDER BY team_name
    `);
    
    // Get transaction types
    const types = await db.all(`
      SELECT DISTINCT type 
      FROM transactions 
      WHERE type IS NOT NULL 
      ORDER BY type
    `);
    
    // Get date range
    const dateRange = await db.first(`
      SELECT 
        MIN(DATE(transaction_date)) as min_date,
        MAX(DATE(transaction_date)) as max_date
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
        COUNT(DISTINCT transaction_id) as total_transactions,
        COUNT(DISTINCT team_key) as total_teams,
        COUNT(DISTINCT tp.player_key) as unique_players
      FROM transactions t
      LEFT JOIN transaction_players tp ON t.transaction_id = tp.transaction_id
    `);
    
    // Get manager stats
    const managerStats = await db.all(`
      SELECT 
        team_name,
        team_key,
        COUNT(*) as transaction_count
      FROM transactions
      WHERE team_name IS NOT NULL
      GROUP BY team_key, team_name
      ORDER BY transaction_count DESC
    `);
    
    // Get recent activity
    const recentActivity = await db.all(`
      SELECT 
        DATE(transaction_date) as date,
        COUNT(*) as count
      FROM transactions
      WHERE transaction_date >= date('now', '-30 days')
      GROUP BY DATE(transaction_date)
      ORDER BY date DESC
      LIMIT 30
    `);
    
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