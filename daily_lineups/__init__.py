"""
Daily Lineups Module for Yahoo Fantasy Baseball League Analytics

This module provides comprehensive historical roster analysis capabilities,
including data collection, storage, and analysis of daily lineup decisions.
"""

__version__ = "0.1.0"
__author__ = "GKL League Analytics Team"

from .collector import DailyLineupsCollector
from .repository import LineupRepository
from .parser import LineupParser
from .job_manager import LineupJobManager

__all__ = [
    "DailyLineupsCollector",
    "LineupRepository", 
    "LineupParser",
    "LineupJobManager"
]

def health_check():
    """
    Check the health status of the Daily Lineups module.
    
    Returns:
        dict: Health status information including:
            - last_update: Timestamp of most recent data
            - lag_hours: Hours since last update
            - coverage_percentage: Data completeness
            - status: 'healthy', 'warning', or 'error'
    """
    from datetime import datetime, timedelta
    from .repository import LineupRepository
    
    repo = LineupRepository()
    
    try:
        last_update = repo.get_last_update_time()
        current_time = datetime.now()
        
        if last_update:
            lag = current_time - last_update
            lag_hours = lag.total_seconds() / 3600
            
            # Determine health status
            if lag_hours < 24:
                status = "healthy"
            elif lag_hours < 48:
                status = "warning"
            else:
                status = "error"
        else:
            lag_hours = None
            status = "error"
        
        # Calculate coverage
        coverage = repo.get_data_coverage_percentage()
        
        return {
            "last_update": last_update.isoformat() if last_update else None,
            "lag_hours": round(lag_hours, 2) if lag_hours else None,
            "coverage_percentage": round(coverage, 2),
            "status": status,
            "timestamp": current_time.isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }