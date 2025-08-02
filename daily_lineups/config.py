"""
Configuration settings for the Daily Lineups module.

This module centralizes all configuration parameters for lineup data collection,
processing, and analysis.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import base configuration from auth module
from auth.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    TOKEN_URL,
    BASE_FANTASY_URL
)

# ============================================
# API Configuration
# ============================================

# Rate limiting settings
API_DELAY_SECONDS = 2.1  # Delay between API requests (Yahoo recommends 2+ seconds)
MAX_CONCURRENT_WORKERS = 2  # Number of concurrent API workers
MAX_RETRIES = 3  # Maximum retry attempts for failed requests
RETRY_BACKOFF_BASE = 2  # Exponential backoff base for retries

# Request timeout
REQUEST_TIMEOUT = 30  # Seconds

# ============================================
# Data Collection Configuration
# ============================================

# Batch processing settings
BATCH_SIZE = 100  # Number of records to process in a batch
CHECKPOINT_FREQUENCY = 10  # Save checkpoint every N batches
TRANSACTION_BATCH_SIZE = 500  # Database transaction batch size

# Collection modes
COLLECTION_MODES = {
    "incremental": "Collect only new/missing data",
    "backfill": "Fill historical gaps",
    "full": "Complete refresh of all data",
    "update": "Update recent data only"
}

# Default collection parameters
DEFAULT_LOOKBACK_DAYS = 7  # Days to look back for incremental updates
DEFAULT_SEASON = 2025  # Current season

# ============================================
# League Configuration
# ============================================

# League keys by season
LEAGUE_KEYS = {
    2025: "mlb.l.6966",
    2024: "431.l.41728",
    2023: "422.l.54537",
    2022: "412.l.34665",
    2021: "404.l.54012",
    2020: "398.l.35682",
    2019: "388.l.34240",
    2018: "378.l.19344",
    2017: "370.l.36931",
    2016: "357.l.62816",
    2015: "346.l.48624",
    2014: "328.l.36901",
    2013: "308.l.43210",
    2012: "268.l.24275",
    2011: "253.l.58530",
    2010: "238.l.174722",
    2009: "215.l.75484",
    2008: "195.l.181050",
}

# Season date ranges
SEASON_DATES = {
    2025: ("2025-03-27", "2025-09-28"),
    2024: ("2024-03-28", "2024-09-29"),
    2023: ("2023-03-30", "2023-10-01"),
    2022: ("2022-04-07", "2022-10-05"),
    2021: ("2021-04-01", "2021-10-03"),
    2020: ("2020-07-23", "2020-09-27"),
    2019: ("2019-03-28", "2019-09-29"),
    2018: ("2018-03-29", "2018-09-30"),
    2017: ("2017-04-02", "2017-10-01"),
    2016: ("2016-04-03", "2016-10-02"),
    2015: ("2015-04-05", "2015-10-04"),
    2014: ("2014-03-30", "2014-09-28"),
    2013: ("2013-03-31", "2013-09-29"),
    2012: ("2012-03-28", "2012-10-03"),
    2011: ("2011-03-31", "2011-09-28"),
    2010: ("2010-04-04", "2010-10-03"),
    2009: ("2009-04-05", "2009-10-04"),
    2008: ("2008-03-25", "2008-09-28"),
}

# ============================================
# Database Configuration
# ============================================

# Database paths
DATABASE_PATH = Path(__file__).parent.parent / "database" / "league_analytics.db"
TEST_DATABASE_PATH = Path(__file__).parent.parent / "database" / "league_analytics_test.db"

# Table names
LINEUP_TABLE = "daily_lineups"
LINEUP_TABLE_TEST = "daily_lineups_test"
POSITIONS_TABLE = "lineup_positions"
USAGE_SUMMARY_TABLE = "player_usage_summary"
PATTERNS_TABLE = "team_lineup_patterns"

# Environment configuration
def get_table_name(environment="production"):
    """Get the appropriate table name based on environment."""
    if environment.lower() == "test":
        return LINEUP_TABLE_TEST
    return LINEUP_TABLE

# ============================================
# Data Retention Configuration
# ============================================

# Historical data settings
KEEP_HISTORICAL_YEARS = 5  # Number of years to retain
ARCHIVE_OLD_DATA = True  # Archive data older than retention period
ARCHIVE_PATH = Path(__file__).parent / "archive"

# ============================================
# Logging Configuration
# ============================================

# Log file settings
LOG_DIRECTORY = Path(__file__).parent / "logs"
LOG_DIRECTORY.mkdir(exist_ok=True)

LOG_FILE = LOG_DIRECTORY / "daily_lineups.log"
ERROR_LOG_FILE = LOG_DIRECTORY / "errors.log"
DEBUG_LOG_FILE = LOG_DIRECTORY / "debug.log"

# Log levels
DEFAULT_LOG_LEVEL = "INFO"
DEBUG_MODE = os.getenv("LINEUP_DEBUG", "false").lower() == "true"

# ============================================
# File Paths
# ============================================

# Checkpoint and state files
CHECKPOINT_FILE = Path(__file__).parent / "checkpoint.json"
STATE_FILE = Path(__file__).parent / "state.json"

# Export directory
EXPORT_DIRECTORY = Path(__file__).parent / "exports"
EXPORT_DIRECTORY.mkdir(exist_ok=True)

# ============================================
# Performance Configuration
# ============================================

# Cache settings
ENABLE_CACHING = True
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_MAX_SIZE = 1000  # Maximum cached items

# Query optimization
MAX_QUERY_RESULTS = 10000  # Maximum results per query
DEFAULT_PAGE_SIZE = 100  # Default pagination size

# ============================================
# Validation Configuration
# ============================================

# Data validation rules
REQUIRED_LINEUP_FIELDS = [
    "date",
    "team_key",
    "team_name",
    "player_id",
    "player_name"
]

VALID_POSITIONS = [
    "C", "1B", "2B", "3B", "SS", "MI", "CI", 
    "OF", "UTIL", "SP", "RP", "P", "BN", "IL", "NA"
]

VALID_PLAYER_STATUS = [
    "healthy", "DTD", "IL10", "IL60", "IL", "NA", "O"
]

# ============================================
# Environment Variables
# ============================================

# Read environment variables
LINEUP_ENV = os.getenv("LINEUP_ENV", "production")
LINEUP_MODE = os.getenv("LINEUP_MODE", "incremental")
LINEUP_START_DATE = os.getenv("LINEUP_START_DATE")
LINEUP_END_DATE = os.getenv("LINEUP_END_DATE")

# Override settings from environment
if os.getenv("LINEUP_BATCH_SIZE"):
    BATCH_SIZE = int(os.getenv("LINEUP_BATCH_SIZE"))

if os.getenv("LINEUP_API_DELAY"):
    API_DELAY_SECONDS = float(os.getenv("LINEUP_API_DELAY"))

# ============================================
# Helper Functions
# ============================================

def get_database_path(environment=None):
    """Get the appropriate database path based on environment."""
    env = environment or LINEUP_ENV
    if env.lower() == "test":
        return TEST_DATABASE_PATH
    return DATABASE_PATH

def get_league_key(season):
    """Get the league key for a given season."""
    return LEAGUE_KEYS.get(season)

def get_season_dates(season):
    """Get the start and end dates for a season."""
    return SEASON_DATES.get(season, (None, None))

def is_valid_position(position):
    """Check if a position code is valid."""
    return position in VALID_POSITIONS

def is_valid_status(status):
    """Check if a player status is valid."""
    return status in VALID_PLAYER_STATUS

# ============================================
# Initialization
# ============================================

# Create necessary directories
for directory in [LOG_DIRECTORY, EXPORT_DIRECTORY, ARCHIVE_PATH]:
    directory.mkdir(parents=True, exist_ok=True)

# Log configuration on import
if DEBUG_MODE:
    print(f"Daily Lineups Config Loaded:")
    print(f"  Environment: {LINEUP_ENV}")
    print(f"  Mode: {LINEUP_MODE}")
    print(f"  Database: {get_database_path()}")
    print(f"  API Delay: {API_DELAY_SECONDS}s")
    print(f"  Batch Size: {BATCH_SIZE}")