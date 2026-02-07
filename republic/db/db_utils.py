"""
Database Utilities
Simple wrapper for connection pool access.
Provides drop-in replacement for sqlite3.connect() pattern.
"""

import sqlite3
import os
from pathlib import Path

# Path discovery
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

# Lazy pool reference
_pool = None

def _get_pool():
    """Lazy initialization of connection pool."""
    global _pool
    if _pool is None:
        try:
            from db.db_pool import get_pool
            _pool = get_pool()
        except ImportError:
            _pool = None
    return _pool


def get_conn(db_path=None, timeout=120.0):
    """
    Get a database connection.
    Uses pool if available, falls back to direct connection.
    
    IMPORTANT: You MUST call release_conn() when done!
    
    Args:
        db_path: Optional path (ignored if using pool)
        timeout: Connection timeout
        
    Returns:
        sqlite3.Connection
    """
    pool = _get_pool()
    if pool:
        return pool.get(timeout=timeout)
    else:
        path = db_path or DB_PATH
        return sqlite3.connect(path, timeout=timeout)


def release_conn(conn):
    """
    Release a connection back to pool or close it.
    
    Args:
        conn: Connection from get_conn()
    """
    pool = _get_pool()
    if pool:
        pool.release(conn)
    else:
        try:
            conn.close()
        except sqlite3.Error:
            pass


class DBContext:
    """
    Context manager for database connections.
    
    Usage:
        with DBContext() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    def __init__(self, db_path=None, timeout=120.0):
        self.db_path = db_path
        self.timeout = timeout
        self._conn = None
    
    def __enter__(self):
        self._conn = get_conn(self.db_path, self.timeout)
        return self._conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            release_conn(self._conn)
            self._conn = None
