/**
 * Player Spotlight route handler for Cloudflare Workers
 */

import { D1Client } from '../db/d1-client.js';

export async function handlePlayerSpotlight(request, env, action) {
  const db = new D1Client(env.DB);
  const { params, query } = request;
  
  try {
    const playerId = params.playerId;
    const season = query.season || new Date().getFullYear();
    
    switch (action) {
      case 'spotlight':
        return await getPlayerSpotlight(db, playerId, season);
      case 'timeline':
        return await getPlayerTimeline(db, playerId, season);
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    console.error('Player spotlight route error:', error);
    throw error;
  }
}

async function getPlayerSpotlight(db, playerId, season) {
  // Get player basic info
  const playerInfo = await db.first(`
    SELECT DISTINCT
      player_name,
      mlb_player_id,
      yahoo_player_id,
      team_code,
      position_codes
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
    ORDER BY date DESC
    LIMIT 1
  `, [playerId]);
  
  if (!playerInfo) {
    throw new Error('Player not found');
  }
  
  // Get usage statistics
  const usageStats = await db.first(`
    SELECT 
      COUNT(*) as total_days,
      SUM(CASE WHEN has_batting_data = 1 THEN 1 ELSE 0 END) as batting_days,
      SUM(CASE WHEN has_pitching_data = 1 THEN 1 ELSE 0 END) as pitching_days,
      AVG(batting_at_bats) as avg_at_bats,
      SUM(batting_hits) as total_hits,
      SUM(batting_home_runs) as total_home_runs,
      SUM(batting_rbis) as total_rbis,
      SUM(batting_stolen_bases) as total_stolen_bases,
      AVG(pitching_innings_pitched) as avg_innings,
      SUM(pitching_wins) as total_wins,
      SUM(pitching_saves) as total_saves,
      SUM(pitching_strikeouts) as total_strikeouts
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
      AND strftime('%Y', date) = ?
  `, [playerId, season.toString()]);
  
  // Get monthly performance
  const monthlyPerformance = await db.all(`
    SELECT 
      strftime('%Y-%m', date) as month,
      COUNT(*) as games,
      SUM(batting_hits) as hits,
      SUM(batting_home_runs) as home_runs,
      SUM(batting_rbis) as rbis,
      SUM(batting_stolen_bases) as stolen_bases,
      SUM(pitching_wins) as wins,
      SUM(pitching_saves) as saves,
      SUM(pitching_strikeouts) as strikeouts
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
      AND strftime('%Y', date) = ?
    GROUP BY month
    ORDER BY month
  `, [playerId, season.toString()]);
  
  return new Response(JSON.stringify({
    player: playerInfo,
    usage: usageStats,
    monthlyPerformance,
    season
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getPlayerTimeline(db, playerId, season) {
  const timeline = await db.all(`
    SELECT 
      date,
      team_code,
      position_codes,
      batting_at_bats,
      batting_hits,
      batting_home_runs,
      batting_rbis,
      batting_stolen_bases,
      pitching_innings_pitched,
      pitching_wins,
      pitching_saves,
      pitching_strikeouts
    FROM daily_gkl_player_stats
    WHERE mlb_player_id = ?
      AND strftime('%Y', date) = ?
    ORDER BY date
  `, [playerId, season.toString()]);
  
  return new Response(JSON.stringify({
    timeline,
    playerId,
    season
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}