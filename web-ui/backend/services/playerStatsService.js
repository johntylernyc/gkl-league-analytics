const database = require('./database');
const { getTableName, getEnvironment } = require('../config/database');

class PlayerStatsService {
  constructor() {
    this.environment = getEnvironment();
    this.playerStatsTableName = getTableName('daily_gkl_player_stats', this.environment);
    this.lineupsTableName = getTableName('daily_lineups', this.environment);
    this.playerMappingTableName = getTableName('player_id_mapping', this.environment);
  }

  /**
   * Determine if a player is primarily a batter, pitcher, or both
   * @param {string} playerId - Yahoo player ID
   * @param {number} season - Season year
   * @returns {Promise<string>} - 'batter', 'pitcher', or 'both'
   */
  async determinePlayerType(playerName, season) {
    try {
      const stats = await database.get(`
        SELECT 
          COUNT(CASE WHEN has_batting_data = 1 THEN 1 END) as batting_games,
          COUNT(CASE WHEN has_pitching_data = 1 THEN 1 END) as pitching_games,
          SUM(CASE WHEN has_batting_data = 1 THEN batting_at_bats ELSE 0 END) as total_at_bats,
          SUM(CASE WHEN has_pitching_data = 1 THEN pitching_innings_pitched ELSE 0 END) as total_innings
        FROM ${this.playerStatsTableName}
        WHERE player_name = ? 
        AND strftime('%Y', date) = ?
        AND (has_batting_data = 1 OR has_pitching_data = 1)
      `, [playerName, season.toString()]);

      if (!stats) {
        return 'batter'; // Default to batter if no stats found
      }

      const { batting_games, pitching_games, total_at_bats, total_innings } = stats;
      
      // If player has significant activity in both areas, classify as 'both'
      if (batting_games >= 5 && pitching_games >= 5 && total_at_bats >= 50 && total_innings >= 10) {
        return 'both';
      }
      
      // If more pitching activity, classify as pitcher
      if (pitching_games > batting_games || (pitching_games > 0 && total_at_bats < 20)) {
        return 'pitcher';
      }
      
      // Default to batter
      return 'batter';
    } catch (error) {
      console.error('Error determining player type:', error);
      return 'batter'; // Safe fallback
    }
  }

  /**
   * Calculate batting statistics with proper ratio handling
   * @param {Array} statsRows - Raw stats data from database
   * @returns {Object} - Aggregated batting statistics
   */
  calculateBattingStats(statsRows) {
    const totals = {
      R: 0,      // Runs
      H: 0,      // Hits
      '3B': 0,   // Triples
      HR: 0,     // Home Runs
      RBI: 0,    // RBIs
      SB: 0,     // Stolen Bases
      AB: 0,     // At Bats (for calculations)
      BB: 0,     // Walks (for OBP)
      HBP: 0,    // Hit by Pitch (for OBP)
      SF: 0,     // Sacrifice Flies (for OBP)
      TB: 0      // Total Bases (for SLG)
    };

    // Sum up the component stats
    statsRows.forEach(row => {
      if (row.has_batting_data) {
        totals.R += row.batting_runs || 0;
        totals.H += row.batting_hits || 0;
        totals['3B'] += row.batting_triples || 0;
        totals.HR += row.batting_home_runs || 0;
        totals.RBI += row.batting_rbis || 0;
        totals.SB += row.batting_stolen_bases || 0;
        totals.AB += row.batting_at_bats || 0;
        totals.BB += row.batting_walks || 0;
        totals.HBP += row.batting_hit_by_pitch || 0;
        totals.SF += row.batting_sacrifice_flies || 0;
        
        // Calculate total bases: Singles + 2*Doubles + 3*Triples + 4*HR
        const singles = (row.batting_hits || 0) - (row.batting_doubles || 0) - (row.batting_triples || 0) - (row.batting_home_runs || 0);
        totals.TB += singles + (2 * (row.batting_doubles || 0)) + (3 * (row.batting_triples || 0)) + (4 * (row.batting_home_runs || 0));
      }
    });

    // Calculate ratios
    const AVG = totals.AB > 0 ? totals.H / totals.AB : 0;
    const OBP = (totals.AB + totals.BB + totals.HBP + totals.SF) > 0 ? 
                (totals.H + totals.BB + totals.HBP) / (totals.AB + totals.BB + totals.HBP + totals.SF) : 0;
    const SLG = totals.AB > 0 ? totals.TB / totals.AB : 0;

    return {
      R: totals.R,
      H: totals.H,
      '3B': totals['3B'],
      HR: totals.HR,
      RBI: totals.RBI,
      SB: totals.SB,
      AVG: parseFloat(AVG.toFixed(3)),
      OBP: parseFloat(OBP.toFixed(3)),
      SLG: parseFloat(SLG.toFixed(3))
    };
  }

  /**
   * Calculate pitching statistics with proper ratio handling
   * @param {Array} statsRows - Raw stats data from database
   * @returns {Object} - Aggregated pitching statistics
   */
  calculatePitchingStats(statsRows) {
    const totals = {
      APP: 0,    // Appearances
      W: 0,      // Wins
      SV: 0,     // Saves
      K: 0,      // Strikeouts
      HLD: 0,    // Holds
      IP: 0,     // Innings Pitched
      ER: 0,     // Earned Runs
      H: 0,      // Hits Allowed
      BB: 0,     // Walks Allowed
      QS: 0      // Quality Starts
    };

    // Sum up the component stats
    statsRows.forEach(row => {
      if (row.has_pitching_data) {
        totals.APP += row.games_played || 0; // Games played as pitcher = appearances
        totals.W += row.pitching_wins || 0;
        totals.SV += row.pitching_saves || 0;
        totals.K += row.pitching_strikeouts || 0;
        totals.HLD += row.pitching_holds || 0;
        totals.IP += row.pitching_innings_pitched || 0;
        totals.ER += row.pitching_earned_runs || 0;
        totals.H += row.pitching_hits_allowed || 0;
        totals.BB += row.pitching_walks_allowed || 0;
        totals.QS += row.pitching_quality_starts || 0;
      }
    });

    // Calculate ratios
    const ERA = totals.IP > 0 ? (totals.ER * 9) / totals.IP : 0;
    const WHIP = totals.IP > 0 ? (totals.H + totals.BB) / totals.IP : 0;
    const K_BB = totals.BB > 0 ? totals.K / totals.BB : (totals.K > 0 ? totals.K : 0);

    return {
      APP: totals.APP,
      W: totals.W,
      SV: totals.SV,
      K: totals.K,
      HLD: totals.HLD,
      ERA: parseFloat(ERA.toFixed(2)),
      WHIP: parseFloat(WHIP.toFixed(3)),
      'K/BB': parseFloat(K_BB.toFixed(2)),
      QS: totals.QS
    };
  }

  /**
   * Get aggregated player statistics by roster usage status
   * @param {string} playerId - Yahoo player ID
   * @param {number} season - Season year
   * @returns {Promise<Object>} - Statistics broken down by usage type
   */
  async getPlayerStatsByUsage(playerId, season) {
    try {
      // First get the player name and current team from lineups table
      const playerInfoQuery = `
        SELECT player_name, team_name as current_team
        FROM ${this.lineupsTableName} 
        WHERE player_id = ? 
        ORDER BY date DESC
        LIMIT 1
      `;
      
      const playerInfoResult = await database.get(playerInfoQuery, [playerId]);
      
      if (!playerInfoResult) {
        console.log(`No player found with ID ${playerId}`);
        return {
          player_type: 'batter',
          usage_breakdown: {}
        };
      }
      
      const playerName = playerInfoResult.player_name;
      const currentTeam = playerInfoResult.current_team;
      console.log(`Found player: ${playerName} (ID: ${playerId}) on team: ${currentTeam}`);

      // Get all stats data with roster status information
      // Join with all lineup entries for this player to determine usage type
      const statsQuery = `
        WITH player_lineup_data AS (
          SELECT 
            date,
            player_id,
            team_name,
            selected_position
          FROM ${this.lineupsTableName}
          WHERE player_name = ?
          AND strftime('%Y', date) = ?
        )
        SELECT 
          s.*,
          pld.selected_position,
          pld.team_name,
          pld.player_id,
          CASE 
            WHEN pld.player_id = ? AND pld.team_name = ? AND pld.selected_position IN ('BN') THEN 'benched'
            WHEN pld.player_id = ? AND pld.team_name = ? AND pld.selected_position IN ('IL', 'IL10', 'IL15', 'IL60') THEN 'injured_list'
            WHEN pld.player_id = ? AND pld.team_name = ? AND pld.selected_position = 'NA' THEN 'minor_leagues'
            WHEN pld.player_id = ? AND pld.team_name = ? AND pld.selected_position IN ('Not Owned', 'FA', 'Not Rostered') THEN 'not_rostered'
            WHEN pld.player_id = ? AND pld.team_name = ? AND pld.selected_position IS NOT NULL AND pld.selected_position NOT IN ('BN', 'IL', 'IL10', 'IL15', 'IL60', 'NA', 'Not Owned', 'FA', 'Not Rostered') THEN 'started'
            WHEN pld.player_id = ? AND pld.team_name != ? THEN 'other_roster'
            WHEN pld.player_id IS NULL THEN 'not_rostered'
            ELSE 'not_rostered'
          END as usage_type
        FROM ${this.playerStatsTableName} s
        LEFT JOIN player_lineup_data pld ON s.date = pld.date
        WHERE s.player_name = ?
        AND strftime('%Y', s.date) = ?
        ORDER BY s.date
      `;

      const allStats = await database.all(statsQuery, [
        playerName, season.toString(), // For CTE
        playerId, currentTeam, // benched
        playerId, currentTeam, // injured_list
        playerId, currentTeam, // minor_leagues
        playerId, currentTeam, // not_rostered (on current team)
        playerId, currentTeam, // started
        playerId, currentTeam, // other_roster check
        playerName, season.toString() // For main WHERE clause
      ]);

      if (!allStats || allStats.length === 0) {
        return {
          player_type: 'batter',
          usage_breakdown: {}
        };
      }

      // Determine player type
      const playerType = await this.determinePlayerType(playerName, season);

      // Group stats by usage type
      const statsByUsage = {};
      allStats.forEach(stat => {
        const usageType = stat.usage_type || 'not_rostered';
        if (!statsByUsage[usageType]) {
          statsByUsage[usageType] = [];
        }
        statsByUsage[usageType].push(stat);
      });

      // Calculate aggregated stats for each usage type
      const usageBreakdown = {};
      Object.keys(statsByUsage).forEach(usageType => {
        const statsRows = statsByUsage[usageType];
        const days = statsRows.length;

        let battingStats = null;
        let pitchingStats = null;

        if (playerType === 'batter' || playerType === 'both') {
          battingStats = this.calculateBattingStats(statsRows);
        }

        if (playerType === 'pitcher' || playerType === 'both') {
          pitchingStats = this.calculatePitchingStats(statsRows);
        }

        usageBreakdown[usageType] = {
          days: days,
          stats: {
            batting: battingStats,
            pitching: pitchingStats
          }
        };
      });

      return {
        player_type: playerType,
        usage_breakdown: usageBreakdown
      };

    } catch (error) {
      console.error('Error getting player stats by usage:', error);
      throw error;
    }
  }

  /**
   * Get performance breakdown for a specific player and season
   * This is the main method called by the API endpoint
   * @param {string} playerId - Yahoo player ID
   * @param {number} season - Season year
   * @returns {Promise<Object>} - Complete performance breakdown data
   */
  async getPerformanceBreakdown(playerId, season) {
    try {
      const result = await this.getPlayerStatsByUsage(playerId, season);
      
      // Add metadata
      result.metadata = {
        season: season,
        player_id: playerId,
        generated_at: new Date().toISOString(),
        data_source: 'daily_gkl_player_stats'
      };

      return result;
    } catch (error) {
      console.error('Error getting performance breakdown:', error);
      throw error;
    }
  }
}

module.exports = new PlayerStatsService();