"""
Configuration settings for the draft results data pipeline.

This module provides configuration constants and helper functions
for the draft results collection process, following the patterns
established in daily_lineups and league_transactions.
"""

from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))

from data_pipeline.config.database_config import get_database_path, get_table_name

# API Configuration
BASE_FANTASY_URL = 'https://fantasysports.yahooapis.com/fantasy/v2'
API_DELAY_SECONDS = 1.0  # Rate limit: 1 request per second
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff multiplier
REQUEST_TIMEOUT = 30  # Seconds

# Database Configuration
BATCH_SIZE = 100  # Number of records to insert at once

def get_draft_table_name(environment='production'):
    """
    Get the draft results table name for the specified environment.
    
    Args:
        environment: 'production' or 'test'
        
    Returns:
        str: Table name (e.g., 'draft_results' or 'draft_results_test')
    """
    return get_table_name('draft_results', environment)

# Draft Types
DRAFT_TYPE_SNAKE = 'snake'
DRAFT_TYPE_AUCTION = 'auction'
VALID_DRAFT_TYPES = [DRAFT_TYPE_SNAKE, DRAFT_TYPE_AUCTION]

# Default values for missing data
DEFAULT_PLAYER_POSITION = 'Unknown'
DEFAULT_PLAYER_TEAM = 'FA'  # Free Agent

# Logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'