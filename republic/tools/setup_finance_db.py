
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'republic.db')

def setup_profit_allocation():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Track which trades have been taxed/processed
    c.execute("""
    CREATE TABLE IF NOT EXISTS profit_allocation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_id INTEGER,
        asset TEXT,
        realized_gain_usd REAL,
        irs_allocation REAL,
        snw_allocation REAL,
        reinvest_allocation REAL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trade_id) REFERENCES trade_queue(id)
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Profit Allocation Table initialized.")

if __name__ == "__main__":
    setup_profit_allocation()
