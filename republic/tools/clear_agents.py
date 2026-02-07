import sqlite3
import time
import os

DB_PATH = os.path.abspath("fulcrum/republic.db")

def clear_agents():
    print(f"Attempting to clear 'agents' table in {DB_PATH}...")
    for i in range(5):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            c = conn.cursor()
            c.execute("DELETE FROM agents;")
            count = c.rowcount
            conn.commit()
            print(f"✅ Cleared {count} rows from agents table.")
            conn.close()
            return
        except sqlite3.OperationalError as e:
            print(f"⚠️ Lock detected ({e}). Retrying {i+1}/5...")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error: {e}")
            return
    print("❌ Failed to clear table after 5 attempts.")

if __name__ == "__main__":
    clear_agents()
