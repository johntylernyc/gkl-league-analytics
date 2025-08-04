"""
Daily Lineups Module for Yahoo Fantasy Baseball League Analytics

This module provides comprehensive historical roster analysis capabilities,
including data collection, storage, and analysis of daily lineup decisions.
"""

__version__ = "0.1.0"
__author__ = "GKL League Analytics Team"

from .parser import LineupParser

__all__ = [
    "LineupParser"
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
    import sqlite3
    from .config import get_database_path, get_lineup_table_name
    
    try:
        db_path = get_database_path()
        table_name = get_lineup_table_name()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get last update time
        cursor.execute(f"""
            SELECT MAX(created_at) FROM {table_name}
        """)
        result = cursor.fetchone()
        last_update = result[0] if result and result[0] else None
        
        current_time = datetime.now()
        
        if last_update:
            last_update_dt = datetime.fromisoformat(last_update)
            lag = current_time - last_update_dt
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
        
        # Get record count for coverage estimate
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        record_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "last_update": last_update,
            "lag_hours": round(lag_hours, 2) if lag_hours else None,
            "record_count": record_count,
            "status": status,
            "timestamp": current_time.isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }