"""
Agent Registration Utility
Provides consistent agent registration to the roster database.
Uses connection pool to prevent database locking.

Usage:
    from utils.agent_registry import register_agent
    
    # In agent __init__ or run_cycle:
    register_agent("AgentSteward", "WEALTH/DYNASTY", db_path)
"""

import time
import os
import logging

# Default DB path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Cached pool reference
_pool = None

def _get_pool():
    """Lazy-load the connection pool."""
    global _pool
    if _pool is None:
        try:
            from db.db_pool import get_pool
            _pool = get_pool()
        except Exception:
            _pool = None
    return _pool

def _get_conn(db_path=None):
    """Get a connection from pool or fallback to direct."""
    pool = _get_pool()
    if pool:
        return pool.get(timeout=10.0), pool
    else:
        import sqlite3
        db = db_path or DEFAULT_DB_PATH
        return sqlite3.connect(db, timeout=10.0), None

def _release_conn(conn, pool):
    """Release connection back to pool or close if direct."""
    if pool:
        pool.release(conn)
    else:
        conn.close()


def register_agent(name: str, department: str, db_path: str = None, status: str = "ACTIVE"):
    """
    Register or update an agent in the agents table.
    
    Args:
        name: Agent name (e.g., "AgentSteward")
        department: Department name (e.g., "WEALTH", "EDUCATION", "STRATEGY")
        db_path: Path to database (defaults to republic.db)
        status: Status string (default "ACTIVE")
    """
    timestamp = time.time()
    
    try:
        conn, pool = _get_conn(db_path)
        try:
            c = conn.cursor()
            
            # Ensure table exists
            c.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    name TEXT PRIMARY KEY,
                    status TEXT,
                    last_active REAL,
                    department TEXT
                )
            """)
            
            # Upsert
            c.execute("""
                INSERT INTO agents (name, status, last_active, department)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    status = excluded.status,
                    last_active = excluded.last_active,
                    department = excluded.department
            """, (name, status, timestamp, department))
            
            conn.commit()
        finally:
            _release_conn(conn, pool)
        
    except Exception as e:
        logging.warning(f"[REGISTRY] Failed to register {name}: {e}")


def heartbeat(name: str, db_path: str = None, status: str = "ACTIVE"):
    """
    Quick heartbeat update - just updates last_active timestamp.
    Call this periodically in agent run cycles.
    """
    timestamp = time.time()
    
    try:
        conn, pool = _get_conn(db_path)
        try:
            c = conn.cursor()
            c.execute("""
                UPDATE agents SET last_active = ?, status = ? WHERE name = ?
            """, (timestamp, status, name))
            conn.commit()
        finally:
            _release_conn(conn, pool)
    except Exception:
        pass


def mark_offline(name: str, db_path: str = None):
    """Mark an agent as offline."""
    try:
        conn, pool = _get_conn(db_path)
        try:
            c = conn.cursor()
            c.execute("UPDATE agents SET status = 'OFFLINE' WHERE name = ?", (name,))
            conn.commit()
        finally:
            _release_conn(conn, pool)
    except Exception:
        pass

