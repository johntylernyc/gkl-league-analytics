const database = require('./database');
const { getTableName, getEnvironment } = require('../config/database');

class LineupService {
  constructor() {
    this.environment = getEnvironment();
    this.tableName = getTableName('daily_lineups', this.environment);
  }

  async ensureConnection() {
    if (!database.db) {
      await database.connect(this.environment);
    }
  }
  
  // Get all available dates with lineup data
  async getAvailableDates() {
    await this.ensureConnection();
    const query = `
      SELECT DISTINCT date
      FROM ${this.tableName}
      ORDER BY date DESC
    `;
    
    const rows = await database.all(query);
    return rows.map(row => row.date);
  }

  // Get all teams
  async getTeams() {
    await this.ensureConnection();
    const query = `
      SELECT DISTINCT team_key, team_name
      FROM ${this.tableName}
      ORDER BY team_name
    `;
    
    return await database.all(query);
  }

  // Get lineups for a specific date
  async getLineupsByDate(date, teamKey = null) {
    await this.ensureConnection();
    let query = `
      SELECT 
        lineup_id,
        season,
        date,
        team_key,
        team_name,
        player_id,
        player_name,
        selected_position,
        position_type,
        player_status,
        eligible_positions,
        player_team
      FROM ${this.tableName}
      WHERE date = ?
    `;
    
    const params = [date];
    
    if (teamKey) {
      query += ' AND team_key = ?';
      params.push(teamKey);
    }
    
    query += ' ORDER BY team_name, position_type DESC, selected_position';
    
    const lineups = await database.all(query, params);
    
    // Group by team for easier consumption
    const groupedLineups = {};
    lineups.forEach(lineup => {
      if (!groupedLineups[lineup.team_key]) {
        groupedLineups[lineup.team_key] = {
          team_key: lineup.team_key,
          team_name: lineup.team_name,
          date: lineup.date,
          players: []
        };
      }
      groupedLineups[lineup.team_key].players.push({
        player_id: lineup.player_id,
        player_name: lineup.player_name,
        selected_position: lineup.selected_position,
        position_type: lineup.position_type,
        player_status: lineup.player_status,
        eligible_positions: lineup.eligible_positions,
        player_team: lineup.player_team
      });
    });
    
    return Object.values(groupedLineups);
  }

  // Get lineup for a specific team on a specific date
  async getTeamLineup(date, teamKey) {
    await this.ensureConnection();
    const query = `
      SELECT 
        player_id,
        player_name,
        selected_position,
        position_type,
        player_status,
        eligible_positions,
        player_team
      FROM ${this.tableName}
      WHERE date = ? AND team_key = ?
      ORDER BY 
        CASE position_type
          WHEN 'B' THEN 1
          WHEN 'P' THEN 2
          ELSE 3
        END,
        selected_position
    `;
    
    const players = await database.all(query, [date, teamKey]);
    
    // Get team info
    const teamQuery = `
      SELECT DISTINCT team_name
      FROM ${this.tableName}
      WHERE team_key = ?
      LIMIT 1
    `;
    
    const teamInfo = await database.get(teamQuery, [teamKey]);
    
    return {
      team_key: teamKey,
      team_name: teamInfo?.team_name || 'Unknown Team',
      date: date,
      players: players.map(p => ({
        ...p,
        eligible_positions: p.eligible_positions ? p.eligible_positions.split(',') : []
      }))
    };
  }

  // Get player usage history
  async getPlayerHistory(playerId, startDate = null, endDate = null) {
    await this.ensureConnection();
    let query = `
      SELECT 
        date,
        team_key,
        team_name,
        selected_position,
        position_type,
        player_status
      FROM ${this.tableName}
      WHERE player_id = ?
    `;
    
    const params = [playerId];
    
    if (startDate) {
      query += ' AND date >= ?';
      params.push(startDate);
    }
    
    if (endDate) {
      query += ' AND date <= ?';
      params.push(endDate);
    }
    
    query += ' ORDER BY date DESC';
    
    const history = await database.all(query, params);
    
    // Get player info
    const playerQuery = `
      SELECT DISTINCT player_name
      FROM ${this.tableName}
      WHERE player_id = ?
      LIMIT 1
    `;
    
    const playerInfo = await database.get(playerQuery, [playerId]);
    
    // Calculate usage stats
    const stats = {
      total_days: history.length,
      games_started: history.filter(h => !['BN', 'IL', 'NA'].includes(h.selected_position)).length,
      games_benched: history.filter(h => h.selected_position === 'BN').length,
      games_injured: history.filter(h => ['IL', 'IL10', 'IL60'].includes(h.selected_position)).length
    };
    
    return {
      player_id: playerId,
      player_name: playerInfo?.player_name || 'Unknown Player',
      stats: stats,
      history: history
    };
  }

  // Get daily summary
  async getDailySummary(date) {
    await this.ensureConnection();
    const summaryQuery = `
      SELECT 
        COUNT(DISTINCT team_key) as teams,
        COUNT(DISTINCT player_id) as unique_players,
        COUNT(*) as total_positions,
        SUM(CASE WHEN position_type = 'B' THEN 1 ELSE 0 END) as batters,
        SUM(CASE WHEN position_type = 'P' THEN 1 ELSE 0 END) as pitchers,
        SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched,
        SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60') THEN 1 ELSE 0 END) as injured
      FROM ${this.tableName}
      WHERE date = ?
    `;
    
    const summary = await database.get(summaryQuery, [date]);
    
    // Get most started players
    const topPlayersQuery = `
      SELECT 
        player_id,
        player_name,
        COUNT(*) as times_started
      FROM ${this.tableName}
      WHERE date = ?
      AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')
      GROUP BY player_id, player_name
      HAVING COUNT(*) > 1
      ORDER BY times_started DESC
      LIMIT 10
    `;
    
    const topPlayers = await database.all(topPlayersQuery, [date]);
    
    return {
      date: date,
      ...summary,
      most_started: topPlayers
    };
  }

  // Search players
  async searchPlayers(searchTerm) {
    await this.ensureConnection();
    const query = `
      SELECT 
        player_id,
        player_name,
        COUNT(DISTINCT date) as days_rostered,
        COUNT(DISTINCT team_key) as teams,
        MIN(date) as first_seen,
        MAX(date) as last_seen
      FROM ${this.tableName}
      WHERE LOWER(player_name) LIKE LOWER(?)
      GROUP BY player_id, player_name
      ORDER BY days_rostered DESC
      LIMIT 20
    `;
    
    return await database.all(query, [`%${searchTerm}%`]);
  }
}

module.exports = new LineupService();