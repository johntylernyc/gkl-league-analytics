"""
REST API for Daily Lineups
Provides HTTP endpoints for accessing lineup data.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, date, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from daily_lineups.repository import LineupRepository
from daily_lineups.config import SEASON_DATES, LEAGUE_KEYS

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize repository
repo = LineupRepository(environment="production")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "daily_lineups_api"
    })


@app.route('/api/lineups/date/<date_str>', methods=['GET'])
def get_lineups_by_date(date_str):
    """
    Get lineups for a specific date.
    
    Query params:
        team_key: Optional team filter
    """
    try:
        team_key = request.args.get('team_key')
        lineups = repo.get_lineup_by_date(date_str, team_key)
        
        return jsonify({
            "success": True,
            "date": date_str,
            "team_key": team_key,
            "count": len(lineups),
            "lineups": lineups
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/player/<player_id>', methods=['GET'])
def get_player_usage(player_id):
    """
    Get usage statistics for a player.
    
    Query params:
        start_date: Optional start date
        end_date: Optional end date
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        usage = repo.get_player_usage(player_id, start_date, end_date)
        
        if not usage:
            return jsonify({
                "success": False,
                "error": "Player not found"
            }), 404
        
        return jsonify({
            "success": True,
            "player_id": player_id,
            "usage": usage
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/team/<team_key>/patterns', methods=['GET'])
def get_team_patterns(team_key):
    """
    Get lineup patterns for a team.
    
    Query params:
        start_date: Optional start date
        end_date: Optional end date
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        patterns = repo.get_team_patterns(team_key, start_date, end_date)
        
        return jsonify({
            "success": True,
            "patterns": patterns
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/team/<team_key>/changes', methods=['GET'])
def get_lineup_changes(team_key):
    """
    Find lineup changes between two dates.
    
    Query params:
        date1: First date (required)
        date2: Second date (required)
    """
    try:
        date1 = request.args.get('date1')
        date2 = request.args.get('date2')
        
        if not date1 or not date2:
            return jsonify({
                "success": False,
                "error": "Both date1 and date2 are required"
            }), 400
        
        changes = repo.find_lineup_changes(team_key, date1, date2)
        
        return jsonify({
            "success": True,
            "changes": changes
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/summary/<date_str>', methods=['GET'])
def get_daily_summary(date_str):
    """Get summary statistics for a date."""
    try:
        summary = repo.get_daily_summary(date_str)
        
        return jsonify({
            "success": True,
            "summary": summary
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/search', methods=['GET'])
def search_players():
    """
    Search for players by name.
    
    Query params:
        q: Search term (required)
        min_days: Minimum days rostered (default: 1)
    """
    try:
        search_term = request.args.get('q')
        if not search_term:
            return jsonify({
                "success": False,
                "error": "Search term 'q' is required"
            }), 400
        
        min_days = int(request.args.get('min_days', 1))
        
        players = repo.search_players(search_term, min_days)
        
        return jsonify({
            "success": True,
            "search_term": search_term,
            "count": len(players),
            "players": players
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/player/<player_id>/eligibility', methods=['GET'])
def get_position_eligibility(player_id):
    """
    Get position eligibility for a player.
    
    Query params:
        date: Optional date (defaults to most recent)
    """
    try:
        date_str = request.args.get('date')
        positions = repo.get_position_eligibility(player_id, date_str)
        
        return jsonify({
            "success": True,
            "player_id": player_id,
            "date": date_str or "most_recent",
            "eligible_positions": positions
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/team/<team_key>/turnover', methods=['GET'])
def get_roster_turnover(team_key):
    """
    Analyze roster turnover for a team.
    
    Query params:
        window: Window size in days (default: 7)
    """
    try:
        window_days = int(request.args.get('window', 7))
        turnovers = repo.get_roster_turnover(team_key, window_days)
        
        return jsonify({
            "success": True,
            "team_key": team_key,
            "window_days": window_days,
            "turnovers": turnovers
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/seasons', methods=['GET'])
def get_available_seasons():
    """Get list of available seasons with data."""
    try:
        seasons = []
        for year, dates in SEASON_DATES.items():
            league_key = LEAGUE_KEYS.get(year)
            if league_key:
                seasons.append({
                    "year": year,
                    "league_key": league_key,
                    "start_date": dates[0],
                    "end_date": dates[1]
                })
        
        return jsonify({
            "success": True,
            "seasons": seasons
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/date-range', methods=['GET'])
def get_date_range_with_data():
    """Get the date range that has data in the database."""
    try:
        conn = repo._execute_query(
            f"SELECT MIN(date) as min_date, MAX(date) as max_date FROM {repo.table_name}",
            ()
        )
        
        if conn and conn[0]['min_date']:
            return jsonify({
                "success": True,
                "min_date": conn[0]['min_date'],
                "max_date": conn[0]['max_date']
            })
        else:
            return jsonify({
                "success": True,
                "min_date": None,
                "max_date": None,
                "message": "No data available"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/lineups/teams', methods=['GET'])
def get_all_teams():
    """Get list of all teams."""
    try:
        teams_data = repo._execute_query(
            f"""
            SELECT DISTINCT team_key, team_name
            FROM {repo.table_name}
            ORDER BY team_name
            """,
            ()
        )
        
        teams = [{"team_key": row['team_key'], "team_name": row['team_name']} 
                for row in teams_data]
        
        return jsonify({
            "success": True,
            "count": len(teams),
            "teams": teams
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


def main():
    """Run the API server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily Lineups REST API")
    parser.add_argument("--port", type=int, default=5001,
                       help="Port to run on (default: 5001)")
    parser.add_argument("--host", default="127.0.0.1",
                       help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--debug", action="store_true",
                       help="Run in debug mode")
    
    args = parser.parse_args()
    
    print(f"Starting Daily Lineups API on http://{args.host}:{args.port}")
    print("Available endpoints:")
    print("  GET /api/health")
    print("  GET /api/lineups/date/<date>")
    print("  GET /api/lineups/player/<player_id>")
    print("  GET /api/lineups/team/<team_key>/patterns")
    print("  GET /api/lineups/team/<team_key>/changes")
    print("  GET /api/lineups/summary/<date>")
    print("  GET /api/lineups/search?q=<term>")
    print("  GET /api/lineups/teams")
    print("  GET /api/lineups/seasons")
    print("  GET /api/lineups/date-range")
    print()
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()