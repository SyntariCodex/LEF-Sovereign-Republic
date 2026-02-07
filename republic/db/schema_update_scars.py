
import sqlite3
import os

def update_schema():
    # Setup Path
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, 'republic.db')
    
    print(f"Updating Database: {db_path}")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create The Book of Scars
    c.execute("""
    CREATE TABLE IF NOT EXISTS lef_scars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scar_type TEXT, -- 'VETO', 'PANIC', 'CRASH', 'LOOP'
        description TEXT,
        context TEXT,   -- JSON dump of state
        timestamp TEXT,
        healed BOOLEAN DEFAULT 0
    )
    """)
    
    print("✅ Created Table: lef_scars")
    
    # Verify
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lef_scars'")
    if c.fetchone():
        print("Verified.")
    else:
        print("Error: Table not found.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_schema()
