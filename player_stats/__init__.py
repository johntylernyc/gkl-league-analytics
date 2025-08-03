"""
Player Stats Module

Daily MLB player statistics data ingestion and management system.
Integrates with pybaseball to collect comprehensive player performance data
aligned with fantasy baseball scoring categories.

Key Components:
- collector.py: Core data collection from pybaseball APIs
- job_manager.py: Job tracking and progress management  
- repository.py: Data access and query interface
- player_id_mapper.py: Yahoo Fantasy ↔ MLB player ID mapping
- data_validator.py: Data quality assurance and validation
- scheduler.py: Daily automation and scheduling

Features:
- Automated daily MLB stats collection
- Historical data backfill capabilities
- Data quality validation and monitoring
- Integration with existing job logging system
- Support for both batting and pitching statistics
- Performance optimization for large datasets
"""

__version__ = "1.0.0"
__author__ = "GKL League Analytics Team"

# Module exports - all core components implemented and available
from .collector import PlayerStatsCollector
from .job_manager import PlayerStatsJobManager
from .repository import PlayerStatsRepository
from .player_id_mapper import PlayerIdMapper
from .data_validator import PlayerStatsValidator
from .pybaseball_integration import PyBaseballIntegration

__all__ = [
    'PlayerStatsCollector',
    'PlayerStatsJobManager', 
    'PlayerStatsRepository',
    'PlayerIdMapper',
    'PlayerStatsValidator',
    'PyBaseballIntegration'
]