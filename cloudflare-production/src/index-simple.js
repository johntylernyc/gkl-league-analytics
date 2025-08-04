/**
 * Simplified GKL Fantasy Baseball API - Cloudflare Workers
 * For debugging deployment issues
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
      // Simple routing
      if (pathname === '/health') {
        return new Response(JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          environment: env.ENVIRONMENT || 'production'
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname === '/transactions/filters') {
        // Simple test response
        return new Response(JSON.stringify({
          teams: [],
          types: ['add', 'drop', 'trade'],
          dateRange: { min_date: '2025-01-01', max_date: '2025-12-31' }
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname === '/transactions/stats') {
        // Simple test response
        return new Response(JSON.stringify({
          overview: {
            total_transactions: 577,
            total_teams: 17,
            unique_players: 353
          },
          managerStats: [],
          recentActivity: []
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname === '/transactions') {
        // Simple test response
        return new Response(JSON.stringify({
          data: [],
          pagination: {
            page: 1,
            limit: 20,
            total: 0,
            totalPages: 0
          }
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Lineup endpoints
      if (pathname === '/lineups/dates') {
        // Return available dates for lineups
        return new Response(JSON.stringify([
          '2025-08-03',
          '2025-08-02',
          '2025-08-01',
          '2025-07-31',
          '2025-07-30',
          '2025-07-29',
          '2025-07-28',
          '2025-07-27',
          '2025-07-26',
          '2025-07-25'
        ]), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname === '/lineups/teams') {
        // Return sample teams from your league
        return new Response(JSON.stringify([
          { team_key: '458.l.6966.t.2', team_name: 'Big Daddy\'s Funk' },
          { team_key: '458.l.6966.t.3', team_name: 'Frank In The House' },
          { team_key: '458.l.6966.t.4', team_name: 'Holy Toledo!' },
          { team_key: '458.l.6966.t.5', team_name: 'Team 5' }
        ]), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname.match(/^\/lineups\/date\/\d{4}-\d{2}-\d{2}$/)) {
        // Return sample lineup data
        return new Response(JSON.stringify([
          {
            team_key: '458.l.6966.t.2',
            team_name: 'Big Daddy\'s Funk',
            date: pathname.split('/').pop(),
            players: [
              {
                player_id: '10882',
                player_name: 'Gregory Soto',
                selected_position: 'P',
                position_type: 'P',
                player_status: 'healthy',
                eligible_positions: 'RP,P',
                player_team: 'NYM'
              },
              {
                player_id: '9095',
                player_name: 'Yu Darvish',
                selected_position: 'SP',
                position_type: 'P',
                player_status: 'healthy',
                eligible_positions: 'SP,P',
                player_team: 'SD'
              },
              {
                player_id: '11397',
                player_name: 'Salvador Perez',
                selected_position: 'C',
                position_type: 'B',
                player_status: 'healthy',
                eligible_positions: 'C,1B',
                player_team: 'KC'
              },
              {
                player_id: '10683',
                player_name: 'Nick Pivetta',
                selected_position: 'BN',
                position_type: 'P',
                player_status: 'healthy',
                eligible_positions: 'SP,P',
                player_team: 'BOS'
              },
              {
                player_id: '12345',
                player_name: 'Max Muncy',
                selected_position: 'IL10',
                position_type: 'B',
                player_status: 'IL10',
                eligible_positions: '3B',
                player_team: 'LAD'
              }
            ]
          },
          {
            team_key: '458.l.6966.t.3',
            team_name: 'Frank In The House',
            date: pathname.split('/').pop(),
            players: [
              {
                player_id: '11111',
                player_name: 'Ronald Acuna Jr.',
                selected_position: 'OF',
                position_type: 'B',
                player_status: 'healthy',
                eligible_positions: 'OF',
                player_team: 'ATL'
              },
              {
                player_id: '22222',
                player_name: 'Freddie Freeman',
                selected_position: '1B',
                position_type: 'B',
                player_status: 'healthy',
                eligible_positions: '1B',
                player_team: 'LAD'
              }
            ]
          }
        ]), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      if (pathname.startsWith('/lineups')) {
        // Return empty lineup data for any other lineup request
        return new Response(JSON.stringify({
          lineups: [],
          summary: {
            teams: 0,
            unique_players: 0,
            benched: 0,
            injured: 0
          }
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Player spotlight endpoints
      if (pathname.startsWith('/player-spotlight/')) {
        return new Response(JSON.stringify({
          player: {
            player_id: 'test',
            name: 'Test Player',
            team: 'TEST'
          },
          stats: {}
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Players endpoints
      if (pathname === '/players') {
        return new Response(JSON.stringify({
          players: [],
          total: 0
        }), {
          headers: {
            'Content-Type': 'application/json',
            ...corsHeaders
          }
        });
      }
      
      // Not found
      return new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
      
    } catch (error) {
      return new Response(JSON.stringify({
        error: 'Internal Server Error',
        message: error.message
      }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          ...corsHeaders
        }
      });
    }
  }
};