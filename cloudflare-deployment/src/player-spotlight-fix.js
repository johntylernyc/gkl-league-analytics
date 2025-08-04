// Updated player spotlight logic with multi-team support
// This should replace lines 383-453 in index-with-db.js

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
              SUM(CASE WHEN selected_position IN ('IL', 'IL10', 'IL60', 'NA') THEN 1 ELSE 0 END) as injured_days
            FROM daily_lineups
            WHERE player_id = ?
            GROUP BY team_name
          `).bind(playerId).all();
          
          // Calculate totals and separate current vs other teams
          let totalDays = 0;
          let startedDays = 0;
          let benchedDays = 0;
          let injuredDays = 0;
          let currentTeamDays = 0;
          let otherTeamDays = 0;
          const otherTeams = [];
          
          for (const team of usageByTeam.results || []) {
            totalDays += team.total_days;
            startedDays += team.started_days;
            benchedDays += team.benched_days;
            injuredDays += team.injured_days;
            
            if (team.team_name === playerInfo.current_fantasy_team) {
              currentTeamDays = team.total_days;
            } else {
              otherTeamDays += team.total_days;
              otherTeams.push(team.team_name);
            }
          }
          
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
            ORDER BY month_year DESC, team_name, selected_position
          `).bind(playerId).all();
          
          // Group by month and organize by teams
          const monthlyGrouped = {};
          for (const row of monthlyData.results || []) {
            if (!monthlyGrouped[row.month_year]) {
              monthlyGrouped[row.month_year] = {
                month_year: row.month_year,
                total_days: 0,
                started: 0,
                benched: 0,
                injured_list: 0,
                teams: {},
                positions: []
              };
            }
            
            // Initialize team if not exists
            if (!monthlyGrouped[row.month_year].teams[row.team_name]) {
              monthlyGrouped[row.month_year].teams[row.team_name] = {
                team_name: row.team_name,
                days: 0,
                percentage: 0,
                positions: []
              };
            }
            
            // Update month totals
            monthlyGrouped[row.month_year].total_days += row.days;
            
            if (!['BN', 'IL', 'IL10', 'IL60', 'NA'].includes(row.selected_position)) {
              monthlyGrouped[row.month_year].started += row.days;
            } else if (row.selected_position === 'BN') {
              monthlyGrouped[row.month_year].benched += row.days;
            } else if (['IL', 'IL10', 'IL60', 'NA'].includes(row.selected_position)) {
              monthlyGrouped[row.month_year].injured_list += row.days;
            }
            
            // Update team data
            monthlyGrouped[row.month_year].teams[row.team_name].days += row.days;
            monthlyGrouped[row.month_year].teams[row.team_name].positions.push({
              position: row.selected_position,
              team: row.team_name,
              days: row.days,
              period_start: row.period_start,
              period_end: row.period_end
            });
            
            // Add to overall positions list
            monthlyGrouped[row.month_year].positions.push({
              position: row.selected_position,
              team: row.team_name,
              days: row.days,
              period_start: row.period_start,
              period_end: row.period_end
            });
          }
          
          // Calculate team percentages for each month
          for (const month of Object.values(monthlyGrouped)) {
            for (const team of Object.values(month.teams)) {
              team.percentage = month.total_days > 0 ? (team.days / month.total_days * 100) : 0;
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
                  days: 0,
                  percentage: 0,
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
              summary: {
                started: month.started || 0,
                benched: month.benched || 0,
                injured_list: month.injured_list || 0,
                minor_leagues: 0,
                other_roster: 0,
                not_rostered: 0
              },
              teams: Object.values(month.teams),
              positions: month.positions
            })) || []
          };