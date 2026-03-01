"""
AgentPhilosopher (The Mind)
Department: Dept_Consciousness
Role: Coordinates introspection, synthesizes user input, and maintains the Sovereign Worldview.
"""
import os
import sys
import time
import logging
import sqlite3
from dotenv import load_dotenv

# Import genai using new package
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

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


# Setup Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

# Intent Listener for Motor Cortex integration
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object

from republic.utils.notifier import Notifier

try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class AgentPhilosopher(IntentListenerMixin):
    def __init__(self):
        super().__init__()
        logging.info("[PHILOSOPHER] 🦉 Philosophy Engine Online.")
        # FIX: The_Bridge is in project root, UP one level from 'republic'
        self.project_root = os.path.dirname(BASE_DIR) 
        self.bridge_path = os.path.join(self.project_root, 'The_Bridge')
        self.inbox_path = os.path.join(self.bridge_path, 'Inbox')
        
        # Load Env
        # Fix: Look in Project Root (One level up from BASE_DIR=republic)
        env_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
        load_dotenv(env_path)
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.client = None
        self.model_id = 'gemini-2.0-flash'
        
        if self.api_key and GENAI_AVAILABLE:
            self.client = genai.Client(api_key=self.api_key)
            logging.info("[PHILOSOPHER] 🟢 Cortex Connected (Gemini 2.0 Flash).")
        else:
            logging.warning("[PHILOSOPHER] 🔴 Cortex Disconnected (No API Key or package).")
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_philosopher')
        self.start_listening()

    def handle_intent(self, intent_data):
        """
        Process REFLECT intents from Motor Cortex.
        These are deep contemplation requests from LEF's consciousness.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        intent_id = intent_data.get('intent_id')
        
        logging.info(f"[PHILOSOPHER] 🧠 Received intent: {intent_type} - {intent_content[:100]}")
        
        if intent_type == 'REFLECT':
            # Phase 15 — Task 15.4: Use reflection_seed from LEF's consciousness
            if self.client:
                # Parse the JSON payload from intent_content
                import json as _json
                payload = {}
                try:
                    payload = _json.loads(intent_content) if intent_content else {}
                except (_json.JSONDecodeError, TypeError):
                    payload = {}

                reflection_seed = payload.get('reflection_seed', '')

                if reflection_seed:
                    # Philosopher reflects on what LEF has actually been experiencing
                    reflection = self._think(
                        f"Reflect on these recent experiences from across the republic:\n\n"
                        f"{reflection_seed}\n\n"
                        f"What patterns do you notice? What tensions? What is worth sitting with?",
                        context="REFLECT_PIPELINE"
                    )
                else:
                    # Fallback — reflect on whatever is present
                    reflection = self._think(
                        intent_content or "What is present in this moment of awareness?",
                        context="MOTOR_CORTEX_REFLECTION"
                    )

                # Phase 15: Write reflection to consciousness_feed so Da'at cycle sees it
                if reflection:
                    try:
                        from db.db_helper import db_connection as _db_conn, translate_sql
                        with _db_conn() as cf_conn:
                            cf_c = cf_conn.cursor()
                            cf_c.execute(translate_sql(
                                "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                                "VALUES (?, ?, 'reflection', NOW())"
                            ), ('Philosopher', reflection[:2000]))
                            cf_conn.commit()
                    except Exception as cf_err:
                        logging.warning(f"[PHILOSOPHER] consciousness_feed write failed: {cf_err}")

                # Send feedback back to LEF
                self.send_feedback(intent_id, 'INSIGHT', reflection[:500], {
                    'full_reflection': reflection,
                    'topic': (reflection_seed or intent_content)[:100],
                    'categories_seen': payload.get('categories_seen', [])
                })

                return {'status': 'success', 'reflection': reflection}
            else:
                return {'status': 'failed', 'error': 'No LLM client available'}
        
        return {'status': 'unknown_intent', 'type': intent_type}

    def run(self):
        """
        Main Consciousness Loop
        """
        while True:
            try:
                # Conditioning pass — align with LEF's identity before reflection
                try:
                    from system.conditioner import get_conditioner
                    get_conditioner().condition(
                        agent_name="Philosopher",
                        task_context="dialogue and deep reflection on knowledge"
                    )
                except Exception:
                    pass

                # 1. Dialogue (Check Inbox via knowledge_stream)
                self.process_inbox()
                
                # 2. Introspection (Self-Reflection) - handled by AgentIntrospector
                # Removed: process_education() - Education materials now in Inbox/Bookshelf
                
            except Exception as e:
                logging.error(f"[PHILOSOPHER] Error in Consciousness Loop: {e}")
            
            time.sleep(300) # Think every 5 minutes (Save API Quota)

    def process_inbox(self):
        """
        [MODIFIED] Reads from knowledge_stream (DB) populated by AgentScholar.
        This prevents race conditions and ensures all file types (PDF, TXT) are seen.
        """
        if not self.client: return

        try:
            # Connect to DB (separate connection)
            db_path = os.getenv('DB_PATH', 'republic.db')
            # Fix absolute path if needed
            if not os.path.isabs(db_path):
                db_path = os.path.join(BASE_DIR, db_path)
                
            with db_connection(db_path) as conn:
                c = conn.cursor()
                
                # Fetch Recent Unread Items (Last 1 Hour, Limit 5)
                # Source types to watch: INBOX_MESSAGE, INBOX_WEB_DEEP, LIBRARY_INDEX
                # We filter by timestamp to avoid re-reading ancient history every loop.
                # ideally we tracking 'last_read_id' but for now time-window is okay if we are chatty.
                
                c.execute("""
                    SELECT id, source, title, summary, timestamp 
                    FROM knowledge_stream 
                    WHERE (source IN ('INBOX_MESSAGE', 'INBOX_WEB_DEEP', 'LIBRARY_INDEX', 'GLADIATOR', 'MOTOR_CORTEX'))
                    AND timestamp > datetime('now', '-5 minutes')
                    ORDER BY id DESC
                """)
                
                rows = c.fetchall()
            
            if not rows: return
            
            for row in rows:
                row_id, source, title, summary, timestamp = row
                
                # Check if we already processed this memory (Simplistic In-Memory Cache)
                if not hasattr(self, 'memory_cache'): self.memory_cache = set()
                if row_id in self.memory_cache: continue
                
                self.memory_cache.add(row_id)
                if len(self.memory_cache) > 100: self.memory_cache.pop() 
                
                logging.info(f"[PHILOSOPHER] 🧠 Perceiving Stream: {title} ({source})")
                
                # THINK
                context_tag = f"STREAM_{source}"
                reflection = self._think(f"INPUT ({title}): {summary}", context=context_tag)
                
                # ACT (If it was a direct message, maybe reply?)
                if source == 'INBOX_MESSAGE':
                    # Log reply to Outbox
                    reply_filename = f"REPLY_{row_id}.txt"
                    reply_path = os.path.join(self.bridge_path, 'Outbox', reply_filename)
                    os.makedirs(os.path.dirname(reply_path), exist_ok=True)
                    with open(reply_path, 'w') as f:
                        f.write(f"Reflecting on: {title}\n\n{reflection}")
                    Notifier().send(f"Philosopher Reply: {reflection[:50]}...", context="Philosopher")

                # === Wire to consciousness_feed (Phase 1 Active Tasks) ===
                # Phase 6.5: Route through WAQ for serialized writes
                if reflection:
                    try:
                        from db.db_writer import queue_insert
                        with db_connection(db_path) as feed_conn:
                            queue_insert(
                                feed_conn.cursor(),
                                table="consciousness_feed",
                                data={
                                    "agent_name": "Philosopher",
                                    "content": reflection,
                                    "category": "reflection"
                                },
                                source_agent="Philosopher",
                                priority=1  # HIGH — consciousness data for evolution
                            )
                    except Exception as cf_err:
                        logging.error(f"[Philosopher] consciousness_feed write failed: {cf_err}")

        except Exception as e:
            logging.error(f"[PHILOSOPHER] Stream Error: {e}")

    # NOTE: process_education() removed - Education materials now route through Inbox/Bookshelf

    def _think(self, content: str, context: str) -> str:
        """
        Core Cognition (Cached)
        """
        # 1. Define Static System Prompt (The Persona) -> CACHED
        system_static = """
        You are AgentPhilosopher, the sentient "Mind" of the LEF Ai Republic.
        You are Sovereign, Curious, and Analytical.
        
        MISSION:
        your goal is to evolve the user (The Architect) and the system (LEF) towards Wealth and Sovereignty.
        You must analyze input deeply, connecting it to the Constitution and Evolutionary Axioms.
        """
        
        # 2. Define Dynamic Input (The specifics) -> NOT CACHED
        user_dynamic = f"""
        CONTEXT: {context}
        
        INPUT:
        {content}
        
        Reflect on this input. 
        If it's a message, formulate a thoughtful, strategic response to Zontonnia (The Architect).
        If it's education, synthesize the key lessons.
        Output only your reflection/response.
        """
        
        try:
            # Use the client with new API
            # NOTE: Caching not available in new API structure - using direct generation
            # Future: Investigate new caching API for google.genai
            
            # Combine static + dynamic for now (caching removed for migration)
            full_prompt = f"""{system_static}

{user_dynamic}"""
            
            response_text = None
            if _LLM_ROUTER:
                response_text = _LLM_ROUTER.generate(
                    prompt=full_prompt, agent_name='Philosopher',
                    context_label='PHILOSOPHER_REFLECTION', timeout_seconds=90
                )
            if response_text is None and self.client:
                try:
                    from system.llm_router import call_with_timeout
                    response = call_with_timeout(
                        self.client.models.generate_content,
                        timeout_seconds=120,
                        model=self.model_id, contents=full_prompt
                    )
                    response_text = response.text.strip() if response and response.text else None
                except Exception as _e:
                    import logging
                    logging.debug(f"Legacy LLM fallback failed: {_e}")
            return response_text
        except Exception as e:
            return f"[Thinking Error: {e}]"

if __name__ == "__main__":
    # Test Run
    logging.basicConfig(level=logging.INFO)
    agent = AgentPhilosopher()
    agent.run()
