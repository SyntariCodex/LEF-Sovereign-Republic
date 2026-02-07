"""
Schema Update: Operational Costs Table
Tracks actual API costs for accurate runway calculation.
"""

import sqlite3
import os

def create_operational_costs_table():
    """Creates operational_costs table for real cost tracking."""
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(BASE_DIR, 'republic.db')
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS operational_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cost_type TEXT,
                cost_usd REAL,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("[SCHEMA] ✅ operational_costs table created/verified")
        
    except Exception as e:
        print(f"[SCHEMA] Error creating operational_costs: {e}")

if __name__ == "__main__":
    create_operational_costs_table()
