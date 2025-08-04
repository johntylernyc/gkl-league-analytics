/**
 * Players route handler for Cloudflare Workers
 */

import { D1Client } from '../db/d1-client.js';

export async function handlePlayers(request, env, action) {
  const db = new D1Client(env.DB);
  const { params, query } = request;
  
  try {
    switch (action) {
      case 'list':
        return await getPlayersList(db, query);
      case 'get':
        return await getPlayer(db, params.playerId);
      case 'stats':
        return await getPlayerStats(db, params.playerId, query);
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    console.error('Players route error:', error);
    throw error;
  }
}

async function getPlayersList(db, query) {
  const page = parseInt(query.page) || 1;
  const limit = Math.min(parseInt(query.limit) || 50, 100);
  const search = query.search || '';
  const position = query.position;
  const team = query.team;
  
  let sql = `
    SELECT DISTINCT
      mlb_player_id,
      player_name,
      yahoo_player_id,
      team_code,
      position_codes
    FROM daily_gkl_player_stats
    WHERE 1=1
  `;
  
  const params = [];
  
  if (search) {
    sql += ` AND player_name LIKE ?`;
    params.push(`%${search}%`);
  }
  
  if (position) {
    sql += ` AND position_codes LIKE ?`;
    params.push(`%${position}%`);
  }
  
  if (team) {
    sql += ` AND team_code = ?`;
    params.push(team);
  }
  
  sql += ` ORDER BY player_name`;
  
  const result = await db.paginate(sql, page, limit, params);
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getPlayer(db, playerId) {
  const player = await db.first(`
    SELECT DISTINCT
      mlb_player_id,
      player_name,
      yahoo_player_id,
      baseball_reference_id,
      fangraphs_id,
      team_code,
      position_codes
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
    ORDER BY date DESC
    LIMIT 1
  `, [playerId]);
  
  if (!player) {
    throw new Error('Player not found');
  }
  
  return new Response(JSON.stringify(player), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getPlayerStats(db, playerId, query) {
  const startDate = query.start_date || '2025-01-01';
  const endDate = query.end_date || new Date().toISOString().split('T')[0];
  
  const stats = await db.all(`
    SELECT *
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
      AND date >= ?
      AND date <= ?
    ORDER BY date DESC
  `, [playerId, startDate, endDate]);
  
  // Calculate aggregates
  const aggregates = await db.first(`
    SELECT 
      COUNT(*) as games,
      SUM(batting_at_bats) as total_at_bats,
      SUM(batting_hits) as total_hits,
      SUM(batting_home_runs) as total_home_runs,
      SUM(batting_rbis) as total_rbis,
      SUM(batting_stolen_bases) as total_stolen_bases,
      SUM(pitching_innings_pitched) as total_innings,
      SUM(pitching_wins) as total_wins,
      SUM(pitching_saves) as total_saves,
      SUM(pitching_strikeouts) as total_strikeouts
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
      AND date >= ?
      AND date <= ?
  `, [playerId, startDate, endDate]);
  
  return new Response(JSON.stringify({
    stats,
    aggregates,
    playerId,
    dateRange: { startDate, endDate }
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}