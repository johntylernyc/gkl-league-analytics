#!/usr/bin/env python3
"""
Populate test database with sample player stats data using correct table names
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_pipeline.player_stats.config import get_config_for_environment
from data_pipeline.player_stats.job_manager import PlayerStatsJobManager

# Sample player data
SAMPLE_PLAYERS = [
    {"id": "p_001", "name": "Mike Trout", "team": "LAA", "position": "OF"},
    {"id": "p_002", "name": "Shohei Ohtani", "team": "LAD", "position": "DH,P"},
    {"id": "p_003", "name": "Aaron Judge", "team": "NYY", "position": "OF"},
    {"id": "p_004", "name": "Mookie Betts", "team": "LAD", "position": "OF,2B"},
    {"id": "p_005", "name": "Ronald Acuna Jr.", "team": "ATL", "position": "OF"},
    {"id": "p_006", "name": "Freddie Freeman", "team": "LAD", "position": "1B"},
    {"id": "p_007", "name": "Jose Altuve", "team": "HOU", "position": "2B"},
    {"id": "p_008", "name": "Gerrit Cole", "team": "NYY", "position": "P"},
    {"id": "p_009", "name": "Sandy Alcantara", "team": "MIA", "position": "P"},
    {"id": "p_010", "name": "Vladimir Guerrero Jr.", "team": "TOR", "position": "1B"},
]

def create_test_schema(conn, config):
    """Create the necessary tables in test database using correct names"""
    cursor = conn.cursor()
    
    # Get table names from config
    player_stats_table = config['gkl_player_stats_table']
    player_mapping_table = config['player_mapping_table']
    
    print(f"Creating tables: {player_stats_table}, {player_mapping_table}")
    
    # Create job_log table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_log (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            environment TEXT NOT NULL,
            status TEXT NOT NULL,
            date_range_start TEXT,
            date_range_end TEXT,
            league_key TEXT,
            records_processed INTEGER,
            records_inserted INTEGER,
            error_message TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP
        )
    """)
    
    # Create player stats table with correct name
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {player_stats_table} (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            date DATE NOT NULL,
            yahoo_player_id TEXT NOT NULL,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
            position_codes TEXT,
            games_played INTEGER DEFAULT 0,
            has_batting_data BOOLEAN DEFAULT FALSE,
            has_pitching_data BOOLEAN DEFAULT FALSE,
            
            -- Batting stats
            batting_at_bats INTEGER,
            batting_runs INTEGER,
            batting_hits INTEGER,
            batting_doubles INTEGER,
            batting_triples INTEGER,
            batting_home_runs INTEGER,
            batting_rbis INTEGER,
            batting_stolen_bases INTEGER,
            batting_walks INTEGER,
            batting_strikeouts INTEGER,
            batting_avg REAL,
            batting_obp REAL,
            batting_slg REAL,
            batting_ops REAL,
            
            -- Pitching stats (simplified)
            pitching_games_started INTEGER,
            pitching_wins INTEGER,
            pitching_losses INTEGER,
            pitching_saves INTEGER,
            pitching_innings_pitched REAL,
            pitching_strikeouts INTEGER,
            pitching_era REAL,
            pitching_whip REAL,
            
            confidence_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (job_id) REFERENCES job_log(job_id),
            UNIQUE(date, yahoo_player_id)
        )
    """)
    
    # Create player_id_mapping table with correct name
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {player_mapping_table} (
            mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            yahoo_player_id TEXT NOT NULL UNIQUE,
            yahoo_player_name TEXT NOT NULL,
            standardized_name TEXT NOT NULL,
            team_code TEXT,
            position_codes TEXT,
            confidence_score REAL NOT NULL DEFAULT 0.0,
            mapping_method TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            validation_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    print("Test database schema created successfully")

def generate_batting_stats():
    """Generate realistic batting statistics"""
    at_bats = random.randint(0, 5)
    hits = random.randint(0, min(at_bats, 3)) if at_bats > 0 else 0
    
    doubles = 1 if hits > 1 and random.random() < 0.2 else 0
    triples = 1 if hits > 1 and random.random() < 0.02 else 0
    home_runs = 1 if hits > 0 and random.random() < 0.15 else 0
    
    runs = random.randint(0, min(hits + 1, 2))
    rbis = home_runs + random.randint(0, 2) if hits > 0 else 0
    walks = 1 if random.random() < 0.1 else 0
    strikeouts = random.randint(0, min(at_bats, 2)) if at_bats > 0 else 0
    stolen_bases = 1 if hits > 0 and random.random() < 0.1 else 0
    
    batting_avg = hits / at_bats if at_bats > 0 else 0.0
    
    return {
        'at_bats': at_bats,
        'runs': runs,
        'hits': hits,
        'doubles': doubles,
        'triples': triples,
        'home_runs': home_runs,
        'rbis': rbis,
        'stolen_bases': stolen_bases,
        'walks': walks,
        'strikeouts': strikeouts,
        'batting_avg': round(batting_avg, 3)
    }

def populate_test_data(days_back=7):
    """Populate test database with sample data"""
    config = get_config_for_environment('test')
    db_path = config['database_path']
    
    print(f"Using test database: {db_path}")
    
    # Create database directory if it doesn't exist
    db_dir = Path(db_path).parent
    db_dir.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # Create schema with correct table names
    create_test_schema(conn, config)
    
    # Initialize job manager for test environment
    job_manager = PlayerStatsJobManager(environment='test')
    
    # Get table names
    player_stats_table = config['gkl_player_stats_table']
    player_mapping_table = config['player_mapping_table']
    
    # Add player mappings first
    cursor = conn.cursor()
    for player in SAMPLE_PLAYERS:
        cursor.execute(f"""
            INSERT OR REPLACE INTO {player_mapping_table} (
                yahoo_player_id, yahoo_player_name, standardized_name,
                team_code, position_codes, confidence_score, mapping_method,
                validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player['id'], player['name'], player['name'].lower().replace(' ', '_'),
            player['team'], player['position'], 0.95, 'exact', 'valid'
        ))
    
    conn.commit()
    print(f"Added {len(SAMPLE_PLAYERS)} player mappings to {player_mapping_table}")
    
    # Generate stats for each day
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    current_date = start_date
    total_records = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"\nGenerating stats for {date_str}...")
        
        # Create a job for this date
        job_id = job_manager.start_job(
            job_type='stats_test_population',
            date_range_start=date_str,
            date_range_end=date_str,
            metadata={'source': 'test_data_generator'}
        )
        
        records_for_date = 0
        
        # Generate stats for each player
        for player in SAMPLE_PLAYERS:
            # Skip some players randomly (simulating days off)
            if random.random() < 0.1:
                continue
            
            # Generate batting stats
            batting_stats = generate_batting_stats()
            
            # Insert the record with correct table name
            cursor.execute(f"""
                INSERT OR REPLACE INTO {player_stats_table} (
                    job_id, date, yahoo_player_id, player_name, team_code, position_codes,
                    games_played, has_batting_data, has_pitching_data,
                    batting_at_bats, batting_runs, batting_hits, batting_doubles,
                    batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                    batting_walks, batting_strikeouts, batting_avg
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                job_id, date_str, player['id'], player['name'], player['team'], player['position'],
                1, True, False,
                batting_stats['at_bats'], batting_stats['runs'], batting_stats['hits'],
                batting_stats['doubles'], batting_stats['triples'], batting_stats['home_runs'],
                batting_stats['rbis'], batting_stats['stolen_bases'], batting_stats['walks'],
                batting_stats['strikeouts'], batting_stats['batting_avg']
            ))
            
            records_for_date += 1
        
        conn.commit()
        
        # Update job status
        job_manager.update_job(
            job_id,
            'completed',
            records_processed=records_for_date,
            records_inserted=records_for_date
        )
        
        print(f"  Created {records_for_date} player records in {player_stats_table}")
        total_records += records_for_date
        
        current_date += timedelta(days=1)
    
    print(f"\n{'=' * 60}")
    print(f"Test data population complete!")
    print(f"  Total days: {days_back + 1}")
    print(f"  Total records: {total_records}")
    print(f"  Stats table: {player_stats_table}")
    print(f"  Mapping table: {player_mapping_table}")
    print(f"  Database: {db_path}")
    
    # Show sample of the data
    print(f"\nSample data from {end_date}:")
    cursor.execute(f"""
        SELECT player_name, batting_hits, batting_runs, batting_rbis, batting_home_runs
        FROM {player_stats_table}
        WHERE date = ?
        ORDER BY batting_hits DESC
        LIMIT 5
    """, (end_date.strftime('%Y-%m-%d'),))
    
    print("\nTop 5 hitters today:")
    print(f"{'Player':<25} H  R  RBI HR")
    print("-" * 40)
    for row in cursor.fetchall():
        print(f"{row[0]:<25} {row[1]:<2} {row[2]:<2} {row[3]:<3} {row[4]:<2}")
    
    conn.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate test database with sample player stats")
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days of data to generate (default: 7)')
    parser.add_argument('--clear', action='store_true',
                       help='Clear existing data before populating')
    
    args = parser.parse_args()
    
    if args.clear:
        config = get_config_for_environment('test')
        # Clear only the test tables, not the whole database
        conn = sqlite3.connect(config['database_path'])
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {config['gkl_player_stats_table']}")
        cursor.execute(f"DELETE FROM {config['player_mapping_table']}")
        cursor.execute("DELETE FROM job_log WHERE job_type = 'stats_test_population'")
        conn.commit()
        conn.close()
        print("Cleared existing test data")
    
    populate_test_data(days_back=args.days)

if __name__ == "__main__":
    main()