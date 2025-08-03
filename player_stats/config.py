"""
Configuration settings for the Player Stats module.

This module centralizes all configuration parameters for MLB player statistics
data collection, processing, and analysis.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import centralized database configuration
from config.database_config import (
    get_database_path,
    get_table_name,
    get_environment,
    is_test_environment
)

# Import season management
from common.season_manager import (
    get_current_season,
    validate_season,
    get_season_dates,
    get_league_key
)

# ============================================
# API Configuration
# ============================================

# pybaseball settings
PYBASEBALL_CACHE_ENABLED = True
PYBASEBALL_CACHE_DIR = Path(__file__).parent / "cache"
API_DELAY_SECONDS = 1.0  # Delay between pybaseball API requests
MAX_RETRIES = 3  # Maximum retry attempts for failed requests
RETRY_BACKOFF_BASE = 2  # Exponential backoff base for retries

# Request timeout
REQUEST_TIMEOUT = 60  # Seconds for pybaseball requests

# ============================================
# Data Collection Configuration
# ============================================

# Batch processing settings
BATCH_SIZE = 50  # Players to process in a single batch
MAX_CONCURRENT_REQUESTS = 2  # Concurrent API requests
COLLECTION_START_TIME = "06:00"  # Daily collection start time (ET)
COLLECTION_DEADLINE = "07:00"  # Target completion time (ET)

# Data collection scope
COLLECT_BATTING_STATS = True
COLLECT_PITCHING_STATS = True
COLLECT_FIELDING_STATS = False  # Future enhancement
COLLECT_ADVANCED_METRICS = False  # Future enhancement

# ============================================
# Database Configuration
# ============================================

def get_player_stats_table_name(environment=None):
    """Get the player stats table name for the environment."""
    return get_table_name('daily_mlb_stats', environment)

def get_batting_staging_table_name(environment=None):
    """Get the batting staging table name for the environment."""
    return get_table_name('mlb_batting_stats_staging', environment)

def get_pitching_staging_table_name(environment=None):
    """Get the pitching staging table name for the environment."""
    return get_table_name('mlb_pitching_stats_staging', environment)

def get_player_mapping_table_name(environment=None):
    """Get the player ID mapping table name for the environment."""
    return get_table_name('player_id_mapping', environment)

def get_gkl_player_stats_table_name(environment=None):
    """Get the GKL player stats table name for the environment."""
    return get_table_name('daily_gkl_player_stats', environment)

# ============================================
# Player ID Mapping Configuration
# ============================================

# Mapping confidence thresholds
MAPPING_CONFIDENCE_THRESHOLD = 0.8  # Minimum confidence for automatic mapping
FUZZY_MATCH_THRESHOLD = 0.85  # Fuzzy string matching threshold
MANUAL_REVIEW_THRESHOLD = 0.6  # Threshold for manual review queue

# Player lookup settings
PLAYER_LOOKUP_BATCH_SIZE = 10  # Players to lookup in a single batch
PLAYER_CACHE_TTL = 86400  # Cache TTL in seconds (24 hours)

# ============================================
# Data Validation Configuration
# ============================================

# Range validation limits
BATTING_AVG_MIN = 0.0
BATTING_AVG_MAX = 1.0
OBP_MIN = 0.0
OBP_MAX = 1.0
SLG_MIN = 0.0
SLG_MAX = 5.0  # Theoretical maximum
ERA_MIN = 0.0
ERA_MAX = 30.0  # Reasonable maximum for daily ERA
WHIP_MIN = 0.0
WHIP_MAX = 10.0  # Reasonable maximum

# Data completeness requirements
REQUIRED_BATTING_FIELDS = [
    'player_id', 'player_name', 'team', 'date',
    'games_played', 'at_bats', 'hits'
]

REQUIRED_PITCHING_FIELDS = [
    'player_id', 'player_name', 'team', 'date',
    'games_played', 'innings_pitched'
]

# Quality check thresholds
MAX_DAILY_QUALITY_ISSUES = 10  # Maximum acceptable quality issues per day
COMPLETENESS_THRESHOLD = 0.95  # Minimum data completeness percentage

# ============================================
# Performance Configuration
# ============================================

# Query performance settings
QUERY_TIMEOUT = 30  # Seconds for database queries
INDEX_REBUILD_THRESHOLD = 10000  # Records before considering index rebuild
BATCH_INSERT_SIZE = 1000  # Records per batch insert

# Memory management
MAX_MEMORY_USAGE_MB = 512  # Maximum memory usage for processing
CHUNK_SIZE = 5000  # Records to process in memory chunks

# ============================================
# Monitoring and Alerting Configuration
# ============================================

# Success criteria (from PRD)
TARGET_SUCCESS_RATE = 0.99  # 99% daily collection success rate
TARGET_QUALITY_RATE = 0.999  # < 0.1% data quality issues
TARGET_COMPLETENESS = 1.0  # 100% rostered player coverage
TARGET_TIMELINESS = 0.95  # 95% stats available by 7 AM ET

# Alert thresholds
ALERT_SUCCESS_RATE_THRESHOLD = 0.95  # Alert if success rate drops below
ALERT_QUALITY_THRESHOLD = 0.01  # Alert if quality issues exceed 1%
ALERT_COLLECTION_TIME_HOURS = 2  # Alert if collection takes longer than 2 hours

# ============================================
# Logging Configuration
# ============================================

# Job types for logging
JOB_TYPE_DAILY_COLLECTION = "player_stats_collection"
JOB_TYPE_BACKFILL = "player_stats_backfill"
JOB_TYPE_MAPPING_UPDATE = "player_id_mapping_update"
JOB_TYPE_VALIDATION = "player_stats_validation"

# Log levels
LOG_LEVEL_PRODUCTION = "INFO"
LOG_LEVEL_TEST = "DEBUG"

# ============================================
# File Paths
# ============================================

# Module directory
MODULE_DIR = Path(__file__).parent

# Cache and temporary files
CACHE_DIR = MODULE_DIR / "cache"
TEMP_DIR = MODULE_DIR / "temp"
LOGS_DIR = MODULE_DIR / "logs"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================
# Statistics Configuration
# ============================================

# Batting statistics to collect (aligned with stat_mappings.json)
BATTING_STATS = [
    'games_played',    # Games Played
    'at_bats',         # At Bats
    'runs',            # Runs
    'hits',            # Hits
    'doubles',         # Doubles
    'triples',         # Triples
    'home_runs',       # Home Runs
    'rbis',            # RBIs
    'stolen_bases',    # Stolen Bases
    'walks',           # Walks
    'strikeouts',      # Strikeouts
    'batting_avg',     # Batting Average
    'on_base_pct',     # On-base Percentage
    'slugging_pct',    # Slugging Percentage
    'ops',             # On-base + Slugging
]

# Pitching statistics to collect
PITCHING_STATS = [
    'games_played',         # Pitching Appearances
    'games_started',        # Games Started
    'wins',                 # Wins
    'losses',               # Losses
    'saves',                # Saves
    'holds',                # Holds
    'innings_pitched',      # Innings Pitched
    'hits_allowed',         # Hits Allowed
    'runs_allowed',         # Runs Allowed
    'earned_runs',          # Earned Runs
    'walks_allowed',        # Walks Allowed
    'strikeouts_pitched',   # Strikeouts
    'home_runs_allowed',    # Home Runs Allowed
    'era',                  # ERA
    'whip',                 # WHIP
    'quality_starts',       # Quality Starts
]

# pybaseball field mapping (pybaseball field -> our field)
PYBASEBALL_BATTING_MAPPING = {
    'Name': 'player_name',
    'Team': 'team',
    'G': 'games_played',
    'AB': 'at_bats',
    'R': 'runs',
    'H': 'hits',
    '2B': 'doubles',
    '3B': 'triples',
    'HR': 'home_runs',
    'RBI': 'rbis',
    'SB': 'stolen_bases',
    'BB': 'walks',
    'SO': 'strikeouts',
    'AVG': 'batting_avg',
    'OBP': 'on_base_pct',
    'SLG': 'slugging_pct',
    'OPS': 'ops',
}

PYBASEBALL_PITCHING_MAPPING = {
    'Name': 'player_name',
    'Team': 'team',
    'G': 'games_played',
    'GS': 'games_started',
    'W': 'wins',
    'L': 'losses',
    'SV': 'saves',
    'HLD': 'holds',
    'IP': 'innings_pitched',
    'H': 'hits_allowed',
    'R': 'runs_allowed',
    'ER': 'earned_runs',
    'BB': 'walks_allowed',
    'SO': 'strikeouts_pitched',
    'HR': 'home_runs_allowed',
    'ERA': 'era',
    'WHIP': 'whip',
    'QS': 'quality_starts',
}

# ============================================
# Environment-specific overrides
# ============================================

def get_config_for_environment(environment=None):
    """Get configuration settings for specific environment."""
    env = get_environment(environment)
    
    config = {
        'environment': env,
        'database_path': get_database_path(env),
        'player_stats_table': get_player_stats_table_name(env),
        'batting_staging_table': get_batting_staging_table_name(env),
        'pitching_staging_table': get_pitching_staging_table_name(env),
        'player_mapping_table': get_player_mapping_table_name(env),
        'gkl_player_stats_table': get_gkl_player_stats_table_name(env),
        'is_test': is_test_environment(env),
        'log_level': LOG_LEVEL_TEST if is_test_environment(env) else LOG_LEVEL_PRODUCTION,
        'data_validation': {
            'max_batting_avg': BATTING_AVG_MAX,
            'max_home_runs_per_game': 10,  # Reasonable daily maximum
            'max_era': ERA_MAX,
            'max_whip': WHIP_MAX,
            'required_batting_fields': REQUIRED_BATTING_FIELDS,
            'required_pitching_fields': REQUIRED_PITCHING_FIELDS,
        },
        'field_mappings': {
            'batting': PYBASEBALL_BATTING_MAPPING,
            'pitching': PYBASEBALL_PITCHING_MAPPING,
        }
    }
    
    return config

# Configuration validation on import
if __name__ == "__main__" or os.getenv('DEBUG_PLAYER_STATS_CONFIG'):
    config = get_config_for_environment()
    print(f"Player Stats Configuration:")
    print(f"  Environment: {config['environment']}")
    print(f"  Database: {config['database_path']}")
    print(f"  Player Stats Table: {config['player_stats_table']}")
    print(f"  Batting Staging Table: {config['batting_staging_table']}")
    print(f"  Pitching Staging Table: {config['pitching_staging_table']}")
    print(f"  Player Mapping Table: {config['player_mapping_table']}")
    print(f"  GKL Player Stats Table: {config['gkl_player_stats_table']}")
    print(f"  Is Test Environment: {config['is_test']}")
    print(f"  Log Level: {config['log_level']}")
    
    # Verify cache directories exist
    print(f"  Cache Directory: {CACHE_DIR} (exists: {CACHE_DIR.exists()})")
    print(f"  Temp Directory: {TEMP_DIR} (exists: {TEMP_DIR.exists()})")
    print(f"  Logs Directory: {LOGS_DIR} (exists: {LOGS_DIR.exists()})")