const database = require('./database');
const { getTableName, getEnvironment } = require('../config/database');
const { getSeasonDays, getSeasonDateRange, daysBetween } = require('../config/seasonDates');
const playerStatsService = require('./playerStatsService');

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
      
      // Get team history for the season
      const teamHistory = await this.getTeamHistory(playerId, season);
      
      // Add team history to player info
      playerInfo.team_history = teamHistory;
      
      // Get season usage statistics (filtered by current team)
      const usageStats = await this.getSeasonUsageStats(playerId, season, playerInfo.current_fantasy_team);
      
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
        yahoo_player_id,
        player_name,
        player_team,
        position_type,
        eligible_positions,
        player_status,
        team_name as current_fantasy_team,
        date as current_team_since
      FROM ${this.tableName}
      WHERE yahoo_player_id = ?
      ORDER BY date DESC
      LIMIT 1
    `, [playerId]);

    if (!player) {
      throw new Error(`Player with ID ${playerId} not found`);
    }

    // Get the actual date when player joined current team
    const teamStartDate = await database.get(`
      SELECT MIN(date) as start_date
      FROM ${this.tableName}
      WHERE yahoo_player_id = ?
      AND team_name = ?
      AND date <= ?
      AND date > COALESCE(
        (SELECT MAX(date) 
         FROM ${this.tableName} 
         WHERE yahoo_player_id = ? 
         AND team_name != ? 
         AND date < ?),
        '1900-01-01'
      )
    `, [playerId, player.current_fantasy_team, player.current_team_since, 
        playerId, player.current_fantasy_team, player.current_team_since]);

    player.current_team_since = teamStartDate?.start_date || player.current_team_since;

    return player;
  }

  // Get team history for a player in a season
  async getTeamHistory(playerId, season) {
    const teams = await database.all(`
      SELECT 
        team_name,
        COUNT(*) as days,
        MIN(date) as from_date,
        MAX(date) as to_date,
        COUNT(*) * 100.0 / (
          SELECT COUNT(*) 
          FROM ${this.tableName} 
          WHERE yahoo_player_id = ? 
          AND strftime('%Y', date) = ?
        ) as percentage
      FROM ${this.tableName}
      WHERE yahoo_player_id = ?
      AND strftime('%Y', date) = ?
      GROUP BY team_name
      ORDER BY MIN(date)
    `, [playerId, season.toString(), playerId, season.toString()]);

    return teams.map(team => ({
      team_name: team.team_name,
      days: team.days,
      percentage: team.percentage,
      from_date: team.from_date,
      to_date: team.to_date
    }));
  }

  // Get season usage statistics with percentages
  async getSeasonUsageStats(playerId, season, currentTeam = null) {
    // If no current team provided, get it from player info
    if (!currentTeam) {
      const playerInfo = await this.getPlayerBasicInfo(playerId);
      currentTeam = playerInfo.current_fantasy_team;
    }

    // Get stats for current team only
    const stats = await database.all(`
      SELECT 
        selected_position,
        COUNT(*) as days,
        COUNT(*) * 100.0 / (
          SELECT COUNT(*) 
          FROM ${this.tableName} 
          WHERE yahoo_player_id = ? 
          AND strftime('%Y', date) = ?
          AND team_name = ?
        ) as percentage
      FROM ${this.tableName}
      WHERE yahoo_player_id = ? 
      AND strftime('%Y', date) = ?
      AND team_name = ?
      GROUP BY selected_position
      ORDER BY days DESC
    `, [playerId, season.toString(), currentTeam, playerId, season.toString(), currentTeam]);

    // Get total days on current team
    const currentTeamResult = await database.get(`
      SELECT COUNT(*) as total_days
      FROM ${this.tableName}
      WHERE yahoo_player_id = ? 
      AND strftime('%Y', date) = ?
      AND team_name = ?
    `, [playerId, season.toString(), currentTeam]);

    // Get days on other teams
    const otherTeamResult = await database.get(`
      SELECT COUNT(*) as other_days
      FROM ${this.tableName}
      WHERE yahoo_player_id = ? 
      AND strftime('%Y', date) = ?
      AND team_name != ?
    `, [playerId, season.toString(), currentTeam]);

    const currentTeamDays = currentTeamResult?.total_days || 0;
    const otherTeamDays = otherTeamResult?.other_days || 0;
    const totalRosteredDays = currentTeamDays + otherTeamDays;
    
    // Get total season days to calculate "Not Owned" accurately
    const totalSeasonDays = getSeasonDays(season);
    const notOwnedDays = Math.max(0, totalSeasonDays - totalRosteredDays);

    // Categorize positions into usage types
    const usageBreakdown = {
      started: { days: 0, percentage: 0, positions: [] },
      benched: { days: 0, percentage: 0, positions: [] },
      injured_list: { days: 0, percentage: 0, positions: [] },
      minor_leagues: { days: 0, percentage: 0, positions: [] },
      other_roster: { days: otherTeamDays, percentage: (otherTeamDays / totalSeasonDays) * 100, positions: [], teams: [] },
      not_rostered: { days: notOwnedDays, percentage: (notOwnedDays / totalSeasonDays) * 100, positions: [] }
    };

    // Get team breakdown for other rosters
    if (otherTeamDays > 0) {
      const otherTeams = await database.all(`
        SELECT 
          team_name,
          COUNT(*) as days
        FROM ${this.tableName}
        WHERE yahoo_player_id = ?
        AND strftime('%Y', date) = ?
        AND team_name != ?
        GROUP BY team_name
        ORDER BY days DESC
      `, [playerId, season.toString(), currentTeam]);

      usageBreakdown.other_roster.teams = otherTeams.map(team => ({
        name: team.team_name,
        days: team.days,
        percentage: (team.days / totalSeasonDays) * 100
      }));
    }

    stats.forEach(stat => {
      const position = stat.selected_position;
      const days = stat.days;
      // Recalculate percentage based on total season days
      const percentage = (days / totalSeasonDays) * 100;

      if (['BN'].includes(position)) {
        usageBreakdown.benched.days += days;
        usageBreakdown.benched.percentage = (usageBreakdown.benched.days / totalSeasonDays) * 100;
        usageBreakdown.benched.positions.push(position);
      } else if (['IL', 'IL10', 'IL15', 'IL60'].includes(position)) {
        // Only actual IL positions, not NA
        usageBreakdown.injured_list.days += days;
        usageBreakdown.injured_list.percentage = (usageBreakdown.injured_list.days / totalSeasonDays) * 100;
        usageBreakdown.injured_list.positions.push(position);
      } else if (position === 'NA') {
        // NA is Minor Leagues, not injured
        usageBreakdown.minor_leagues.days += days;
        usageBreakdown.minor_leagues.percentage = (usageBreakdown.minor_leagues.days / totalSeasonDays) * 100;
        usageBreakdown.minor_leagues.positions.push(position);
      } else if (position === 'Not Owned' || position === 'FA' || position === 'Not Rostered') {
        usageBreakdown.not_rostered.days += days;
        usageBreakdown.not_rostered.percentage = (usageBreakdown.not_rostered.days / totalSeasonDays) * 100;
        if (!usageBreakdown.not_rostered.positions.includes(position)) {
          usageBreakdown.not_rostered.positions.push(position);
        }
      } else {
        // Active positions (C, 1B, 2B, etc.)
        usageBreakdown.started.days += days;
        usageBreakdown.started.percentage = (usageBreakdown.started.days / totalSeasonDays) * 100;
        usageBreakdown.started.positions.push(position);
      }
    });

    // Ensure not_rostered has the correct days if there are unaccounted days
    if (usageBreakdown.not_rostered.days > 0 && usageBreakdown.not_rostered.positions.length === 0) {
      usageBreakdown.not_rostered.positions.push('Not Rostered');
    }

    return {
      season: season,
      total_days: totalSeasonDays,
      current_team_days: currentTeamDays,
      other_team_days: otherTeamDays,
      current_team: currentTeam,
      usage_breakdown: usageBreakdown,
      position_details: stats
    };
  }

  // Get monthly breakdown data
  async getMonthlyBreakdown(playerId, season) {
    const monthlyStats = await database.all(`
      SELECT 
        strftime('%Y-%m', date) as month_year,
        CASE strftime('%m', date)
          WHEN '01' THEN 'January'
          WHEN '02' THEN 'February'
          WHEN '03' THEN 'March'
          WHEN '04' THEN 'April'
          WHEN '05' THEN 'May'
          WHEN '06' THEN 'June'
          WHEN '07' THEN 'July'
          WHEN '08' THEN 'August'
          WHEN '09' THEN 'September'
          WHEN '10' THEN 'October'
          WHEN '11' THEN 'November'
          WHEN '12' THEN 'December'
        END as month_name,
        MIN(date) as earliest_date,
        MAX(date) as latest_date,
        MIN(date) as period_start,
        MAX(date) as period_end,
        selected_position,
        team_name,
        COUNT(*) as position_days
      FROM ${this.tableName}
      WHERE yahoo_player_id = ? 
      AND strftime('%Y', date) = ?
      GROUP BY month_year, month_name, selected_position, team_name
      ORDER BY month_year, MIN(date), team_name, selected_position
    `, [playerId, season.toString()]);
    
    // Get actual total days per month from database
    const monthTotals = await database.all(`
      SELECT 
        strftime('%Y-%m', date) as month_year,
        COUNT(DISTINCT date) as total_days
      FROM ${this.tableName}
      WHERE yahoo_player_id = ?
      AND strftime('%Y', date) = ?
      GROUP BY month_year
    `, [playerId, season.toString()]);

    // Helper function to get actual calendar days in a month
    const getCalendarDaysInMonth = (year, month) => {
      const monthNum = parseInt(month);
      return new Date(year, monthNum, 0).getDate(); // Last day of month = total days
    };

    // Helper function to get day counts for a month (total, past, future) considering season boundaries
    const getMonthDayBreakdown = (year, month) => {
      const monthNum = parseInt(month);
      const today = new Date();
      const currentYear = today.getFullYear();
      const currentMonth = today.getMonth() + 1; // getMonth() returns 0-based
      
      // Get the season date range to constrain the month
      const seasonRange = getSeasonDateRange(season);
      const seasonStart = new Date(seasonRange.start);
      const seasonEnd = new Date(seasonRange.end);
      
      // Calculate the actual start and end dates for this month within the season
      const monthStart = new Date(year, monthNum - 1, 1); // month is 1-based, Date constructor expects 0-based
      const monthEnd = new Date(year, monthNum, 0); // Last day of the month
      
      const effectiveStart = monthStart < seasonStart ? seasonStart : monthStart;
      const effectiveEnd = monthEnd > seasonEnd ? seasonEnd : monthEnd;
      
      // If effective start is after effective end, this month has no season days
      if (effectiveStart > effectiveEnd) {
        return { total: 0, past: 0, future: 0 };
      }
      
      // Calculate total days in this month within the season
      const totalSeasonDays = Math.floor((effectiveEnd - effectiveStart) / (1000 * 60 * 60 * 24)) + 1;
      
      // If this is a past month, all season days are "past"
      if (year < currentYear || (year === currentYear && monthNum < currentMonth)) {
        return { total: totalSeasonDays, past: totalSeasonDays, future: 0 };
      }
      
      // If this is the current month, split between past and future based on today
      if (year === currentYear && monthNum === currentMonth) {
        const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        
        // Calculate how many season days have passed in this month
        let pastDays = 0;
        let futureDays = 0;
        
        if (todayDate >= effectiveStart) {
          const pastEnd = todayDate < effectiveEnd ? todayDate : effectiveEnd;
          pastDays = Math.floor((pastEnd - effectiveStart) / (1000 * 60 * 60 * 24)) + 1;
          
          if (todayDate < effectiveEnd) {
            futureDays = Math.floor((effectiveEnd - todayDate) / (1000 * 60 * 60 * 24));
          }
        } else {
          // Today is before the season starts in this month
          futureDays = totalSeasonDays;
        }
        
        return { total: totalSeasonDays, past: pastDays, future: futureDays };
      }
      
      // Future months - all season days are future
      return { total: totalSeasonDays, past: 0, future: totalSeasonDays };
    };

    // Create a map of month totals using calendar days (but track past vs future)
    const monthTotalsMap = {};
    const monthFutureDaysMap = {};
    monthTotals.forEach(mt => {
      const [year, month] = mt.month_year.split('-');
      const breakdown = getMonthDayBreakdown(parseInt(year), parseInt(month));
      monthTotalsMap[mt.month_year] = breakdown.total;
      monthFutureDaysMap[mt.month_year] = breakdown.future;
    });
    
    // Group by month and calculate summaries with team information
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
          total_days: monthTotalsMap[monthKey] || 0,  // Use the correct total from the map
          future_days: monthFutureDaysMap[monthKey] || 0,  // Days that haven't happened yet
          summary: {
            started: 0,
            benched: 0,
            injured_list: 0,
            minor_leagues: 0,
            other_roster: 0,
            not_rostered: 0
          },
          positions: [],
          teams: {}  // Track team-specific data
        };
      }

      // Initialize team data if not exists
      if (!monthlyData[monthKey].teams[stat.team_name]) {
        monthlyData[monthKey].teams[stat.team_name] = {
          team_name: stat.team_name,
          days: 0,
          positions: [],
          summary: {
            started: 0,
            benched: 0,
            injured_list: 0,
            not_rostered: 0
          }
        };
      }
      monthlyData[monthKey].positions.push({
        position: stat.selected_position,
        team: stat.team_name,
        days: stat.position_days,
        period_start: stat.period_start,
        period_end: stat.period_end
      });

      // Add to team-specific data
      monthlyData[monthKey].teams[stat.team_name].days += stat.position_days;
      monthlyData[monthKey].teams[stat.team_name].positions.push({
        position: stat.selected_position,
        days: stat.position_days,
        period_start: stat.period_start,
        period_end: stat.period_end
      });

      // Categorize into summary buckets
      const position = stat.selected_position;
      if (['BN'].includes(position)) {
        monthlyData[monthKey].summary.benched += stat.position_days;
        monthlyData[monthKey].teams[stat.team_name].summary.benched += stat.position_days;
      } else if (['IL', 'IL10', 'IL15', 'IL60'].includes(position)) {
        monthlyData[monthKey].summary.injured_list += stat.position_days;
        monthlyData[monthKey].teams[stat.team_name].summary.injured_list += stat.position_days;
      } else if (position === 'NA') {
        monthlyData[monthKey].summary.minor_leagues += stat.position_days;
        monthlyData[monthKey].teams[stat.team_name].summary.minor_leagues += stat.position_days;
      } else if (position === 'Not Owned' || position === 'FA') {
        monthlyData[monthKey].summary.not_rostered += stat.position_days;
        monthlyData[monthKey].teams[stat.team_name].summary.not_rostered += stat.position_days;
      } else {
        monthlyData[monthKey].summary.started += stat.position_days;
        monthlyData[monthKey].teams[stat.team_name].summary.started += stat.position_days;
      }
    });

    // Convert teams object to array
    Object.values(monthlyData).forEach(month => {
      month.teams = Object.values(month.teams);
    });

    // Generate missing months from season start to today (or latest database date)
    const seasonRange = getSeasonDateRange(season);
    const today = new Date().toISOString().split('T')[0];
    
    // Determine the end date for month generation
    const latestDbDate = monthlyStats.length > 0 ? 
      Math.max(...monthlyStats.map(s => s.latest_date)) : seasonRange.start;
    const endDate = today < seasonRange.end ? today : seasonRange.end;
    const actualEndDate = latestDbDate > endDate ? latestDbDate : endDate;
    
    // Generate all months from season start to end date
    const existingMonths = new Set(Object.keys(monthlyData));
    const currentDate = new Date(seasonRange.start);
    const finalDate = new Date(actualEndDate);
    
    while (currentDate <= finalDate) {
      const monthKey = currentDate.toISOString().substr(0, 7); // YYYY-MM
      
      if (!existingMonths.has(monthKey)) {
        // Calculate days in this month for the season
        const [yearStr, monthStr] = monthKey.split('-');
        const year = parseInt(yearStr);
        const month = parseInt(monthStr);
        const breakdown = getMonthDayBreakdown(year, month);
        
        // Only create months that have some relevance (past days or current month)
        if (breakdown.past > 0 || (breakdown.future > 0 && breakdown.past === 0 && year === new Date().getFullYear() && month === new Date().getMonth() + 1)) {
          const monthStart = new Date(year, month - 1, 1); // month is 1-based, Date constructor expects 0-based
          const monthEnd = new Date(year, month, 0); // Last day of the month
          
          // Constrain to season dates
          const effectiveStart = monthStart < new Date(seasonRange.start) ? 
            new Date(seasonRange.start) : monthStart;
          const effectiveEnd = monthEnd > new Date(actualEndDate) ? 
            new Date(actualEndDate) : monthEnd;
          
          const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                             'July', 'August', 'September', 'October', 'November', 'December'];
          
          monthlyData[monthKey] = {
            month: monthNames[month - 1], // month is 1-based, array is 0-based
            year: year,
            month_year: monthKey,
            earliest_date: effectiveStart.toISOString().split('T')[0],
            latest_date: effectiveEnd.toISOString().split('T')[0],
            total_days: breakdown.total,
            future_days: breakdown.future,
            summary: {
              started: 0,
              benched: 0,
              injured_list: 0,
              minor_leagues: 0,
              other_roster: 0,
              not_rostered: breakdown.past  // Only past days are "not rostered", future days are handled separately
            },
            positions: [],
            teams: []
          };
        }
      }
      
      // Move to next month
      currentDate.setMonth(currentDate.getMonth() + 1);
    }

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
      WHERE yahoo_player_id = ?
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
      WHERE yahoo_player_id = ? 
      AND strftime('%Y', date) = ?
      ORDER BY date ASC
    `, [playerId, season.toString()]);

    return timeline;
  }

  // Search players for autocomplete in player spotlight
  async searchPlayers(query, limit = 10) {
    const players = await database.all(`
      SELECT DISTINCT 
        yahoo_player_id,
        player_name,
        player_team,
        position_type,
        COUNT(*) as total_appearances
      FROM ${this.tableName}
      WHERE player_name LIKE ?
      GROUP BY yahoo_player_id, player_name, player_team, position_type
      ORDER BY total_appearances DESC, player_name ASC
      LIMIT ?
    `, [`%${query}%`, limit]);

    return players;
  }

  // Get performance breakdown data for a specific player and season
  async getPlayerPerformanceBreakdown(playerId, season = 2025) {
    try {
      // Get performance breakdown from PlayerStatsService
      const performanceData = await playerStatsService.getPerformanceBreakdown(playerId, season);
      
      // Add basic player information for context
      const playerInfo = await this.getPlayerBasicInfo(playerId);
      
      return {
        ...performanceData,
        player_info: {
          yahoo_yahoo_player_id: playerInfo.yahoo_player_id,
          player_name: playerInfo.player_name,
          player_team: playerInfo.player_team,
          position_type: playerInfo.position_type,
          eligible_positions: playerInfo.eligible_positions,
          current_fantasy_team: playerInfo.current_fantasy_team
        }
      };
    } catch (error) {
      console.error('Error getting player performance breakdown:', error);
      throw error;
    }
  }
}

module.exports = new PlayerSpotlightService();