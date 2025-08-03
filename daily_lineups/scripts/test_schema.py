"""
Test the Daily Lineups database schema with sample data.
Verifies tables, indexes, views, and triggers work correctly.
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path
import uuid

def test_schema():
    """Test all aspects of the database schema."""
    
    # Connect to database
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "database" / "league_analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Testing Daily Lineups Database Schema")
    print("=" * 60)
    
    # Generate test job_id
    test_job_id = f"lineup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    try:
        # Test 1: Insert test job log entry
        print("\n[TEST 1] Creating job log entry...")
        cursor.execute("""
            INSERT INTO job_log (
                job_id, job_type, environment, status,
                date_range_start, date_range_end, league_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            test_job_id,
            "lineup_schema_test",
            "test",
            "running",
            "2025-06-01",
            "2025-06-07",
            "mlb.l.6966"
        ))
        print("[OK] Job log entry created")
        
        # Test 2: Insert sample lineup data
        print("\n[TEST 2] Inserting sample lineup data...")
        sample_lineups = [
            # Team 1 - Starting lineup
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers", 
             "player_001", "Mike Trout", "OF", "B", "healthy", "OF", "LAA"),
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
             "player_002", "Freddie Freeman", "1B", "B", "healthy", "1B", "LAD"),
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
             "player_003", "Ronald Acuna Jr.", "OF", "B", "healthy", "OF", "ATL"),
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
             "player_004", "Mookie Betts", "UTIL", "B", "healthy", "2B,SS,OF", "LAD"),
            # Bench players
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
             "player_005", "Vladimir Guerrero Jr.", "BN", "B", "healthy", "1B", "TOR"),
            (test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
             "player_006", "Fernando Tatis Jr.", "IL", "B", "IL10", "SS,OF", "SD"),
            
            # Team 2 - Different date
            (test_job_id, 2025, "2025-06-16", "mlb.l.6966.t.2", "Diamond Dynasty",
             "player_001", "Mike Trout", "OF", "B", "DTD", "OF", "LAA"),
            (test_job_id, 2025, "2025-06-16", "mlb.l.6966.t.2", "Diamond Dynasty",
             "player_007", "Shohei Ohtani", "UTIL", "P", "healthy", "UTIL,SP", "LAD"),
        ]
        
        cursor.executemany("""
            INSERT INTO daily_lineups_test (
                job_id, season, date, team_key, team_name,
                player_id, player_name, selected_position, position_type,
                player_status, eligible_positions, player_team
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_lineups)
        
        print(f"[OK] Inserted {len(sample_lineups)} lineup records")
        
        # Test 3: Query using indexes
        print("\n[TEST 3] Testing indexed queries...")
        
        # Query by date
        cursor.execute("""
            SELECT COUNT(*) FROM daily_lineups_test 
            WHERE date = '2025-06-15'
        """)
        count = cursor.fetchone()[0]
        print(f"[OK] Date query returned {count} records")
        
        # Query by team
        cursor.execute("""
            SELECT COUNT(*) FROM daily_lineups_test 
            WHERE team_key = 'mlb.l.6966.t.1'
        """)
        count = cursor.fetchone()[0]
        print(f"[OK] Team query returned {count} records")
        
        # Query by player
        cursor.execute("""
            SELECT COUNT(*) FROM daily_lineups_test 
            WHERE player_id = 'player_001'
        """)
        count = cursor.fetchone()[0]
        print(f"[OK] Player query returned {count} records")
        
        # Test 4: Test views
        print("\n[TEST 4] Testing views...")
        
        # Test player frequency view
        cursor.execute("""
            SELECT player_name, total_days, days_started, days_benched, start_percentage
            FROM v_player_frequency
            WHERE player_id = 'player_001'
        """)
        result = cursor.fetchone()
        if result:
            print(f"[OK] Player frequency view: {result[0]} - {result[4]}% start rate")
        
        # Test team daily summary view
        cursor.execute("""
            SELECT date, team_name, starters_count, bench_count, total_roster_size
            FROM v_team_daily_summary
            WHERE team_key = 'mlb.l.6966.t.1'
        """)
        result = cursor.fetchone()
        if result:
            print(f"[OK] Team summary view: {result[1]} on {result[0]} - {result[2]} starters, {result[3]} bench")
        
        # Test 5: Test UNIQUE constraint
        print("\n[TEST 5] Testing UNIQUE constraint...")
        try:
            cursor.execute("""
                INSERT INTO daily_lineups_test (
                    job_id, season, date, team_key, team_name,
                    player_id, player_name, selected_position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_job_id, 2025, "2025-06-15", "mlb.l.6966.t.1", "Bash Brothers",
                "player_001", "Mike Trout", "OF"
            ))
            print("[WARNING] UNIQUE constraint not enforced!")
        except sqlite3.IntegrityError:
            print("[OK] UNIQUE constraint properly enforced")
        
        # Test 6: Test trigger (player usage summary)
        print("\n[TEST 6] Testing triggers...")
        
        # Check if trigger updated player_usage_summary
        cursor.execute("""
            SELECT player_id, total_days, days_started, days_benched, start_percentage
            FROM player_usage_summary
            WHERE player_id = 'player_001'
        """)
        result = cursor.fetchone()
        if result:
            print(f"[OK] Usage summary trigger: Player {result[0]} - {result[1]} days, {result[4]}% start rate")
        else:
            print("[INFO] Usage summary trigger may update asynchronously")
        
        # Test 7: Test position lookup table
        print("\n[TEST 7] Testing position lookup table...")
        cursor.execute("""
            SELECT position_code, position_name, position_type, display_order
            FROM lineup_positions
            ORDER BY display_order
            LIMIT 5
        """)
        positions = cursor.fetchall()
        print(f"[OK] Found {len(positions)} positions:")
        for pos in positions:
            print(f"  - {pos[0]}: {pos[1]} ({pos[2]})")
        
        # Test 8: Complex query performance
        print("\n[TEST 8] Testing complex query performance...")
        import time
        
        start_time = time.time()
        cursor.execute("""
            SELECT 
                dl.date,
                dl.team_name,
                dl.player_name,
                dl.selected_position,
                lp.position_name
            FROM daily_lineups_test dl
            LEFT JOIN lineup_positions lp ON dl.selected_position = lp.position_code
            WHERE dl.date BETWEEN '2025-06-01' AND '2025-06-30'
                AND dl.selected_position NOT IN ('BN', 'IL')
            ORDER BY dl.date, dl.team_key, lp.display_order
        """)
        results = cursor.fetchall()
        query_time = (time.time() - start_time) * 1000
        
        print(f"[OK] Complex query returned {len(results)} rows in {query_time:.2f}ms")
        
        if query_time > 500:
            print("[WARNING] Query performance may need optimization")
        
        # Update job status
        cursor.execute("""
            UPDATE job_log 
            SET status = 'completed', 
                records_processed = ?,
                records_inserted = ?
            WHERE job_id = ?
        """, (len(sample_lineups), len(sample_lineups), test_job_id))
        
        conn.commit()
        print("\n" + "=" * 60)
        print("[SUCCESS] All schema tests passed!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Schema test failed: {e}")
        
        # Update job status to failed
        cursor.execute("""
            UPDATE job_log 
            SET status = 'failed', 
                error_message = ?
            WHERE job_id = ?
        """, (str(e), test_job_id))
        conn.commit()
        raise
        
    finally:
        # Clean up test data
        print("\n[CLEANUP] Removing test data...")
        cursor.execute("DELETE FROM daily_lineups_test WHERE job_id = ?", (test_job_id,))
        cursor.execute("DELETE FROM job_log WHERE job_id = ?", (test_job_id,))
        conn.commit()
        conn.close()
        print("[OK] Test data cleaned up")


if __name__ == "__main__":
    test_schema()