import time
import os
import sys

# Phase 37: Use env-based DB path instead of hardcoded (TLS-03)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


def clear_agents():
    print(f"Attempting to clear 'agents' table in {DB_PATH}...")
    for i in range(5):
        try:
            with db_connection(DB_PATH) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM agents;")
                count = c.rowcount
                conn.commit()
                print(f"✅ Cleared {count} rows from agents table.")
                return
        except Exception as e:
            if 'locked' in str(e).lower():
                print(f"⚠️ Lock detected ({e}). Retrying {i+1}/5...")
                time.sleep(2)
            else:
                print(f"❌ Error: {e}")
                return
    print("❌ Failed to clear table after 5 attempts.")

if __name__ == "__main__":
    clear_agents()
