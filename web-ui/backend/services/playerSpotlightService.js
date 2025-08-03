const database = require('./database');
const { getTableName, getEnvironment } = require('../config/database');

class PlayerSpotlightService {
  constructor() {
    this.environment = getEnvironment();
    this.tableName = getTableName('daily_lineups', this.environment);
  }

  // Get comprehensive player spotlight data for a specific season
  async getPlayerSpotlight(playerId, season = 2025) {
    try {
      // Get basic player information
      const playerInfo = await this.getPlayerBasicInfo(playerId);
      
      // Get season usage statistics
      const usageStats = await this.getSeasonUsageStats(playerId, season);
      
      // Get monthly breakdown data
      const monthlyData = await this.getMonthlyBreakdown(playerId, season);
      
      // Get available seasons for this player
      const availableSeasons = await this.getAvailableSeasons(playerId);

      return {
        player: playerInfo,
        season: season,
        usage_breakdown: usageStats,
        monthly_data: monthlyData,
        available_seasons: availableSeasons,
        data_completeness: {
          has_usage_data: usageStats.total_days > 0,
          has_monthly_data: monthlyData.length > 0,
          earliest_date: monthlyData.length > 0 ? monthlyData[0].earliest_date : null,
          latest_date: monthlyData.length > 0 ? monthlyData[monthlyData.length - 1].latest_date : null
        }
      };
    } catch (error) {
      console.error('Error fetching player spotlight data:', error);
      throw error;
    }
  }

  // Get basic player information
  async getPlayerBasicInfo(playerId) {
    const player = await database.get(`
      SELECT 
        player_id,
        player_name,
        player_team,
        position_type,
        eligible_positions,
        player_status,
        team_name as current_fantasy_team
      FROM ${this.tableName}
      WHERE player_id = ?
      ORDER BY date DESC
      LIMIT 1
    `, [playerId]);

    if (!player) {
      throw new Error(`Player with ID ${playerId} not found`);
    }

    return player;
  }

  // Get season usage statistics with percentages
  async getSeasonUsageStats(playerId, season) {
    const stats = await database.all(`
      SELECT 
        selected_position,
        COUNT(*) as days,
        COUNT(*) * 100.0 / (
          SELECT COUNT(*) 
          FROM ${this.tableName} 
          WHERE player_id = ? 
          AND strftime('%Y', date) = ?
        ) as percentage
      FROM ${this.tableName}
      WHERE player_id = ? 
      AND strftime('%Y', date) = ?
      GROUP BY selected_position
      ORDER BY days DESC
    `, [playerId, season.toString(), playerId, season.toString()]);

    // Get total days for this player in the season
    const totalResult = await database.get(`
      SELECT COUNT(*) as total_days
      FROM ${this.tableName}
      WHERE player_id = ? 
      AND strftime('%Y', date) = ?
    `, [playerId, season.toString()]);

    const totalDays = totalResult?.total_days || 0;

    // Categorize positions into usage types
    const usageBreakdown = {
      started: { days: 0, percentage: 0, positions: [] },
      benched: { days: 0, percentage: 0, positions: [] },
      injured_list: { days: 0, percentage: 0, positions: [] },
      other_roster: { days: 0, percentage: 0, positions: [] },
      not_owned: { days: 0, percentage: 0, positions: [] }
    };

    stats.forEach(stat => {
      const position = stat.selected_position;
      const days = stat.days;
      const percentage = stat.percentage;

      if (['BN'].includes(position)) {
        usageBreakdown.benched.days += days;
        usageBreakdown.benched.percentage += percentage;
        usageBreakdown.benched.positions.push(position);
      } else if (['IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(position)) {
        usageBreakdown.injured_list.days += days;
        usageBreakdown.injured_list.percentage += percentage;
        usageBreakdown.injured_list.positions.push(position);
      } else if (position === 'Not Owned' || position === 'FA') {
        usageBreakdown.not_owned.days += days;
        usageBreakdown.not_owned.percentage += percentage;
        usageBreakdown.not_owned.positions.push(position);
      } else {
        // Active positions (C, 1B, 2B, etc.)
        usageBreakdown.started.days += days;
        usageBreakdown.started.percentage += percentage;
        usageBreakdown.started.positions.push(position);
      }
    });

    return {
      season: season,
      total_days: totalDays,
      usage_breakdown: usageBreakdown,
      position_details: stats
    };
  }

  // Get monthly breakdown data
  async getMonthlyBreakdown(playerId, season) {
    const monthlyStats = await database.all(`
      SELECT 
        strftime('%Y-%m', date) as month_year,
        strftime('%B', date) as month_name,
        MIN(date) as earliest_date,
        MAX(date) as latest_date,
        COUNT(*) as total_days,
        selected_position,
        COUNT(*) as position_days
      FROM ${this.tableName}
      WHERE player_id = ? 
      AND strftime('%Y', date) = ?
      GROUP BY month_year, selected_position
      ORDER BY month_year, position_days DESC
    `, [playerId, season.toString()]);

    // Group by month and calculate summaries
    const monthlyData = {};
    
    monthlyStats.forEach(stat => {
      const monthKey = stat.month_year;
      
      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = {
          month: stat.month_name,
          year: parseInt(season),
          month_year: monthKey,
          earliest_date: stat.earliest_date,
          latest_date: stat.latest_date,
          total_days: 0,
          summary: {
            started: 0,
            benched: 0,
            injured_list: 0,
            other_roster: 0,
            not_owned: 0
          },
          positions: []
        };
      }

      monthlyData[monthKey].total_days += stat.position_days;
      monthlyData[monthKey].positions.push({
        position: stat.selected_position,
        days: stat.position_days
      });

      // Categorize into summary buckets
      const position = stat.selected_position;
      if (['BN'].includes(position)) {
        monthlyData[monthKey].summary.benched += stat.position_days;
      } else if (['IL', 'IL10', 'IL15', 'IL60', 'NA'].includes(position)) {
        monthlyData[monthKey].summary.injured_list += stat.position_days;
      } else if (position === 'Not Owned' || position === 'FA') {
        monthlyData[monthKey].summary.not_owned += stat.position_days;
      } else {
        monthlyData[monthKey].summary.started += stat.position_days;
      }
    });

    return Object.values(monthlyData).sort((a, b) => a.month_year.localeCompare(b.month_year));
  }

  // Get available seasons for a player
  async getAvailableSeasons(playerId) {
    const seasons = await database.all(`
      SELECT 
        DISTINCT strftime('%Y', date) as season,
        COUNT(*) as total_days,
        MIN(date) as earliest_date,
        MAX(date) as latest_date
      FROM ${this.tableName}
      WHERE player_id = ?
      GROUP BY strftime('%Y', date)
      ORDER BY season DESC
    `, [playerId]);

    return seasons.map(season => ({
      season: parseInt(season.season),
      total_days: season.total_days,
      earliest_date: season.earliest_date,
      latest_date: season.latest_date
    }));
  }

  // Get timeline data with daily granularity
  async getPlayerTimeline(playerId, season, granularity = 'day') {
    if (granularity === 'month') {
      return this.getMonthlyBreakdown(playerId, season);
    }

    const timeline = await database.all(`
      SELECT 
        date,
        selected_position,
        player_status,
        team_name,
        player_team
      FROM ${this.tableName}
      WHERE player_id = ? 
      AND strftime('%Y', date) = ?
      ORDER BY date ASC
    `, [playerId, season.toString()]);

    return timeline;
  }

  // Search players for autocomplete in player spotlight
  async searchPlayers(query, limit = 10) {
    const players = await database.all(`
      SELECT DISTINCT 
        player_id,
        player_name,
        player_team,
        position_type,
        COUNT(*) as total_appearances
      FROM ${this.tableName}
      WHERE player_name LIKE ?
      GROUP BY player_id, player_name, player_team, position_type
      ORDER BY total_appearances DESC, player_name ASC
      LIMIT ?
    `, [`%${query}%`, limit]);

    return players;
  }
}

module.exports = new PlayerSpotlightService();