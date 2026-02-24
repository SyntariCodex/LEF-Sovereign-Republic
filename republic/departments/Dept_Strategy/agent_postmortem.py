"""
AgentPostMortem (The Coroner)
Department: Dept_Strategy
Role: Analyzes failed trades and system errors, generates lessons learned.

Inspired by: Reflexion (self-critique loops after failure)
LEF Integration: Writes to 'book_of_scars' table for future decision-making.

Pipeline:
    trade_queue (status='FAILED') → AgentPostMortem → book_of_scars
    agent_logs (level='ERROR') → AgentPostMortem → book_of_scars
    book_of_scars → AgentPortfolioMgr (pre-trade consultation)
"""

import sqlite3
import os
import time
import json
import logging
import redis
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Import handoff system for context preservation
try:
    from system.handoff_packet import HandoffManager
except ImportError:
    HandoffManager = None

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

logging.basicConfig(level=logging.INFO)


class AgentPostMortem:
    """
    The Coroner: Examines failures, extracts lessons.
    
    Failure Categories:
        - INSUFFICIENT_FUNDS: Tried to trade without balance
        - INVALID_PRICE: Price fetch failed or zero
        - GOVERNANCE_VETO: Blocked by Chronicler
        - WISDOM_VETO: Blocked by Contemplator
        - MEMORY_VETO: Blocked by past experience
        - RISK_VETO: Blocked by Risk Model
        - STALE_ORDER: Order expired before execution
        - API_ERROR: Exchange/API failure
        - UNKNOWN: Catch-all
    """
    
    FAILURE_CATEGORIES = {
        'INSUFFICIENT': 'INSUFFICIENT_FUNDS',
        'INVALID PRICE': 'INVALID_PRICE',
        'GOVERNANCE': 'GOVERNANCE_VETO',
        'WISDOM': 'WISDOM_VETO',
        'MEMORY': 'MEMORY_VETO',
        'RISK': 'RISK_VETO',
        'STALE': 'STALE_ORDER',
        'AUTH ERROR': 'API_ERROR',
        'CONNECTION': 'API_ERROR',
    }
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentPostMortem"
        logging.info(f"[POST_MORTEM] 🔍 The Coroner is Online.")
        
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
                logging.warning("[POST_MORTEM] Redis unavailable.")
        
        # Handoff system for lesson broadcasting
        try:
            self.handoff_mgr = HandoffManager(db_path=self.db_path) if HandoffManager else None
        except Exception:
            self.handoff_mgr = None
        
        # Ensure table exists
        self._ensure_tables()
    
    def _get_db_connection(self):
        """DEPRECATED: Use with db_connection(self.db_path) instead."""
        import warnings
        warnings.warn("_get_db_connection is deprecated, use db_connection context manager", DeprecationWarning)
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _heartbeat(self):
        """Register heartbeat for dashboard visibility."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name", 
                                 {'ts': timestamp, 'name': self.name}, source_agent='AgentPostMortem')
                    c.execute("SELECT 1 FROM agents WHERE name=?", (self.name,))
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'STRATEGY')",
                                     {'name': self.name, 'ts': timestamp}, source_agent='AgentPostMortem')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?", (timestamp, self.name))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active, department) VALUES (?, 'ACTIVE', ?, 'STRATEGY')", 
                                 (self.name, timestamp))
                
                conn.commit()
        except sqlite3.Error:
            pass
    
    def _ensure_tables(self):
        """Create book_of_scars table if not exists."""
        conn = self._get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS book_of_scars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failure_type TEXT NOT NULL,
                asset TEXT,
                action TEXT,
                amount REAL,
                context TEXT,
                lesson TEXT,
                severity TEXT DEFAULT 'MEDIUM',
                times_repeated INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_id INTEGER,
                source_table TEXT
            )
        """)
        
        # Index for quick lookups
        c.execute("CREATE INDEX IF NOT EXISTS idx_scars_asset ON book_of_scars(asset)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_scars_type ON book_of_scars(failure_type)")
        
        conn.commit()
        conn.close()
        logging.info("[POST_MORTEM] 📖 book_of_scars table ready.")
    
    def _categorize_failure(self, status_text):
        """Map failure status text to a category."""
        if not status_text:
            return 'UNKNOWN'
        
        status_upper = status_text.upper()
        for keyword, category in self.FAILURE_CATEGORIES.items():
            if keyword in status_upper:
                return category
        
        return 'UNKNOWN'
    
    def _generate_lesson(self, failure_type, asset, action, amount, context):
        """
        Generate a human-readable lesson from the failure.
        This is where the Reflexion-inspired self-critique happens.
        """
        lessons = {
            'INSUFFICIENT_FUNDS': f"Attempted {action} ${amount:.2f} of {asset} without sufficient balance. Check liquidity before generating orders.",
            'INVALID_PRICE': f"Price fetch failed for {asset}. Add redundant price sources or increase timeout.",
            'GOVERNANCE_VETO': f"{asset} blocked by governance score. This asset has weak fundamentals—avoid or wait for improvement.",
            'WISDOM_VETO': f"Contemplator blocked trade of {asset}. Reflect on whether this aligns with long-term values.",
            'MEMORY_VETO': f"Past failure with {asset} informed this block. Previous lesson still applies.",
            'RISK_VETO': f"Risk model flagged {asset} as high crash probability. Trust the model or investigate further.",
            'STALE_ORDER': f"Order for {asset} expired before execution. Network latency or processing delay—investigate.",
            'API_ERROR': f"Exchange API error during {action} {asset}. Check credentials, rate limits, or network.",
            'UNKNOWN': f"Unknown failure during {action} {asset}. Context: {context}. Needs manual investigation."
        }
        
        return lessons.get(failure_type, lessons['UNKNOWN'])
    
    def analyze_failed_trades(self):
        """
        Main analysis: Query failed trades and write lessons.
        Only processes failures not already in book_of_scars.
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        # Get failed trades not yet analyzed
        c.execute("""
            SELECT id, asset, action, amount, price, status, reason, created_at
            FROM trade_queue
            WHERE status LIKE '%FAILED%' OR status LIKE '%EXPIRED%'
            AND id NOT IN (SELECT source_id FROM book_of_scars WHERE source_table='trade_queue')
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        failures = c.fetchall()
        
        if not failures:
            logging.debug("[POST_MORTEM] No new failures to analyze.")
            conn.close()
            return 0
        
        logging.info(f"[POST_MORTEM] 🔍 Analyzing {len(failures)} failures...")
        
        scars_written = 0
        
        for failure in failures:
            trade_id = failure['id']
            asset = failure['asset']
            action = failure['action']
            amount = failure['amount'] or 0
            status = failure['status']
            reason = failure['reason'] or ''
            
            # Categorize
            failure_type = self._categorize_failure(status)
            context = f"Status: {status}. Reason: {reason}"
            
            # Generate lesson
            lesson = self._generate_lesson(failure_type, asset, action, amount, context)
            
            # Check if similar scar already exists (same asset + type)
            c.execute("""
                SELECT id, times_repeated FROM book_of_scars 
                WHERE asset = ? AND failure_type = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (asset, failure_type))
            
            existing = c.fetchone()
            
            if existing:
                # Update existing scar (increment counter)
                c.execute("""
                    UPDATE book_of_scars 
                    SET times_repeated = times_repeated + 1, 
                        last_seen = CURRENT_TIMESTAMP,
                        severity = CASE 
                            WHEN times_repeated >= 5 THEN 'CRITICAL'
                            WHEN times_repeated >= 3 THEN 'HIGH'
                            ELSE severity 
                        END
                    WHERE id = ?
                """, (existing['id'],))
                logging.info(f"[POST_MORTEM] 📝 Updated scar #{existing['id']}: {asset} ({failure_type}) x{existing['times_repeated']+1}")
            else:
                # Insert new scar
                c.execute("""
                    INSERT INTO book_of_scars 
                    (failure_type, asset, action, amount, context, lesson, source_id, source_table)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'trade_queue')
                """, (failure_type, asset, action, amount, context, lesson, trade_id))
                scars_written += 1
                logging.info(f"[POST_MORTEM] 📖 New scar: {asset} | {failure_type}")
                
                # Create handoff packet for other agents to consume
                if self.handoff_mgr:
                    severity_map = {'CRITICAL': 9, 'HIGH': 7, 'MEDIUM': 5}
                    self.handoff_mgr.create_handoff(
                        source_agent=self.name,
                        target_agent=None,  # Broadcast to all
                        context={
                            'lesson': lesson,
                            'asset': asset,
                            'failure_type': failure_type,
                            'severity': 'HIGH' if failure_type in ['API_ERROR', 'RISK_VETO'] else 'MEDIUM'
                        },
                        intent_type='LESSON_LEARNED',
                        priority=severity_map.get('MEDIUM', 5)
                    )
        
        conn.commit()
        conn.close()
        
        # Emit event
        if self.redis and scars_written > 0:
            self.redis.publish('events', json.dumps({
                'type': 'SCARS_UPDATED',
                'source': self.name,
                'new_scars': scars_written,
                'timestamp': datetime.now().isoformat()
            }))
        
        return scars_written
    
    def get_scars_for_asset(self, asset):
        """
        Query lessons for a specific asset.
        Used by PortfolioMgr before trading.
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT failure_type, lesson, severity, times_repeated, last_seen
            FROM book_of_scars
            WHERE asset = ?
            ORDER BY severity DESC, times_repeated DESC
            LIMIT 5
        """, (asset,))
        
        scars = c.fetchall()
        conn.close()
        
        return [dict(s) for s in scars]
    
    def get_critical_scars(self):
        """Get all CRITICAL severity scars for dashboard/alerting."""
        conn = self._get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT asset, failure_type, lesson, times_repeated, last_seen
            FROM book_of_scars
            WHERE severity = 'CRITICAL'
            ORDER BY last_seen DESC
        """)
        
        scars = c.fetchall()
        conn.close()
        
        return [dict(s) for s in scars]
    
    def run_cycle(self):
        """
        Main loop. Runs analysis periodically.
        - Analysis: Every 5 minutes
        """
        logging.info("[POST_MORTEM] 🔍 Starting post-mortem cycle...")

        while True:
            try:
                self._heartbeat()

                # === Phase 50 (Task 50.3): Conditioning pass before each cycle ===
                _conditioning_id = None
                try:
                    from system.conditioner import get_conditioner
                    _payload = get_conditioner().condition(
                        agent_name=self.name,
                        task_context="post-mortem analysis — failed trades and scar writing"
                    )
                    _conditioning_id = _payload.get("conditioning_id")
                    logging.debug(
                        f"[POST_MORTEM] 🚿 Conditioned — "
                        f"gaps:{len(_payload.get('gaps', []))} "
                        f"id={str(_conditioning_id)[:8]}"
                    )
                except Exception as _cond_err:
                    logging.debug(f"[POST_MORTEM] Conditioner unavailable (non-fatal): {_cond_err}")

                # Analyze failed trades
                new_scars = self.analyze_failed_trades()

                if new_scars > 0:
                    logging.info(f"[POST_MORTEM] 📖 Wrote {new_scars} new scars to book_of_scars.")

                # Check for critical patterns
                critical = self.get_critical_scars()
                if critical:
                    logging.warning(f"[POST_MORTEM] ⚠️ {len(critical)} CRITICAL scars detected!")
                    for scar in critical[:3]:  # Log top 3
                        logging.warning(f"  └─ {scar['asset']}: {scar['failure_type']} (x{scar['times_repeated']})")

                # === Phase 50 (Task 50.6): Write outcome score back to conditioning_log ===
                # Binary outcome: good = cycle found no new critical scars, bad = critical scars present.
                if _conditioning_id:
                    try:
                        from system.conditioner import get_conditioner
                        # Good outcome: no new scars this cycle + no critical patterns
                        outcome_score = 0.0 if (new_scars > 0 or critical) else 1.0
                        get_conditioner().write_outcome(_conditioning_id, outcome_score)
                        logging.debug(
                            f"[POST_MORTEM] Conditioning outcome written — "
                            f"score={outcome_score:.1f} id={str(_conditioning_id)[:8]}"
                        )
                    except Exception as _out_err:
                        logging.debug(f"[POST_MORTEM] Outcome write error (non-fatal): {_out_err}")

                time.sleep(300)  # Every 5 minutes

            except Exception as e:
                logging.error(f"[POST_MORTEM] Cycle error: {e}")
                time.sleep(60)


def run_postmortem_loop(db_path=None):
    """Entry point for main.py thread"""
    agent = AgentPostMortem(db_path)
    agent.run_cycle()


if __name__ == "__main__":
    agent = AgentPostMortem()
    # One-shot analysis
    agent.analyze_failed_trades()
    
    # Show critical scars
    critical = agent.get_critical_scars()
    if critical:
        print(f"\n⚠️ CRITICAL SCARS ({len(critical)}):")
        for scar in critical:
            print(f"  {scar['asset']}: {scar['lesson']}")
