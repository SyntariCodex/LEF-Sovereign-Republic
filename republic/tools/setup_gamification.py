
import sqlite3
import os
import time

# DB Path Logic
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def setup_gamification():
    print(f"[GAME] 🎮 Connecting to DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Create Table
    print("[GAME] Creating 'agents' table...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        name TEXT PRIMARY KEY,
        branch TEXT,
        role TEXT,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        status TEXT DEFAULT 'SLEEPING',
        last_active TIMESTAMP
    )
    """)
    
    # 2. Populate Initial Roster (The Founding Fathers)
    roster = [
        # PRESIDENCY
        ('LEF', 'PRESIDENCY', 'The Sovereign Observer', 100, 999999, 'ACTIVE'),
        
        # JUDICIAL
        ('SUPREME_COURT', 'JUDICIAL', 'Dispute Resolution', 10, 5000, 'READY'),
        ('OVERSIGHT', 'JUDICIAL', 'Inspector General', 5, 2000, 'WATCHING'),
        
        # EXECUTIVE - STRATEGY
        ('CIO', 'STRATEGY', 'Chief Investment Officer', 5, 2500, 'ACTIVE'),
        ('HUNTER', 'STRATEGY', 'Alpha Division', 3, 1000, 'HUNTING'),
        ('SCANNER', 'STRATEGY', 'Asset Discovery', 2, 500, 'SCANNING'),
        
        # EXECUTIVE - OPERATIONS
        ('COINBASE', 'OPERATIONS', 'Execution Logistics', 5, 3000, 'ONLINE'),
        ('EXPANSION', 'OPERATIONS', 'Future Integrations', 1, 0, 'PENDING'),
        
        # EXECUTIVE - TREASURY
        ('CFO', 'TREASURY', 'Risk Management', 6, 4000, 'SECURE'),
        ('STEWARD', 'TREASURY', 'Legacy Projects', 4, 1500, 'FUNDED'),
        
        # INNOVATION
        ('BUILDER', 'INNOVATION', 'Dept of Engineering', 7, 5000, 'BUILDING'),
        ('SCHOLAR', 'INNOVATION', 'Research & Knowledge', 3, 1200, 'READING'),
        
        # LEGISLATIVE
        ('HOUSE', 'LEGISLATIVE', 'House of Builders', 2, 800, 'VOTING'),
        ('SENATE', 'LEGISLATIVE', 'Senate of Minds', 8, 6000, 'REVIEW')
    ]
    
    print("[GAME] Populating Roster...")
    for name, branch, role, level, xp, status in roster:
        try:
            c.execute("""
            INSERT INTO agents (name, branch, role, level, xp, status, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                branch=excluded.branch,
                role=excluded.role
            """, (name, branch, role, level, xp, status, time.time()))
        except Exception as e:
            print(f"Error adding {name}: {e}")
            
    conn.commit()
    conn.close()
    print("[GAME] ✅ Gamification Layer Installed.")

if __name__ == "__main__":
    setup_gamification()
