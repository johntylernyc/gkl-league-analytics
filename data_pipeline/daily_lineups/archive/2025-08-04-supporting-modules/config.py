"""
Configuration settings for the Daily Lineups module.

This module centralizes all configuration parameters for lineup data collection,
processing, and analysis.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import base configuration from auth module
from auth.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    TOKEN_URL,
    BASE_FANTASY_URL,
    LEAGUE_KEYS,  # Now comes from centralized metadata
    SEASON_DATES  # Now comes from centralized metadata
)

# Import centralized database configuration
from data_pipeline.config.database_config import (
    get_database_path,
    get_table_name,
    get_environment,
    is_test_environment
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

# League keys and season dates are now imported from centralized metadata
# via auth.config module. They are available as LEAGUE_KEYS and SEASON_DATES
# imported at the top of this file.

# Import season manager for convenience functions
from common.season_manager import (
    SeasonManager,
    get_available_seasons,
    get_league_key,
    get_season_dates,
    get_current_season,
    COLLECTION_PROFILES
)

# ============================================
# Database Configuration
# ============================================

# Legacy database paths (for backward compatibility)
# These are now handled by config.database_config module
DATABASE_PATH = None  # Will be set dynamically
TEST_DATABASE_PATH = None  # Will be set dynamically

# Table base names
LINEUP_TABLE_BASE = "daily_lineups"
POSITIONS_TABLE = "lineup_positions"
USAGE_SUMMARY_TABLE = "player_usage_summary"
PATTERNS_TABLE = "team_lineup_patterns"

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

# The get_database_path function is now imported from config.database_config
# The get_table_name function is now imported from config.database_config

# For backward compatibility, create wrapper functions
def get_lineup_table_name(environment=None):
    """Get the appropriate lineup table name based on environment."""
    env = environment or get_environment()
    return get_table_name(LINEUP_TABLE_BASE, env)

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