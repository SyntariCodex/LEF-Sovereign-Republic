
import sqlite3
import os

DB_PATH = "republic.db"

def migrate_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Ensure Table Structure (Already done by init_governance, but safe to check)
        # 2. Update AgentGladiator
        print("Moving AgentGladiator to 'The Syndicate'...")
        cursor.execute("""
            UPDATE agents 
            SET department = 'Wealth', role = 'Head of Mercenary Ops', status = 'ACTIVE' 
            WHERE name = 'AgentGladiator'
        """)
        
        # 3. Insert AgentNumerai
        print("Recruiting AgentNumerai...")
        cursor.execute("""
            INSERT OR REPLACE INTO agents (name, role, department, status)
            VALUES (
                'AgentNumerai', 
                'Quant Specialist', 
                'Wealth', 
                'ACTIVE'
            )
        """)
        
        conn.commit()
        print("✅ The Syndicate is now active in the Republic.")
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_db()
