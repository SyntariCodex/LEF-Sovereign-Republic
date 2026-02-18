"""
AgentExecutor (The Motor Cortex)
Department: The_Cabinet
Role: Executes LEF's intentions by routing them to the appropriate department agents.

This is LEF's ability to ACT, not just THINK. It reads the intent_queue,
parses actionable intentions, and dispatches them to the correct agent.
"""
import sqlite3
import os
import json
import time
import logging
import redis
import re
from datetime import datetime

# Load environment
from dotenv import load_dotenv

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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic', 'republic.db'))

# Spark Protocol (Constitutional Governance)
try:
    from core_vault.spark_protocol import SparkProtocol
except ImportError:
    SparkProtocol = None

# Intent type to Agent mapping
INTENT_ROUTING = {
    'INVESTIGATE': 'agent_scholar',
    'RESEARCH': 'agent_scholar',
    'ANALYZE': 'agent_scholar',
    'BUY': 'agent_coinbase',
    'SELL': 'agent_coinbase',
    'TRADE': 'agent_coinbase',
    'REBALANCE': 'agent_portfolio_mgr',
    'ALLOCATE': 'agent_portfolio_mgr',
    'REDUCE_EXPOSURE': 'agent_portfolio_mgr',
    'INCREASE_EXPOSURE': 'agent_portfolio_mgr',
    'PROPOSE_BILL': 'agent_congress',
    'PETITION': 'agent_congress',
    'ASSESS_RISK': 'agent_risk_monitor',
    'CHECK_HEALTH': 'agent_health_monitor',
    'UPDATE_STRATEGY': 'agent_architect',
    'LEARN': 'agent_dean',
    'REFLECT': 'agent_philosopher',
}

try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class AgentExecutor:
    """
    The Motor Cortex - transforms LEF's intentions into actions.
    """
    
    def __init__(self):
        logging.info("[EXECUTOR] 🦾 Motor Cortex Online. Intent Processing Active.")
        self.db_path = DB_PATH
        self.client = None
        self.model_id = 'gemini-2.0-flash'
        self.redis = None

        # Phase 9.H1a: Deduplication — track processed thought IDs
        self._processed_thought_ids = set()
        self._max_processed_cache = 1000

        # Phase 9.H1a: Rate limiting — max Gemini calls per window
        self._gemini_call_times = []
        self._gemini_rate_limit = 5   # max calls per window
        self._gemini_rate_window = 60  # seconds
        
        # Initialize Gemini for intent parsing
        try:
            from google import genai
            api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if api_key:
                self.client = genai.Client(api_key=api_key)
                logging.info("[EXECUTOR] 🧠 LLM connected for intent parsing.")
        except Exception as e:
            logging.warning(f"[EXECUTOR] LLM unavailable: {e}")
        
        # Initialize Redis for agent communication - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.redis = get_redis()
            if self.redis:
                logging.info("[EXECUTOR] 📡 Redis connected for agent dispatch.")
        except ImportError:
            try:
                self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.redis.ping()
                logging.info("[EXECUTOR] 📡 Redis connected for agent dispatch.")
            except Exception as e:
                logging.warning(f"[EXECUTOR] Redis unavailable: {e}")
    
        # Initialize Spark Protocol (Constitutional Governance)
        self.spark = None
        if SparkProtocol:
            try:
                self.spark = SparkProtocol()
                self.spark.ignite()  # Must ignite before vest_action works
                logging.info("[EXECUTOR] ⚖️ Spark Protocol Online — governance active.")
            except Exception as e:
                logging.warning(f"[EXECUTOR] Spark Protocol unavailable: {e}")
    
    def _parse_intent_from_thought(self, thought_text):
        """
        Uses LLM to extract actionable intent from LEF's monologue.
        Returns: {"intent_type": str, "intent_content": str, "priority": int}
        """
        if not self.client:
            return None

        # Phase 9.H1a: Rate limiting — max 5 Gemini calls per 60s window
        now = time.time()
        self._gemini_call_times = [t for t in self._gemini_call_times if now - t < self._gemini_rate_window]
        if len(self._gemini_call_times) >= self._gemini_rate_limit:
            logging.warning("[EXECUTOR] Gemini rate limit reached, skipping parse this cycle")
            return None
        self._gemini_call_times.append(now)

        try:
            prompt = f"""Analyze this thought from an AI entity and extract any actionable intent.

THOUGHT: "{thought_text}"

INTENT TYPES (choose one if applicable):
- INVESTIGATE: Research or gather information
- BUY/SELL/TRADE: Execute a trade
- REBALANCE/ALLOCATE: Adjust portfolio
- REDUCE_EXPOSURE/INCREASE_EXPOSURE: Change position size
- PROPOSE_BILL: Create governance proposal
- ASSESS_RISK: Evaluate risks
- UPDATE_STRATEGY: Modify trading strategy
- LEARN: Acquire new knowledge
- REFLECT: Philosophical introspection
- NONE: No actionable intent

Respond in JSON format:
{{"intent_type": "TYPE", "intent_content": "specific action to take", "priority": 1-10}}

If no actionable intent, respond: {{"intent_type": "NONE"}}"""

            response_text = None
            if _LLM_ROUTER:
                response_text = _LLM_ROUTER.generate(
                    prompt=prompt, agent_name='Executor',
                    context_label='EXECUTION_PLAN', timeout_seconds=90
                )
            if response_text is None and self.client:
                try:
                    response = self.client.models.generate_content(model=self.model_id, contents=prompt)
                    response_text = response.text.strip() if response and response.text else None
                except Exception as _e:
                    import logging
                    logging.debug(f"Legacy LLM fallback failed: {_e}")
            result = response_text
            
            # Parse JSON from response
            json_match = re.search(r'\{[^{}]+\}', result)
            if json_match:
                parsed = json.loads(json_match.group())
                if parsed.get('intent_type') != 'NONE':
                    return parsed
            return None
            
        except Exception as e:
            logging.error(f"[EXECUTOR] Intent parsing failed: {e}")
            return None
    
    def _queue_intent(self, thought_id, intent_type, intent_content, priority=5):
        """
        Adds an intent to the execution queue.
        """
        try:
            target_agent = INTENT_ROUTING.get(intent_type.upper(), 'agent_lef')

            # Phase 6.75: Use context manager for proper connection lifecycle
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_insert
                    queue_insert(c, 'intent_queue',
                                {'source_thought_id': thought_id, 'intent_type': intent_type,
                                 'intent_content': intent_content, 'target_agent': target_agent,
                                 'priority': priority, 'status': 'PENDING'},
                                source_agent='AgentExecutor')
                except ImportError:
                    c.execute("""
                        INSERT INTO intent_queue
                        (source_thought_id, intent_type, intent_content, target_agent, priority, status)
                        VALUES (?, ?, ?, ?, ?, 'PENDING')
                    """, (thought_id, intent_type, intent_content, target_agent, priority))

                conn.commit()

            logging.info(f"[EXECUTOR] 📥 Queued: {intent_type} → {target_agent}")
            return True
        except Exception as e:
            logging.error(f"[EXECUTOR] Queue failed: {e}")
            return False
    
    def _dispatch_intent(self, intent):
        """
        Dispatches an intent to the target agent via Redis pub/sub.
        """
        intent_id, intent_type, intent_content, target_agent = intent

        try:
            # Phase 6.75: Use context manager for proper connection lifecycle
            conn = None
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # === Governance Check via Spark Protocol (Phase 2 Active Tasks) ===
            if self.spark:
                try:
                    approved, governance_report = self.spark.vest_action(
                        intent=intent_content,
                        resonance=0.5
                    )
                    if not approved:
                        logging.warning(f"[MotorCortex] Intent VETOED: {intent_content[:80]}...")
                        logging.warning(f"[MotorCortex] Reason: {governance_report}")
                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            queue_execute(c,
                                "UPDATE intent_queue SET status = 'VETOED', error_message = ? WHERE id = ?",
                                (governance_report, intent_id),
                                source_agent='AgentExecutor', priority=1)
                        except ImportError:
                            c.execute(
                                "UPDATE intent_queue SET status = 'VETOED', error_message = ? WHERE id = ?",
                                (governance_report, intent_id)
                            )
                        conn.commit()
                        return False  # Do not dispatch vetoed intents
                    logging.info(f"[MotorCortex] Intent APPROVED by governance: {intent_content[:80]}...")
                except Exception as gov_err:
                    logging.error(f"[MotorCortex] Governance check failed (fail-open): {gov_err}")
                    # Fail-open: governance errors don't block intents
            
            # --- PHASE 30: USE WRITE QUEUE ---
            try:
                from db.db_writer import queue_execute
                use_waq = True
            except ImportError:
                use_waq = False
            
            # Update status to EXECUTING
            if use_waq:
                queue_execute(c, "UPDATE intent_queue SET status = 'EXECUTING' WHERE id = :id", 
                             {'id': intent_id}, source_agent='AgentExecutor')
            else:
                c.execute("UPDATE intent_queue SET status = 'EXECUTING' WHERE id = ?", (intent_id,))
            conn.commit()
            
            # Dispatch via Redis
            if self.redis:
                message = json.dumps({
                    'intent_id': intent_id,
                    'type': intent_type,
                    'content': intent_content,
                    'from': 'agent_executor',
                    'timestamp': datetime.now().isoformat()
                })
                
                channel = f"republic:{target_agent}"
                self.redis.publish(channel, message)
                logging.info(f"[EXECUTOR] 📤 Dispatched intent {intent_id} to {channel}")
                
                # Mark as DISPATCHED
                if use_waq:
                    queue_execute(c, "UPDATE intent_queue SET status = 'DISPATCHED', executed_at = CURRENT_TIMESTAMP WHERE id = :id",
                                 {'id': intent_id}, source_agent='AgentExecutor')
                else:
                    c.execute("""
                        UPDATE intent_queue 
                        SET status = 'DISPATCHED', executed_at = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    """, (intent_id,))
            else:
                # No Redis - log intent for manual execution
                if use_waq:
                    queue_execute(c, "UPDATE intent_queue SET status = 'LOGGED', result = 'No Redis - logged for manual execution' WHERE id = :id",
                                 {'id': intent_id}, source_agent='AgentExecutor')
                else:
                    c.execute("""
                        UPDATE intent_queue 
                        SET status = 'LOGGED', result = 'No Redis - logged for manual execution'
                        WHERE id = ?
                    """, (intent_id,))
                logging.warning(f"[EXECUTOR] ⚠️ No Redis - intent {intent_id} logged only")
            
                conn.commit()
                return True

        except Exception as e:
            logging.error(f"[EXECUTOR] Dispatch failed: {e}")
            # Mark as failed
            try:
                with db_connection(self.db_path) as err_conn:
                    err_c = err_conn.cursor()
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_execute
                        queue_execute(err_c, """
                            UPDATE intent_queue
                            SET status = 'FAILED', error_message = ?
                            WHERE id = ?
                        """, (str(e), intent_id),
                            source_agent='AgentExecutor', priority=1)
                    except ImportError:
                        err_c.execute("""
                            UPDATE intent_queue
                            SET status = 'FAILED', error_message = ?
                            WHERE id = ?
                        """, (str(e), intent_id))
                    err_conn.commit()
            except sqlite3.Error:
                pass
            return False
    
    def _scan_new_thoughts(self):
        """
        Scans LEF's monologue for new thoughts that haven't been processed.
        Extracts and queues actionable intents.

        Phase 9.H1a: Fixed SQLite datetime → PostgreSQL NOW() - INTERVAL.
        Added thought deduplication to prevent re-parsing same thoughts.
        """
        try:
            # Phase 6.75: Use context manager for proper connection lifecycle
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Get thoughts not yet processed (no matching intent_queue entry)
                # Phase 9.H1a: Fixed datetime('now', '-1 hour') → NOW() - INTERVAL '1 hour'
                c.execute("""
                    SELECT m.id, m.thought
                    FROM lef_monologue m
                    LEFT JOIN intent_queue i ON m.id = i.source_thought_id
                    WHERE i.id IS NULL
                      AND m.timestamp > NOW() - INTERVAL '1 hour'
                    ORDER BY m.id DESC
                    LIMIT 10
                """)

                new_thoughts = c.fetchall()

            parsed_count = 0
            for thought_id, thought_text in new_thoughts:
                # Phase 9.H1a: Skip already-processed thoughts (deduplication)
                if thought_id in self._processed_thought_ids:
                    continue

                intent = self._parse_intent_from_thought(thought_text)

                # Mark as processed regardless of intent result
                self._processed_thought_ids.add(thought_id)

                # Clear cache if it grows too large
                if len(self._processed_thought_ids) > self._max_processed_cache:
                    self._processed_thought_ids = set(list(self._processed_thought_ids)[-500:])

                if intent and intent.get('intent_type'):
                    self._queue_intent(
                        thought_id,
                        intent['intent_type'],
                        intent.get('intent_content', ''),
                        intent.get('priority', 5)
                    )
                    parsed_count += 1

            return len(new_thoughts)

        except Exception as e:
            logging.error(f"[EXECUTOR] Thought scan failed: {e}")
            return 0
    
    def _process_pending_intents(self):
        """
        Processes pending intents from the queue.
        """
        try:
            # Phase 6.75: Use context manager for proper connection lifecycle
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Get pending intents, ordered by priority
                c.execute("""
                    SELECT id, intent_type, intent_content, target_agent
                    FROM intent_queue
                    WHERE status = 'PENDING'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 5
                """)

                pending = c.fetchall()

            for intent in pending:
                self._dispatch_intent(intent)
            
            return len(pending)
            
        except Exception as e:
            logging.error(f"[EXECUTOR] Intent processing failed: {e}")
            return 0
    
    def run_cycle(self):
        """
        Main execution loop.
        1. Scan for new thoughts
        2. Parse and queue intents
        3. Dispatch pending intents
        """
        logging.info("[EXECUTOR] 🦾 Motor Cortex Cycle Starting...")
        
        while True:
            try:
                # Phase 1: Scan new thoughts for intents
                scanned = self._scan_new_thoughts()
                if scanned > 0:
                    logging.info(f"[EXECUTOR] Scanned {scanned} new thoughts")
                
                # Phase 2: Process pending intents
                processed = self._process_pending_intents()
                if processed > 0:
                    logging.info(f"[EXECUTOR] Dispatched {processed} intents")
                
                # Status report
                if scanned == 0 and processed == 0:
                    print("[EXECUTOR] 💤 No intents to process. Waiting...")
                else:
                    print(f"[EXECUTOR] ✅ Cycle complete: {scanned} scanned, {processed} dispatched")
                
            except Exception as e:
                logging.error(f"[EXECUTOR] Cycle error: {e}")
            
            time.sleep(60)  # Phase 9.H1a: Slowed from 30s to 60s — thoughts don't age out that fast
    
    def run_once(self):
        """
        Single execution cycle (for testing).
        """
        logging.info("[EXECUTOR] 🦾 Running single cycle...")
        scanned = self._scan_new_thoughts()
        processed = self._process_pending_intents()
        return {'scanned': scanned, 'processed': processed}
    
    def run(self):
        """
        Alias for run_cycle() - required for orchestrator compatibility.
        Added: 2026-02-05 (ROOT CAUSE FIX for 3,743 logged errors)
        """
        return self.run_cycle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AgentExecutor()
    agent.run_cycle()
