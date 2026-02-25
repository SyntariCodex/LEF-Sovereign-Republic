"""
Database Connection Helper
Provides a unified interface for database connections across all agents.
Uses the connection pool as primary, falls back to direct connection if needed.

Phase 8: Supports both SQLite and PostgreSQL.
The DATABASE_BACKEND env var controls which backend to use.

Usage:
    from db.db_helper import get_connection, release_connection

    conn, pool = get_connection()
    try:
        # Do database work
        conn.execute("SELECT * FROM agents")
        conn.commit()
    finally:
        release_connection(conn, pool)

Or use the context manager:
    from db.db_helper import db_connection

    with db_connection() as conn:
        conn.execute("SELECT * FROM agents")
        conn.commit()
"""

import os
import re
import time
import logging
import datetime
from contextlib import contextmanager
from pathlib import Path

_logger = logging.getLogger(__name__)

# Default DB path
BASE_DIR = Path(__file__).parent.parent
DEFAULT_DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
DATABASE_BACKEND = os.getenv('DATABASE_BACKEND', 'sqlite').lower()

# Cached pool reference
_pool = None
_pool_failed = False

# Phase 38.6: Module-level startup staleness check — fires once per process.
# Warns operators immediately if the SQLite DB is stale AND the backend
# defaults to 'sqlite' because DATABASE_BACKEND env var was not set.
try:
    _sqlite_path = DEFAULT_DB_PATH
    if DATABASE_BACKEND == 'sqlite' and os.path.exists(_sqlite_path):
        _db_age_hours = (time.time() - os.path.getmtime(_sqlite_path)) / 3600
        if _db_age_hours > 24:
            _logger.critical(
                "[DB_HELPER] ⚠️  STALE SQLITE ON STARTUP: '%s' last modified %.1fh ago. "
                "DATABASE_BACKEND defaults to 'sqlite' — if PostgreSQL is the intended backend, "
                "set DATABASE_BACKEND=postgresql in your environment.",
                _sqlite_path, _db_age_hours
            )
except OSError:
    pass


def get_backend() -> str:
    """Return the current database backend name."""
    return DATABASE_BACKEND


def is_postgresql() -> bool:
    """Return True if using PostgreSQL backend."""
    return DATABASE_BACKEND == 'postgresql'


def translate_sql(sql: str) -> str:
    """
    Translate SQLite-specific SQL to PostgreSQL-compatible SQL.

    Conversions:
    - ? placeholders → %s placeholders
    - PRAGMA statements → no-op (returns empty string)
    - INSERT OR REPLACE → INSERT ... ON CONFLICT DO UPDATE
    - INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    - AUTOINCREMENT → (stripped, PostgreSQL uses SERIAL)
    - IFNULL → COALESCE
    - datetime('now') → NOW()
    - strftime('%s', ...) → EXTRACT(EPOCH FROM ...)

    For SQLite backend, returns SQL unchanged.
    """
    if DATABASE_BACKEND != 'postgresql':
        return sql

    # PRAGMA statements are SQLite-specific, skip them
    stripped = sql.strip().upper()
    if stripped.startswith('PRAGMA'):
        return ''

    result = sql

    # ? → %s parameter substitution
    result = result.replace('?', '%s')

    # INSERT OR REPLACE → INSERT ... ON CONFLICT DO UPDATE
    # Parse the table and columns to generate proper ON CONFLICT clause
    _had_or_replace = bool(re.search(r'INSERT\s+OR\s+REPLACE\s+INTO', result, flags=re.IGNORECASE))
    result = re.sub(
        r'INSERT\s+OR\s+REPLACE\s+INTO',
        'INSERT INTO',
        result,
        flags=re.IGNORECASE
    )
    if _had_or_replace and 'ON CONFLICT' not in result.upper():
        # Extract column names from VALUES clause to build DO UPDATE SET
        col_match = re.search(r'INSERT\s+INTO\s+\w+\s*\(([^)]+)\)', result, flags=re.IGNORECASE)
        if col_match:
            cols = [c.strip().strip("'\"") for c in col_match.group(1).split(',')]
            # First column is typically the primary key for system_state-style tables
            conflict_col = cols[0]
            update_cols = cols[1:]
            if update_cols:
                updates = ', '.join([f"{c} = EXCLUDED.{c}" for c in update_cols])
                result = result.rstrip().rstrip(';') + f' ON CONFLICT ({conflict_col}) DO UPDATE SET {updates}'
            else:
                result = result.rstrip().rstrip(';') + f' ON CONFLICT ({conflict_col}) DO NOTHING'

    # INSERT OR IGNORE → INSERT INTO ... ON CONFLICT DO NOTHING
    _had_or_ignore = bool(re.search(r'INSERT\s+OR\s+IGNORE\s+INTO', result, flags=re.IGNORECASE))
    result = re.sub(
        r'INSERT\s+OR\s+IGNORE\s+INTO',
        'INSERT INTO',
        result,
        flags=re.IGNORECASE
    )
    if _had_or_ignore and 'ON CONFLICT' not in result.upper():
        result = result.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'

    # IFNULL → COALESCE
    result = re.sub(r'\bIFNULL\b', 'COALESCE', result, flags=re.IGNORECASE)

    # datetime('now') → NOW()
    result = re.sub(r"datetime\s*\(\s*'now'\s*\)", "NOW()", result, flags=re.IGNORECASE)

    # datetime('now', '-N hours/days/minutes') → NOW() - INTERVAL 'N hours/days/minutes'
    result = re.sub(
        r"datetime\s*\(\s*'now'\s*,\s*'([^']+)'\s*\)",
        lambda m: f"NOW() + INTERVAL '{m.group(1)}'",
        result,
        flags=re.IGNORECASE
    )

    # strftime('%s','now') - column → EXTRACT(EPOCH FROM (NOW() - column))
    # Must come BEFORE the general strftime conversion so the specific pattern matches first
    result = re.sub(
        r"strftime\s*\(\s*'%s'\s*,\s*'now'\s*\)\s*-\s*(\w+)",
        r"EXTRACT(EPOCH FROM (NOW() - \1))",
        result,
        flags=re.IGNORECASE
    )

    # strftime('%s', 'now') → EXTRACT(EPOCH FROM NOW())
    result = re.sub(
        r"strftime\s*\(\s*'%s'\s*,\s*'now'\s*\)",
        "EXTRACT(EPOCH FROM NOW())",
        result,
        flags=re.IGNORECASE
    )

    # SQLite scalar MIN(a, b) → PostgreSQL LEAST(a, b)
    # SQLite scalar MAX(a, b) → PostgreSQL GREATEST(a, b)
    # Process inside-out for nested cases like MAX(0.1, MIN(0.99, x))
    _prev = None
    while _prev != result:
        _prev = result
        result = re.sub(
            r'\bMIN\s*\(([^(),]+),\s*((?:[^()]|\([^()]*\))+)\)',
            r'LEAST(\1, \2)',
            result, count=1, flags=re.IGNORECASE
        )
        result = re.sub(
            r'\bMAX\s*\(([^(),]+),\s*((?:[^()]|\([^()]*\))+)\)',
            r'GREATEST(\1, \2)',
            result, count=1, flags=re.IGNORECASE
        )

    # AUTOINCREMENT → strip (PostgreSQL uses SERIAL)
    result = re.sub(r'\bAUTOINCREMENT\b', '', result, flags=re.IGNORECASE)

    # GROUP_CONCAT(col) → string_agg(col::text, ',')
    # GROUP_CONCAT(col, sep) → string_agg(col::text, sep)
    result = re.sub(
        r'\bGROUP_CONCAT\s*\(\s*(\w+)\s*,\s*([^)]+)\s*\)',
        r'string_agg(\1::text, \2)',
        result, flags=re.IGNORECASE
    )
    result = re.sub(
        r'\bGROUP_CONCAT\s*\(\s*(\w+)\s*\)',
        r"string_agg(\1::text, ',')",
        result, flags=re.IGNORECASE
    )

    # INTEGER PRIMARY KEY → INTEGER PRIMARY KEY (keep as-is for PG, but strip AUTOINCREMENT above)
    # CREATE TABLE IF NOT EXISTS with SQLite-only types — mostly compatible

    return result


def upsert_sql(table: str, columns: list, conflict_column: str) -> str:
    """
    Generate database-agnostic upsert SQL.

    Phase 8: Replaces INSERT OR REPLACE with proper ON CONFLICT syntax for PostgreSQL.

    Args:
        table: Target table name
        columns: List of column names
        conflict_column: The column with UNIQUE/PRIMARY KEY constraint

    Returns:
        SQL string with appropriate placeholder style (? for SQLite, %s for PostgreSQL)
    """
    if DATABASE_BACKEND == 'postgresql':
        ph = '%s'
        placeholders = ', '.join([ph] * len(columns))
        update_cols = [c for c in columns if c != conflict_column]
        if update_cols:
            updates = ', '.join([f"{c} = EXCLUDED.{c}" for c in update_cols])
            return (
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict_column}) DO UPDATE SET {updates}"
            )
        else:
            return (
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict_column}) DO NOTHING"
            )
    else:
        ph = '?'
        placeholders = ', '.join([ph] * len(columns))
        return f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"


def ignore_insert_sql(table: str, columns: list, conflict_column: str = None) -> str:
    """
    Generate database-agnostic INSERT OR IGNORE SQL.

    Phase 8: Replaces INSERT OR IGNORE with ON CONFLICT DO NOTHING for PostgreSQL.

    Args:
        table: Target table name
        columns: List of column names
        conflict_column: Optional conflict column (PostgreSQL needs it for ON CONFLICT)

    Returns:
        SQL string with appropriate placeholder style
    """
    if DATABASE_BACKEND == 'postgresql':
        ph = '%s'
        placeholders = ', '.join([ph] * len(columns))
        conflict = f" ({conflict_column})" if conflict_column else ""
        return (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT{conflict} DO NOTHING"
        )
    else:
        ph = '?'
        placeholders = ', '.join([ph] * len(columns))
        return f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"


def translate_params(params):
    """
    Translate parameter format if needed.
    SQLite uses tuples, PostgreSQL uses tuples too, so this is mostly a pass-through.
    """
    if params is None:
        return None
    return params


def _get_pool():
    """Lazy-load the connection pool."""
    global _pool, _pool_failed

    if _pool_failed:
        return None

    if _pool is None:
        try:
            from db.db_pool import get_pool
            _pool = get_pool()
        except Exception:
            _pool_failed = True
            _pool = None
    return _pool


def get_connection(db_path: str = None, timeout: float = 120.0):
    """
    Get a database connection from the pool or fallback to direct.

    Args:
        db_path: Optional path to database file (SQLite only, ignored for PostgreSQL)
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (connection, pool) - pool is None if direct connection

    IMPORTANT: Always call release_connection() when done!
    """
    pool = _get_pool()

    if pool:
        conn = pool.get(timeout=timeout)
        if pool.backend == 'sqlite':
            _configure_sqlite_connection(conn)
        # PostgreSQL connections are already wrapped by the pool
        return conn, pool
    else:
        # Fallback: direct connection (no pool available)
        if DATABASE_BACKEND == 'postgresql':
            conn = _PgConnectionWrapper(_create_direct_pg_connection())
        else:
            conn = _create_direct_sqlite_connection(db_path, timeout)
        return conn, None


def _create_direct_sqlite_connection(db_path=None, timeout=120.0):
    """Create a direct SQLite connection (fallback when pool unavailable)."""
    import sqlite3
    db = db_path or DEFAULT_DB_PATH

    # Phase 38.6: Staleness guard — warn if connecting to a stale SQLite DB.
    # Protects against silently reading old data when PostgreSQL is the primary
    # backend but DATABASE_BACKEND env var was omitted, causing a silent fallback
    # to the legacy republic.db file which may be days or weeks out of date.
    try:
        if os.path.exists(db):
            age_hours = (time.time() - os.path.getmtime(db)) / 3600
            if age_hours > 24:
                _logger.critical(
                    "[DB_HELPER] ⚠️  STALE SQLITE: '%s' last modified %.1fh ago. "
                    "If PostgreSQL is the intended backend, set DATABASE_BACKEND=postgresql "
                    "to avoid reading stale data. Current backend: %s",
                    db, age_hours, DATABASE_BACKEND
                )
    except OSError:
        pass

    conn = sqlite3.connect(db, timeout=timeout)
    _configure_sqlite_connection(conn)
    return conn


def _create_direct_pg_connection():
    """Create a direct PostgreSQL connection (fallback when pool unavailable)."""
    import psycopg2
    from db.db_pool import _get_pg_params
    pg_params = _get_pg_params()
    conn = psycopg2.connect(**pg_params)
    conn.autocommit = False
    return conn


def _configure_sqlite_connection(conn):
    """
    Configure SQLite connection for optimal concurrent access.
    WAL mode allows multiple readers + one writer.
    """
    import sqlite3
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=120000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.OperationalError:
        pass


# =========================================================================
# PostgreSQL Auto-Translating Connection Wrapper
# =========================================================================
# Wraps psycopg2 connections so that SQLite-style SQL (?, AUTOINCREMENT,
# datetime('now'), PRAGMA, etc.) is automatically translated to PostgreSQL.
# This lets ALL agents use db_connection() without modifying their SQL.
# =========================================================================

class _DualAccessRow:
    """
    A row that supports both index access (row[0]) and name access (row['col']).
    Mimics sqlite3.Row behavior for PostgreSQL results.
    """
    __slots__ = ('_values', '_columns')

    def __init__(self, values, columns):
        self._values = values
        self._columns = columns

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        if isinstance(key, str):
            try:
                idx = self._columns.index(key)
                return self._values[idx]
            except ValueError:
                raise KeyError(f"No column named '{key}'")
        raise TypeError(f"Invalid key type: {type(key)}")

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return f"_DualAccessRow({dict(zip(self._columns, self._values))})"

    def keys(self):
        return list(self._columns)


class _PgCursorWrapper:
    """Wraps a psycopg2 cursor to auto-translate SQLite SQL.

    Phase 8.3: Auto-rollback on failed queries to prevent PostgreSQL
    'current transaction is aborted' cascading errors.  In PostgreSQL,
    a single failed query poisons the entire transaction — all subsequent
    queries fail until an explicit ROLLBACK.  SQLite doesn't have this
    behaviour, so the 300+ raw sqlite3.connect() call sites never handled
    it.  By catching exceptions and auto-rolling-back here, we keep the
    connection usable for subsequent queries.
    """

    def __init__(self, cursor, pg_conn=None):
        self._cursor = cursor
        self._pg_conn = pg_conn  # Raw psycopg2 connection for auto-rollback

    @property
    def connection(self):
        """Expose parent connection (sqlite3 cursor compat)."""
        return self._cursor.connection

    def _coerce_row(self, row):
        """Convert Decimal values to float and wrap as DualAccessRow."""
        from decimal import Decimal
        if row is None:
            return None
        # Coerce Decimal to float
        coerced = tuple(float(v) if isinstance(v, Decimal) else v for v in row)
        # Wrap with column names for dual access
        if self._cursor.description:
            columns = [desc[0] for desc in self._cursor.description]
            return _DualAccessRow(coerced, columns)
        return coerced

    @staticmethod
    def _coerce_epoch_params(params):
        """
        Convert epoch timestamps (from time.time()) to datetime objects.
        PostgreSQL TIMESTAMP columns reject raw numeric epoch values.
        Range 1e9–2e9 covers years ~2001–2033.
        """
        def _convert(v):
            if isinstance(v, (int, float)) and 1_000_000_000 < v < 2_000_000_000:
                try:
                    return datetime.datetime.fromtimestamp(v)
                except (ValueError, OSError):
                    return v
            return v

        if isinstance(params, dict):
            return {k: _convert(v) for k, v in params.items()}
        if isinstance(params, (tuple, list)):
            return tuple(_convert(v) for v in params)
        return params

    # Column names known to be TIMESTAMP in PostgreSQL schema
    _TIMESTAMP_COLUMNS = (
        'timestamp',
        'last_active', 'last_heartbeat', 'last_updated',
        'created_at', 'executed_at', 'opened_at', 'closed_at',
        'migrated_at', 'ingested_at', 'resolved_at', 'consumed_at',
        'posted_at', 'responded_at', 'last_seen', 'last_validated',
        'last_applied', 'last_used', 'completed_at', 'target_date',
        'added_at', 'allocated_at', 'approved_at', 'assigned_at',
        'ended_at', 'first_seen', 'github_last_commit', 'observed_at',
        'started_at', 'updated_at',
    )

    def execute(self, sql, params=None):
        translated = translate_sql(sql)
        if not translated:  # PRAGMA → empty string
            return self._cursor
        # Convert named params :name → %(name)s
        if params and isinstance(params, dict):
            translated = re.sub(r':(\w+)', r'%(\1)s', translated)
        # Convert sqlite_master references for table listing queries
        if 'sqlite_master' in translated:
            # Replace the common "SELECT name FROM sqlite_master WHERE type='table'" pattern
            translated = re.sub(
                r"SELECT\s+name\s+FROM\s+sqlite_master\s+WHERE\s+type\s*=\s*'table'",
                "SELECT tablename AS name FROM pg_tables WHERE schemaname='public'",
                translated,
                flags=re.IGNORECASE
            )
            # Fallback: generic replacement
            translated = translated.replace('sqlite_master', 'pg_tables')
            # Fix column name: sqlite_master uses 'name', pg_tables uses 'tablename'
            if 'pg_tables' in translated:
                translated = re.sub(r"\bname\s*=", "tablename =", translated, flags=re.IGNORECASE)
        # Coerce epoch timestamps to datetime for TIMESTAMP columns
        if params:
            sql_lower = translated.lower()
            if any(col in sql_lower for col in self._TIMESTAMP_COLUMNS):
                params = self._coerce_epoch_params(params)
        # Phase 8.3: Auto-rollback on failure to prevent transaction poisoning
        try:
            return self._cursor.execute(translated, params)
        except Exception as e:
            if self._pg_conn:
                try:
                    self._pg_conn.rollback()
                    _logger.debug(f"[DB_HELPER] Auto-rollback after failed query: {type(e).__name__}: {e}")
                except Exception:
                    pass
            raise

    def executemany(self, sql, params_list):
        translated = translate_sql(sql)
        if not translated:
            return self._cursor
        # Coerce epoch timestamps in batch params too
        if params_list:
            sql_lower = translated.lower()
            if any(col in sql_lower for col in self._TIMESTAMP_COLUMNS):
                params_list = [self._coerce_epoch_params(p) for p in params_list]
        # Phase 8.3: Auto-rollback on failure
        try:
            return self._cursor.executemany(translated, params_list)
        except Exception as e:
            if self._pg_conn:
                try:
                    self._pg_conn.rollback()
                    _logger.debug(f"[DB_HELPER] Auto-rollback after failed executemany: {type(e).__name__}: {e}")
                except Exception:
                    pass
            raise

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._coerce_row(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [self._coerce_row(r) for r in rows]

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        return [self._coerce_row(r) for r in rows]

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        return self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __next__(self):
        return next(self._cursor)


class _PgConnectionWrapper:
    """
    Wraps a psycopg2 connection to provide SQLite-compatible interface.

    Auto-translates SQL in execute() and cursor().execute().
    Also provides row_factory compatibility (returns dict-like rows).
    When created by the pool, holds a pool reference so close() returns
    the connection to the pool instead of actually closing it.
    """

    def __init__(self, conn, pool=None):
        self._conn = conn
        self._pool = pool  # Reference to pool for proper release on close()
        self._closed = False  # Guard against double-close
        self.row_factory = None  # SQLite compatibility
        self._checkout_time = time.time()  # Phase 8.4: Track when connection was checked out

    # NOTE: __del__ finalizer intentionally REMOVED (Phase 8.4b).
    # ThreadedConnectionPool gives the SAME raw connection to the same thread
    # on repeated getconn() calls. Multiple wrappers can share one raw conn.
    # __del__ on stale wrappers would close connections still in active use.
    # Leak recovery is handled by the DBPool-Reaper thread instead.

    def cursor(self):
        # Use standard cursor (returns tuples) for maximum SQLite compat
        # Agents access rows by index (row[0]) and by name (row['col']),
        # so we use a regular cursor and let _coerce_row handle type conversion
        raw_cursor = self._conn.cursor()
        return _PgCursorWrapper(raw_cursor, pg_conn=self._conn)

    def execute(self, sql, params=None):
        """Direct execute on connection (SQLite pattern)."""
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        """Close or return to pool. If pool-managed, return instead of closing."""
        if self._closed:
            return
        self._closed = True
        if self._pool:
            try:
                self._pool.release(self)
            except Exception:
                try:
                    self._conn.close()
                except Exception:
                    pass
        else:
            return self._conn.close()

    @property
    def autocommit(self):
        return self._conn.autocommit

    @autocommit.setter
    def autocommit(self, value):
        self._conn.autocommit = value

    # Pass through any other attributes to the underlying connection
    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Commit/rollback and return connection to pool."""
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        except Exception:
            pass
        self.close()
        return False


def release_connection(conn, pool):
    """
    Release a connection back to the pool or close it.

    Args:
        conn: The connection to release (may be wrapped)
        pool: The pool it came from (None if direct)
    """
    # Unwrap if it's a PostgreSQL wrapper — pool needs the raw connection
    raw_conn = conn._conn if isinstance(conn, _PgConnectionWrapper) else conn

    if pool:
        try:
            pool.release(raw_conn)
        except Exception:
            try:
                raw_conn.close()
            except Exception:
                pass
    else:
        try:
            raw_conn.close()
        except Exception:
            pass


@contextmanager
def db_connection(db_path: str = None, timeout: float = 120.0):
    """
    Context manager for database connections.

    Usage:
        with db_connection() as conn:
            conn.execute("SELECT 1")
            conn.commit()
    """
    conn, pool = get_connection(db_path, timeout)
    try:
        yield conn
    finally:
        release_connection(conn, pool)


@contextmanager
def db_connection_with_retry(db_path: str = None, timeout: float = 120.0,
                              max_retries: int = 3, base_delay: float = 0.5):
    """
    Context manager with automatic retry on database lock.
    Uses exponential backoff between retries.
    """
    import time
    import random

    last_error = None

    for attempt in range(max_retries):
        conn, pool = get_connection(db_path, timeout)
        try:
            yield conn
            return  # Success, exit
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            is_lock_error = (
                "locked" in error_str or
                "deadlock" in error_str or
                "could not serialize" in error_str
            )
            if is_lock_error and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                import logging
                logging.warning(f"[DB] Lock detected, retry {attempt+1}/{max_retries} in {delay:.2f}s")
                time.sleep(delay)
            else:
                raise
        finally:
            release_connection(conn, pool)

    if last_error:
        raise last_error


def execute_with_retry(sql: str, params: tuple = (), db_path: str = None,
                       max_retries: int = 3, retry_delay: float = 0.5):
    """
    Execute SQL with automatic retry on database lock.

    Automatically translates SQL for the current backend.
    """
    import time

    translated_sql = translate_sql(sql)
    if not translated_sql:
        return None  # PRAGMA or other no-op

    for attempt in range(max_retries):
        conn, pool = get_connection(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(translated_sql, params or ())
            conn.commit()
            return cursor
        except Exception as e:
            error_str = str(e).lower()
            is_lock_error = "locked" in error_str or "deadlock" in error_str
            if is_lock_error and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            raise
        finally:
            release_connection(conn, pool)

    return None


def db_write_with_retry(conn, sql, params=None, max_retries=3, base_delay=0.1):
    """
    Execute a write operation with retry on database locked errors.
    Uses exponential backoff with jitter.

    Phase 5.5 — Task 5.5.1: Fix concurrency.
    Phase 8 — Updated for PostgreSQL compatibility.
    """
    import time
    import random
    import logging

    translated_sql = translate_sql(sql)
    if not translated_sql:
        return None  # PRAGMA or other no-op

    for attempt in range(max_retries):
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(translated_sql, params)
            else:
                cursor.execute(translated_sql)
            conn.commit()
            return cursor
        except Exception as e:
            error_str = str(e).lower()
            is_lock_error = (
                "database is locked" in error_str or
                "deadlock" in error_str or
                "could not serialize" in error_str
            )
            if is_lock_error and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                logging.warning(f"[DB] Locked, retry {attempt + 1}/{max_retries} in {delay:.2f}s")
                time.sleep(delay)
            else:
                raise
    return None


def query_one(sql: str, params: tuple = (), db_path: str = None):
    """Execute a query and return the first row."""
    translated_sql = translate_sql(sql)
    if not translated_sql:
        return None
    with db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(translated_sql, params or ())
        return cursor.fetchone()


def query_all(sql: str, params: tuple = (), db_path: str = None):
    """Execute a query and return all rows."""
    translated_sql = translate_sql(sql)
    if not translated_sql:
        return []
    with db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(translated_sql, params or ())
        return cursor.fetchall()
