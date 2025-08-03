"""
Central configuration module for the GKL League Analytics project.
"""

from .database_config import (
    get_database_path,
    get_table_suffix,
    get_table_name,
    get_environment,
    is_test_environment,
    is_production_environment
)

__all__ = [
    'get_database_path',
    'get_table_suffix',
    'get_table_name',
    'get_environment',
    'is_test_environment',
    'is_production_environment'
]