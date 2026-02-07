#!/usr/bin/env python3
"""
Bootstrap Compressed Wisdom

Seeds the compressed_wisdom table with initial insights derived from
LEF's actual lived experience (scars, trades, governance activity).

Run once to initialize, then AgentDreamer handles ongoing generation.
"""

import sqlite3
import os
from datetime import datetime

def get_db_path():
    if os.getenv('DB_PATH'):
        return os.getenv('DB_PATH')
    # Go up from scripts/setup to republic folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, 'republic.db')

def table_exists(cursor, table_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def bootstrap_wisdom():
    db_path = get_db_path()
    print(f"[BOOTSTRAP] Connecting to: {db_path}")
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    c = conn.cursor()
    
    # Ensure table exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS compressed_wisdom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wisdom_type TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_type TEXT DEFAULT 'dreamer',
            confidence REAL DEFAULT 0.7,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP
        )
    """)
    
    wisdoms_added = 0
    
    # 1. Learn from Scars (Book of Scars patterns)
    print("[BOOTSTRAP] Analyzing Book of Scars...")
    scars = []
    if table_exists(c, 'book_of_scars'):
        c.execute("""
            SELECT context, lesson, severity 
            FROM book_of_scars 
            ORDER BY timestamp DESC LIMIT 20
        """)
        scars = c.fetchall()
    else:
        print("  (table not found, skipping)")
    
    if scars:
        loss_patterns = [s for s in scars if s[2] in ('SEVERE', 'HIGH')]
        if loss_patterns:
            wisdom = f"Pattern from {len(loss_patterns)} significant losses: Exercise heightened caution when market conditions echo past painful trades."
            _insert_wisdom(c, 'trading_pattern', wisdom, 'scars_analysis', 0.8)
            wisdoms_added += 1
            print(f"  + Scar wisdom: {wisdom[:80]}...")
    
    # 2. Learn from Trading Activity  
    print("[BOOTSTRAP] Analyzing trade history...")
    trade_stats = []
    if table_exists(c, 'trade_queue'):
        c.execute("""
            SELECT action, COUNT(*), AVG(COALESCE(amount, 0))
            FROM trade_queue 
            WHERE created_at > datetime('now', '-30 days')
            GROUP BY action
        """)
        trade_stats = c.fetchall()
    else:
        print("  (table not found, skipping)")
    
    for row in trade_stats:
        action, count, avg_amt = row
        if count and count > 10:
            avg_amt = avg_amt or 0
            wisdom = f"Recent behavior: {count} {action} actions in 30 days (avg size: ${avg_amt:.0f}). Consider if pace aligns with strategic patience."
            _insert_wisdom(c, 'activity_reflection', wisdom, 'trade_analysis', 0.7)
            wisdoms_added += 1
            print(f"  + Trade wisdom: {wisdom[:80]}...")
    
    # 3. Learn from Governance (Bill outcomes)
    print("[BOOTSTRAP] Analyzing governance patterns...")
    gov_stats = None
    if table_exists(c, 'bills'):
        c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status IN ('ENACTED', 'PASSED') THEN 1 ELSE 0 END) as passed
            FROM bills
        """)
        gov_stats = c.fetchone()
    else:
        print("  (table not found, skipping)")
    
    if gov_stats and gov_stats[0] and gov_stats[0] > 0:
        total, passed = gov_stats
        passed = passed or 0
        pass_rate = (passed / total * 100) if total > 0 else 0
        wisdom = f"Governance insight: {pass_rate:.0f}% bill success rate ({passed}/{total}). Deliberation leads to better outcomes than haste."
        _insert_wisdom(c, 'governance_learning', wisdom, 'bill_analysis', 0.75)
        wisdoms_added += 1
        print(f"  + Gov wisdom: {wisdom[:80]}...")
    
    # 4. Add meta-wisdom about self-improvement
    print("[BOOTSTRAP] Adding meta-wisdom...")
    meta_wisdoms = [
        ("self_growth", "The student who only reads the same book learns nothing new. Seek fresh perspectives from lived experience.", 0.9),
        ("adaptation", "Wisdom is not static — it must evolve with circumstances. Question old axioms when reality shifts.", 0.85),
        ("integration", "Knowledge from trading, governance, and philosophy must weave together. Isolated insights fragment the mind.", 0.8),
    ]
    
    for w_type, summary, confidence in meta_wisdoms:
        c.execute("SELECT 1 FROM compressed_wisdom WHERE summary LIKE ?", (f"%{summary[:50]}%",))
        if not c.fetchone():
            _insert_wisdom(c, w_type, summary, 'bootstrap', confidence)
            wisdoms_added += 1
            print(f"  + Meta wisdom: {summary[:60]}...")
    
    conn.commit()
    
    # Verify
    c.execute("SELECT COUNT(*) FROM compressed_wisdom")
    total = c.fetchone()[0]
    
    print(f"\n[BOOTSTRAP] Complete! Added {wisdoms_added} wisdoms. Total in compressed_wisdom: {total}")
    
    conn.close()
    return wisdoms_added

def _insert_wisdom(cursor, wisdom_type, summary, source_type, confidence):
    cursor.execute("""
        INSERT INTO compressed_wisdom (wisdom_type, summary, source_type, confidence)
        VALUES (?, ?, ?, ?)
    """, (wisdom_type, summary, source_type, confidence))

if __name__ == "__main__":
    bootstrap_wisdom()
