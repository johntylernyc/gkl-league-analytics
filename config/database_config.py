"""
Central database configuration for GKL League Analytics.

This module provides a single source of truth for database paths and table names,
ensuring proper separation between test and production environments.

Environment Control:
    - Set DATA_ENV=test for test environment
    - Set DATA_ENV=production for production (default)
    - Can also be controlled via function parameters
"""

import os
from pathlib import Path

# Database file names
PRODUCTION_DB = "league_analytics.db"
TEST_DB = "league_analytics_test.db"

# Default environment
DEFAULT_ENVIRONMENT = "production"

# Base path to database directory
BASE_DIR = Path(__file__).parent.parent
DATABASE_DIR = BASE_DIR / "database"


def get_environment(override=None):
    """
    Get the current environment setting.
    
    Args:
        override: Optional environment override ('test' or 'production')
    
    Returns:
        str: The environment ('test' or 'production')
    """
    if override:
        return override.lower()
    
    # Check environment variable
    env = os.getenv('DATA_ENV', DEFAULT_ENVIRONMENT).lower()
    
    # Validate environment
    if env not in ['test', 'production']:
        print(f"Warning: Invalid DATA_ENV '{env}', using 'production'")
        return 'production'
    
    return env


def get_database_path(environment=None):
    """
    Get the appropriate database path based on environment.
    
    Args:
        environment: Optional environment override ('test' or 'production')
    
    Returns:
        Path: Full path to the database file
    """
    env = get_environment(environment)
    
    if env == 'test':
        return DATABASE_DIR / TEST_DB
    else:
        return DATABASE_DIR / PRODUCTION_DB


def get_table_suffix(environment=None):
    """
    Get the table suffix for the environment.
    
    For transactions tables, we use suffixes:
    - _test for test environment
    - _production for production environment
    
    Args:
        environment: Optional environment override
    
    Returns:
        str: Table suffix ('_test' or '_production')
    """
    env = get_environment(environment)
    
    if env == 'test':
        return '_test'
    else:
        return '_production'


def get_table_name(base_name, environment=None):
    """
    Get the full table name for the environment.
    
    Args:
        base_name: Base table name (e.g., 'transactions', 'daily_lineups')
        environment: Optional environment override
    
    Returns:
        str: Full table name with environment suffix
    """
    env = get_environment(environment)
    suffix = get_table_suffix(env)
    
    # Special handling for certain tables
    if base_name == 'transactions':
        # Production uses 'transactions', test uses 'transactions_test'
        if env == 'test':
            return f"{base_name}_test"
        else:
            return base_name
    elif base_name == 'daily_lineups':
        # Daily lineups doesn't use suffix pattern currently
        # but we'll prepare for it
        if env == 'test':
            return f"{base_name}_test"
        else:
            return base_name
    elif base_name == 'job_log':
        # Job log is shared but we could separate it
        return base_name
    else:
        # Default behavior for other tables
        if env == 'test':
            return f"{base_name}_test"
        else:
            return base_name


def is_test_environment(environment=None):
    """
    Check if we're in test environment.
    
    Args:
        environment: Optional environment override
    
    Returns:
        bool: True if test environment
    """
    return get_environment(environment) == 'test'


def is_production_environment(environment=None):
    """
    Check if we're in production environment.
    
    Args:
        environment: Optional environment override
    
    Returns:
        bool: True if production environment
    """
    return get_environment(environment) == 'production'


# Configuration validation on import
if __name__ == "__main__" or os.getenv('DEBUG_CONFIG'):
    env = get_environment()
    print(f"Database Configuration:")
    print(f"  Current Environment: {env}")
    print(f"  Database Path: {get_database_path()}")
    print(f"  Table Suffix: {get_table_suffix()}")
    print(f"  Transactions Table: {get_table_name('transactions')}")
    print(f"  Daily Lineups Table: {get_table_name('daily_lineups')}")
    print(f"  Job Log Table: {get_table_name('job_log')}")
    
    # Verify database directory exists
    if not DATABASE_DIR.exists():
        print(f"  WARNING: Database directory does not exist: {DATABASE_DIR}")
    else:
        # Check which databases exist
        prod_db = DATABASE_DIR / PRODUCTION_DB
        test_db = DATABASE_DIR / TEST_DB
        print(f"  Production DB exists: {prod_db.exists()} ({prod_db})")
        print(f"  Test DB exists: {test_db.exists()} ({test_db})")