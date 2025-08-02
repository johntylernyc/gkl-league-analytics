const database = require('./database');

class TransactionService {
  
  // Get all transactions with pagination and filtering
  async getTransactions(options = {}) {
    const {
      page = 1,
      limit = 50,
      search = '',
      transactionType = '',
      movementType = '',
      startDate = '',
      endDate = '',
      teamName = '',
      playerName = '',
      playerPosition = ''
    } = options;

    let sql = `
      SELECT 
        id,
        date,
        league_key,
        transaction_id,
        transaction_type,
        player_id,
        player_name,
        player_position,
        player_team,
        movement_type,
        destination_team_key,
        destination_team_name,
        source_team_key,
        source_team_name,
        job_id,
        created_at
      FROM transactions_production
      WHERE 1=1
    `;
    
    const params = [];
    let paramIndex = 1;

    // Add search filters
    if (search) {
      sql += ` AND (player_name LIKE ?${paramIndex} OR destination_team_name LIKE ?${paramIndex + 1} OR source_team_name LIKE ?${paramIndex + 2})`;
      params.push(`%${search}%`, `%${search}%`, `%${search}%`);
      paramIndex += 3;
    }

    if (transactionType) {
      sql += ` AND transaction_type = ?${paramIndex}`;
      params.push(transactionType);
      paramIndex++;
    }

    if (movementType) {
      sql += ` AND movement_type = ?${paramIndex}`;
      params.push(movementType);
      paramIndex++;
    }

    if (startDate) {
      sql += ` AND date >= ?${paramIndex}`;
      params.push(startDate);
      paramIndex++;
    }

    if (endDate) {
      sql += ` AND date <= ?${paramIndex}`;
      params.push(endDate);
      paramIndex++;
    }

    if (teamName) {
      sql += ` AND (destination_team_name LIKE ?${paramIndex} OR source_team_name LIKE ?${paramIndex + 1})`;
      params.push(`%${teamName}%`, `%${teamName}%`);
      paramIndex += 2;
    }

    if (playerName) {
      sql += ` AND player_name LIKE ?${paramIndex}`;
      params.push(`%${playerName}%`);
      paramIndex++;
    }

    if (playerPosition) {
      // Handle multiple positions (comma-separated) and match if player has any of the selected positions
      const selectedPositions = playerPosition.split(',').map(p => p.trim()).filter(p => p);
      if (selectedPositions.length > 0) {
        const positionConditions = selectedPositions.map(() => {
          // Use exact position matching with comma boundaries to prevent 'C' from matching 'CF'
          return `(
            player_position = ?${paramIndex++} OR 
            player_position LIKE ?${paramIndex++} OR 
            player_position LIKE ?${paramIndex++} OR 
            player_position LIKE ?${paramIndex++}
          )`;
        });
        sql += ` AND (${positionConditions.join(' OR ')})`;
        selectedPositions.forEach(pos => {
          // Match exact position or position with comma boundaries
          params.push(pos);                    // Exact match (single position)
          params.push(`${pos},%`);            // At beginning followed by comma
          params.push(`%, ${pos},%`);         // In middle surrounded by comma and space
          params.push(`%, ${pos}`);           // At end preceded by comma and space
        });
      }
    }

    // Add ordering and pagination
    sql += ` ORDER BY date DESC, created_at DESC`;
    
    // Get total count for pagination
    const countSql = sql.replace(/SELECT.*?FROM/, 'SELECT COUNT(*) as count FROM');
    const countResult = await database.get(countSql, params);
    const totalCount = countResult.count;

    // Add pagination
    const offset = (page - 1) * limit;
    sql += ` LIMIT ?${paramIndex} OFFSET ?${paramIndex + 1}`;
    params.push(limit, offset);

    const transactions = await database.all(sql, params);

    return {
      transactions,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: totalCount,
        totalPages: Math.ceil(totalCount / limit)
      }
    };
  }

  // Get transaction statistics
  async getStatistics() {
    const stats = await database.all(`
      SELECT 
        COUNT(*) as total_transactions,
        COUNT(DISTINCT player_id) as unique_players,
        COUNT(DISTINCT destination_team_name) + COUNT(DISTINCT source_team_name) as unique_teams,
        MIN(date) as earliest_date,
        MAX(date) as latest_date
      FROM transactions_production
    `);

    const typeBreakdown = await database.all(`
      SELECT transaction_type, COUNT(*) as count 
      FROM transactions_production 
      GROUP BY transaction_type 
      ORDER BY count DESC
    `);

    const movementBreakdown = await database.all(`
      SELECT movement_type, COUNT(*) as count 
      FROM transactions_production 
      GROUP BY movement_type 
      ORDER BY count DESC
    `);

    const topTeams = await database.all(`
      SELECT 
        destination_team_name as team_name, 
        COUNT(*) as acquisitions 
      FROM transactions_production 
      WHERE destination_team_name IS NOT NULL 
      GROUP BY destination_team_name 
      ORDER BY acquisitions DESC 
      LIMIT 10
    `);

    const topPlayers = await database.all(`
      SELECT 
        player_name, 
        COUNT(*) as transaction_count 
      FROM transactions_production 
      GROUP BY player_name 
      ORDER BY transaction_count DESC 
      LIMIT 10
    `);

    const mostDroppedPlayer = await database.get(`
      SELECT 
        player_name, 
        COUNT(*) as drop_count 
      FROM transactions_production 
      WHERE movement_type = 'drop' 
      GROUP BY player_name 
      ORDER BY drop_count DESC 
      LIMIT 1
    `);

    const recentActivity = await database.all(`
      SELECT 
        date,
        COUNT(*) as transaction_count
      FROM transactions_production 
      GROUP BY date 
      ORDER BY date DESC 
      LIMIT 30
    `);

    const managerStats = await database.all(`
      SELECT 
        CASE 
          WHEN destination_team_name IS NOT NULL THEN destination_team_name
          ELSE source_team_name
        END as team_name,
        COUNT(*) as transaction_count
      FROM transactions_production
      WHERE (destination_team_name IS NOT NULL OR source_team_name IS NOT NULL)
      GROUP BY team_name
      ORDER BY transaction_count DESC
    `);

    return {
      overview: stats[0],
      typeBreakdown,
      movementBreakdown,
      topTeams,
      topPlayers,
      mostDroppedPlayer,
      recentActivity,
      managerStats
    };
  }

  // Get unique values for filter dropdowns
  async getFilterOptions() {
    const transactionTypes = await database.all(`
      SELECT DISTINCT transaction_type 
      FROM transactions_production 
      WHERE transaction_type IS NOT NULL 
      ORDER BY transaction_type
    `);

    const movementTypes = await database.all(`
      SELECT DISTINCT movement_type 
      FROM transactions_production 
      WHERE movement_type IS NOT NULL 
      ORDER BY movement_type
    `);

    const teams = await database.all(`
      SELECT DISTINCT team_name FROM (
        SELECT destination_team_name as team_name FROM transactions_production WHERE destination_team_name IS NOT NULL
        UNION
        SELECT source_team_name as team_name FROM transactions_production WHERE source_team_name IS NOT NULL
      ) 
      ORDER BY team_name
    `);

    // Get all position combinations and split them into individual positions
    const positionCombinations = await database.all(`
      SELECT DISTINCT player_position 
      FROM transactions_production 
      WHERE player_position IS NOT NULL 
      ORDER BY player_position
    `);

    // Split position combinations and create unique set of individual positions
    const positionSet = new Set();
    positionCombinations.forEach(row => {
      const positions = row.player_position.split(',');
      positions.forEach(pos => {
        const trimmedPos = pos.trim();
        if (trimmedPos) {
          positionSet.add(trimmedPos);
        }
      });
    });

    // Define valid baseball positions only (exclude things like "P (Probable)", "Util", etc.)
    const validPositions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'SP', 'RP'];
    
    // Filter to only include valid positions that exist in the data
    const finalPositions = validPositions.filter(pos => positionSet.has(pos));

    return {
      transactionTypes: transactionTypes.map(t => t.transaction_type),
      movementTypes: movementTypes.map(t => t.movement_type),
      teams: teams.map(t => t.team_name),
      positions: finalPositions
    };
  }

  // Search players for autocomplete
  async searchPlayers(query, limit = 10) {
    const players = await database.all(`
      SELECT DISTINCT player_name, player_position, player_team
      FROM transactions_production 
      WHERE player_name LIKE ? 
      ORDER BY player_name 
      LIMIT ?
    `, [`%${query}%`, limit]);

    return players;
  }
}

module.exports = new TransactionService();