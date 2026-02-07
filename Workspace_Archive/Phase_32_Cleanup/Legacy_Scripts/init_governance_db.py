import sqlite3
import os

DB_PATH = "republic.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create Agents Table (Two Pillars Schema)
    cursor.execute("DROP TABLE IF EXISTS agents")
    cursor.execute("""
        CREATE TABLE agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            role TEXT,
            department TEXT, -- WEALTH or PHILOSOPHY
            division TEXT,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)
    
    # 2. Seed Agents (The Republic)
    
    # --- PILLAR I: WEALTH ---
    wealth_agents = [
        ("AgentCIO", "Head of Wealth", "WEALTH", "EXECUTIVE"),
        ("AgentCFO", "Treasury Commander", "WEALTH", "TREASURY"),
        ("AgentCoinbase", "Execution Officer", "WEALTH", "OPERATIONS"),
        ("AgentOversight", "OIG & Audit", "WEALTH", "OPERATIONS"),
        ("AgentSentinel", "Strategy & Intel", "WEALTH", "STRATEGY"),
        ("AgentSimulator", "Backtesting Engine", "WEALTH", "STRATEGY"),     # Rescued
        ("AgentArchivist", "System Maintainer", "WEALTH", "OPERATIONS"),    # Rescued
        ("AgentBuilder", "Code Constructor", "WEALTH", "OPERATIONS"),       # Rescued
    ]
    
    # --- PILLAR II: PHILOSOPHY ---
    philosophy_agents = [
        ("AgentLEF", "Head of Philosophy", "PHILOSOPHY", "EXECUTIVE"),
        ("Department of Philosophy", "Observer", "PHILOSOPHY", "OBSERVER"), 
        ("AgentPsychologist", "Divergence Analyst", "PHILOSOPHY", "ANALYSIS"),
        ("AgentCritic", "Scotoma Security", "PHILOSOPHY", "SECURITY"),
        ("AgentScholar", "Chief Librarian", "PHILOSOPHY", "LIBRARY"),
        ("Congress", "Legislative Body", "PHILOSOPHY", "STRUCTURE"),        # Rescued
        ("The Court", "Judicial Body", "PHILOSOPHY", "ALIGNMENT"),          # Rescued
    ]
    
    # --- GLADIATOR (The Mercenary) ---
    # Gladiator serves both. We assign it to "OPERATIONS" technically but it floats.
    # Let's put it in WEALTH for now as it makes money, but it is a "Shared Asset".
    mercenaries = [
        ("AgentGladiator", "Arena Champion", "WEALTH", "OPERATIONS")
    ]
    
    all_agents = wealth_agents + philosophy_agents + mercenaries
    
    for name, role, dept, div in all_agents:
        cursor.execute("""
            INSERT INTO agents (name, role, department, division, level, xp, status)
            VALUES (?, ?, ?, ?, 1, 0, 'ACTIVE')
        """, (name, role, dept, div))
        
    conn.commit()
    print(f"[INIT] Republic Established. {len(all_agents)} Agents seeded.")
    conn.close()

if __name__ == "__main__":
    init_db()
