/**
 * GKL Fantasy Baseball API - CloudFlare Workers with D1 Database
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    };
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders
      });
    }
    
    try {
      // Health check
      if (pathname === '/health') {
        return new Response(JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          environment: env.ENVIRONMENT || 'production',
          database: 'connected'
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Lineup dates endpoint
      if (pathname === '/lineups/dates') {
        const result = await env.DB.prepare(
          "SELECT DISTINCT date FROM daily_lineups ORDER BY date DESC LIMIT 30"
        ).all();
        
        const dates = result.results.map(row => row.date);
        
        return new Response(JSON.stringify(dates), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Lineup teams endpoint
      if (pathname === '/lineups/teams') {
        const result = await env.DB.prepare(
          "SELECT DISTINCT team_key, team_name FROM daily_lineups WHERE team_name IS NOT NULL ORDER BY team_name"
        ).all();
        
        return new Response(JSON.stringify(result.results), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Lineup by date endpoint
      const dateMatch = pathname.match(/^\/lineups\/date\/(\d{4}-\d{2}-\d{2})$/);
      if (dateMatch) {
        const date = dateMatch[1];
        
        // Get all lineups for the date
        const result = await env.DB.prepare(`
          SELECT 
            team_key,
            team_name,
            date,
            player_id,
            player_name,
            selected_position,
            position_type,
            player_status,
            eligible_positions,
            player_team
          FROM daily_lineups
          WHERE date = ?
          ORDER BY team_name, 
            CASE 
              WHEN position_type = 'B' AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') THEN 1
              WHEN position_type = 'P' AND selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') THEN 2
              WHEN selected_position = 'BN' THEN 3
              ELSE 4
            END,
            selected_position
        `).bind(date).all();
        
        // Group players by team and calculate summary stats
        const teamMap = {};
        const uniquePlayers = new Set();
        let totalBenched = 0;
        let totalInjured = 0;
        
        for (const row of result.results) {
          if (!teamMap[row.team_key]) {
            teamMap[row.team_key] = {
              team_key: row.team_key,
              team_name: row.team_name,
              date: row.date,
              players: []
            };
          }
          
          teamMap[row.team_key].players.push({
            player_id: row.player_id,
            player_name: row.player_name,
            selected_position: row.selected_position,
            position_type: row.position_type,
            player_status: row.player_status,
            eligible_positions: row.eligible_positions,
            player_team: row.player_team
          });
          
          // Track unique players
          uniquePlayers.add(row.player_id);
          
          // Count benched and injured
          if (row.selected_position === 'BN') {
            totalBenched++;
          }
          if (['IL', 'IL10', 'IL60', 'NA'].includes(row.selected_position)) {
            totalInjured++;
          }
        }
        
        const lineups = Object.values(teamMap);
        
        // Calculate summary statistics
        const summary = {
          teams: lineups.length,
          unique_players: uniquePlayers.size,
          benched: totalBenched,
          injured: totalInjured
        };
        
        // Return just the lineups array (frontend expects this format)
        return new Response(JSON.stringify(lineups), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Lineup summary endpoint
      const summaryMatch = pathname.match(/^\/lineups\/summary\/(\d{4}-\d{2}-\d{2})$/);
      if (summaryMatch) {
        const date = summaryMatch[1];
        
        // Get summary statistics for the date
        const result = await env.DB.prepare(`
          SELECT 
            COUNT(DISTINCT team_key) as teams,
            COUNT(DISTINCT player_id) as unique_players,
            SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched,
            SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60', 'NA') THEN 1 ELSE 0 END) as injured
          FROM daily_lineups
          WHERE date = ?
        `).bind(date).first();
        
        const summary = {
          teams: result?.teams || 0,
          unique_players: result?.unique_players || 0,
          benched: result?.benched || 0,
          injured: result?.injured || 0
        };
        
        return new Response(JSON.stringify(summary), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Transaction filters endpoint
      if (pathname === '/transactions/filters') {
        try {
          // Get unique teams (just the names)
          const teamsResult = await env.DB.prepare(`
            SELECT DISTINCT source_team_name as team_name 
            FROM transactions 
            WHERE source_team_name IS NOT NULL AND source_team_name != ''
            ORDER BY source_team_name
          `).all();
          
          // Get transaction types (add/drop/trade)
          const typesResult = await env.DB.prepare(`
            SELECT DISTINCT movement_type 
            FROM transactions 
            WHERE movement_type IS NOT NULL 
            ORDER BY movement_type
          `).all();
          
          // Get MLB teams
          const mlbTeamsResult = await env.DB.prepare(`
            SELECT DISTINCT player_team 
            FROM transactions 
            WHERE player_team IS NOT NULL AND player_team != ''
            ORDER BY player_team
          `).all();
          
          // Get positions - return standard position categories
          // Rather than raw position strings, we'll return proper position categories
          const positions = [
            'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF',
            'SP', 'RP'
          ];
          
          // Get date range
          const dateRange = await env.DB.prepare(`
            SELECT 
              MIN(DATE(date)) as min_date,
              MAX(DATE(date)) as max_date
            FROM transactions
          `).first();
          
          const response = {
            transactionTypes: typesResult?.results?.map(t => t.movement_type) || [],
            movementTypes: typesResult?.results?.map(t => t.movement_type) || [],
            teams: teamsResult?.results?.map(t => t.team_name) || [],
            positions: positions,
            mlbTeams: mlbTeamsResult?.results?.map(t => t.player_team) || [],
            dateRange: dateRange || { min_date: null, max_date: null }
          };
          
          return new Response(JSON.stringify(response), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          console.error('Filter error:', error);
          return new Response(JSON.stringify({
            transactionTypes: [],
            movementTypes: [],
            teams: [],
            positions: [],
            mlbTeams: [],
            dateRange: { min_date: null, max_date: null }
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Transaction stats endpoint
      if (pathname === '/transactions/stats') {
        try {
          // Get overview stats - count distinct transaction_id for add, add/drop, and trade types
          const overview = await env.DB.prepare(`
            SELECT 
              COUNT(DISTINCT transaction_id) as total_transactions,
              COUNT(DISTINCT CASE WHEN source_team_name IS NOT NULL AND source_team_name != '' THEN source_team_key ELSE destination_team_key END) as total_teams,
              COUNT(DISTINCT player_name) as unique_players
            FROM transactions
            WHERE transaction_type IN ('add', 'add/drop', 'trade')
              AND (
                (source_team_name IS NOT NULL AND source_team_name != '') OR
                (destination_team_name IS NOT NULL AND destination_team_name != '')
              )
          `).first();
          
          // Get manager stats - count distinct transaction_id for transactions where team is involved
          const managerStats = await env.DB.prepare(`
            SELECT 
              team_name,
              team_key,
              COUNT(DISTINCT transaction_id) as transaction_count
            FROM (
              SELECT DISTINCT
                source_team_name as team_name,
                source_team_key as team_key,
                transaction_id
              FROM transactions
              WHERE source_team_name IS NOT NULL 
                AND source_team_name != ''
                AND transaction_type IN ('add', 'add/drop', 'trade')
              
              UNION
              
              SELECT DISTINCT
                destination_team_name as team_name,
                destination_team_key as team_key,
                transaction_id
              FROM transactions
              WHERE destination_team_name IS NOT NULL 
                AND destination_team_name != ''
                AND transaction_type IN ('add', 'add/drop', 'trade')
            ) team_transactions
            WHERE team_name IS NOT NULL AND team_name != ''
            GROUP BY team_key, team_name
            ORDER BY transaction_count DESC
          `).all();
          
          // Get most dropped player
          const mostDropped = await env.DB.prepare(`
            SELECT 
              player_name,
              player_id,
              COUNT(*) as drop_count
            FROM transactions
            WHERE movement_type = 'drop' AND player_name IS NOT NULL
            GROUP BY player_name, player_id
            ORDER BY drop_count DESC
            LIMIT 1
          `).first();
          
          return new Response(JSON.stringify({
            overview: overview || {},
            managerStats: managerStats.results || [],
            recentActivity: [],
            mostDroppedPlayer: mostDropped || null
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          console.error('Stats error:', error);
          return new Response(JSON.stringify({
            overview: {},
            managerStats: [],
            recentActivity: [],
            mostDroppedPlayer: null
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Transactions list endpoint
      if (pathname === '/transactions') {
        const page = parseInt(url.searchParams.get('page')) || 1;
        const limit = Math.min(parseInt(url.searchParams.get('limit')) || 20, 100);
        const offset = (page - 1) * limit;
        
        // Get filter parameters
        const search = url.searchParams.get('search') || '';
        const transactionType = url.searchParams.get('transactionType') || '';
        const movementType = url.searchParams.get('movementType') || '';
        const teamName = url.searchParams.get('teamName') || '';
        const playerTeam = url.searchParams.get('playerTeam') || '';
        const playerPosition = url.searchParams.get('playerPosition') || '';
        const startDate = url.searchParams.get('startDate') || '';
        const endDate = url.searchParams.get('endDate') || '';
        
        try {
          // Build WHERE clause
          const conditions = [];
          const bindings = [];
          
          if (search) {
            conditions.push("player_name LIKE ?");
            bindings.push(`%${search}%`);
          }
          
          if (movementType) {
            conditions.push("movement_type = ?");
            bindings.push(movementType);
          }
          
          if (teamName) {
            conditions.push("(source_team_name = ? OR destination_team_name = ?)");
            bindings.push(teamName, teamName);
          }
          
          if (playerTeam) {
            conditions.push("player_team = ?");
            bindings.push(playerTeam);
          }
          
          if (playerPosition) {
            // Special handling for DH - also match Util
            if (playerPosition === 'DH') {
              conditions.push("(player_position = ? OR player_position LIKE ? OR player_position LIKE ? OR player_position = ? OR player_position LIKE ? OR player_position LIKE ?)");
              bindings.push('DH', 'DH,%', '%,DH,%', 'Util', 'Util,%', '%,Util,%');
            } else {
              // Match exact position or position in comma-separated list
              // This ensures "C" doesn't match "CF" and "RF" doesn't match other positions
              conditions.push("(player_position = ? OR player_position LIKE ? OR player_position LIKE ? OR player_position LIKE ?)");
              bindings.push(
                playerPosition,                    // Exact match (e.g., "C")
                `${playerPosition},%`,             // At start (e.g., "C,1B")
                `%,${playerPosition},%`,           // In middle (e.g., "1B,C,2B")
                `%,${playerPosition}`              // At end (e.g., "1B,C")
              );
            }
          }
          
          if (startDate) {
            conditions.push("DATE(date) >= ?");
            bindings.push(startDate);
          }
          
          if (endDate) {
            conditions.push("DATE(date) <= ?");
            bindings.push(endDate);
          }
          
          const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
          
          // Query with filters
          const query = `
            SELECT * FROM transactions 
            ${whereClause}
            ORDER BY date DESC, created_at DESC
            LIMIT ? OFFSET ?
          `;
          bindings.push(limit, offset);
          
          const result = await env.DB.prepare(query).bind(...bindings).all();
          
          // Count query with same filters (excluding limit/offset)
          const countBindings = bindings.slice(0, -2);
          const countQuery = `SELECT COUNT(*) as total FROM transactions ${whereClause}`;
          const countResult = await env.DB.prepare(countQuery).bind(...countBindings).first();
          
          return new Response(JSON.stringify({
            transactions: result.results || [],
            data: result.results || [],
            pagination: {
              page,
              limit,
              total: countResult?.total || 0,
              totalPages: Math.ceil((countResult?.total || 0) / limit)
            }
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          return new Response(JSON.stringify({
            transactions: [],
            data: [],
            pagination: { page: 1, limit: 20, total: 0, totalPages: 0 }
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player spotlight endpoint
      const playerSpotlightMatch = pathname.match(/^\/players\/(\d+)\/spotlight$/);
      if (playerSpotlightMatch) {
        const playerId = playerSpotlightMatch[1];
        const season = parseInt(url.searchParams.get('season')) || 2025;
        
        try {
          // Get player basic info from latest lineup
          const playerInfo = await env.DB.prepare(`
            SELECT DISTINCT
              player_id,
              player_name,
              player_team,
              position_type,
              eligible_positions,
              player_status,
              team_name as current_fantasy_team
            FROM daily_lineups
            WHERE player_id = ?
            ORDER BY date DESC
            LIMIT 1
          `).bind(playerId).first();
          
          if (!playerInfo) {
            return new Response(JSON.stringify({ error: 'Player not found' }), {
              status: 404,
              headers: { 'Content-Type': 'application/json', ...corsHeaders }
            });
          }
          
          // Get team history
          const teamHistory = await env.DB.prepare(`
            SELECT 
              team_name,
              COUNT(*) as days,
              MIN(date) as from_date,
              MAX(date) as to_date
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY team_name
            ORDER BY MAX(date) DESC
          `).bind(playerId).all();
          
          // The first team in results (ordered by MAX(date) DESC) is the current team
          const actualCurrentTeam = teamHistory.results?.[0]?.team_name || playerInfo.current_fantasy_team;
          
          // Update playerInfo with the correct current team
          playerInfo.current_fantasy_team = actualCurrentTeam;
          
          // Calculate total days for percentages
          const totalDaysAllTeams = teamHistory.results?.reduce((sum, team) => sum + team.days, 0) || 0;
          
          // Format team history with percentages
          const formattedTeamHistory = teamHistory.results?.map(team => ({
            team_name: team.team_name,
            days: team.days,
            percentage: totalDaysAllTeams > 0 ? (team.days / totalDaysAllTeams * 100) : 0,
            from_date: team.from_date,
            to_date: team.to_date
          })) || [];
          
          // Get usage breakdown per team
          const usageByTeam = await env.DB.prepare(`
            SELECT 
              team_name,
              COUNT(*) as total_days,
              SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') THEN 1 ELSE 0 END) as started_days,
              SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched_days,
              SUM(CASE WHEN selected_position = 'NA' THEN 1 ELSE 0 END) as minor_league_days,
              SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60') THEN 1 ELSE 0 END) as injured_days
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY team_name
          `).bind(playerId).all();
          
          // Calculate totals and separate current vs other teams
          let totalDays = 0;
          let startedDays = 0;
          let benchedDays = 0;
          let minorLeagueDays = 0;
          let injuredDays = 0;
          let currentTeamDays = 0;
          let otherTeamDays = 0;
          const otherTeams = [];
          
          for (const team of usageByTeam.results || []) {
            totalDays += team.total_days;
            startedDays += team.started_days;
            benchedDays += team.benched_days;
            minorLeagueDays += team.minor_league_days;
            injuredDays += team.injured_days;
            
            if (team.team_name === playerInfo.current_fantasy_team) {
              currentTeamDays = team.total_days;
            } else {
              otherTeamDays += team.total_days;
              // Create team object with required properties
              otherTeams.push({
                name: team.team_name,
                days: team.total_days,
                percentage: totalDays > 0 ? (team.total_days / totalDays * 100) : 0
              });
            }
          }
          
          // Get actual date range from database to determine season coverage
          const dateRangeResult = await env.DB.prepare(`
            SELECT 
              MIN(date) as min_date,
              MAX(date) as max_date
            FROM daily_lineups
          `).first();
          
          const minDate = dateRangeResult?.min_date || '2025-07-01';
          const maxDate = dateRangeResult?.max_date || '2025-08-03';
          
          // Generate months that contain any database data (extend to full calendar months)
          const generateSeasonMonths = (startDate, endDate) => {
            const months = [];
            const start = new Date(startDate);
            const end = new Date(endDate);
            
            // Start from the beginning of the first month
            const current = new Date(start.getFullYear(), start.getMonth(), 1);
            // End at the end of the last month
            const endMonth = new Date(end.getFullYear(), end.getMonth() + 1, 0);
            
            while (current <= endMonth) {
              const monthYear = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}`;
              months.push(monthYear);
              current.setMonth(current.getMonth() + 1);
            }
            return months;
          };
          
          const seasonMonths = generateSeasonMonths(minDate, maxDate);
          
          // Get full days in each calendar month (not constrained by database range)
          const getFullDaysInMonth = (monthYear) => {
            const [year, month] = monthYear.split('-');
            const monthEnd = new Date(parseInt(year), parseInt(month), 0);
            return monthEnd.getDate();
          };
          
          // Get actual days in each month within the database range (for data processing)
          const getDataDaysInMonth = (monthYear) => {
            const [year, month] = monthYear.split('-');
            const monthStart = new Date(parseInt(year), parseInt(month) - 1, 1);
            const monthEnd = new Date(parseInt(year), parseInt(month), 0);
            
            // Constrain to actual database dates
            const seasonStart = new Date(minDate);
            const seasonEnd = new Date(maxDate);
            
            const actualStart = monthStart < seasonStart ? seasonStart : monthStart;
            const actualEnd = monthEnd > seasonEnd ? seasonEnd : monthEnd;
            
            if (actualStart > actualEnd) return 0;
            
            // Calculate days between dates
            const timeDiff = actualEnd.getTime() - actualStart.getTime();
            return Math.floor(timeDiff / (1000 * 3600 * 24)) + 1;
          };
          
          // Get monthly breakdown with team and position details
          const monthlyData = await env.DB.prepare(`
            SELECT 
              strftime('%Y-%m', date) as month_year,
              team_name,
              selected_position,
              COUNT(*) as days,
              MIN(date) as period_start,
              MAX(date) as period_end
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY strftime('%Y-%m', date), team_name, selected_position
            ORDER BY month_year ASC, team_name, selected_position
          `).bind(playerId).all();
          
          // Get current date to determine future days
          const today = new Date();
          const currentDateStr = today.toISOString().split('T')[0]; // YYYY-MM-DD format
          
          // Initialize complete season with all months
          const monthlyGrouped = {};
          for (const monthYear of seasonMonths) {
            const fullDaysInMonth = getFullDaysInMonth(monthYear);
            const dataDaysInMonth = getDataDaysInMonth(monthYear);
            
            // Calculate future days (days that haven't happened yet in the calendar month)
            const [year, month] = monthYear.split('-');
            const monthStart = new Date(parseInt(year), parseInt(month) - 1, 1);
            const monthEnd = new Date(parseInt(year), parseInt(month), 0);
            
            let futureDays = 0;
            if (today <= monthEnd) {
              // Calculate days from today through end of month
              const futureStart = today > monthStart ? new Date(today.getTime() + 24*60*60*1000) : monthStart; // Start from tomorrow
              if (futureStart <= monthEnd) {
                const timeDiff = monthEnd.getTime() - futureStart.getTime();
                futureDays = Math.floor(timeDiff / (1000 * 3600 * 24)) + 1;
              }
            }
            
            const pastDays = fullDaysInMonth - futureDays;
            
            monthlyGrouped[monthYear] = {
              month_year: monthYear,
              total_days: fullDaysInMonth,
              started: 0,
              benched: 0,
              minor_leagues: 0,
              injured_list: 0,
              not_rostered: 0, // Will be calculated after processing all roster data
              future_days: futureDays,
              data_days: dataDaysInMonth, // Track how many days have data
              teams: {},
              positions: []
            };
          }
          // Fill in actual roster data
          for (const row of monthlyData.results || []) {
            const month = monthlyGrouped[row.month_year];
            if (!month) continue; // Skip months outside season range
            
            // Initialize team if not exists
            if (!month.teams[row.team_name]) {
              month.teams[row.team_name] = {
                team_name: row.team_name,
                days: 0,
                percentage: 0,
                positions: []
              };
            }
            
            // Don't modify not_rostered here - we'll calculate it after all data is processed
            
            if (!['BN', 'IL', 'IL10', 'IL60', 'NA'].includes(row.selected_position)) {
              month.started += row.days;
            } else if (row.selected_position === 'BN') {
              month.benched += row.days;
            } else if (row.selected_position === 'NA') {
              month.minor_leagues += row.days;
            } else if (['IL', 'IL10', 'IL60'].includes(row.selected_position)) {
              month.injured_list += row.days;
            }
            
            // Update team data
            month.teams[row.team_name].days += row.days;
            month.teams[row.team_name].positions.push({
              position: row.selected_position,
              team: row.team_name,
              days: row.days,
              period_start: row.period_start,
              period_end: row.period_end
            });
            
            // Add to overall positions list
            month.positions.push({
              position: row.selected_position,
              team: row.team_name,
              days: row.days,
              period_start: row.period_start,
              period_end: row.period_end
            });
          }
          
          // Calculate team percentages, not_rostered days, and sort positions chronologically for each month
          for (const month of Object.values(monthlyGrouped)) {
            // Calculate total rostered days for this month
            const totalRosteredDays = month.started + month.benched + month.minor_leagues + month.injured_list;
            
            // Calculate not_rostered as the difference between data days and rostered days
            // This ensures we only show "not rostered" for days where data exists but player wasn't on a team
            month.not_rostered = Math.max(0, month.data_days - totalRosteredDays);
            
            // Sort overall positions chronologically
            month.positions.sort((a, b) => (a.period_start || '').localeCompare(b.period_start || ''));
            
            for (const team of Object.values(month.teams)) {
              team.percentage = month.total_days > 0 ? (team.days / month.total_days * 100) : 0;
              // Sort team positions chronologically  
              team.positions.sort((a, b) => (a.period_start || '').localeCompare(b.period_start || ''));
            }
          }
          
          const response = {
            player: {
              player_id: playerInfo.player_id,
              player_name: playerInfo.player_name,
              player_team: playerInfo.player_team,
              position_type: playerInfo.position_type,
              eligible_positions: playerInfo.eligible_positions,
              player_status: playerInfo.player_status,
              current_fantasy_team: playerInfo.current_fantasy_team,
              current_team_since: formattedTeamHistory.length > 0 ? formattedTeamHistory[0].from_date : '2025-03-27',
              team_history: formattedTeamHistory
            },
            season: season,
            usage_breakdown: {
              season: season,
              total_days: totalDays,
              current_team_days: currentTeamDays,
              other_team_days: otherTeamDays,
              current_team: playerInfo.current_fantasy_team,
              usage_breakdown: {
                started: {
                  days: startedDays,
                  percentage: totalDays > 0 ? (startedDays / totalDays * 100) : 0,
                  positions: playerInfo.eligible_positions.split(',')
                },
                benched: {
                  days: benchedDays,
                  percentage: totalDays > 0 ? (benchedDays / totalDays * 100) : 0,
                  positions: ['BN']
                },
                injured_list: {
                  days: injuredDays,
                  percentage: totalDays > 0 ? (injuredDays / totalDays * 100) : 0,
                  positions: []
                },
                minor_leagues: {
                  days: minorLeagueDays,
                  percentage: totalDays > 0 ? (minorLeagueDays / totalDays * 100) : 0,
                  positions: []
                },
                other_roster: {
                  days: otherTeamDays,
                  percentage: totalDays > 0 ? (otherTeamDays / totalDays * 100) : 0,
                  positions: [],
                  teams: otherTeams
                },
                not_rostered: {
                  days: 0,
                  percentage: 0,
                  positions: []
                }
              }
            },
            monthly_data: Object.values(monthlyGrouped).map(month => ({
              month_year: month.month_year,
              total_days: month.total_days,
              future_days: month.future_days || 0,
              summary: {
                started: month.started || 0,
                benched: month.benched || 0,
                minor_leagues: month.minor_leagues || 0,
                injured_list: month.injured_list || 0,
                other_roster: 0,
                not_rostered: Math.max(0, month.not_rostered) || 0
              },
              teams: Object.values(month.teams),
              positions: month.positions
            })) || []
          };
          
          return new Response(JSON.stringify(response), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          console.error('Player spotlight error:', error);
          return new Response(JSON.stringify({
            error: 'Failed to fetch player data',
            message: error.message
          }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Debug endpoint - test specific player stats
      if (pathname === '/debug/player-stats') {
        try {
          // Get a player with actual stats data
          const playerWithStats = await env.DB.prepare(`
            SELECT * FROM daily_gkl_player_stats 
            WHERE player_name LIKE '%Scherzer%' OR player_name LIKE '%Verlander%'
            LIMIT 1
          `).first();
          
          return new Response(JSON.stringify({
            message: 'Player with stats',
            player_data: playerWithStats || {}
          }, null, 2), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
          
        } catch (error) {
          return new Response(JSON.stringify({ 
            error: error.message
          }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }

      // Debug endpoint - test JOIN
      if (pathname === '/debug/join-test') {
        try {
          // Test if JOIN is working at all
          const joinTest = await env.DB.prepare(`
            SELECT COUNT(*) as join_count
            FROM daily_gkl_player_stats s
            JOIN daily_lineups l ON s.yahoo_player_id = l.player_id AND s.date = l.date
            LIMIT 1
          `).first();
          
          // Check sample data from both tables
          const statsPlayers = await env.DB.prepare(`
            SELECT DISTINCT yahoo_player_id, date FROM daily_gkl_player_stats ORDER BY date DESC LIMIT 10
          `).all();
          
          const lineupPlayers = await env.DB.prepare(`
            SELECT DISTINCT player_id, date FROM daily_lineups ORDER BY date DESC LIMIT 10
          `).all();
          
          return new Response(JSON.stringify({
            message: 'JOIN test',
            join_count: joinTest?.join_count || 0,
            stats_players: statsPlayers?.results || [],
            lineup_players: lineupPlayers?.results || []
          }, null, 2), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
          
        } catch (error) {
          return new Response(JSON.stringify({ 
            error: error.message
          }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }

      // Debug endpoint to check database tables and data
      if (pathname === '/debug/tables') {
        try {
          // Check if daily_gkl_player_stats table exists and get sample data
          const tablesQuery = await env.DB.prepare(`
            SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
          `).all();
          
          let statsTableInfo = { exists: false, sampleData: null, count: 0 };
          
          try {
            const statsCount = await env.DB.prepare(`
              SELECT COUNT(*) as count FROM daily_gkl_player_stats LIMIT 1
            `).first();
            
            const sampleStats = await env.DB.prepare(`
              SELECT * FROM daily_gkl_player_stats LIMIT 5
            `).all();
            
            statsTableInfo = {
              exists: true,
              count: statsCount?.count || 0,
              sampleData: sampleStats?.results || []
            };
          } catch (error) {
            statsTableInfo.error = error.message;
          }
          
          return new Response(JSON.stringify({
            tables: tablesQuery?.results || [],
            daily_gkl_player_stats: statsTableInfo,
            debug_timestamp: new Date().toISOString()
          }, null, 2), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
          
        } catch (error) {
          return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }

      // Debug endpoint for player usage
      const debugUsageMatch = pathname.match(/^\/debug\/player-usage\/(\d+)$/);
      if (debugUsageMatch) {
        const playerId = debugUsageMatch[1];
        
        try {
          const usageByTeam = await env.DB.prepare(`
            SELECT 
              team_name,
              COUNT(*) as total_days,
              SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') THEN 1 ELSE 0 END) as started_days,
              SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched_days,
              SUM(CASE WHEN selected_position = 'NA' THEN 1 ELSE 0 END) as minor_league_days,
              SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60') THEN 1 ELSE 0 END) as injured_days
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY team_name
          `).bind(playerId).all();
          
          const playerInfo = await env.DB.prepare(`
            SELECT player_name, COUNT(*) as total_records
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY player_name
          `).bind(playerId).first();
          
          return new Response(JSON.stringify({
            player_id: playerId,
            player_name: playerInfo?.player_name,
            total_records: playerInfo?.total_records,
            usage_by_team: usageByTeam.results
          }, null, 2), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player performance breakdown endpoint
      const performanceMatch = pathname.match(/^\/players\/(\d+)\/performance-breakdown$/);
      if (performanceMatch) {
        const playerId = performanceMatch[1];
        const season = parseInt(url.searchParams.get('season')) || 2025;
        
        try {
          // Get current team for this player
          const currentTeamResult = await env.DB.prepare(`
            SELECT team_name
            FROM daily_lineups
            WHERE player_id = ?
            ORDER BY date DESC
            LIMIT 1
          `).bind(playerId).first();
          
          const currentTeam = currentTeamResult?.team_name;
          
          // Get usage breakdown by team
          const usageByTeam = await env.DB.prepare(`
            SELECT 
              team_name,
              COUNT(*) as total_days,
              SUM(CASE WHEN selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA') THEN 1 ELSE 0 END) as started_days,
              SUM(CASE WHEN selected_position = 'BN' THEN 1 ELSE 0 END) as benched_days,
              SUM(CASE WHEN selected_position = 'NA' THEN 1 ELSE 0 END) as minor_league_days,
              SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60') THEN 1 ELSE 0 END) as injured_days
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY team_name
          `).bind(playerId).all();
          
          // Separate current team vs other teams
          let currentTeamUsage = { total_days: 0, started_days: 0, benched_days: 0, minor_league_days: 0, injured_days: 0 };
          let otherTeamsUsage = { total_days: 0, started_days: 0, benched_days: 0, minor_league_days: 0, injured_days: 0 };
          const otherTeamsList = [];
          
          for (const team of usageByTeam.results || []) {
            if (team.team_name === currentTeam) {
              currentTeamUsage = team;
            } else {
              otherTeamsUsage.total_days += team.total_days;
              otherTeamsUsage.started_days += team.started_days;
              otherTeamsUsage.benched_days += team.benched_days;
              otherTeamsUsage.minor_league_days += team.minor_league_days;
              otherTeamsUsage.injured_days += team.injured_days;
              
              otherTeamsList.push({
                team_name: team.team_name,
                days: team.total_days,
                started_days: team.started_days,
                benched_days: team.benched_days,
                minor_league_days: team.minor_league_days,
                injured_days: team.injured_days
              });
            }
          }
          
          // Get player type
          const playerInfo = await env.DB.prepare(`
            SELECT position_type
            FROM daily_lineups
            WHERE player_id = ?
            LIMIT 1
          `).bind(playerId).first();
          
          const isPitcher = playerInfo?.position_type === 'P';
          
          // Get stats aggregated by roster situation and team
          const getStatsForSituation = async (situationFilter, teamFilter = '') => {
            try {
              // First try to find the player in daily_gkl_player_stats using player name
              const playerNameResult = await env.DB.prepare(`
                SELECT player_name FROM daily_lineups WHERE player_id = ? LIMIT 1
              `).bind(playerId).first();
              
              if (!playerNameResult?.player_name) {
                console.log('Could not find player name for ID:', playerId);
                return {};
              }
              
              // Try to match by player name in the stats table
              const statsResult = await env.DB.prepare(`
                SELECT 
                  COALESCE(SUM(s.batting_runs), 0) as runs,
                  COALESCE(SUM(s.batting_hits), 0) as hits,
                  COALESCE(SUM(s.batting_triples), 0) as triples,
                  COALESCE(SUM(s.batting_home_runs), 0) as home_runs,
                  COALESCE(SUM(s.batting_rbis), 0) as rbis,
                  COALESCE(SUM(s.batting_stolen_bases), 0) as stolen_bases,
                  COALESCE(SUM(s.batting_at_bats), 0) as at_bats,
                  COALESCE(SUM(s.batting_walks), 0) as walks,
                  COALESCE(SUM(s.batting_hit_by_pitch), 0) as hbp,
                  COALESCE(SUM(s.batting_sacrifice_flies), 0) as sf,
                  COALESCE(SUM(s.batting_total_bases), 0) as total_bases,
                  COALESCE(SUM(s.pitching_games_started), 0) as appearances,
                  COALESCE(SUM(s.pitching_wins), 0) as wins,
                  COALESCE(SUM(s.pitching_saves), 0) as saves,
                  COALESCE(SUM(s.pitching_strikeouts), 0) as strikeouts,
                  COALESCE(SUM(s.pitching_holds), 0) as holds,
                  COALESCE(SUM(s.pitching_earned_runs), 0) as earned_runs,
                  COALESCE(SUM(s.pitching_innings_pitched), 0) as innings_pitched,
                  COALESCE(SUM(s.pitching_hits_allowed), 0) as hits_allowed,
                  COALESCE(SUM(s.pitching_walks_allowed), 0) as pitching_walks,
                  COALESCE(SUM(s.pitching_quality_starts), 0) as quality_starts
                FROM daily_gkl_player_stats s
                WHERE s.player_name = ?
                  AND EXISTS (
                    SELECT 1 FROM daily_lineups l 
                    WHERE l.player_id = ? 
                    AND l.date = s.date
                    ${situationFilter} ${teamFilter}
                  )
              `).bind(playerNameResult.player_name, playerId).first();
              return statsResult || {};
            } catch (error) {
              console.log('Stats query failed for situation:', situationFilter, teamFilter, error);
              return {};
            }
          };

          // Get aggregated stats for all teams (simpler approach for now)
          const startedStats = await getStatsForSituation(
            "AND l.selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')", 
            ''
          );
          const benchedStats = await getStatsForSituation(
            "AND l.selected_position = 'BN'", 
            ''
          );
          const minorLeagueStats = await getStatsForSituation(
            "AND l.selected_position = 'NA'", 
            ''
          );
          const injuredListStats = await getStatsForSituation(
            "AND l.selected_position IN ('IL', 'IL10', 'IL60')", 
            ''
          );
          
          // Get stats for each individual other team (for expandable view)
          const otherTeamsDetailedStats = [];
          for (const team of otherTeamsList) {
            const teamStartedStats = await getStatsForSituation(
              "AND l.selected_position NOT IN ('BN', 'IL', 'IL10', 'IL60', 'NA')", 
              `AND l.team_name = '${team.team_name.replace(/'/g, "''")}'`
            );
            const teamBenchedStats = await getStatsForSituation(
              "AND l.selected_position = 'BN'", 
              `AND l.team_name = '${team.team_name.replace(/'/g, "''")}'`
            );
            
            otherTeamsDetailedStats.push({
              team_name: team.team_name,
              days: team.days,
              started_days: team.started_days,
              benched_days: team.benched_days,
              started_stats: teamStartedStats,
              benched_stats: teamBenchedStats
            });
          }

          // Calculation functions
          const calculateAvg = (hits, atBats) => atBats > 0 ? hits / atBats : 0;
          const calculateOBP = (hits, walks, hbp, atBats, sf) => {
            const denominator = atBats + walks + hbp + sf;
            return denominator > 0 ? (hits + walks + hbp) / denominator : 0;
          };
          const calculateSLG = (totalBases, atBats) => atBats > 0 ? totalBases / atBats : 0;
          const calculateERA = (earnedRuns, inningsPitched) => inningsPitched > 0 ? (earnedRuns * 9) / inningsPitched : 0;
          const calculateWHIP = (hits, walks, inningsPitched) => inningsPitched > 0 ? (hits + walks) / inningsPitched : 0;
          const calculateKBB = (strikeouts, walks) => walks > 0 ? strikeouts / walks : strikeouts > 0 ? strikeouts : 0;

          // Calculate total usage across all teams
          let totalUsage = { started_days: 0, benched_days: 0, minor_league_days: 0, injured_days: 0 };
          for (const team of usageByTeam.results || []) {
            totalUsage.started_days += team.started_days || 0;
            totalUsage.benched_days += team.benched_days || 0;
            totalUsage.minor_league_days += team.minor_league_days || 0;
            totalUsage.injured_days += team.injured_days || 0;
          }
          
          // Create performance breakdown response using aggregated stats
          const breakdown = {
            player_type: isPitcher ? 'pitcher' : 'batter',
            usage_breakdown: {
              started: {
                days: totalUsage.started_days || 0,
                stats: {
                  batting: {
                    R: startedStats?.runs || 0,
                    H: startedStats?.hits || 0,
                    '3B': startedStats?.triples || 0,
                    HR: startedStats?.home_runs || 0,
                    RBI: startedStats?.rbis || 0,
                    SB: startedStats?.stolen_bases || 0,
                    AVG: calculateAvg(startedStats?.hits, startedStats?.at_bats),
                    OBP: calculateOBP(startedStats?.hits, startedStats?.walks, startedStats?.hbp, startedStats?.at_bats, startedStats?.sf),
                    SLG: calculateSLG(startedStats?.total_bases, startedStats?.at_bats)
                  },
                  pitching: {
                    APP: startedStats?.appearances || 0,
                    W: startedStats?.wins || 0,
                    SV: startedStats?.saves || 0,
                    K: startedStats?.strikeouts || 0,
                    HLD: startedStats?.holds || 0,
                    ERA: calculateERA(startedStats?.earned_runs, startedStats?.innings_pitched),
                    WHIP: calculateWHIP(startedStats?.hits_allowed, startedStats?.pitching_walks, startedStats?.innings_pitched),
                    'K/BB': calculateKBB(startedStats?.strikeouts, startedStats?.pitching_walks),
                    QS: startedStats?.quality_starts || 0
                  }
                }
              },
              benched: {
                days: totalUsage.benched_days || 0,
                stats: {
                  batting: {
                    R: benchedStats?.runs || 0,
                    H: benchedStats?.hits || 0,
                    '3B': benchedStats?.triples || 0,
                    HR: benchedStats?.home_runs || 0,
                    RBI: benchedStats?.rbis || 0,
                    SB: benchedStats?.stolen_bases || 0,
                    AVG: calculateAvg(benchedStats?.hits, benchedStats?.at_bats),
                    OBP: calculateOBP(benchedStats?.hits, benchedStats?.walks, benchedStats?.hbp, benchedStats?.at_bats, benchedStats?.sf),
                    SLG: calculateSLG(benchedStats?.total_bases, benchedStats?.at_bats)
                  },
                  pitching: {
                    APP: benchedStats?.appearances || 0,
                    W: benchedStats?.wins || 0,
                    SV: benchedStats?.saves || 0,
                    K: benchedStats?.strikeouts || 0,
                    HLD: benchedStats?.holds || 0,
                    ERA: calculateERA(benchedStats?.earned_runs, benchedStats?.innings_pitched),
                    WHIP: calculateWHIP(benchedStats?.hits_allowed, benchedStats?.pitching_walks, benchedStats?.innings_pitched),
                    'K/BB': calculateKBB(benchedStats?.strikeouts, benchedStats?.pitching_walks),
                    QS: benchedStats?.quality_starts || 0
                  }
                }
              },
              minor_leagues: {
                days: totalUsage.minor_league_days || 0,
                stats: {
                  batting: {
                    R: minorLeagueStats?.runs || 0,
                    H: minorLeagueStats?.hits || 0,
                    '3B': minorLeagueStats?.triples || 0,
                    HR: minorLeagueStats?.home_runs || 0,
                    RBI: minorLeagueStats?.rbis || 0,
                    SB: minorLeagueStats?.stolen_bases || 0,
                    AVG: calculateAvg(minorLeagueStats?.hits, minorLeagueStats?.at_bats),
                    OBP: calculateOBP(minorLeagueStats?.hits, minorLeagueStats?.walks, minorLeagueStats?.hbp, minorLeagueStats?.at_bats, minorLeagueStats?.sf),
                    SLG: calculateSLG(minorLeagueStats?.total_bases, minorLeagueStats?.at_bats)
                  },
                  pitching: {
                    APP: minorLeagueStats?.appearances || 0,
                    W: minorLeagueStats?.wins || 0,
                    SV: minorLeagueStats?.saves || 0,
                    K: minorLeagueStats?.strikeouts || 0,
                    HLD: minorLeagueStats?.holds || 0,
                    ERA: calculateERA(minorLeagueStats?.earned_runs, minorLeagueStats?.innings_pitched),
                    WHIP: calculateWHIP(minorLeagueStats?.hits_allowed, minorLeagueStats?.pitching_walks, minorLeagueStats?.innings_pitched),
                    'K/BB': calculateKBB(minorLeagueStats?.strikeouts, minorLeagueStats?.pitching_walks),
                    QS: minorLeagueStats?.quality_starts || 0
                  }
                }
              },
              injured_list: {
                days: totalUsage.injured_days || 0,
                stats: {
                  batting: {
                    R: injuredListStats?.runs || 0,
                    H: injuredListStats?.hits || 0,
                    '3B': injuredListStats?.triples || 0,
                    HR: injuredListStats?.home_runs || 0,
                    RBI: injuredListStats?.rbis || 0,
                    SB: injuredListStats?.stolen_bases || 0,
                    AVG: calculateAvg(injuredListStats?.hits, injuredListStats?.at_bats),
                    OBP: calculateOBP(injuredListStats?.hits, injuredListStats?.walks, injuredListStats?.hbp, injuredListStats?.at_bats, injuredListStats?.sf),
                    SLG: calculateSLG(injuredListStats?.total_bases, injuredListStats?.at_bats)
                  },
                  pitching: {
                    APP: injuredListStats?.appearances || 0,
                    W: injuredListStats?.wins || 0,
                    SV: injuredListStats?.saves || 0,
                    K: injuredListStats?.strikeouts || 0,
                    HLD: injuredListStats?.holds || 0,
                    ERA: calculateERA(injuredListStats?.earned_runs, injuredListStats?.innings_pitched),
                    WHIP: calculateWHIP(injuredListStats?.hits_allowed, injuredListStats?.pitching_walks, injuredListStats?.innings_pitched),
                    'K/BB': calculateKBB(injuredListStats?.strikeouts, injuredListStats?.pitching_walks),
                    QS: injuredListStats?.quality_starts || 0
                  }
                }
              },
              other_roster: {
                days: otherTeamsList.reduce((sum, team) => sum + team.days, 0),
                stats: {
                  batting: {
                    R: (otherTeamsStartedStats?.runs || 0) + (otherTeamsBenchedStats?.runs || 0),
                    H: (otherTeamsStartedStats?.hits || 0) + (otherTeamsBenchedStats?.hits || 0),
                    '3B': (otherTeamsStartedStats?.triples || 0) + (otherTeamsBenchedStats?.triples || 0),
                    HR: (otherTeamsStartedStats?.home_runs || 0) + (otherTeamsBenchedStats?.home_runs || 0),
                    RBI: (otherTeamsStartedStats?.rbis || 0) + (otherTeamsBenchedStats?.rbis || 0),
                    SB: (otherTeamsStartedStats?.stolen_bases || 0) + (otherTeamsBenchedStats?.stolen_bases || 0),
                    AVG: calculateAvg(
                      (otherTeamsStartedStats?.hits || 0) + (otherTeamsBenchedStats?.hits || 0),
                      (otherTeamsStartedStats?.at_bats || 0) + (otherTeamsBenchedStats?.at_bats || 0)
                    ),
                    OBP: calculateOBP(
                      (otherTeamsStartedStats?.hits || 0) + (otherTeamsBenchedStats?.hits || 0),
                      (otherTeamsStartedStats?.walks || 0) + (otherTeamsBenchedStats?.walks || 0),
                      (otherTeamsStartedStats?.hbp || 0) + (otherTeamsBenchedStats?.hbp || 0),
                      (otherTeamsStartedStats?.at_bats || 0) + (otherTeamsBenchedStats?.at_bats || 0),
                      (otherTeamsStartedStats?.sf || 0) + (otherTeamsBenchedStats?.sf || 0)
                    ),
                    SLG: calculateSLG(
                      (otherTeamsStartedStats?.total_bases || 0) + (otherTeamsBenchedStats?.total_bases || 0),
                      (otherTeamsStartedStats?.at_bats || 0) + (otherTeamsBenchedStats?.at_bats || 0)
                    )
                  },
                  pitching: {
                    APP: (otherTeamsStartedStats?.appearances || 0) + (otherTeamsBenchedStats?.appearances || 0),
                    W: (otherTeamsStartedStats?.wins || 0) + (otherTeamsBenchedStats?.wins || 0),
                    SV: (otherTeamsStartedStats?.saves || 0) + (otherTeamsBenchedStats?.saves || 0),
                    K: (otherTeamsStartedStats?.strikeouts || 0) + (otherTeamsBenchedStats?.strikeouts || 0),
                    HLD: (otherTeamsStartedStats?.holds || 0) + (otherTeamsBenchedStats?.holds || 0),
                    ERA: calculateERA(
                      (otherTeamsStartedStats?.earned_runs || 0) + (otherTeamsBenchedStats?.earned_runs || 0),
                      (otherTeamsStartedStats?.innings_pitched || 0) + (otherTeamsBenchedStats?.innings_pitched || 0)
                    ),
                    WHIP: calculateWHIP(
                      (otherTeamsStartedStats?.hits_allowed || 0) + (otherTeamsBenchedStats?.hits_allowed || 0),
                      (otherTeamsStartedStats?.pitching_walks || 0) + (otherTeamsBenchedStats?.pitching_walks || 0),
                      (otherTeamsStartedStats?.innings_pitched || 0) + (otherTeamsBenchedStats?.innings_pitched || 0)
                    ),
                    'K/BB': calculateKBB(
                      (otherTeamsStartedStats?.strikeouts || 0) + (otherTeamsBenchedStats?.strikeouts || 0),
                      (otherTeamsStartedStats?.pitching_walks || 0) + (otherTeamsBenchedStats?.pitching_walks || 0)
                    ),
                    QS: (otherTeamsStartedStats?.quality_starts || 0) + (otherTeamsBenchedStats?.quality_starts || 0)
                  }
                },
                teams: otherTeamsDetailedStats.map(team => ({
                  team_name: team.team_name,
                  days: team.days,
                  stats: {
                    batting: {
                      R: (team.started_stats?.runs || 0) + (team.benched_stats?.runs || 0),
                      H: (team.started_stats?.hits || 0) + (team.benched_stats?.hits || 0),
                      '3B': (team.started_stats?.triples || 0) + (team.benched_stats?.triples || 0),
                      HR: (team.started_stats?.home_runs || 0) + (team.benched_stats?.home_runs || 0),
                      RBI: (team.started_stats?.rbis || 0) + (team.benched_stats?.rbis || 0),
                      SB: (team.started_stats?.stolen_bases || 0) + (team.benched_stats?.stolen_bases || 0),
                      AVG: calculateAvg(
                        (team.started_stats?.hits || 0) + (team.benched_stats?.hits || 0),
                        (team.started_stats?.at_bats || 0) + (team.benched_stats?.at_bats || 0)
                      ),
                      OBP: calculateOBP(
                        (team.started_stats?.hits || 0) + (team.benched_stats?.hits || 0),
                        (team.started_stats?.walks || 0) + (team.benched_stats?.walks || 0),
                        (team.started_stats?.hbp || 0) + (team.benched_stats?.hbp || 0),
                        (team.started_stats?.at_bats || 0) + (team.benched_stats?.at_bats || 0),
                        (team.started_stats?.sf || 0) + (team.benched_stats?.sf || 0)
                      ),
                      SLG: calculateSLG(
                        (team.started_stats?.total_bases || 0) + (team.benched_stats?.total_bases || 0),
                        (team.started_stats?.at_bats || 0) + (team.benched_stats?.at_bats || 0)
                      )
                    },
                    pitching: {
                      APP: (team.started_stats?.appearances || 0) + (team.benched_stats?.appearances || 0),
                      W: (team.started_stats?.wins || 0) + (team.benched_stats?.wins || 0),
                      SV: (team.started_stats?.saves || 0) + (team.benched_stats?.saves || 0),
                      K: (team.started_stats?.strikeouts || 0) + (team.benched_stats?.strikeouts || 0),
                      HLD: (team.started_stats?.holds || 0) + (team.benched_stats?.holds || 0),
                      ERA: calculateERA(
                        (team.started_stats?.earned_runs || 0) + (team.benched_stats?.earned_runs || 0),
                        (team.started_stats?.innings_pitched || 0) + (team.benched_stats?.innings_pitched || 0)
                      ),
                      WHIP: calculateWHIP(
                        (team.started_stats?.hits_allowed || 0) + (team.benched_stats?.hits_allowed || 0),
                        (team.started_stats?.pitching_walks || 0) + (team.benched_stats?.pitching_walks || 0),
                        (team.started_stats?.innings_pitched || 0) + (team.benched_stats?.innings_pitched || 0)
                      ),
                      'K/BB': calculateKBB(
                        (team.started_stats?.strikeouts || 0) + (team.benched_stats?.strikeouts || 0),
                        (team.started_stats?.pitching_walks || 0) + (team.benched_stats?.pitching_walks || 0)
                      ),
                      QS: (team.started_stats?.quality_starts || 0) + (team.benched_stats?.quality_starts || 0)
                    }
                  }
                }))
              }
            },
            metadata: {
              season: season,
              player_id: playerId,
              generated_at: new Date().toISOString(),
              data_source: 'daily_gkl_player_stats'
            }
          };
          
          return new Response(JSON.stringify(breakdown), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          // If stats table doesn't exist or error, return minimal valid structure
          console.error('Performance breakdown error for player', playerId, ':', error);
          console.error('Error stack:', error.stack);
          return new Response(JSON.stringify({
            player_type: 'batter',
            usage_breakdown: {
              started: {
                days: 0,
                stats: {
                  batting: {
                    R: 0, H: 0, '3B': 0, HR: 0, RBI: 0, SB: 0,
                    AVG: 0, OBP: 0, SLG: 0
                  },
                  pitching: {
                    APP: 0, W: 0, SV: 0, K: 0, HLD: 0,
                    ERA: 0, WHIP: 0, 'K/BB': 0, QS: 0
                  }
                }
              },
              benched: {
                days: 0,
                stats: {
                  batting: {
                    R: 0, H: 0, '3B': 0, HR: 0, RBI: 0, SB: 0,
                    AVG: 0, OBP: 0, SLG: 0
                  },
                  pitching: {
                    APP: 0, W: 0, SV: 0, K: 0, HLD: 0,
                    ERA: 0, WHIP: 0, 'K/BB': 0, QS: 0
                  }
                }
              },
              minor_leagues: {
                days: 0,
                stats: {
                  batting: {
                    R: 0, H: 0, '3B': 0, HR: 0, RBI: 0, SB: 0,
                    AVG: 0, OBP: 0, SLG: 0
                  },
                  pitching: {
                    APP: 0, W: 0, SV: 0, K: 0, HLD: 0,
                    ERA: 0, WHIP: 0, 'K/BB': 0, QS: 0
                  }
                }
              },
              injured_list: {
                days: 0,
                stats: {
                  batting: {
                    R: 0, H: 0, '3B': 0, HR: 0, RBI: 0, SB: 0,
                    AVG: 0, OBP: 0, SLG: 0
                  },
                  pitching: {
                    APP: 0, W: 0, SV: 0, K: 0, HLD: 0,
                    ERA: 0, WHIP: 0, 'K/BB': 0, QS: 0
                  }
                }
              }
            },
            metadata: {
              season: season,
              player_id: playerId,
              generated_at: new Date().toISOString(),
              data_source: 'daily_gkl_player_stats'
            }
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player timeline endpoint
      const playerTimelineMatch = pathname.match(/^\/players\/(\d+)\/timeline$/);
      if (playerTimelineMatch) {
        const playerId = playerTimelineMatch[1];
        
        return new Response(JSON.stringify({
          timeline: [],
          summary: {}
        }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }
      
      // Player seasons endpoint
      const playerSeasonsMatch = pathname.match(/^\/players\/(\d+)\/seasons$/);
      if (playerSeasonsMatch) {
        return new Response(JSON.stringify({
          seasons: [2025]
        }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }
      
      // Players search/list
      if (pathname === '/players' || pathname === '/players/search') {
        return new Response(JSON.stringify({
          players: [],
          total: 0
        }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }
      
      // Player search positions endpoint
      if (pathname === '/player-search/positions') {
        try {
          const positions = await env.DB.prepare(`
            SELECT DISTINCT eligible_positions 
            FROM daily_lineups 
            WHERE eligible_positions IS NOT NULL
          `).all();
          
          // Extract unique positions from comma-separated values
          const allPositions = new Set();
          positions.results?.forEach(row => {
            if (row.eligible_positions) {
              row.eligible_positions.split(',').forEach(pos => {
                allPositions.add(pos.trim());
              });
            }
          });
          
          // Sort positions in logical baseball order
          const positionOrder = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'Util', 'DH', 'OF', 'IF', 'SP', 'RP', 'P', 'IL', 'IL10', 'IL15', 'IL60', 'NA'];
          const sortedPositions = Array.from(allPositions).sort((a, b) => {
            const aIndex = positionOrder.indexOf(a);
            const bIndex = positionOrder.indexOf(b);
            
            // If both positions are in the order array, sort by index
            if (aIndex !== -1 && bIndex !== -1) {
              return aIndex - bIndex;
            }
            // If only one is in the order array, prioritize it
            if (aIndex !== -1) return -1;
            if (bIndex !== -1) return 1;
            // If neither is in the order array, sort alphabetically
            return a.localeCompare(b);
          });
          
          return new Response(JSON.stringify(sortedPositions), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          return new Response(JSON.stringify([]), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player search MLB teams endpoint
      if (pathname === '/player-search/teams') {
        try {
          const teams = await env.DB.prepare(`
            SELECT DISTINCT player_team 
            FROM daily_lineups 
            WHERE player_team IS NOT NULL AND player_team != ''
            ORDER BY player_team
          `).all();
          
          return new Response(JSON.stringify(teams.results?.map(t => t.player_team) || []), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          return new Response(JSON.stringify([]), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player search GKL teams endpoint
      if (pathname === '/player-search/gkl-teams') {
        try {
          const teams = await env.DB.prepare(`
            SELECT DISTINCT team_name 
            FROM daily_lineups 
            WHERE team_name IS NOT NULL AND team_name != ''
            ORDER BY team_name
          `).all();
          
          return new Response(JSON.stringify(teams.results?.map(t => t.team_name) || []), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          return new Response(JSON.stringify([]), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Player search endpoint
      if (pathname === '/player-search/search') {
        try {
          const search = url.searchParams.get('search') || '';
          const position = url.searchParams.get('position') || '';
          const mlbTeam = url.searchParams.get('mlbTeam') || '';
          const gklTeam = url.searchParams.get('gklTeam') || '';
          const page = parseInt(url.searchParams.get('page')) || 1;
          const limit = Math.min(parseInt(url.searchParams.get('limit')) || 20, 100);
          const offset = (page - 1) * limit;
          
          // Build WHERE clause
          const conditions = [];
          const bindings = [];
          
          if (search) {
            conditions.push("player_name LIKE ?");
            bindings.push(`%${search}%`);
          }
          
          if (position) {
            conditions.push("eligible_positions LIKE ?");
            bindings.push(`%${position}%`);
          }
          
          if (mlbTeam) {
            conditions.push("player_team = ?");
            bindings.push(mlbTeam);
          }
          
          if (gklTeam) {
            conditions.push("team_name = ?");
            bindings.push(gklTeam);
          }
          
          const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
          
          // Get players with all stats and transaction info
          const query = `
            WITH player_summary AS (
              SELECT 
                player_id,
                player_name,
                MAX(player_team) as mlb_team,
                MAX(team_name) as most_recent_team,
                MAX(eligible_positions) as position,
                MAX(player_status) as health_status,
                COUNT(*) as days_rostered,
                MAX(date) as last_seen
              FROM daily_lineups
              ${whereClause}
              GROUP BY player_id, player_name
            ),
            transaction_stats AS (
              SELECT 
                player_id,
                COUNT(*) as transaction_count,
                SUM(CASE WHEN movement_type = 'add' THEN 1 ELSE 0 END) as times_added,
                SUM(CASE WHEN movement_type = 'drop' THEN 1 ELSE 0 END) as times_dropped
              FROM transactions
              GROUP BY player_id
            )
            SELECT 
              ps.*,
              COALESCE(ts.transaction_count, 0) as transaction_count,
              COALESCE(ts.times_added, 0) as times_added,
              COALESCE(ts.times_dropped, 0) as times_dropped,
              CASE 
                WHEN ps.days_rostered > 0 THEN 'Rostered'
                ELSE 'Free Agent'
              END as roster_status
            FROM player_summary ps
            LEFT JOIN transaction_stats ts ON ps.player_id = ts.player_id
            ORDER BY ps.player_name
            LIMIT ? OFFSET ?
          `;
          
          bindings.push(limit, offset);
          
          const result = await env.DB.prepare(query).bind(...bindings).all();
          
          // Get total count
          const countQuery = `
            SELECT COUNT(DISTINCT player_id) as total
            FROM daily_lineups
            ${whereClause}
          `;
          
          const countBindings = bindings.slice(0, -2); // Remove limit and offset
          const countResult = await env.DB.prepare(countQuery).bind(...countBindings).first();
          
          return new Response(JSON.stringify({
            players: result.results || [],
            total: countResult?.total || 0,
            page,
            limit,
            totalPages: Math.ceil((countResult?.total || 0) / limit)
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        } catch (error) {
          console.error('Player search error:', error);
          return new Response(JSON.stringify({
            players: [],
            total: 0,
            page: 1,
            limit: 20,
            totalPages: 0
          }), {
            headers: { 'Content-Type': 'application/json', ...corsHeaders }
          });
        }
      }
      
      // Default lineup response
      if (pathname.startsWith('/lineups')) {
        return new Response(JSON.stringify({
          lineups: [],
          summary: { teams: 0, unique_players: 0, benched: 0, injured: 0 }
        }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders }
        });
      }
      
      // Not found
      return new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
      
    } catch (error) {
      console.error('Worker error:', error);
      return new Response(JSON.stringify({
        error: 'Internal Server Error',
        message: error.message
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...corsHeaders }
      });
    }
  }
};