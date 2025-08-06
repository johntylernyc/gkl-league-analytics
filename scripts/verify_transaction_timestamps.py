#!/usr/bin/env python3
"""
Verify transaction timestamps in the database.
"""
import sqlite3
from pathlib import Path
from datetime import datetime

def verify_timestamps():
    """Verify transaction timestamps in all databases."""
    databases = [
        ('Production', 'database/league_analytics.db'),
        ('Test', 'database/league_analytics_test.db')
    ]
    
    for db_name, db_path_str in databases:
        db_path = Path(__file__).parent.parent / db_path_str
        
        if not db_path.exists():
            print(f"\n{db_name} database not found: {db_path_str}")
            continue
            
        print(f"\n{db_name} Database Analysis")
        print("="*50)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            # Check if transactions table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
            if not cursor.fetchone():
                print("  transactions table does not exist")
                continue
            
            # Check if timestamp column exists
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'timestamp' not in columns:
                print("  WARNING: timestamp column does not exist!")
                continue
            
            # Check for NULL or 0 timestamps
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN timestamp IS NULL OR timestamp = 0 THEN 1 ELSE 0 END) as missing
                FROM transactions
            """)
            
            result = cursor.fetchone()
            if result:
                total, missing = result
                if total > 0:
                    print(f"  Total transactions: {total:,}")
                    print(f"  Missing timestamps: {missing:,} ({missing/total*100:.1f}%)")
                else:
                    print("  No transactions found")
            
            # Sample some recent records
            cursor.execute("""
                SELECT date, timestamp, player_name, transaction_type, movement_type
                FROM transactions
                ORDER BY date DESC, id DESC
                LIMIT 10
            """)
            
            rows = cursor.fetchall()
            if rows:
                print("\n  Recent transactions:")
                print("  " + "-"*80)
                for row in rows:
                    date, ts, player, trans_type, move_type = row
                    if ts and ts > 0:
                        dt = datetime.fromtimestamp(ts)
                        time_str = dt.strftime('%I:%M %p')
                        tz = "PST" if dt.month < 3 or dt.month > 11 else "PDT"
                        print(f"  {date} {time_str} {tz} - {move_type}: {player} ({trans_type})")
                    else:
                        print(f"  {date} (NO TIME) - {move_type}: {player} ({trans_type})")
            
            # Check date distribution of missing timestamps
            cursor.execute("""
                SELECT date, COUNT(*) as count
                FROM transactions
                WHERE timestamp IS NULL OR timestamp = 0
                GROUP BY date
                ORDER BY date DESC
                LIMIT 5
            """)
            
            missing_dates = cursor.fetchall()
            if missing_dates:
                print("\n  Dates with missing timestamps:")
                for date, count in missing_dates:
                    print(f"    {date}: {count} transactions")
                    
        except sqlite3.Error as e:
            print(f"  Database error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    print("Transaction Timestamp Verification")
    print("==================================")
    verify_timestamps()
    
    print("\n\nNext Steps:")
    print("-----------")
    print("1. If missing timestamps exist, run backfill for those date ranges")
    print("2. Test the updated collection scripts with a small date range")
    print("3. Verify new transactions have timestamps")
    print("4. Proceed to frontend implementation")