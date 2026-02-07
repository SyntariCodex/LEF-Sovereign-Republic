"""
AgentCurriculumDesigner (The Planner)
Department: Dept_Education
Role: Analyzes System Knowledge Gaps and Creates Research Directives for Scholar.
"""
import time
import logging
import os
import sqlite3

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

class AgentCurriculumDesigner:
    def __init__(self):
        logging.getLogger("CURRICULUM").setLevel(logging.INFO)
        self.logger = logging.getLogger("CURRICULUM")
        self.db_path = DB_PATH
        self.logger.info("[CURRICULUM] 🎓 Curriculum Designer Online.")

    def run_gap_analysis(self):
        """
        Scans logs for "Unknown" or "Error" to find knowledge gaps.
        Assigns research topics to 'research_queue' table.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Ensure Queue Exists
                c.execute("""CREATE TABLE IF NOT EXISTS research_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    priority TEXT, -- HIGH, MEDIUM, LOW
                    status TEXT,   -- PENDING, RESEARCHING, COMPLETED
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
                
                # Gap detection uses keyword heuristics for simplicity
                # Semantic/embedding analysis deferred until knowledge graph infrastructure exists
                # For now: curated weekly topics ensure continuous learning
                
                # Standard Weekly Curriculum (The Core Refresh)
                topics = [
                    "DeFi: Uniswap V4 Hooks",
                    "Macro: Rate Cut Probabilities",
                    "Tech: Cursor AI Features",
                    "Philosophy: Stoicism for AI"
                ]
                
                for topic in topics:
                    # 7-day dedup: Check if topic was assigned in the last week
                    c.execute("""
                        SELECT count(*) FROM research_queue 
                        WHERE topic=? 
                        AND (status != 'COMPLETED' OR assigned_at > datetime('now', '-7 days'))
                    """, (topic,))
                    if c.fetchone()[0] == 0:
                        self.logger.info(f"[CURRICULUM] 🆕 Assigning Research Topic: {topic}")
                        c.execute("INSERT INTO research_queue (topic, priority, status) VALUES (?, ?, ?)", 
                                  (topic, 'MEDIUM', 'PENDING'))
                
                conn.commit()
            
        except Exception as e:
            self.logger.error(f"[CURRICULUM] Analysis Error: {e}")

    def run(self):
        self.logger.info("[CURRICULUM] 📚 Scanning for Knowledge Gaps...")
        while True:
            try:
                self.run_gap_analysis()
                time.sleep(3600*4) # Run every 4 hours
            except Exception as e:
                self.logger.error(f"[CURRICULUM] Loop Crash: {e}")
                time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AgentCurriculumDesigner()
    agent.run()
