"""
HealthOracle (The Medical Board)
Department: Dept_Health
Role: Provides a standard interface for other departments to query Agent Health.
"""
import sqlite3
import os
import logging
from dataclasses import dataclass

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

@dataclass
class HealthStatus:
    is_fit: bool
    score: float
    chronic_issue: bool
    reason: str

class HealthOracle:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        
    def check_fitness(self, agent_name: str) -> HealthStatus:
        """
        Determines if an agent is Fit For Duty.
        Criteria:
        - No Chronic Issue Detected
        - Health Score >= 50.0
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT health_score, chronic_issue_detected FROM agent_health_ledger WHERE name=?", (agent_name,))
                row = c.fetchone()
            
            if not row:
                # No record? Assume healthy (innocent until proven guilty).
                return HealthStatus(True, 100.0, False, "No medical record found.")
                
            score, chronic = row
            
            if chronic:
                return HealthStatus(False, score, True, "Chronic Issue Detected (Repeated Crashes).")
                
            if score < 50.0:
                return HealthStatus(False, score, False, f"Health Score Critical ({score:.1f}).")
                
            return HealthStatus(True, score, False, "Fit for Duty.")
            
        except Exception as e:
            logging.error(f"[HEALTH_ORACLE] Query Failed: {e}")
            # Fail open (safe) or closed? 
            # In a sovereign system, we fail OPEN to prevent paralysis, but log the error.
            return HealthStatus(True, 100.0, False, "Medical Records Unavailable.")
