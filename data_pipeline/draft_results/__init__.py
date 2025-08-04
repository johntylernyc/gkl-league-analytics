"""
Draft Results Data Pipeline Module

This module handles the collection and management of draft data from the Yahoo Fantasy Sports API.
"""

__version__ = "1.0.0"
__author__ = "GKL League Analytics Team"

# Import main components when available
try:
    from .collector import DraftResultsCollector
except ImportError:
    # Collector not yet implemented
    pass

__all__ = [
    "DraftResultsCollector",
]