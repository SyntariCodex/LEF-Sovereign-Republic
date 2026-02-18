"""
AgentSurgeonGeneral (The Overseer)
Department: Dept_Health
Role: Coordinates all health-related activities. Escalates critical issues.
"""
import time
import logging
import sqlite3
import os

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


try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class AgentSurgeonGeneral:
    def __init__(self, db_path=None):
        logging.info("[SURGEON] 🩺 Surgeon General Reporting for Duty.")
        if not db_path:
            import sys
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if BASE_DIR not in sys.path:
                sys.path.insert(0, BASE_DIR)
            db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        self.db_path = db_path
        
    def monitor_health(self):
        """
        Triage Loop:
        1. Check agent_logs for recent CRITICAL/ERRORs.
        2. Update agent_health_ledger.
        3. Flag Chronic Issues.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # 1. Scan for recent crashes (Last 5 mins)
                # Exclude infrastructure loggers that produce ERROR/CRITICAL
                # entries during normal operation (not actual agent crashes)
                c.execute("""
                    SELECT source, MAX(message), count(*)
                    FROM agent_logs
                    WHERE level IN ('ERROR', 'CRITICAL')
                    AND timestamp > datetime('now', '-5 minutes')
                    AND source NOT IN (
                        'root', 'Brainstem', 'httpx', 'google_genai.models',
                        'SurfaceAwareness', 'FrequencyJournal', 'PathwayRegistry',
                        'DaatNode', 'ReverbTracker'
                    )
                    GROUP BY source
                """)
                errors = c.fetchall()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute, queue_insert
                    use_waq = True
                except ImportError:
                    use_waq = False
                
                for source, msg, count in errors:
                    agent_name = source.replace('[', '').replace(']', '').split(' ')[0]
                    if not agent_name or agent_name in ('unknown', ''):
                        continue
                    penalty = count * 10

                    from db.db_helper import ignore_insert_sql
                    ignore_sql = ignore_insert_sql('agent_health_ledger', ['name'], 'name')

                    if use_waq:
                        queue_execute(c, ignore_sql, (agent_name,), source_agent='AgentSurgeonGeneral')
                        queue_execute(c, "UPDATE agent_health_ledger SET crash_count = crash_count + :cnt, health_score = health_score - :pen WHERE name=:name",
                                     {'cnt': count, 'pen': penalty, 'name': agent_name}, source_agent='AgentSurgeonGeneral')
                    else:
                        c.execute(ignore_sql, (agent_name,))
                        c.execute("UPDATE agent_health_ledger SET crash_count = crash_count + ?, health_score = health_score - ? WHERE name=?", (count, penalty, agent_name))
                    
                    # Triage: Chronic Issue?
                    if count >= 3:
                        logging.critical(f"[SURGEON] 🚑 CHRONIC FAILURE DETECTED in {agent_name} ({count} crashes/5m).")
                        
                        alert_title = f"SCHISM ALERT: {agent_name}"
                        alert_msg = f"Chronic failures/Tracebacks detected. Code Defect likely active. \nLast Error: {msg}"
                        
                        c.execute("SELECT id FROM knowledge_stream WHERE title=? AND timestamp > datetime('now', '-1 hour')", (alert_title,))
                        if not c.fetchone():
                            if use_waq:
                                queue_insert(c, 'knowledge_stream', 
                                            {'source': 'SURGEON_GENERAL', 'title': alert_title, 'summary': alert_msg, 'sentiment_score': -1.0},
                                            source_agent='AgentSurgeonGeneral')
                                queue_execute(c, "UPDATE agent_health_ledger SET chronic_issue_detected=1 WHERE name=:name", {'name': agent_name}, source_agent='AgentSurgeonGeneral')
                            else:
                                c.execute("INSERT INTO knowledge_stream (source, title, summary, sentiment_score) VALUES (?, ?, ?, -1.0)",
                                          ("SURGEON_GENERAL", alert_title, alert_msg))
                                c.execute("UPDATE agent_health_ledger SET chronic_issue_detected=1 WHERE name=?", (agent_name,))
                            logging.info("[SURGEON] 💉 Schism Alert injected into Knowledge Stream.")

                # Heal Score (Regen)
                if use_waq:
                    queue_execute(c, "UPDATE agent_health_ledger SET health_score = MIN(100, health_score + 1) WHERE health_score < 100", {}, source_agent='AgentSurgeonGeneral')
                else:
                    c.execute("UPDATE agent_health_ledger SET health_score = MIN(100, health_score + 1) WHERE health_score < 100")
                
                conn.commit()
            
        except Exception as e:
            logging.error(f"[SURGEON] Triage Failed: {e}")

    def run(self):
        while True:
            self.monitor_health()
            time.sleep(60) # Rounds every minute
