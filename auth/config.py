"""
Authentication configuration for Yahoo Fantasy Sports API.
Uses centralized league keys and season dates from metadata module.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    pass

# Import centralized league configuration
from metadata.league_keys import LEAGUE_KEYS, SEASON_DATES
from common.season_manager import get_league_key, get_current_season

# ---- OAUTH CONFIGURATION ----
# Load from environment variables for security
CLIENT_ID = os.getenv('YAHOO_CLIENT_ID')
CLIENT_SECRET = os.getenv('YAHOO_CLIENT_SECRET')
REDIRECT_URI = os.getenv('YAHOO_REDIRECT_URI', 'https://createdbydata.com')
AUTHORIZATION_CODE = os.getenv('YAHOO_AUTHORIZATION_CODE')

# Validate required environment variables
required_vars = ['YAHOO_CLIENT_ID', 'YAHOO_CLIENT_SECRET', 'YAHOO_AUTHORIZATION_CODE']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please create .env file with these variables.")

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