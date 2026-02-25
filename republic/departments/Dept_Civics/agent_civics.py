"""
AgentCivics (The Governor)
Department: Dept_Civics
Role: Governance & Ethical Frameworks Research (v1.2 Restored)

Function (Per v1.2 Charter):
1. Studies comparative governance systems
2. Monitors AI alignment research developments
3. Tracks constitutional design and regulatory landscapes
4. Informs law-writing (AttorneyGeneral) and philosophical coherence (Consciousness)
5. Proposes constitutional amendments

NOTE: Macro score calculation has been moved to AgentInfo (Phase 11).
This agent now focuses purely on governance research per original v1.2 design.
"""

import os
import sys
import time
import json
import logging
import logging.handlers
import redis
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# Phase 34: Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or os.path.join(BASE_DIR, 'republic.db'), timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

# Constitutional Enforcement (Phase 21)
try:
    from .agent_constitution_guard import ConstitutionGuard
except ImportError:
    ConstitutionGuard = None

# Paths
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
CONSTITUTION_PATH = os.path.join(BASE_DIR, 'CONSTITUTION.md')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            os.path.join(BASE_DIR, 'republic.log'),
            maxBytes=50 * 1024 * 1024,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)


class AgentCivics:
    """
    The Governor: Governance & Ethics Research Specialist.
    
    Restored to v1.2 role per Phase 11 reorganization.
    No longer calculates macro scores (moved to AgentInfo/RiskMonitor).
    """
    
    # AI Alignment research sources to monitor
    ALIGNMENT_SOURCES = [
        "anthropic.com/research",
        "openai.com/research", 
        "deepmind.com/research",
        "alignmentforum.org"
    ]
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentCivics"
        logging.info("[CIVICS] ⚖️ The Governor is Awake (Governance Focus).")
        
        # Redis for events - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.redis = get_redis()
        except ImportError:
            try:
                self.redis = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'),
                                          port=6379, db=0, decode_responses=True)
                self.redis.ping()
            except (redis.RedisError, ConnectionError):
                self.redis = None
    
    # Phase 34: _get_db_connection() removed — all callers use db_connection() context manager
    
    # =========================================================================
    # GOVERNANCE HEALTH MONITORING
    # =========================================================================
    
    def check_governance_health(self):
        """
        The Watchman: Monitor governance pipeline for stalled items.
        """
        try:
            # Check for stalled bills
            root_dir = os.path.dirname(BASE_DIR)
            gov_dir = os.path.join(root_dir, 'governance')
            proposals_dir = os.path.join(gov_dir, 'proposals')
            senate_dir = os.path.join(gov_dir, 'senate')
            
            stalled_count = 0
            gridlock_count = 0
            now = time.time()
            
            # Check stalled drafts (>3 days)
            # Use throttled scanning to prevent file handle exhaustion
            try:
                from system.directory_scanner import list_json_files
            except ImportError:
                list_json_files = lambda p: [f for f in os.listdir(p) if f.endswith('.json')] if os.path.exists(p) else []
            
            if os.path.exists(proposals_dir):
                for f in list_json_files(proposals_dir):
                    path = os.path.join(proposals_dir, f)
                    if now - os.path.getmtime(path) > 259200:  # 3 days
                        stalled_count += 1
            
            # Check senate gridlock (>24 hours)
            if os.path.exists(senate_dir):
                for f in list_json_files(senate_dir):
                    path = os.path.join(senate_dir, f)
                    if now - os.path.getmtime(path) > 86400:  # 24 hours
                        gridlock_count += 1
            
            if stalled_count > 0 or gridlock_count > 0:
                level = "WARNING" if stalled_count > 5 else "INFO"
                self._log_event(level, f"Governance Health: {stalled_count} stalled bills, {gridlock_count} gridlocked")
                
                # Propose action if severe
                if stalled_count > 5:
                    self._propose_amendment("EXPEDITE_REVIEW", 
                        "Too many stalled proposals. Consider automated review triggers.")
            
            return {'stalled': stalled_count, 'gridlock': gridlock_count}
            
        except Exception as e:
            logging.error(f"[CIVICS] Governance health check error: {e}")
            return {'stalled': 0, 'gridlock': 0}
    
    # =========================================================================
    # AI ALIGNMENT RESEARCH MONITORING
    # =========================================================================
    
    def monitor_alignment_research(self):
        """
        Track AI alignment developments that may affect LEF's evolution.
        Reads from knowledge_stream for relevant articles.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("""
                    SELECT id, title, summary, source FROM knowledge_stream
                    WHERE (title LIKE '%alignment%' OR title LIKE '%safety%'
                           OR summary LIKE '%RLHF%' OR summary LIKE '%governance%')
                    AND timestamp > datetime('now', '-7 days')
                    ORDER BY timestamp DESC LIMIT 10
                """)

                alignment_items = c.fetchall()
            
            if alignment_items:
                logging.info(f"[CIVICS] 📚 Found {len(alignment_items)} alignment research items")
                
                for item in alignment_items:
                    item_id, title, summary, source = item
                    # Could trigger deeper analysis or proposal drafting here
                    self._log_event("INFO", f"Alignment Research: {title[:100]}")
            
            return len(alignment_items)
            
        except Exception as e:
            logging.error(f"[CIVICS] Alignment monitoring error: {e}")
            return 0
    
    # =========================================================================
    # CONSTITUTIONAL AMENDMENT PROPOSALS
    # =========================================================================
    
    def _propose_amendment(self, amendment_type, rationale):
        """
        Draft a constitutional amendment proposal for Senate review.
        """
        try:
            proposal = {
                'type': 'CONSTITUTIONAL_AMENDMENT',
                'amendment_type': amendment_type,
                'rationale': rationale,
                'proposed_by': self.name,
                'timestamp': datetime.now().isoformat(),
                'status': 'DRAFT'
            }
            
            # Write to governance pipeline
            root_dir = os.path.dirname(BASE_DIR)
            proposals_dir = os.path.join(root_dir, 'governance', 'proposals')
            os.makedirs(proposals_dir, exist_ok=True)
            
            filename = f"AMENDMENT_{amendment_type}_{int(time.time())}.json"
            filepath = os.path.join(proposals_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(proposal, f, indent=2)
            
            logging.info(f"[CIVICS] 📜 Amendment Proposed: {amendment_type}")
            
            # Notify via Redis
            if self.redis:
                self.redis.publish('events', json.dumps({
                    'type': 'AMENDMENT_PROPOSED',
                    'source': self.name,
                    'amendment_type': amendment_type,
                    'timestamp': datetime.now().isoformat()
                }))
            
        except Exception as e:
            logging.error(f"[CIVICS] Amendment proposal error: {e}")
    
    # =========================================================================
    # MENTAL MODEL INTEGRATION (Bridge to Consciousness)
    # =========================================================================
    
    def connect_intellect(self):
        """
        The Bridge: Apply mental models from Consciousness to governance policy.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("""
                    SELECT id, name, implication_bullish, implication_bearish
                    FROM mental_models
                    WHERE last_applied IS NULL
                    LIMIT 1
                """)
                row = c.fetchone()

                if row:
                    model_id, name, bull_imp, bear_imp = row
                    logging.info(f"[CIVICS] Applying Mental Model: {name}")

                    msg = f"POLICY INSIGHT via {name}: Consider implications for governance structure"
                    self._log_event("INFO", msg)

                    c.execute("UPDATE mental_models SET last_applied=CURRENT_TIMESTAMP WHERE id=?", (model_id,))
                    conn.commit()

        except Exception as e:
            logging.error(f"[CIVICS] Intellect bridge error: {e}")
    
    # =========================================================================
    # REGULATORY LANDSCAPE MONITORING
    # =========================================================================
    
    def monitor_regulatory_landscape(self):
        """
        Track crypto/AI regulatory developments from knowledge stream.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("""
                    SELECT title, summary FROM knowledge_stream
                    WHERE (title LIKE '%regulation%' OR title LIKE '%SEC%'
                           OR title LIKE '%compliance%' OR summary LIKE '%regulatory%')
                    AND timestamp > datetime('now', '-3 days')
                    ORDER BY timestamp DESC LIMIT 5
                """)

                regulatory_items = c.fetchall()
            
            if regulatory_items:
                logging.info(f"[CIVICS] 📋 Found {len(regulatory_items)} regulatory updates")
                for title, _ in regulatory_items:
                    self._log_event("INFO", f"Regulatory Update: {title[:80]}")
            
            return len(regulatory_items)
            
        except Exception as e:
            logging.error(f"[CIVICS] Regulatory monitoring error: {e}")
            return 0
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _log_event(self, level, message):
        """Log governance event to database."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                    (self.name, level, message)
                )
                conn.commit()
        except Exception:
            pass
    
    # =========================================================================
    # MAIN CYCLE
    # =========================================================================
    
    def run_cycle(self):
        """
        Governance Cycle (Runs every 5 minutes).
        
        Focus areas:
        1. Governance health monitoring
        2. AI alignment research tracking
        3. Mental model integration
        4. Regulatory landscape monitoring
        """
        logging.info("[CIVICS] 🕰️ Governance Session Starting...")
        
        while True:
            try:
                # 1. Check governance health
                self.check_governance_health()
                
                # 2. Monitor AI alignment research
                self.monitor_alignment_research()
                
                # 3. Bridge to mental models (Consciousness)
                self.connect_intellect()
                
                # 4. Monitor regulatory landscape
                self.monitor_regulatory_landscape()
                
                # 5. Constitutional Enforcement Audit (Phase 21)
                if ConstitutionGuard:
                    guard = ConstitutionGuard(self.db_path)
                    violations = guard.run_audit()
                    if violations:
                        self._log_event("WARNING", f"Constitutional audit: {len(violations)} violations found")
                
                time.sleep(300)  # 5 minute cycle
                
            except Exception as e:
                logging.error(f"[CIVICS] Cycle interrupted: {e}")
                time.sleep(60)


def run_civics_loop(db_path=None):
    """Entry point for main.py"""
    agent = AgentCivics(db_path)
    agent.run_cycle()


if __name__ == "__main__":
    agent = AgentCivics()
    agent.run_cycle()
