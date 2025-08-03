const database = require('./database');
const { getTableName } = require('../config/database');

class PlayerService {
  constructor() {
    this.tableName = getTableName('transactions');
    this.lineupsTableName = getTableName('daily_lineups');
    this.currentSeason = 2025;
  }

  // Search players with filters
  async searchPlayers(options = {}) {
    const {
      search = '',
      position = '',
      mlbTeam = '',
      gklTeam = '',
      status = '',
      page = 1,
      limit = 20
    } = options;

    const offset = (parseInt(page) - 1) * parseInt(limit);
    const conditions = [`season = ?`];
    const params = [this.currentSeason];

    // Build WHERE conditions
    if (search) {
      conditions.push('player_name LIKE ?');
      params.push(`%${search}%`);
    }

    if (position) {
      // Handle multiple positions separated by comma
      const positions = position.split(',').filter(p => p);
      if (positions.length > 0) {
        // For multiple positions, show players who have ANY of the selected positions (OR logic)
        const positionConditions = positions.map(pos => {
          return `(
            eligible_positions = ? OR 
            eligible_positions LIKE ? OR 
            eligible_positions LIKE ? OR 
            eligible_positions LIKE ? OR
            eligible_positions LIKE ?
          )`;
        });
        
        // Use OR to show players who have ANY of the selected positions
        conditions.push(`(${positionConditions.join(' OR ')})`);
        
        positions.forEach(pos => {
          // Match exact position or position with comma boundaries
          params.push(pos);                    // Exact match (single position)
          params.push(`${pos},%`);            // At beginning followed by comma
          params.push(`%,${pos},%`);          // In middle surrounded by commas
          params.push(`%,${pos}`);            // At end preceded by comma
          params.push(`%, ${pos}`);           // At end preceded by comma and space (some have spaces)
        });
      }
    }

    if (mlbTeam) {
      conditions.push('player_team = ?');
      params.push(mlbTeam);
    }

    if (gklTeam) {
      conditions.push('team_name = ?');
      params.push(gklTeam);
    }

    const whereClause = `WHERE ${conditions.join(' AND ')}`;

    // Get total count of unique players
    const countQuery = `
      SELECT COUNT(DISTINCT player_id) as total
      FROM ${this.lineupsTableName}
      ${whereClause}
    `;

    const countResult = await database.get(countQuery, params);
    const total = countResult?.total || 0;

    // Get players with aggregated stats from daily lineups
    const playersQuery = `
      WITH player_lineup_stats AS (
        SELECT 
          player_id,
          player_name,
          eligible_positions as position,
          player_team as mlb_team,
          COUNT(*) as lineup_appearances,
          COUNT(DISTINCT date) as days_rostered,
          COUNT(DISTINCT team_name) as teams_played_for,
          MAX(date) as last_lineup_date
        FROM ${this.lineupsTableName} dl
        ${whereClause}
        GROUP BY player_id, player_name, eligible_positions, player_team
      ),
      player_current_info AS (
        SELECT 
          pls.*,
          (SELECT team_name FROM ${this.lineupsTableName} dl2 
           WHERE dl2.player_id = pls.player_id AND dl2.season = ${this.currentSeason}
           ORDER BY date DESC, lineup_id DESC LIMIT 1) as most_recent_team,
          (SELECT player_status FROM ${this.lineupsTableName} dl3 
           WHERE dl3.player_id = pls.player_id AND dl3.season = ${this.currentSeason}
           ORDER BY date DESC, lineup_id DESC LIMIT 1) as health_status,
          -- Check if player is on a roster on the most recent date
          CASE 
            WHEN EXISTS (
              SELECT 1 FROM ${this.lineupsTableName} dl4 
              WHERE dl4.player_id = pls.player_id 
                AND dl4.season = ${this.currentSeason}
                AND dl4.date = (SELECT MAX(date) FROM ${this.lineupsTableName} WHERE season = ${this.currentSeason})
            ) THEN 'Rostered'
            ELSE 'Free Agent'
          END as roster_status
        FROM player_lineup_stats pls
      ),
      transaction_stats AS (
        SELECT 
          player_id,
          COUNT(*) as transaction_count,
          SUM(CASE WHEN movement_type = 'add' THEN 1 ELSE 0 END) as times_added,
          SUM(CASE WHEN movement_type = 'drop' THEN 1 ELSE 0 END) as times_dropped,
          SUM(CASE WHEN movement_type = 'trade' THEN 1 ELSE 0 END) as times_traded
        FROM ${this.tableName}
        GROUP BY player_id
      )
      SELECT 
        pci.*,
        COALESCE(ts.transaction_count, 0) as transaction_count,
        COALESCE(ts.times_added, 0) as times_added,
        COALESCE(ts.times_dropped, 0) as times_dropped,
        COALESCE(ts.times_traded, 0) as times_traded
      FROM player_current_info pci
      LEFT JOIN transaction_stats ts ON pci.player_id = ts.player_id
      ORDER BY pci.days_rostered DESC, pci.player_name
      LIMIT ? OFFSET ?
    `;

    const queryParams = [...params, parseInt(limit), offset];
    const players = await database.all(playersQuery, queryParams);

    return {
      players,
      total,
      page: parseInt(page),
      limit: parseInt(limit)
    };
  }

  // Get unique positions from the database
  async getPositions() {
    // Get all position strings (including comma-separated ones) from daily lineups
    const positionRows = await database.all(`
      SELECT DISTINCT eligible_positions as position 
      FROM ${this.lineupsTableName}
      WHERE season = ? 
        AND eligible_positions IS NOT NULL 
        AND eligible_positions != ''
    `, [this.currentSeason]);

    // Extract individual positions from comma-separated strings
    const allPositions = new Set();
    positionRows.forEach(row => {
      const positions = row.position.split(',').map(p => p.trim());
      positions.forEach(pos => {
        if (pos) allPositions.add(pos);
      });
    });

    // Convert to array and sort
    const sortedPositions = Array.from(allPositions).sort((a, b) => {
      const order = {
        'C': 1, '1B': 2, '2B': 3, '3B': 4, 'SS': 5,
        'LF': 6, 'CF': 7, 'RF': 8,
        'SP': 9, 'RP': 10, 'Util': 11
      };
      const orderA = order[a] || 99;
      const orderB = order[b] || 99;
      if (orderA !== orderB) return orderA - orderB;
      return a.localeCompare(b);
    });

    return sortedPositions;
  }

  // Get unique MLB teams from the database
  async getMlbTeams() {
    const teams = await database.all(`
      SELECT DISTINCT player_team as team 
      FROM ${this.lineupsTableName}
      WHERE season = ?
        AND player_team IS NOT NULL 
        AND player_team != ''
      ORDER BY player_team
    `, [this.currentSeason]);

    return teams.map(t => t.team);
  }

  // Get unique GKL fantasy teams from the database
  async getGklTeams() {
    const teams = await database.all(`
      SELECT DISTINCT team_name 
      FROM ${this.lineupsTableName}
      WHERE season = ?
        AND team_name IS NOT NULL 
        AND team_name != ''
      ORDER BY team_name
    `, [this.currentSeason]);

    return teams.map(t => t.team_name);
  }

  // Get player details by ID
  async getPlayerById(playerId) {
    // Get player data from daily lineups
    const player = await database.get(`
      SELECT 
        player_id,
        player_name,
        eligible_positions as position,
        player_team as mlb_team,
        COUNT(*) as lineup_appearances,
        COUNT(DISTINCT date) as days_rostered,
        COUNT(DISTINCT team_name) as teams_played_for,
        MAX(date) as last_lineup_date
      FROM ${this.lineupsTableName}
      WHERE player_id = ? AND season = ?
      GROUP BY player_id, player_name, eligible_positions, player_team
    `, [playerId, this.currentSeason]);

    if (!player) {
      return null;
    }

    // Get current team and status from most recent lineup entry
    const currentInfo = await database.get(`
      SELECT 
        team_name as most_recent_team,
        player_status as health_status,
        CASE 
          WHEN EXISTS (
            SELECT 1 FROM ${this.lineupsTableName} dl2 
            WHERE dl2.player_id = ? 
              AND dl2.season = ?
              AND dl2.date = (SELECT MAX(date) FROM ${this.lineupsTableName} WHERE season = ?)
          ) THEN 'Rostered'
          ELSE 'Free Agent'
        END as roster_status
      FROM ${this.lineupsTableName}
      WHERE player_id = ? AND season = ?
      ORDER BY date DESC, lineup_id DESC
      LIMIT 1
    `, [playerId, this.currentSeason, this.currentSeason, playerId, this.currentSeason]);

    // Get transaction stats
    const transactionStats = await database.get(`
      SELECT 
        COUNT(*) as transaction_count,
        SUM(CASE WHEN movement_type = 'add' THEN 1 ELSE 0 END) as times_added,
        SUM(CASE WHEN movement_type = 'drop' THEN 1 ELSE 0 END) as times_dropped,
        SUM(CASE WHEN movement_type = 'trade' THEN 1 ELSE 0 END) as times_traded
      FROM ${this.tableName}
      WHERE player_id = ?
    `, [playerId]);

    return {
      ...player,
      ...currentInfo,
      transaction_count: transactionStats?.transaction_count || 0,
      times_added: transactionStats?.times_added || 0,
      times_dropped: transactionStats?.times_dropped || 0,
      times_traded: transactionStats?.times_traded || 0
    };
  }
}

module.exports = new PlayerService();