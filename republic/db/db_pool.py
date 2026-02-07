"""
Database Connection Pool
Thread-safe singleton connection pool for SQLite and PostgreSQL.

USAGE:
    from db.db_pool import get_connection, release_connection

    # Option 1: Context manager (preferred)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table")

    # Option 2: Manual (legacy compatibility)
    conn = get_connection()
    try:
        # do work
    finally:
        release_connection(conn)

Phase 8: PostgreSQL support via DATABASE_BACKEND environment variable.
Set DATABASE_BACKEND=postgresql to use PostgreSQL, otherwise defaults to sqlite.
"""

import os
import time
import threading
import queue
import logging
from pathlib import Path

# Path discovery
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
DATABASE_BACKEND = os.getenv('DATABASE_BACKEND', 'sqlite').lower()

# Configuration
POOL_SIZE = 200 if DATABASE_BACKEND == 'sqlite' else 200  # Match SQLite pool size for 46-agent swarm
CONNECTION_TIMEOUT = 120.0  # seconds
MAX_OVERFLOW = 50 if DATABASE_BACKEND == 'sqlite' else 20  # PostgreSQL needs fewer
CONNECTION_RECYCLE_SECONDS = 120  # Recycle connections older than 2 minutes

logger = logging.getLogger(__name__)


def _get_pg_params() -> dict:
    """Get PostgreSQL connection parameters from environment."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'republic'),
        'user': os.getenv('POSTGRES_USER', 'republic_user'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }


class ConnectionPool:
    """Thread-safe connection pool singleton. Supports SQLite and PostgreSQL."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.backend = DATABASE_BACKEND
        self._pool_lock = threading.Lock()
        self._active_count = 0
        self._overflow_count = 0
        self._overflow_total = 0
        self._conn_created_at = {}

        # Phase 6.75: Health logging
        self._last_health_log = 0
        self._health_log_interval = 60

        if self.backend == 'postgresql':
            self._init_pg_pool()
        else:
            self._init_sqlite_pool()

        self._initialized = True

    def _init_sqlite_pool(self):
        """Initialize SQLite connection pool."""
        import sqlite3
        self._pool = queue.Queue(maxsize=POOL_SIZE)
        self._in_use = set()

        for _ in range(POOL_SIZE):
            conn = self._create_sqlite_connection()
            self._conn_created_at[id(conn)] = time.time()
            self._pool.put(conn)

        logger.info(
            f"[DB_POOL] SQLite pool initialized with {POOL_SIZE} connections "
            f"(max_overflow={MAX_OVERFLOW}, recycle={CONNECTION_RECYCLE_SECONDS}s)"
        )

    def _init_pg_pool(self):
        """Initialize PostgreSQL connection pool using psycopg2.pool.ThreadedConnectionPool."""
        import psycopg2
        import psycopg2.pool
        import psycopg2.extras

        pg_params = _get_pg_params()
        minconn = 10
        maxconn = POOL_SIZE

        self._pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            **pg_params
        )
        self._pool = None  # Not used for PostgreSQL
        self._in_use = set()

        logger.info(
            f"[DB_POOL] PostgreSQL pool initialized "
            f"(min={minconn}, max={maxconn}, host={pg_params['host']}:{pg_params['port']})"
        )

    def _create_sqlite_connection(self):
        """Create a new SQLite connection with proper settings."""
        import sqlite3
        conn = sqlite3.connect(
            DB_PATH,
            timeout=CONNECTION_TIMEOUT,
            check_same_thread=False,
            isolation_level=None
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=120000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _maybe_recycle(self, conn):
        """Recycle a connection if it's older than CONNECTION_RECYCLE_SECONDS (SQLite only)."""
        if self.backend != 'sqlite':
            return conn
        import sqlite3
        conn_id = id(conn)
        created = self._conn_created_at.get(conn_id, 0)
        if time.time() - created > CONNECTION_RECYCLE_SECONDS:
            try:
                conn.close()
            except sqlite3.Error:
                pass
            self._conn_created_at.pop(conn_id, None)
            new_conn = self._create_sqlite_connection()
            self._conn_created_at[id(new_conn)] = time.time()
            return new_conn
        return conn

    def get(self, timeout: float = 120.0):
        """Get a connection from the pool."""
        self._maybe_log_health()

        if self.backend == 'postgresql':
            return self._get_pg(timeout)
        else:
            return self._get_sqlite(timeout)

    def _get_sqlite(self, timeout: float):
        """Get a SQLite connection from the pool."""
        try:
            conn = self._pool.get(timeout=timeout)
            conn = self._maybe_recycle(conn)
            with self._pool_lock:
                self._in_use.add(id(conn))
                self._active_count += 1
            return conn
        except queue.Empty:
            with self._pool_lock:
                if self._overflow_count >= MAX_OVERFLOW:
                    logger.warning(f"[DB_POOL] Max overflow ({MAX_OVERFLOW}) reached, waiting...")
                    conn = self._pool.get(timeout=CONNECTION_TIMEOUT)
                    conn = self._maybe_recycle(conn)
                    self._in_use.add(id(conn))
                    self._active_count += 1
                    return conn
                self._overflow_count += 1
                self._overflow_total += 1
            conn = self._create_sqlite_connection()
            self._conn_created_at[id(conn)] = time.time()
            return conn

    def _get_pg(self, timeout: float):
        """Get a PostgreSQL connection from the pool, wrapped for SQLite compat."""
        import psycopg2
        try:
            raw_conn = self._pg_pool.getconn()
            raw_conn.autocommit = False
            with self._pool_lock:
                self._in_use.add(id(raw_conn))
                self._active_count += 1
            # Wrap with auto-translating wrapper so ALL agents get SQL translation
            # Pass pool reference so close() returns to pool instead of closing
            try:
                from db.db_helper import _PgConnectionWrapper
                return _PgConnectionWrapper(raw_conn, pool=self)
            except ImportError:
                return raw_conn
        except psycopg2.pool.PoolError as e:
            logger.error(f"[DB_POOL] PostgreSQL pool error: {e}")
            raise
        except Exception as e:
            logger.error(f"[DB_POOL] PostgreSQL connection error: {e}")
            raise

    def release(self, conn):
        """Return a connection to the pool."""
        if self.backend == 'postgresql':
            self._release_pg(conn)
        else:
            self._release_sqlite(conn)

    def _release_sqlite(self, conn):
        """Release a SQLite connection."""
        import sqlite3
        with self._pool_lock:
            conn_id = id(conn)
            if conn_id in self._in_use:
                self._in_use.discard(conn_id)
                self._active_count -= 1
                try:
                    conn.rollback()
                    self._pool.put_nowait(conn)
                except queue.Full:
                    self._overflow_count = max(0, self._overflow_count - 1)
                    self._conn_created_at.pop(conn_id, None)
                    conn.close()
            else:
                self._overflow_count = max(0, self._overflow_count - 1)
                self._conn_created_at.pop(conn_id, None)
                try:
                    conn.close()
                except sqlite3.Error:
                    pass

    def _release_pg(self, conn):
        """Release a PostgreSQL connection (unwraps if wrapped)."""
        import psycopg2
        # Unwrap if it's a _PgConnectionWrapper
        try:
            from db.db_helper import _PgConnectionWrapper
            raw_conn = conn._conn if isinstance(conn, _PgConnectionWrapper) else conn
        except ImportError:
            raw_conn = conn

        with self._pool_lock:
            conn_id = id(raw_conn)
            self._in_use.discard(conn_id)
            self._active_count = max(0, self._active_count - 1)
        try:
            raw_conn.rollback()
            self._pg_pool.putconn(raw_conn)
        except Exception as e:
            logger.warning(f"[DB_POOL] PostgreSQL release error: {e}")
            try:
                self._pg_pool.putconn(raw_conn, close=True)
            except Exception:
                pass

    def close_all(self):
        """Close all connections in the pool."""
        if self.backend == 'postgresql':
            try:
                self._pg_pool.closeall()
            except Exception:
                pass
        else:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except queue.Empty:
                    break
        logger.info(f"[DB_POOL] All {self.backend} connections closed")

    def _maybe_log_health(self):
        """Phase 6.75: Log pool health every 60 seconds for monitoring."""
        now = time.time()
        if now - self._last_health_log >= self._health_log_interval:
            self._last_health_log = now
            if self.backend == 'postgresql':
                # psycopg2 ThreadedConnectionPool doesn't expose detailed stats
                total_capacity = POOL_SIZE
                utilization = self._active_count / total_capacity * 100 if total_capacity > 0 else 0
                status = "HEALTHY" if utilization < 60 else ("HIGH" if utilization < 85 else "CRITICAL")
                logger.info(
                    f"[DB_POOL] {status} [PG] | Active: {self._active_count} | "
                    f"Utilization: {utilization:.0f}% of {total_capacity}"
                )
            else:
                available = self._pool.qsize()
                total_capacity = POOL_SIZE + MAX_OVERFLOW
                utilization = (self._active_count + self._overflow_count) / total_capacity * 100 if total_capacity > 0 else 0
                status = "HEALTHY" if utilization < 60 else ("HIGH" if utilization < 85 else "CRITICAL")
                logger.info(
                    f"[DB_POOL] {status} [SQLite] | Active: {self._active_count} | Available: {available} | "
                    f"Overflow: {self._overflow_count}/{MAX_OVERFLOW} | "
                    f"Utilization: {utilization:.0f}% of {total_capacity} | "
                    f"Lifetime overflow: {self._overflow_total}"
                )

    @property
    def active_connections(self) -> int:
        return self._active_count

    @property
    def available_connections(self) -> int:
        if self.backend == 'postgresql':
            return POOL_SIZE - self._active_count
        return self._pool.qsize()


class ConnectionContext:
    """Context manager for database connections."""

    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._conn = None

    def __enter__(self):
        self._conn = self._pool.get()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._pool.release(self._conn)
            self._conn = None


# Global pool instance
_pool = None


def get_pool() -> ConnectionPool:
    """Get the global connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool()
    return _pool


def get_connection(timeout: float = 120.0):
    """
    Get a database connection from the pool.

    For legacy compatibility - returns a raw connection.
    IMPORTANT: You MUST call release_connection() when done!

    Prefer using as context manager:
        with get_connection() as conn:
            ...
    """
    return get_pool().get(timeout)


def release_connection(conn):
    """Release a connection back to the pool."""
    get_pool().release(conn)


def with_connection():
    """Context manager for database connections."""
    return ConnectionContext(get_pool())


def pool_status() -> dict:
    """Get current pool status."""
    pool = get_pool()
    return {
        "backend": pool.backend,
        "active": pool.active_connections,
        "available": pool.available_connections,
        "pool_size": POOL_SIZE,
        "overflow_active": pool._overflow_count,
        "overflow_max": MAX_OVERFLOW,
        "overflow_lifetime": pool._overflow_total
    }
