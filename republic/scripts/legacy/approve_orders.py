import sqlite3
import time
import os

DB_PATH = 'republic/republic.db'

def approve_orders():
    print(f"Connecting to {DB_PATH}...")
    # Retry loop
    for i in range(5):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60.0) # High timeout
            c = conn.cursor()
            c.execute("UPDATE trade_queue SET status='APPROVED' WHERE status='NEW' AND reason='GROWTH_STRATEGY'")
            count = c.rowcount
            conn.commit()
            conn.close()
            print(f"✅ Success! Approved {count} stuck orders.")
            return
        except sqlite3.OperationalError as e:
            print(f"🔒 Database locked. Retrying ({i+1}/5)...")
            time.sleep(1)
            
if __name__ == "__main__":
    approve_orders()
