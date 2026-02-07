"""
AgentChiefOfStaff
Department: The_Cabinet
Role: Overseer & Router. Ensures laws are enacted.
"""
import os
import time
import sqlite3
import logging
from dotenv import load_dotenv

# Import genai using new package
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Import Health Oracle (The Medical Board)
from departments.Dept_Health.interface import HealthOracle

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


# Load Environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

class AgentChiefOfStaff:
    def __init__(self):
        logging.info("[CoS] 🦅 Chief of Staff Reporting.")
        self.last_log_id = 0
        self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        self.health_oracle = HealthOracle(self.db_path)
        
        # Initialize Gemini (The Brain)
        self.client = None
        self.model_id = 'gemini-2.0-flash'
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
            logging.info("[CoS] 🟢 Cortex Connected (Gemini).")
        else:
            logging.warning("[CoS] 🔴 Cortex Disconnected (No API Key or package).")
        
        # Initialize last_log_id to current max
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT MAX(id) FROM agent_logs")
            row = c.fetchone()
            if row and row[0]:
                self.last_log_id = row[0]
            conn.close()
        except sqlite3.Error:
            pass

    def run(self):
        """
        Main Loop: Monitor republic health and route tasks.
        """
        while True:
            # Health Check (Consult the Oracle)
            status = self.health_oracle.check_fitness("SCHOLAR")
            
            # NOTE: draft_submission_pitch() removed - competitions require human-in-loop
            
            time.sleep(10) # 10s Poll Cycle

    # NOTE: draft_submission_pitch() removed - External competitions require human-in-loop

    def print_roll_call(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT name, current_task, level FROM agents ORDER BY level DESC")
            agents = c.fetchall()
            conn.close()
            
            print(f"[CoS] 🦅 Republic Status Check: {len(agents)} Agents Online.")
        except sqlite3.Error:
            pass

