#!/usr/bin/env python3
"""Direct timestamp update."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'database' / 'league_analytics.db'
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Direct update
cursor.execute("""
    UPDATE transactions 
    SET timestamp = 1754397670
    WHERE transaction_id = '583'
""")

print(f"Rows updated: {cursor.rowcount}")

# Verify
cursor.execute("SELECT transaction_id, timestamp FROM transactions WHERE transaction_id = '583'")
for row in cursor.fetchall():
    print(f"Transaction {row[0]}: timestamp = {row[1]}")

conn.commit()
conn.close()