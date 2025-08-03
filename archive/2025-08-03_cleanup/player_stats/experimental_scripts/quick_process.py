#!/usr/bin/env python3
"""Quick script to process staging data into final table."""

import sqlite3
from datetime import date

db_path = 'R:/GitHub/gkl-league-analytics/database/league_analytics_test.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get unique players from staging
cursor.execute("""
    SELECT DISTINCT player_name, team FROM mlb_batting_stats_staging_test
    UNION
    SELECT DISTINCT player_name, team FROM mlb_pitching_stats_staging_test
""")
players = cursor.fetchall()

print(f"Processing {len(players)} unique players...")

success_count = 0
for player_name, team in players[:100]:  # Process first 100 as test
    # Get batting stats
    cursor.execute("""
        SELECT games_played, at_bats, runs, hits, home_runs, rbis 
        FROM mlb_batting_stats_staging_test 
        WHERE player_name = ? AND team = ? 
        LIMIT 1
    """, (player_name, team))
    batting = cursor.fetchone()
    
    # Get pitching stats
    cursor.execute("""
        SELECT games_played, wins, losses, saves, era, whip
        FROM mlb_pitching_stats_staging_test
        WHERE player_name = ? AND team = ?
        LIMIT 1
    """, (player_name, team))
    pitching = cursor.fetchone()
    
    # Create simple record
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_gkl_player_stats_test (
                job_id, date, yahoo_player_id, player_name, team_code,
                games_played, has_batting_data, has_pitching_data,
                batting_at_bats, batting_runs, batting_hits, batting_home_runs, batting_rbis,
                pitching_wins, pitching_losses, pitching_saves, pitching_era, pitching_whip,
                confidence_score
            ) VALUES (
                'manual_test', '2024-07-01', ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                0.5
            )
        """, (
            f"test_{player_name.replace(' ', '_').lower()}",  # Fake yahoo ID
            player_name,
            team,
            (batting[0] if batting else 0) or (pitching[0] if pitching else 0),
            batting is not None,
            pitching is not None,
            batting[1] if batting else None,  # at_bats
            batting[2] if batting else None,  # runs
            batting[3] if batting else None,  # hits
            batting[4] if batting else None,  # home_runs
            batting[5] if batting else None,  # rbis
            pitching[1] if pitching else None,  # wins
            pitching[2] if pitching else None,  # losses
            pitching[3] if pitching else None,  # saves
            pitching[4] if pitching else None,  # era
            pitching[5] if pitching else None,  # whip
        ))
        success_count += 1
        print(f"[OK] Processed {player_name} ({team})")
    except Exception as e:
        print(f"[FAIL] Failed {player_name}: {e}")

conn.commit()
print(f"\nProcessed {success_count} players successfully")

# Check results
cursor.execute("SELECT COUNT(*) FROM daily_gkl_player_stats_test")
total = cursor.fetchone()[0]
print(f"Total records in final table: {total}")

# Show sample
cursor.execute("""
    SELECT player_name, team_code, has_batting_data, has_pitching_data,
           batting_home_runs, pitching_wins
    FROM daily_gkl_player_stats_test
    LIMIT 5
""")
print("\nSample final records:")
for row in cursor.fetchall():
    print(f"  {row[0]} ({row[1]}): Batting={row[2]}, Pitching={row[3]}, HR={row[4]}, W={row[5]}")

conn.close()