"""
ActionLogger (The Training Recorder)
LAM-style action logging for LEF self-improvement.

Captures structured training data: intent → action → outcome
Inspired by Rabbit R1's Large Action Model training format.
Uses connection pool to prevent database locking.

Usage:
    from republic.system.action_logger import get_action_logger
    
    logger = get_action_logger()
    with logger.log_action("AgentPortfolioMgr", "Rebalance portfolio", "TRADE") as record:
        # Do the work
        record["action_details"] = {"sold": "BTC", "bought": "ETH"}
        record["outcome_details"] = "Rebalanced 5% allocation"
"""

import json
import time
import logging
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Optional, Any


class ActionLogger:
    """
    LAM-style action logging for self-improvement training.
    
    Logs structured triplets:
    - Intent: What the agent wanted to do
    - Action: What it actually did
    - Outcome: SUCCESS/FAILURE/PARTIAL and details
    
    This data can later be used for:
    - Fine-tuning decision models
    - Pattern recognition (what works, what doesn't)
    - Self-critique and improvement loops
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'republic.db')
        self.db_path = db_path
        self._pool = None
        self._ensure_table()
    
    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool

    def _get_connection(self):
        """Get a connection from the pool or fallback to direct connect."""
        pool = self._get_pool()
        if pool:
            conn = pool.get(timeout=30.0)
            conn.row_factory = __import__('sqlite3').Row
            return conn, pool
        else:
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            return conn, None

    def _release_connection(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()
    
    def _ensure_table(self):
        """Create action_training_log table if not exists."""
        conn, pool = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_training_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    agent_name TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    context TEXT,
                    action_type TEXT,
                    action_details TEXT,
                    outcome TEXT DEFAULT 'PENDING',
                    outcome_details TEXT,
                    reward_signal REAL DEFAULT 0,
                    duration_ms INTEGER,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_agent 
                ON action_training_log(agent_name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_type 
                ON action_training_log(action_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_outcome 
                ON action_training_log(outcome)
            """)
            conn.commit()
            logging.debug("[ACTION_LOG] 📝 action_training_log table ready.")
        finally:
            self._release_connection(conn, pool)
    
    @contextmanager
    def log_action(
        self,
        agent_name: str,
        intent: str,
        action_type: str,
        context: Optional[Dict] = None
    ):
        """
        Context manager to log an action with automatic timing.
        
        Args:
            agent_name: Name of the agent performing the action
            intent: What the agent intends to do (human-readable)
            action_type: Category (TRADE, ANALYSIS, GOVERNANCE, RESEARCH, etc.)
            context: Optional dict of contextual information
            
        Yields:
            record: Mutable dict to add action_details, outcome_details, etc.
            
        Example:
            with logger.log_action("AgentPortfolioMgr", "Buy BTC dip", "TRADE") as rec:
                result = execute_trade(...)
                rec["action_details"] = {"asset": "BTC", "amount": 0.1}
                rec["outcome_details"] = f"Bought at ${result.price}"
        """
        start_time = time.time()
        
        record = {
            "agent_name": agent_name,
            "intent": intent,
            "action_type": action_type,
            "context": context,
            "action_details": None,
            "outcome": "PENDING",
            "outcome_details": None,
            "reward_signal": 0,
            "metadata": None
        }
        
        try:
            yield record
            # If we get here without exception, mark as success
            if record["outcome"] == "PENDING":
                record["outcome"] = "SUCCESS"
                record["reward_signal"] = 1.0
        except Exception as e:
            record["outcome"] = "FAILURE"
            record["outcome_details"] = str(e)
            record["reward_signal"] = -1.0
            raise  # Re-raise the exception
        finally:
            # Calculate duration and save
            record["duration_ms"] = int((time.time() - start_time) * 1000)
            self._save_record(record)
    
    def _save_record(self, record: Dict):
        """Persist action record to database."""
        conn, pool = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO action_training_log 
                (agent_name, intent, context, action_type, action_details,
                 outcome, outcome_details, reward_signal, duration_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["agent_name"],
                record["intent"],
                json.dumps(record["context"]) if record["context"] else None,
                record["action_type"],
                json.dumps(record["action_details"]) if record["action_details"] else None,
                record["outcome"],
                record["outcome_details"],
                record["reward_signal"],
                record["duration_ms"],
                json.dumps(record["metadata"]) if record["metadata"] else None
            ))
            conn.commit()
            logging.debug(f"[ACTION_LOG] 📝 Logged: {record['agent_name']} - {record['intent'][:30]}... → {record['outcome']}")
        except Exception as e:
            logging.error(f"[ACTION_LOG] Failed to save record: {e}")
        finally:
            self._release_connection(conn, pool)
    
    def log_simple(
        self,
        agent_name: str,
        intent: str,
        action_type: str,
        outcome: str,
        action_details: Optional[Dict] = None,
        outcome_details: Optional[str] = None,
        context: Optional[Dict] = None,
        reward_signal: float = 0
    ):
        """
        Simple one-shot action logging without context manager.
        
        Use when you don't need timing or the action is already complete.
        """
        record = {
            "agent_name": agent_name,
            "intent": intent,
            "action_type": action_type,
            "context": context,
            "action_details": action_details,
            "outcome": outcome,
            "outcome_details": outcome_details,
            "reward_signal": reward_signal,
            "duration_ms": 0,
            "metadata": None
        }
        self._save_record(record)
    
    def get_training_data(
        self,
        limit: int = 1000,
        agent_name: Optional[str] = None,
        action_type: Optional[str] = None,
        outcome: Optional[str] = None
    ) -> list:
        """
        Export training data for model fine-tuning.
        
        Returns list of dicts in training-ready format.
        """
        conn, pool = self._get_connection()
        try:
            query = """
                SELECT * FROM action_training_log
                WHERE 1=1
            """
            params = []
            
            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            if outcome:
                query += " AND outcome = ?"
                params.append(outcome)
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "timestamp": row["timestamp"],
                    "agent": row["agent_name"],
                    "intent": row["intent"],
                    "context": json.loads(row["context"]) if row["context"] else None,
                    "action_type": row["action_type"],
                    "action_details": json.loads(row["action_details"]) if row["action_details"] else None,
                    "outcome": row["outcome"],
                    "outcome_details": row["outcome_details"],
                    "reward": row["reward_signal"],
                    "duration_ms": row["duration_ms"]
                })
            
            return results
        finally:
            self._release_connection(conn, pool)
    
    def get_stats(self) -> Dict:
        """Get action logging statistics."""
        conn, pool = self._get_connection()
        try:
            stats = {}
            
            # Total actions
            cursor = conn.execute("SELECT COUNT(*) FROM action_training_log")
            stats["total_actions"] = cursor.fetchone()[0]
            
            # By outcome
            cursor = conn.execute("""
                SELECT outcome, COUNT(*) as count 
                FROM action_training_log 
                GROUP BY outcome
            """)
            stats["by_outcome"] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # By agent
            cursor = conn.execute("""
                SELECT agent_name, COUNT(*) as count 
                FROM action_training_log 
                GROUP BY agent_name
                ORDER BY count DESC
                LIMIT 10
            """)
            stats["by_agent"] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Success rate
            total = stats["total_actions"]
            successes = stats["by_outcome"].get("SUCCESS", 0)
            stats["success_rate"] = round(successes / total * 100, 1) if total > 0 else 0
            
            return stats
        finally:
            self._release_connection(conn, pool)


# Singleton instance
_logger = None

def get_action_logger(db_path: str = None) -> ActionLogger:
    """Get or create the singleton ActionLogger."""
    global _logger
    if _logger is None:
        _logger = ActionLogger(db_path)
    return _logger


# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("ACTION LOGGER - Self Test")
    print("=" * 60)
    
    logger = get_action_logger()
    
    # Test context manager
    print("\nTesting context manager logging...")
    with logger.log_action("TestAgent", "Test the logging system", "TEST") as record:
        record["action_details"] = {"test_key": "test_value"}
        record["outcome_details"] = "Self-test completed"
        time.sleep(0.1)  # Simulate work
    
    # Test simple logging
    print("Testing simple logging...")
    logger.log_simple(
        "TestAgent",
        "Another test action",
        "TEST",
        "SUCCESS",
        action_details={"foo": "bar"},
        outcome_details="Simple test passed"
    )
    
    # Show stats
    stats = logger.get_stats()
    print(f"\nStats: {stats}")
    
    # Show recent data
    data = logger.get_training_data(limit=5)
    print(f"\nRecent actions ({len(data)}):")
    for d in data:
        print(f"  [{d['outcome']}] {d['agent']}: {d['intent'][:40]}...")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")

