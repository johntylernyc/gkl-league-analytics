#!/usr/bin/env python3
"""
Debug database insertion specifically
"""

import sqlite3
import os

# Database configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(script_dir, '..', 'database', 'league_analytics.db')

def test_insertion():
    # Create a sample transaction
    sample_transactions = [{
        "date": "2025-07-25",
        "league_key": "mlb.l.6966",
        "transaction_id": "999",
        "transaction_type": "add",
        "player_id": "99999",
        "player_name": "Test Player",
        "position": "OF",
        "player_team": "TEST",
        "movement_type": "add",
        "fantasy_team_id": "13"
    }]
    
    sample_teams = {
        "13": {
            "team_id": "13",
            "team_key": "458.l.6966.t.13",
            "team_name": "Test Team",
            "manager_name": "Test Manager",
            "league_key": "mlb.l.6966"
        }
    }
    
    print("Testing database insertion...")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute('SELECT COUNT(*) FROM transactions_test')
    current_count = cursor.fetchone()[0]
    print(f"Current transactions in test table: {current_count}")
    
    # First insert fantasy teams
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO fantasy_teams 
            (team_id, team_key, team_name, manager_name, league_key, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ("13", "458.l.6966.t.13", "Test Team", "Test Manager", "mlb.l.6966"))
        
        teams_inserted = cursor.rowcount
        print(f"Fantasy teams inserted: {teams_inserted}")
        
        # Then insert transaction
        cursor.execute('''
            INSERT OR IGNORE INTO transactions_test 
            (date, league_key, transaction_id, transaction_type, player_id, 
             player_name, position, player_team, movement_type, fantasy_team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ("2025-07-25", "mlb.l.6966", "999", "add", "99999", "Test Player", "OF", "TEST", "add", "13"))
        
        txn_inserted = cursor.rowcount
        print(f"Transactions inserted: {txn_inserted}")
        
        conn.commit()
        
        # Check final state
        cursor.execute('SELECT COUNT(*) FROM transactions_test')
        final_count = cursor.fetchone()[0]
        print(f"Final transactions in test table: {final_count}")
        
        # Check if our test record exists
        cursor.execute('SELECT * FROM transactions_test WHERE transaction_id = ?', ("999",))
        test_record = cursor.fetchone()
        if test_record:
            print(f"Test record found: {test_record}")
        else:
            print("Test record NOT found")
            
        # Check for duplicates of this exact combination
        cursor.execute('''
            SELECT COUNT(*) FROM transactions_test 
            WHERE transaction_id = ? AND player_id = ? AND movement_type = ?
        ''', ("999", "99999", "add"))
        duplicate_count = cursor.fetchone()[0]
        print(f"Duplicate combinations for test record: {duplicate_count}")
        
    except Exception as e:
        print(f"Error during insertion: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()

if __name__ == "__main__":
    test_insertion()