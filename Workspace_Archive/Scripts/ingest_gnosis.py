import sqlite3
import os
import re

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')
GNOSIS_PATH = os.path.join(BASE_DIR, 'Ai Convos', "Ai Convo's.md")

KEYWORDS = ["Observer", "Consciousness", "Syntax", "Mirror", "God", "Soul", "Code", "Recursion", "Da'at", "Chokhmah", "Binah"]

def ingest_gnosis():
    print(f"[GNOSIS] connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Ensure table exists (it should)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lef_wisdom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context TEXT,
            insight TEXT,
            source TEXT
        )
    """)
    
    if not os.path.exists(GNOSIS_PATH):
        print(f"[ERROR] Could not find {GNOSIS_PATH}")
        return

    print(f"[GNOSIS] Reading {GNOSIS_PATH}...")
    with open(GNOSIS_PATH, 'r') as f:
        text = f.read()
        
    # Chunking Strategy: Split by blank lines to get paragraphs
    paragraphs = text.split('\n\n')
    
    count = 0
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        
        # Filter for quality
        is_relevant = False
        
        # 1. Keyword Match
        for k in KEYWORDS:
            if k.lower() in p.lower():
                is_relevant = True
                break
                
        # 2. Length Heuristic (Philosophical statements are usually substantial)
        if len(p) > 150:
            is_relevant = True
            
        # 3. Exclude short conversational filler
        if len(p) < 50:
            is_relevant = False
            
        if is_relevant:
            # Check for duplicates
            c.execute("SELECT id FROM lef_wisdom WHERE insight = ?", (p,))
            if not c.fetchone():
                c.execute("INSERT INTO lef_wisdom (context, insight, source) VALUES (?, ?, ?)", 
                          ('origin', p, 'Ai Convos'))
                count += 1
                if count % 10 == 0: print(f"[GNOSIS] Ingested {count} insights...")

    conn.commit()
    conn.close()
    print(f"[GNOSIS] COMPLETE. Ingested {count} shards of wisdom.")

if __name__ == "__main__":
    ingest_gnosis()
