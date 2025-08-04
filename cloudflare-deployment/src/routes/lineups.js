/**
 * Lineups route handler for Cloudflare Workers
 */

import { D1Client } from '../db/d1-client.js';

export async function handleLineups(request, env, action) {
  const db = new D1Client(env.DB);
  const { params, query } = request;
  
  try {
    switch (action) {
      case 'list':
        return await getLineupsList(db, query);
      case 'daily':
        return await getDailyLineups(db, params.date);
      case 'team':
        return await getTeamLineup(db, params.date, params.teamId);
      default:
        throw new Error('Invalid action');
    }
  } catch (error) {
    console.error('Lineups route error:', error);
    throw error;
  }
}

async function getLineupsList(db, query) {
  const startDate = query.start_date || '2025-01-01';
  const endDate = query.end_date || new Date().toISOString().split('T')[0];
  
  const lineups = await db.all(`
    SELECT 
      date,
      COUNT(DISTINCT team_key) as teams_count,
      COUNT(DISTINCT player_key) as players_count,
      COUNT(*) as total_positions
    FROM daily_lineups
    WHERE date >= ? AND date <= ?
    GROUP BY date
    ORDER BY date DESC
    LIMIT 100
  `, [startDate, endDate]);
  
  return new Response(JSON.stringify({
    lineups,
    dateRange: { startDate, endDate }
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getDailyLineups(db, date) {
  const lineups = await db.all(`
    SELECT 
      dl.*,
      t.team_name,
      t.manager_name
    FROM daily_lineups dl
    LEFT JOIN teams t ON dl.team_key = t.team_key
    WHERE dl.date = ?
    ORDER BY dl.team_key, dl.position
  `, [date]);
  
  // Group by team
  const teamLineups = {};
  lineups.forEach(lineup => {
    if (!teamLineups[lineup.team_key]) {
      teamLineups[lineup.team_key] = {
        team_key: lineup.team_key,
        team_name: lineup.team_name,
        manager_name: lineup.manager_name,
        positions: []
      };
    }
    teamLineups[lineup.team_key].positions.push(lineup);
  });
  
  return new Response(JSON.stringify({
    date,
    teams: Object.values(teamLineups)
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function getTeamLineup(db, date, teamId) {
  const lineup = await db.all(`
    SELECT 
      dl.*,
      t.team_name,
      t.manager_name
    FROM daily_lineups dl
    LEFT JOIN teams t ON dl.team_key = t.team_key
    WHERE dl.date = ? AND dl.team_key = ?
    ORDER BY dl.position
  `, [date, teamId]);
  
  if (lineup.length === 0) {
    throw new Error('Lineup not found');
  }
  
  return new Response(JSON.stringify({
    date,
    team_key: teamId,
    team_name: lineup[0]?.team_name,
    manager_name: lineup[0]?.manager_name,
    positions: lineup
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
}