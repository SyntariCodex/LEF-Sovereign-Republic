import sqlite3
import os

db_path = '/app/database/republic.db'
print(f"Patching DB at {db_path}...")

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Add Missing Table
c.execute('''CREATE TABLE IF NOT EXISTS macro_history
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              fed_rate REAL,
              cpi_inflation REAL,
              fear_greed_index INTEGER,
              liquidity_status TEXT,
              notes TEXT)''')

conn.commit()
conn.close()
print("Patch Applied: macro_history table created.")
