#!/usr/bin/env python3
"""Clear daily stats data to re-collect with correct mappings"""

import sqlite3
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from data_pipeline.player_stats.config import get_config_for_environment

config = get_config_for_environment('test')
conn = sqlite3.connect(config['database_path'])
cursor = conn.cursor()

# Delete daily stats
cursor.execute(f"""
    DELETE FROM {config['gkl_player_stats_table']} 
    WHERE job_id IN (
        SELECT job_id FROM job_log 
        WHERE job_type = 'stats_daily_collection'
    )
""")

deleted = cursor.rowcount
conn.commit()
print(f"Deleted {deleted} incorrectly mapped daily stats records")

conn.close()