import sqlite3
import os

DB_PATH = os.path.abspath("republic.db")

def enable_wal():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current mode
        cursor.execute("PRAGMA journal_mode;")
        current_mode = cursor.fetchone()[0]
        print(f"Current Mode: {current_mode}")
        
        if current_mode.upper() != 'WAL':
            cursor.execute("PRAGMA journal_mode=WAL;")
            new_mode = cursor.fetchone()[0]
            print(f"✅ Enabled WAL Mode. New Mode: {new_mode}")
        else:
            print("✅ Already in WAL Mode.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    enable_wal()
