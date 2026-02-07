"""
Database Connection Utilities
Department: Shared Infrastructure
File: db_utils.py

Provides resilient database connections with:
- WAL mode enabled
- Retry logic with exponential backoff
- Connection pooling ready

"LEF's thoughts should never be lost to a database lock."
"""

import sqlite3
import time
import os
import functools
from typing import Callable, Any, Optional
from pathlib import Path

# Default database path
DEFAULT_DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path(__file__).parent.parent / "republic.db")
)


def get_resilient_connection(db_path: str = None, timeout: float = 30.0) -> sqlite3.Connection:
    """
    Get a SQLite connection with WAL mode and appropriate timeout.
    
    WAL (Write-Ahead Logging) allows concurrent reads with one writer,
    reducing lock contention significantly.
    """
    db_path = db_path or DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path, timeout=timeout)

    # Enable WAL mode for better concurrency (SQLite only)
    backend = os.getenv('DATABASE_BACKEND', 'sqlite')
    if backend != 'postgresql':
        conn.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout to wait for locks
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys=ON")

    return conn


def with_retry(max_retries: int = 5, 
               initial_delay: float = 0.1,
               max_delay: float = 2.0,
               backoff_factor: float = 2.0):
    """
    Decorator that retries a function on database lock errors.
    
    Uses exponential backoff to reduce contention.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e):
                        last_error = e
                        if attempt < max_retries:
                            time.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                            continue
                    raise
            
            # If we got here, all retries failed
            raise last_error
        
        return wrapper
    return decorator


def execute_with_retry(cursor_or_conn, 
                       sql: str, 
                       params: tuple = None,
                       max_retries: int = 5) -> Any:
    """
    Execute SQL with retry logic built in.
    
    Args:
        cursor_or_conn: Either a cursor or connection
        sql: SQL statement to execute
        params: Optional parameters for the query
        max_retries: Maximum number of retry attempts
    
    Returns:
        The cursor after execution
    """
    delay = 0.1
    
    for attempt in range(max_retries + 1):
        try:
            if params:
                return cursor_or_conn.execute(sql, params)
            else:
                return cursor_or_conn.execute(sql)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 2.0)
                continue
            raise


def commit_with_retry(conn: sqlite3.Connection, 
                      max_retries: int = 5) -> bool:
    """
    Commit a transaction with retry logic.
    
    Returns True if successful, raises on failure.
    """
    delay = 0.1
    
    for attempt in range(max_retries + 1):
        try:
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 2.0)
                continue
            raise


class ResilientCursor:
    """
    A cursor wrapper that automatically retries on database locks.
    
    Usage:
        conn = get_resilient_connection()
        with ResilientCursor(conn) as cursor:
            cursor.execute("INSERT INTO ...", params)
    """
    
    def __init__(self, connection: sqlite3.Connection, max_retries: int = 5):
        self.connection = connection
        self.cursor = connection.cursor()
        self.max_retries = max_retries
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            commit_with_retry(self.connection, self.max_retries)
        self.cursor.close()
        return False
    
    def execute(self, sql: str, params: tuple = None):
        """Execute with automatic retry."""
        return execute_with_retry(self.cursor, sql, params, self.max_retries)
    
    def executemany(self, sql: str, params_list: list):
        """Execute many with retry logic."""
        delay = 0.1
        for attempt in range(self.max_retries + 1):
            try:
                return self.cursor.executemany(sql, params_list)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self.max_retries:
                    time.sleep(delay)
                    delay = min(delay * 2, 2.0)
                    continue
                raise
    
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        return self.cursor.fetchall()
    
    def fetchmany(self, size: int = None):
        return self.cursor.fetchmany(size)
    
    @property
    def lastrowid(self):
        return self.cursor.lastrowid
    
    @property
    def rowcount(self):
        return self.cursor.rowcount


# Migration helper: Enable WAL mode on existing database
def migrate_to_wal(db_path: str = None):
    """
    One-time migration to enable WAL mode on existing database.
    """
    if os.getenv('DATABASE_BACKEND', 'sqlite') == 'postgresql':
        print("[DB] PostgreSQL backend - WAL migration not applicable")
        return

    db_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)

    backend = os.getenv('DATABASE_BACKEND', 'sqlite')
    if backend != 'postgresql':
        current_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        print(f"[DB] Current journal mode: {current_mode}")

        if current_mode.lower() != "wal":
            result = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            print(f"[DB] Migrated to journal mode: {result}")
        else:
            print("[DB] Already in WAL mode")

    conn.close()


if __name__ == "__main__":
    # Test and migrate
    print("=== Database Utilities Test ===")
    migrate_to_wal()
    
    conn = get_resilient_connection()
    with ResilientCursor(conn) as cursor:
        cursor.execute("SELECT 1")
        print(f"Test query result: {cursor.fetchone()}")
    conn.close()
    print("✅ Resilient database utilities working")
