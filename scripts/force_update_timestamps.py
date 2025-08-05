#!/usr/bin/env python3
"""Force update timestamps - simplified approach."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check the actual state
cursor.execute("SELECT transaction_id, timestamp FROM transactions WHERE date = '2025-08-04' LIMIT 5")
print("Before update:")
for row in cursor.fetchall():
    print(f"  Transaction {row[0]}: timestamp = {row[1]}")

# Force update a specific transaction
cursor.execute("""
    UPDATE transactions 
    SET timestamp = 1754397670
    WHERE transaction_id = '583' 
    AND league_key = '458.l.6966'
""")

print(f"\nRows updated: {cursor.rowcount}")

# Check after update
cursor.execute("SELECT transaction_id, timestamp FROM transactions WHERE transaction_id = '583'")
print("\nAfter update:")
for row in cursor.fetchall():
    print(f"  Transaction {row[0]}: timestamp = {row[1]}")

conn.commit()
conn.close()