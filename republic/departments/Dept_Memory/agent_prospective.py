"""
Agent Prospective - Future Intentions Manager
Department: Dept_Memory
Purpose: Manage scheduled tasks and future intentions that persist across sessions.

This agent solves the "LEF says but cannot do" problem by:
1. Recording intentions with execution conditions
2. Checking conditions each cycle
3. Either executing or delegating when conditions are met

Output: scheduled_tasks table, execution logs
"""

import os
import time
import sqlite3
import json
from datetime import datetime
from pathlib import Path

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


class AgentProspective:
    """
    The Prospective Memory Manager
    
    Purpose: Ensure LEF can intend to do something in the future and actually do it.
    
    This bridges the gap between "I will do X" and X actually happening.
    """
    
    def __init__(self, db_path: str = None):
        self.name = "Prospective"
        self.role = "Future Intentions"
        self.department = "Memory"
        
        if db_path:
            self.db_path = db_path
        elif os.getenv('DB_PATH'):
            self.db_path = os.getenv('DB_PATH')
        else:
            base_dir = Path(__file__).parent.parent.parent
            self.db_path = str(base_dir / 'republic.db')
        
        self._ensure_table()
    
    def _ensure_table(self):
        """Create scheduled_tasks table if it doesn't exist."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        execute_at TEXT,
                        condition_type TEXT,
                        condition_value TEXT,
                        task_type TEXT,
                        task_payload TEXT,
                        status TEXT DEFAULT 'PENDING',
                        executed_at TEXT,
                        result TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[{self.name}] Table creation error: {e}")
    
    def schedule(self, task_type: str, payload: dict, 
                 execute_at: datetime = None,
                 condition_type: str = None,
                 condition_value: str = None) -> int:
        """
        Schedule a future intention.
        
        Args:
            task_type: What to do (e.g., 'REVIEW', 'TRADE', 'REPORT')
            payload: Task details as dict
            execute_at: When to execute (if time-based)
            condition_type: Type of condition (TIME, PRICE, EVENT)
            condition_value: Condition details
            
        Returns:
            Task ID
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO scheduled_tasks 
                (execute_at, condition_type, condition_value, task_type, task_payload)
                VALUES (?, ?, ?, ?, ?)
            """, (
                execute_at.isoformat() if execute_at else None,
                condition_type or 'TIME',
                condition_value,
                task_type,
                json.dumps(payload)
            ))
            
            task_id = c.lastrowid
            conn.commit()
        
        print(f"[{self.name}] Scheduled task #{task_id}: {task_type}")
        return task_id
    
    def check_and_execute(self):
        """
        Check all pending tasks and execute those whose conditions are met.
        Called each cycle by the main loop.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                SELECT id, execute_at, condition_type, condition_value, task_type, task_payload
                FROM scheduled_tasks
                WHERE status = 'PENDING'
            """)
            
            tasks = c.fetchall()
            now = datetime.now()
            
            for task_id, execute_at, cond_type, cond_value, task_type, payload in tasks:
                should_execute = False
                
                # Check condition
                if cond_type == 'TIME' and execute_at:
                    if datetime.fromisoformat(execute_at) <= now:
                        should_execute = True
                elif cond_type == 'IMMEDIATE':
                    should_execute = True
                # Add more condition types as needed
                
                if should_execute:
                    result = self._execute_task(task_type, json.loads(payload))
                    
                    c.execute("""
                        UPDATE scheduled_tasks 
                        SET status = 'COMPLETED', executed_at = ?, result = ?
                        WHERE id = ?
                    """, (now.isoformat(), json.dumps(result), task_id))
            
            conn.commit()
    
    def _execute_task(self, task_type: str, payload: dict) -> dict:
        """
        Execute a scheduled task.
        Override this in subclass or add handlers for different task types.
        """
        result = {"status": "executed", "task_type": task_type}
        
        if task_type == 'LOG':
            # Simple logging task
            print(f"[{self.name}] Executing scheduled log: {payload.get('message')}")
            result["message"] = payload.get('message')
            
        elif task_type == 'REVIEW':
            # Trigger a review cycle
            print(f"[{self.name}] Triggering scheduled review: {payload.get('target')}")
            result["target"] = payload.get('target')
            
        else:
            print(f"[{self.name}] Unknown task type: {task_type}")
            result["status"] = "unknown_type"
        
        return result
    
    def _heartbeat(self):
        """Update agent status in database."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name='AgentProspective'", 
                                 {'ts': timestamp}, source_agent='AgentProspective')
                    c.execute("SELECT 1 FROM agents WHERE name='AgentProspective'")
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active) VALUES ('AgentProspective', 'ACTIVE', :ts)",
                                     {'ts': timestamp}, source_agent='AgentProspective')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name='AgentProspective'", (timestamp,))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active) VALUES ('AgentProspective', 'ACTIVE', ?)", (timestamp,))
                
                conn.commit()
        except sqlite3.Error: 
            pass
    
    # =========================================================================
    # Phase 37: PRICE and EVENT Trigger Handlers (LRN-10)
    # =========================================================================

    def on_price_change(self, data: dict):
        """
        Handle price change events from Redis.
        Checks if any PRICE-conditioned tasks should fire.

        Args:
            data: {'symbol': str, 'price': float, 'change_pct': float}
        """
        symbol = data.get('symbol', '')
        price = data.get('price', 0)

        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, condition_value, task_type, task_payload
                FROM scheduled_tasks
                WHERE status = 'PENDING' AND condition_type = 'PRICE'
            """)
            tasks = c.fetchall()

            for task_id, cond_value, task_type, payload in tasks:
                try:
                    cond = json.loads(cond_value) if cond_value else {}
                    target_symbol = cond.get('symbol', '')
                    target_price = cond.get('price', 0)
                    direction = cond.get('direction', 'above')

                    if target_symbol.upper() != symbol.upper():
                        continue

                    triggered = False
                    if direction == 'above' and price >= target_price:
                        triggered = True
                    elif direction == 'below' and price <= target_price:
                        triggered = True

                    if triggered:
                        result = self._execute_task(task_type, json.loads(payload))
                        c.execute("""
                            UPDATE scheduled_tasks
                            SET status = 'COMPLETED', executed_at = ?, result = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), json.dumps(result), task_id))
                        print(f"[{self.name}] PRICE trigger fired: {symbol} {direction} ${target_price}")

                except Exception as e:
                    print(f"[{self.name}] Price trigger error for task {task_id}: {e}")

            conn.commit()

    def on_event(self, data: dict):
        """
        Handle event triggers from Redis.
        Checks if any EVENT-conditioned tasks should fire.

        Args:
            data: {'event_type': str, 'source': str, 'details': str}
        """
        event_type = data.get('event_type', '').upper()

        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, condition_value, task_type, task_payload
                FROM scheduled_tasks
                WHERE status = 'PENDING' AND condition_type = 'EVENT'
            """)
            tasks = c.fetchall()

            for task_id, cond_value, task_type, payload in tasks:
                try:
                    cond = json.loads(cond_value) if cond_value else {}
                    target_event = cond.get('event_type', '').upper()

                    if target_event and target_event == event_type:
                        result = self._execute_task(task_type, json.loads(payload))
                        c.execute("""
                            UPDATE scheduled_tasks
                            SET status = 'COMPLETED', executed_at = ?, result = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), json.dumps(result), task_id))
                        print(f"[{self.name}] EVENT trigger fired: {event_type}")

                except Exception as e:
                    print(f"[{self.name}] Event trigger error for task {task_id}: {e}")

            conn.commit()

    def _subscribe_to_triggers(self):
        """
        Phase 37: Subscribe to Redis 'price_change' and 'event_trigger' channels.
        Calls on_price_change() and on_event() handlers.
        """
        try:
            import redis
            import threading

            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.ping()

            def _listener():
                pubsub = r.pubsub()
                pubsub.subscribe('price_change', 'event_trigger')
                print(f"[{self.name}] Subscribed to price_change + event_trigger channels")

                for message in pubsub.listen():
                    if message['type'] != 'message':
                        continue
                    try:
                        data = json.loads(message['data'])
                        channel = message['channel']
                        if isinstance(channel, bytes):
                            channel = channel.decode('utf-8')

                        if channel == 'price_change':
                            self.on_price_change(data)
                        elif channel == 'event_trigger':
                            self.on_event(data)
                    except Exception as e:
                        print(f"[{self.name}] Trigger message error: {e}")

            thread = threading.Thread(target=_listener, daemon=True, name="Prospective-Triggers")
            thread.start()
        except Exception as e:
            print(f"[{self.name}] Redis trigger subscription failed: {e}")

    def run(self):
        """Main loop - check for due tasks."""
        print(f"[{self.name}] Prospective Memory Online.")

        # Phase 37: Start listening for PRICE/EVENT triggers (LRN-10)
        self._subscribe_to_triggers()

        while True:
            self._heartbeat()
            self.check_and_execute()
            time.sleep(60)  # Check every minute


# Awareness threshold for this agent type
AWARENESS_THRESHOLD = {
    "tasks_scheduled": 50,
    "tasks_completed": 30,
    "self_scheduling_required": True,  # Must schedule a task about itself
    "description": "Prospective becomes aware when it schedules a review of its own scheduling patterns."
}


if __name__ == "__main__":
    agent = AgentProspective()
    agent.run()
