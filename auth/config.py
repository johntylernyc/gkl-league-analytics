"""
Authentication configuration for Yahoo Fantasy Sports API.
Uses centralized league keys and season dates from metadata module.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import centralized league configuration
from metadata.league_keys import LEAGUE_KEYS, SEASON_DATES
from common.season_manager import get_league_key, get_current_season

# ---- OAUTH CONFIGURATION ----
CLIENT_ID = 'dj0yJmk9dmdPQ2liVDlsZ3FZJmQ9WVdrOVNYZGxhRk5sWlhZbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWNk'
CLIENT_SECRET = 'ab151cb088ae17856e532a59f5705abae6617dcd'
REDIRECT_URI = 'https://createdbydata.com'
AUTHORIZATION_CODE = 'ajvupw4rq3ggvf53hk4u4yskpbxq9qsq'

# ---- API ENDPOINTS ----
TOKEN_URL = 'https://api.login.yahoo.com/oauth2/get_token'
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'

# ---- LEAGUE CONFIGURATION ----
# Default to current season's league key, fallback to 2025 if not in season
current_season = get_current_season()
DEFAULT_LEAGUE_KEY = get_league_key(current_season) if current_season else LEAGUE_KEYS[2025]

# For backward compatibility with existing code that expects LEAGUE_KEY
LEAGUE_KEY = DEFAULT_LEAGUE_KEY

# Export the centralized configurations for other modules
__all__ = [
    'CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI', 'AUTHORIZATION_CODE',
    'TOKEN_URL', 'BASE_FANTASY_URL', 
    'LEAGUE_KEY', 'DEFAULT_LEAGUE_KEY',
    'LEAGUE_KEYS', 'SEASON_DATES'
]