"""
Token Budget System
Department: System
Role: Central rate-limiter to prevent agent starvation across LLM providers.

The Budget ensures that no single agent can monopolize tokens, 
starving others of their voice.
"""
import time
import os
import logging
import threading
from datetime import datetime, timedelta

class TokenBudget:
    """
    Manages token allocation and rate-limiting across all LLM providers.
    Uses SQLite for persistence so limits survive restarts.
    Uses connection pool to prevent database locking.
    """
    
    # Default limits per model tier (tokens and calls per hour)
    DEFAULT_LIMITS = {
        'gemini-1.5-pro': {
            'tokens_per_hour': 500_000,
            'calls_per_hour': 30,
            'priority': 2  # High cost, reserve for deep thinking
        },
        'gemini-1.5-flash': {
            'tokens_per_hour': 1_000_000,
            'calls_per_hour': 100,
            'priority': 0  # Default tier
        },
        'gemini-2.0-flash': {
            'tokens_per_hour': 1_000_000,
            'calls_per_hour': 100,
            'priority': 0  # Default tier
        },
        'gemini-2.0-flash-exp': {
            'tokens_per_hour': 1_000_000,
            'calls_per_hour': 100,
            'priority': 1  # Experimental, slightly rate-limit
        },
        'claude-sonnet': {
            'tokens_per_hour': 200_000,
            'calls_per_hour': 20,
            'priority': 3  # Highest cost, reserve for wisdom
        },
        'claude-haiku': {
            'tokens_per_hour': 500_000,
            'calls_per_hour': 50,
            'priority': 1  # Fast/cheap Claude
        }
    }
    
    def __init__(self, db_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = db_path or os.getenv('DB_PATH', os.path.join(base_dir, 'republic.db'))
        self._lock = threading.Lock()
        self._pool = None
        self._ensure_schema()
    
    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception as e:
                print(f"[TokenBudget] Pool init failed, using fallback: {e}")
                self._pool = None
        return self._pool
    
    def _get_conn(self):
        """Get a connection from the pool or fallback to direct connect."""
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=10.0), pool
        else:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=30), None
    
    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()
        
    def _ensure_schema(self):
        """Create the token_usage table if it doesn't exist."""
        try:
            conn, pool = self._get_conn()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS token_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_token_usage_model_time 
                    ON token_usage (model, timestamp)
                """)
                conn.commit()
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            print(f"[TokenBudget] Schema error: {e}")
    
    @staticmethod
    def _normalize_model(model_id: str) -> str:
        """Phase 39: Map full model IDs to budget tier names for rate limiting."""
        m = model_id.lower()
        if 'gemini-2.0-flash' in m:
            return 'gemini-2.0-flash'
        if 'gemini-1.5-flash' in m:
            return 'gemini-1.5-flash'
        if 'gemini-1.5-pro' in m:
            return 'gemini-1.5-pro'
        if 'claude' in m and 'haiku' in m:
            return 'claude-haiku'
        if 'claude' in m:
            return 'claude-sonnet'  # sonnet, opus, etc.
        if 'ollama' in m or 'llama' in m:
            return 'gemini-1.5-flash'  # use flash limits for local models
        return 'gemini-1.5-flash'  # safe default

    def can_call(self, model: str, agent_name: str) -> bool:
        """
        Check if an agent can make a call to a specific model.
        Returns False if rate limit is exhausted.
        """
        model = self._normalize_model(model)  # Phase 39: normalize full IDs
        limits = self.DEFAULT_LIMITS.get(model, self.DEFAULT_LIMITS['gemini-1.5-flash'])
        
        with self._lock:
            try:
                conn, pool = self._get_conn()
                try:
                    c = conn.cursor()
                    
                    # Count calls in the last hour
                    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                    c.execute("""
                        SELECT COUNT(*) FROM token_usage 
                        WHERE model = ? AND timestamp > ?
                    """, (model, one_hour_ago))
                    
                    call_count = c.fetchone()[0]
                finally:
                    self._release_conn(conn, pool)
                
                if call_count >= limits['calls_per_hour']:
                    print(f"[TokenBudget] ⚠️ {agent_name} blocked: {model} limit reached ({call_count}/{limits['calls_per_hour']} calls/hr)")
                    return False
                    
                return True
                
            except Exception as e:
                logging.error(f"[TokenBudget] Check failed (denying): {e}")
                return False  # Fail-closed: deny if budget check fails
    
    def record_usage(self, model: str, tokens_used: int, agent_name: str):
        """
        Record a completed API call for rate-limiting.
        """
        model = self._normalize_model(model)  # Phase 39: normalize full IDs
        with self._lock:
            try:
                conn, pool = self._get_conn()
                try:
                    conn.execute("""
                        INSERT INTO token_usage (model, agent_name, tokens_used)
                        VALUES (?, ?, ?)
                    """, (model, agent_name, tokens_used))
                    conn.commit()
                finally:
                    self._release_conn(conn, pool)
            except Exception as e:
                print(f"[TokenBudget] Record error: {e}")
    
    def get_usage_summary(self, hours: int = 1) -> dict:
        """
        Returns a summary of token usage per model in the last N hours.
        """
        summary = {}
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                c.execute("""
                    SELECT model, SUM(tokens_used), COUNT(*) 
                    FROM token_usage 
                    WHERE timestamp > ?
                    GROUP BY model
                """, (cutoff,))
                
                for row in c.fetchall():
                    model, tokens, calls = row
                    limits = self.DEFAULT_LIMITS.get(model, {})
                    summary[model] = {
                        'tokens_used': tokens,
                        'calls_made': calls,
                        'tokens_limit': limits.get('tokens_per_hour', 0),
                        'calls_limit': limits.get('calls_per_hour', 0)
                    }
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            print(f"[TokenBudget] Summary error: {e}")
            
        return summary
    
    def cleanup_old_records(self, hours: int = 24):
        """
        Prune usage records older than N hours to prevent DB bloat.
        """
        try:
            conn, pool = self._get_conn()
            try:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                conn.execute("DELETE FROM token_usage WHERE timestamp < ?", (cutoff,))
                conn.commit()
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            print(f"[TokenBudget] Cleanup error: {e}")


# Singleton instance for easy import
_budget_instance = None

def get_budget() -> TokenBudget:
    """Returns the singleton TokenBudget instance."""
    global _budget_instance
    if _budget_instance is None:
        _budget_instance = TokenBudget()
    return _budget_instance


if __name__ == "__main__":
    # Test
    budget = TokenBudget()
    print("Can call claude-sonnet?", budget.can_call('claude-sonnet', 'TestAgent'))
    budget.record_usage('claude-sonnet', 1000, 'TestAgent')
    print("Usage summary:", budget.get_usage_summary())

