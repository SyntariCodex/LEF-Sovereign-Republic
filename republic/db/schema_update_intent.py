#!/usr/bin/env python3
"""
Schema update for Intent Executor (Motor Cortex).
Creates intent_queue table to track LEF's actionable intentions.
"""
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def update_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Intent Queue - tracks LEF's actionable intentions
    c.execute("""
        CREATE TABLE IF NOT EXISTS intent_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_thought_id INTEGER,
            intent_type TEXT,
            intent_content TEXT,
            target_agent TEXT,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'PENDING',
            result TEXT,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            executed_at DATETIME,
            FOREIGN KEY (source_thought_id) REFERENCES lef_monologue(id)
        )
    """)
    
    # Index for efficient polling
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_intent_status 
        ON intent_queue(status, priority DESC, created_at ASC)
    """)
    
    conn.commit()
    conn.close()
    print("✅ Intent queue schema created successfully")

if __name__ == "__main__":
    update_schema()
