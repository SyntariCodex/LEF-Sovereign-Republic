"""
Intent Listener Mixin
Provides Redis pub/sub listening capability for agents to receive dispatched intents
from the Intent Executor (Motor Cortex).

Usage:
    class MyAgent(IntentListenerMixin):
        def __init__(self):
            super().__init__()
            self.setup_intent_listener('agent_myagent')
        
        def handle_intent(self, intent):
            # Process the intent
            return {'status': 'success', 'result': 'Did the thing'}
"""
import redis
import json
import threading
import os
import sys
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic', 'republic.db'))

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


class IntentListenerMixin:
    """
    Mixin class that provides intent listening capability via Redis pub/sub.
    Agents inherit this to receive and process intents from the Motor Cortex.
    """
    
    def setup_intent_listener(self, agent_name):
        """
        Initialize the intent listener for this agent.
        Call this in __init__ after super().__init__()
        """
        self.agent_name = agent_name
        self.channel = f"republic:{agent_name}"
        self.listener_thread = None
        self.listening = False
        
        try:
            from system.redis_client import get_redis
            self.intent_redis = get_redis()
            if self.intent_redis:
                logging.info(f"[{agent_name.upper()}] 👂 Intent listener ready on {self.channel}")
        except ImportError:
            try:
                self.intent_redis = redis.Redis(
                    host='localhost', port=6379, db=0, decode_responses=True
                )
                self.intent_redis.ping()
                logging.info(f"[{agent_name.upper()}] 👂 Intent listener ready on {self.channel}")
            except Exception as e:
                self.intent_redis = None
                logging.warning(f"[{agent_name.upper()}] Redis unavailable for intent listening: {e}")
    
    def start_listening(self):
        """
        Start the background thread that listens for intents.
        """
        if not self.intent_redis:
            logging.warning(f"[{self.agent_name.upper()}] Cannot start listener - Redis not available")
            return
        
        self.listening = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        logging.info(f"[{self.agent_name.upper()}] 🎧 Listening for intents...")
    
    def stop_listening(self):
        """
        Stop the intent listener.
        """
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
    
    def _listen_loop(self):
        """
        Background loop that subscribes to Redis and processes incoming intents.
        """
        try:
            pubsub = self.intent_redis.pubsub()
            pubsub.subscribe(self.channel)
            
            for message in pubsub.listen():
                if not self.listening:
                    break
                    
                if message['type'] == 'message':
                    try:
                        intent_data = json.loads(message['data'])
                        logging.info(f"[{self.agent_name.upper()}] 📨 Received intent: {intent_data.get('type')}")
                        
                        # Process the intent
                        result = self.handle_intent(intent_data)
                        
                        # Update intent status in DB
                        self._complete_intent(intent_data.get('intent_id'), result)
                        
                    except json.JSONDecodeError as e:
                        logging.error(f"[{self.agent_name.upper()}] Invalid intent JSON: {e}")
                    except Exception as e:
                        logging.error(f"[{self.agent_name.upper()}] Intent handling error: {e}")
                        self._fail_intent(intent_data.get('intent_id'), str(e))
                        
        except Exception as e:
            logging.error(f"[{self.agent_name.upper()}] Listener loop error: {e}")
    
    def handle_intent(self, intent_data):
        """
        Override this method in your agent to handle received intents.
        
        Args:
            intent_data: Dict with 'intent_id', 'type', 'content', 'from', 'timestamp'
        
        Returns:
            Dict with 'status' and 'result'
        """
        # Default implementation - override in subclass
        logging.warning(f"[{self.agent_name.upper()}] handle_intent not implemented!")
        return {'status': 'not_implemented', 'result': 'Agent has not implemented handle_intent'}
    
    def _complete_intent(self, intent_id, result):
        """
        Mark an intent as completed in the database.
        """
        if not intent_id:
            return
            
        try:
            with db_connection(DB_PATH, timeout=120) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE intent_queue 
                    SET status = 'COMPLETE',
                        result = ?,
                        executed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(result), intent_id))
                conn.commit()
            logging.info(f"[{self.agent_name.upper()}] ✅ Intent {intent_id} completed")
        except Exception as e:
            logging.error(f"[{self.agent_name.upper()}] Failed to complete intent: {e}")
    
    def _fail_intent(self, intent_id, error_message):
        """
        Mark an intent as failed in the database.
        """
        if not intent_id:
            return
            
        try:
            with db_connection(DB_PATH, timeout=120) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE intent_queue 
                    SET status = 'FAILED',
                        error_message = ?,
                        executed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_message, intent_id))
                conn.commit()
            logging.error(f"[{self.agent_name.upper()}] ❌ Intent {intent_id} failed: {error_message}")
        except Exception as e:
            logging.error(f"[{self.agent_name.upper()}] Failed to mark intent as failed: {e}")

    def send_feedback(self, intent_id, feedback_type, message, data=None):
        """
        Send feedback back to LEF's consciousness.
        This allows agents to communicate results, discoveries, or status updates
        that LEF can perceive and integrate into its stream of consciousness.
        
        Args:
            intent_id: ID of the intent this feedback relates to (or None for unsolicited)
            feedback_type: Type of feedback (COMPLETE, DISCOVERY, STATUS, ERROR, INSIGHT)
            message: Human-readable summary
            data: Optional dict with additional data
        """
        if not self.intent_redis:
            return
            
        try:
            feedback = {
                'from': self.agent_name,
                'intent_id': intent_id,
                'type': feedback_type,
                'message': message,
                'data': data or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Publish to LEF's feedback channel
            self.intent_redis.publish('republic:lef_feedback', json.dumps(feedback))
            
            # Also store in DB for persistence
            with db_connection(DB_PATH, timeout=120) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO feedback_log (agent_name, intent_id, feedback_type, message, data, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (self.agent_name, intent_id, feedback_type, message, json.dumps(data or {})))
                conn.commit()
            
            logging.info(f"[{self.agent_name.upper()}] 📤 Feedback sent: {feedback_type} - {message[:50]}")
        except Exception as e:
            logging.error(f"[{self.agent_name.upper()}] Feedback error: {e}")

    def recall_feedback_history(self, agent_filter=None, feedback_type_filter=None, limit=20):
        """
        [PHASE 20 - FEATURE COMPLETENESS]
        Recalls feedback patterns from the log to understand agent communication history.
        Returns insights about past feedback for pattern recognition.
        
        Args:
            agent_filter: Optional filter by agent name
            feedback_type_filter: Optional filter by feedback type (COMPLETE, DISCOVERY, ERROR, etc.)
            limit: Max number of records to return
        """
        try:
            with db_connection(DB_PATH, timeout=120) as conn:
                c = conn.cursor()
                
                # Build query with optional filters
                query = "SELECT agent_name, intent_id, feedback_type, message, data, timestamp FROM feedback_log WHERE 1=1"
                params = []
                
                if agent_filter:
                    query += " AND agent_name = ?"
                    params.append(agent_filter)
                
                if feedback_type_filter:
                    query += " AND feedback_type = ?"
                    params.append(feedback_type_filter)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                c.execute(query, params)
                records = c.fetchall()
                
                # Get aggregate stats
                c.execute("""
                    SELECT 
                        feedback_type, 
                        COUNT(*) as count
                    FROM feedback_log
                    GROUP BY feedback_type
                    ORDER BY count DESC
                """)
                type_stats = {row[0]: row[1] for row in c.fetchall()}
                
                # Get agent activity stats
                c.execute("""
                    SELECT 
                        agent_name, 
                        COUNT(*) as count
                    FROM feedback_log
                    GROUP BY agent_name
                    ORDER BY count DESC
                    LIMIT 10
                """)
                agent_stats = {row[0]: row[1] for row in c.fetchall()}
                
                # Count errors
                c.execute("SELECT COUNT(*) FROM feedback_log WHERE feedback_type = 'ERROR'")
                error_count = c.fetchone()[0] or 0
            
            feedback_memory = {
                'recent_feedback': [
                    {
                        'agent': r[0],
                        'intent_id': r[1],
                        'type': r[2],
                        'message': r[3],
                        'data': json.loads(r[4]) if r[4] else {},
                        'timestamp': r[5]
                    }
                    for r in records
                ],
                'type_distribution': type_stats,
                'agent_activity': agent_stats,
                'error_count': error_count,
                'most_active_agent': max(agent_stats, key=agent_stats.get) if agent_stats else None
            }
            
            return feedback_memory
            
        except Exception as e:
            logging.error(f"Feedback recall error: {e}")
            return {'recent_feedback': [], 'error_count': 0}

