#!/usr/bin/env python3
"""
Populate test database with sample player stats data
This will help visualize how the job imports and data collection work
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

# Sample player data - mix of real player names for realism
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
    {"id": "p_011", "name": "Juan Soto", "team": "NYY", "position": "OF"},
    {"id": "p_012", "name": "Trea Turner", "team": "PHI", "position": "SS"},
    {"id": "p_013", "name": "Paul Goldschmidt", "team": "STL", "position": "1B"},
    {"id": "p_014", "name": "Nolan Arenado", "team": "STL", "position": "3B"},
    {"id": "p_015", "name": "Marcus Semien", "team": "TEX", "position": "2B"},
]

def create_test_schema(conn):
    """Create the necessary tables in test database"""
    cursor = conn.cursor()
    
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
    
    # Create daily_gkl_player_stats table (simplified schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_gkl_player_stats (
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
            
            -- Pitching stats
            pitching_games_started INTEGER,
            pitching_wins INTEGER,
            pitching_losses INTEGER,
            pitching_saves INTEGER,
            pitching_innings_pitched REAL,
            pitching_hits_allowed INTEGER,
            pitching_runs_allowed INTEGER,
            pitching_earned_runs INTEGER,
            pitching_walks_allowed INTEGER,
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
    
    # Create player_id_mapping table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_id_mapping (
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
    # Simulate a game's worth of stats
    at_bats = random.randint(0, 5)  # 0-5 ABs per game
    hits = random.randint(0, min(at_bats, 4)) if at_bats > 0 else 0
    
    # Realistic distribution
    doubles = 1 if hits > 1 and random.random() < 0.2 else 0
    triples = 1 if hits > 1 and random.random() < 0.02 else 0
    home_runs = 1 if hits > 0 and random.random() < 0.15 else 0
    
    # Adjust hits for extra bases
    singles = max(0, hits - doubles - triples - home_runs)
    
    runs = random.randint(0, min(hits + 1, 3))
    rbis = home_runs + random.randint(0, 2) if hits > 0 else 0
    walks = 1 if random.random() < 0.1 else 0
    strikeouts = random.randint(0, min(at_bats, 3)) if at_bats > 0 else 0
    stolen_bases = 1 if singles > 0 and random.random() < 0.1 else 0
    
    # Calculate averages (would be season totals in real implementation)
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

def generate_pitching_stats():
    """Generate realistic pitching statistics"""
    # Only some players pitch
    is_starter = random.random() < 0.3
    
    if not is_starter:
        return None
    
    innings = round(random.uniform(5.0, 8.0), 1)
    hits = random.randint(3, 9)
    runs = random.randint(0, 5)
    earned_runs = random.randint(0, runs)
    walks = random.randint(0, 3)
    strikeouts = random.randint(3, 12)
    
    # Calculate ERA and WHIP
    era = (earned_runs * 9.0) / innings if innings > 0 else 0.0
    whip = (hits + walks) / innings if innings > 0 else 0.0
    
    return {
        'games_started': 1,
        'wins': 1 if runs < 3 and random.random() < 0.5 else 0,
        'losses': 1 if runs >= 4 and random.random() < 0.5 else 0,
        'saves': 0,
        'innings_pitched': innings,
        'hits_allowed': hits,
        'runs_allowed': runs,
        'earned_runs': earned_runs,
        'walks_allowed': walks,
        'strikeouts': strikeouts,
        'era': round(era, 2),
        'whip': round(whip, 2)
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
    
    # Create schema
    create_test_schema(conn)
    
    # Initialize job manager for test environment
    job_manager = PlayerStatsJobManager(environment='test')
    
    # Add player mappings first
    cursor = conn.cursor()
    for player in SAMPLE_PLAYERS:
        cursor.execute("""
            INSERT OR REPLACE INTO player_id_mapping (
                yahoo_player_id, yahoo_player_name, standardized_name,
                team_code, position_codes, confidence_score, mapping_method,
                validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player['id'], player['name'], player['name'].lower().replace(' ', '_'),
            player['team'], player['position'], 0.95, 'exact', 'valid'
        ))
    
    conn.commit()
    print(f"Added {len(SAMPLE_PLAYERS)} player mappings")
    
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
            
            # Generate pitching stats (only for pitchers)
            pitching_stats = None
            if 'P' in player['position']:
                pitching_stats = generate_pitching_stats()
            
            # Insert the record
            cursor.execute("""
                INSERT OR REPLACE INTO daily_gkl_player_stats (
                    job_id, date, yahoo_player_id, player_name, team_code, position_codes,
                    games_played, has_batting_data, has_pitching_data,
                    batting_at_bats, batting_runs, batting_hits, batting_doubles,
                    batting_triples, batting_home_runs, batting_rbis, batting_stolen_bases,
                    batting_walks, batting_strikeouts, batting_avg,
                    pitching_games_started, pitching_wins, pitching_losses, pitching_saves,
                    pitching_innings_pitched, pitching_hits_allowed, pitching_runs_allowed,
                    pitching_earned_runs, pitching_walks_allowed, pitching_strikeouts,
                    pitching_era, pitching_whip
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                job_id, date_str, player['id'], player['name'], player['team'], player['position'],
                1, True, pitching_stats is not None,
                # Batting stats
                batting_stats['at_bats'], batting_stats['runs'], batting_stats['hits'],
                batting_stats['doubles'], batting_stats['triples'], batting_stats['home_runs'],
                batting_stats['rbis'], batting_stats['stolen_bases'], batting_stats['walks'],
                batting_stats['strikeouts'], batting_stats['batting_avg'],
                # Pitching stats
                pitching_stats['games_started'] if pitching_stats else None,
                pitching_stats['wins'] if pitching_stats else None,
                pitching_stats['losses'] if pitching_stats else None,
                pitching_stats['saves'] if pitching_stats else None,
                pitching_stats['innings_pitched'] if pitching_stats else None,
                pitching_stats['hits_allowed'] if pitching_stats else None,
                pitching_stats['runs_allowed'] if pitching_stats else None,
                pitching_stats['earned_runs'] if pitching_stats else None,
                pitching_stats['walks_allowed'] if pitching_stats else None,
                pitching_stats['strikeouts'] if pitching_stats else None,
                pitching_stats['era'] if pitching_stats else None,
                pitching_stats['whip'] if pitching_stats else None
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
        
        print(f"  Created {records_for_date} player records")
        total_records += records_for_date
        
        current_date += timedelta(days=1)
    
    print(f"\n{'=' * 60}")
    print(f"Test data population complete!")
    print(f"  Total days: {days_back + 1}")
    print(f"  Total records: {total_records}")
    print(f"  Database: {db_path}")
    
    # Show sample of the data
    print(f"\nSample data from {end_date}:")
    cursor.execute("""
        SELECT player_name, batting_hits, batting_runs, batting_rbis, batting_home_runs
        FROM daily_gkl_player_stats
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
        db_path = Path(config['database_path'])
        if db_path.exists():
            print(f"Removing existing test database: {db_path}")
            db_path.unlink()
    
    populate_test_data(days_back=args.days)

if __name__ == "__main__":
    main()