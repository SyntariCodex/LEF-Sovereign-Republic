#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

Migrates all data from republic.db (SQLite) to PostgreSQL while:
- Preserving primary key IDs
- Respecting foreign key relationships (parent tables first)
- Handling SERIAL sequence resets
- Verifying data integrity (especially NUMERIC precision)
- Supporting safe re-runs with TRUNCATE CASCADE
"""

import os
import sys
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from datetime import datetime as dt

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Add republic root to path for .env loading
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / '.env')
except ImportError:
    print("WARNING: python-dotenv not installed. Using environment variables only.")


# Table migration order (parent tables first to satisfy foreign keys)
TABLE_ORDER = [
    # No foreign key dependencies
    'virtual_wallets',
    'library_catalog',
    'projects',
    'skills',
    'competitor_profiles',
    'lef_monologue',
    'conversations',
    'knowledge_stream',
    'consciousness_feed',
    'identity_memory',
    'trading_strategies',
    'claude_state',
    'onchain_identity',
    'system_metrics',
    'circuit_breaker_state',
    'external_observer_reports',

    # Depends on virtual_wallets
    'assets',
    'futures_positions',
    'stablecoin_buckets',

    # Depends on library_catalog
    'mental_models',

    # Depends on projects
    'project_tasks',

    # Depends on skills
    'skill_executions',

    # Depends on competitor_profiles
    'competitor_observations',

    # Depends on lef_monologue
    'intent_queue',

    # Depends on conversations
    'conversation_messages',

    # Depends on futures_positions
    'derivatives_trades',

    # Depends on intent_queue
    'feedback_log',

    # Trade-related tables (complex dependencies)
    'trade_queue',
    'trade_history',

    # Depends on trade_queue
    'profit_allocation',
    'realized_pnl',
    'execution_logs',
]

# Financial tables that need precision verification
FINANCIAL_TABLES = [
    'assets',
    'trade_queue',
    'trade_history',
    'realized_pnl',
    'profit_allocation',
    'stablecoin_buckets',
]


# ---------------------------------------------------------------
# Data Transformations
# ---------------------------------------------------------------
# SQLite is weakly typed. Some columns store Unix epoch floats
# where PostgreSQL expects TIMESTAMP, or integers where PG expects
# BOOLEAN. These transformations fix the mismatch at migration time.

def _epoch_to_timestamp(val):
    """Convert Unix epoch (float/int) to ISO timestamp string, pass through text."""
    if val is None:
        return None
    # Handle bogus literal defaults stored as text in SQLite
    if isinstance(val, str):
        bogus = val.strip().upper()
        if bogus in ('TS', 'CURRENT_TIMESTAMP', 'TIMESTAMP', ''):
            return dt.now().strftime('%Y-%m-%d %H:%M:%S')
        return val  # Already a valid string timestamp
    if isinstance(val, (int, float)):
        try:
            return dt.fromtimestamp(val).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError, OverflowError):
            return None
    return val


def _int_to_bool(val):
    """Convert SQLite 0/1 integer to Python bool for PostgreSQL BOOLEAN."""
    if val is None:
        return None
    if isinstance(val, int):
        return bool(val)
    return val


def _text_date_to_epoch(val):
    """Convert text date like '2026-01-22 08:48:29' to Unix epoch float for NUMERIC column."""
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return dt.fromisoformat(val).timestamp()
        except ValueError:
            return val
    return val


def _strip_nul(val):
    """Remove NUL (0x00) bytes from text values — PostgreSQL rejects them."""
    if isinstance(val, str) and '\x00' in val:
        return val.replace('\x00', '')
    return val


# Column-level transformations keyed by (table, column_index)
# Built dynamically during migration based on schema inspection
TABLE_TRANSFORMS: Dict[str, Dict[int, Any]] = {}


def _build_transforms(sqlite_conn: sqlite3.Connection, pg_conn: psycopg2.extensions.connection, table: str, columns: List[str]):
    """
    Build per-column transformation functions for a table by comparing
    SQLite stored types against PostgreSQL expected types.
    """
    transforms = {}
    pg_cursor = pg_conn.cursor()

    # Get PG column types
    pg_cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    pg_types = {row[0]: row[1] for row in pg_cursor.fetchall()}

    for idx, col in enumerate(columns):
        pg_type = pg_types.get(col, '')

        # Epoch → TIMESTAMP conversion
        if 'timestamp' in pg_type:
            transforms[idx] = _epoch_to_timestamp

        # Integer → BOOLEAN conversion
        elif pg_type == 'boolean':
            transforms[idx] = _int_to_bool

    # Special case: memory_experiences_archive.timestamp is NUMERIC in PG
    # but may have text dates in SQLite
    if table == 'memory_experiences_archive':
        for idx, col in enumerate(columns):
            if col == 'timestamp':
                transforms[idx] = _text_date_to_epoch

    return transforms


def _apply_transforms(data: List[tuple], transforms: Dict[int, Any], strip_nul: bool = False) -> List[tuple]:
    """Apply column-level transformations to all rows."""
    if not transforms and not strip_nul:
        return data

    result = []
    for row in data:
        row_list = list(row)
        # Apply column transforms
        for idx, func in transforms.items():
            if idx < len(row_list):
                row_list[idx] = func(row_list[idx])
        # Strip NUL bytes from all string values
        if strip_nul:
            row_list = [_strip_nul(v) for v in row_list]
        result.append(tuple(row_list))
    return result


def get_sqlite_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Connect to SQLite database."""
    if db_path is None:
        db_path = os.getenv('DB_PATH', str(REPO_ROOT / 'republic.db'))

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_connection(pg_params: Optional[Dict[str, str]] = None) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database."""
    if pg_params is None:
        pg_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'republic'),
            'user': os.getenv('POSTGRES_USER', 'republic_user'),
            'password': os.getenv('POSTGRES_PASSWORD', ''),
        }

    try:
        conn = psycopg2.connect(**pg_params)
        conn.autocommit = False
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        print(f"Connection params: host={pg_params['host']}, port={pg_params['port']}, db={pg_params['database']}, user={pg_params['user']}")
        sys.exit(1)


def get_all_tables(sqlite_conn: sqlite3.Connection) -> List[str]:
    """Get all table names from SQLite, excluding system tables."""
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(sqlite_conn: sqlite3.Connection, table: str) -> List[str]:
    """Get column names for a table."""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_primary_key_column(pg_conn: psycopg2.extensions.connection, table: str) -> Optional[str]:
    """Get the primary key column name for a PostgreSQL table."""
    cursor = pg_conn.cursor()
    cursor.execute("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass
        AND i.indisprimary
    """, (table,))

    result = cursor.fetchone()
    return result[0] if result else None


def reset_sequence(pg_conn: psycopg2.extensions.connection, table: str, pk_column: str):
    """Reset PostgreSQL sequence to max(id) + 1 after inserting with explicit IDs."""
    cursor = pg_conn.cursor()

    # Find the sequence name
    cursor.execute("""
        SELECT pg_get_serial_sequence(%s, %s)
    """, (table, pk_column))

    result = cursor.fetchone()
    if not result or not result[0]:
        return  # No sequence for this column

    sequence_name = result[0]

    # Get max ID and reset sequence
    cursor.execute(f"SELECT COALESCE(MAX({pk_column}), 0) FROM {table}")
    max_id = cursor.fetchone()[0]

    cursor.execute(f"SELECT setval(%s, %s)", (sequence_name, max_id + 1))
    print(f"  └─ Reset sequence {sequence_name} to {max_id + 1}")


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg2.extensions.connection,
    table: str,
    truncate_first: bool = True
) -> Tuple[int, int]:
    """
    Migrate a single table from SQLite to PostgreSQL.
    Returns (sqlite_count, pg_count).
    """
    print(f"\n📦 Migrating table: {table}")

    # Get data from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
    sqlite_count = sqlite_cursor.fetchone()[0]

    if sqlite_count == 0:
        print(f"  └─ Empty table, skipping")
        return 0, 0

    print(f"  ├─ SQLite rows: {sqlite_count}")

    # Get all columns
    columns = get_table_columns(sqlite_conn, table)

    # Fetch all data
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()

    # Convert to tuples (psycopg2 format)
    data = [tuple(row) for row in rows]

    # Build and apply data transformations (epoch→timestamp, int→bool, NUL stripping)
    transforms = _build_transforms(sqlite_conn, pg_conn, table, columns)
    strip_nul = True  # Always strip NUL bytes — PostgreSQL rejects them
    if transforms or strip_nul:
        transform_desc = []
        for idx, func in transforms.items():
            transform_desc.append(f"{columns[idx]}→{func.__name__}")
        if transform_desc:
            print(f"  ├─ Transforms: {', '.join(transform_desc)}")
        data = _apply_transforms(data, transforms, strip_nul=strip_nul)

    # Migrate to PostgreSQL
    pg_cursor = pg_conn.cursor()

    try:
        # Truncate if requested
        if truncate_first:
            pg_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"  ├─ Truncated PostgreSQL table")

        # Prepare INSERT statement for execute_values
        # execute_values expects: "INSERT INTO table (cols) VALUES %s"
        # with a single %s placeholder that it expands into batched VALUES
        cols_str = ', '.join(columns)
        insert_sql = f"INSERT INTO {table} ({cols_str}) VALUES %s"

        # Build template for execute_values: "(%s, %s, ...)" per row
        template = '(' + ', '.join(['%s'] * len(columns)) + ')'

        # Batch insert using execute_values (much faster)
        if data:
            # Use page_size for very large tables
            page_size = 1000 if len(data) > 10000 else len(data)
            execute_values(pg_cursor, insert_sql, data, template=template, page_size=page_size)
            print(f"  ├─ Inserted {len(data)} rows")

        # Reset sequence if table has a primary key
        pk_column = get_primary_key_column(pg_conn, table)
        if pk_column:
            reset_sequence(pg_conn, table, pk_column)

        # Verify count
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cursor.fetchone()[0]

        # Commit
        pg_conn.commit()

        status = "✓" if pg_count == sqlite_count else "⚠"
        print(f"  └─ {status} PostgreSQL rows: {pg_count}")

        return sqlite_count, pg_count

    except Exception as e:
        pg_conn.rollback()
        print(f"  └─ ✗ ERROR: {e}")
        return sqlite_count, 0


def verify_financial_precision(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg2.extensions.connection,
    table: str,
    sample_size: int = 5
):
    """
    Verify that NUMERIC values are preserved correctly.
    Compares a sample of rows between SQLite and PostgreSQL.
    """
    print(f"\n🔍 Verifying financial precision for: {table}")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Get primary key
    pk_column = get_primary_key_column(pg_conn, table)
    if not pk_column:
        print(f"  └─ No primary key, skipping verification")
        return

    # Get sample IDs
    sqlite_cursor.execute(f"SELECT {pk_column} FROM {table} ORDER BY {pk_column} LIMIT {sample_size}")
    sample_ids = [row[0] for row in sqlite_cursor.fetchall()]

    if not sample_ids:
        print(f"  └─ No data to verify")
        return

    # Compare each row
    columns = get_table_columns(sqlite_conn, table)
    cols_str = ', '.join(columns)

    mismatches = []
    for sample_id in sample_ids:
        # Get from SQLite
        sqlite_cursor.execute(f"SELECT {cols_str} FROM {table} WHERE {pk_column} = ?", (sample_id,))
        sqlite_row = dict(zip(columns, sqlite_cursor.fetchone()))

        # Get from PostgreSQL
        pg_cursor.execute(f"SELECT {cols_str} FROM {table} WHERE {pk_column} = %s", (sample_id,))
        pg_row = dict(zip(columns, pg_cursor.fetchone()))

        # Compare numeric values
        for col in columns:
            sqlite_val = sqlite_row[col]
            pg_val = pg_row[col]

            # Convert to Decimal for comparison
            if sqlite_val is not None and pg_val is not None:
                try:
                    sqlite_decimal = Decimal(str(sqlite_val))
                    pg_decimal = Decimal(str(pg_val))

                    if sqlite_decimal != pg_decimal:
                        mismatches.append({
                            'id': sample_id,
                            'column': col,
                            'sqlite': sqlite_decimal,
                            'postgres': pg_decimal
                        })
                except (ValueError, TypeError, ArithmeticError):
                    # Not a numeric column or conversion error, skip
                    pass

    if mismatches:
        print(f"  └─ ⚠ Found {len(mismatches)} precision mismatches:")
        for mm in mismatches[:3]:  # Show first 3
            print(f"      {mm['column']} (id={mm['id']}): SQLite={mm['sqlite']} vs PG={mm['postgres']}")
    else:
        print(f"  └─ ✓ All sampled values match (n={len(sample_ids)})")


def migrate(sqlite_path: Optional[str] = None, pg_params: Optional[Dict[str, str]] = None, truncate_first: bool = True):
    """Migrate all data from SQLite to PostgreSQL."""

    print("=" * 70)
    print("  SQLite → PostgreSQL Migration")
    print("=" * 70)

    # Connect to databases
    print("\n🔌 Connecting to databases...")
    sqlite_conn = get_sqlite_connection(sqlite_path)
    pg_conn = get_pg_connection(pg_params)
    print("  ✓ Connected to SQLite and PostgreSQL")

    # Get all tables
    all_tables = get_all_tables(sqlite_conn)
    print(f"\n📊 Found {len(all_tables)} tables in SQLite")

    # Determine migration order
    ordered_tables = []
    for table in TABLE_ORDER:
        if table in all_tables:
            ordered_tables.append(table)
            all_tables.remove(table)

    # Add any remaining tables (not in our predefined order)
    if all_tables:
        print(f"\n⚠ Warning: {len(all_tables)} tables not in predefined order:")
        for table in all_tables:
            print(f"  - {table}")
        ordered_tables.extend(all_tables)

    # Migrate each table
    print(f"\n🚀 Starting migration of {len(ordered_tables)} tables...")
    results = {}

    for table in ordered_tables:
        try:
            sqlite_count, pg_count = migrate_table(sqlite_conn, pg_conn, table, truncate_first)
            results[table] = (sqlite_count, pg_count)
        except Exception as e:
            print(f"\n✗ FATAL ERROR migrating {table}: {e}")
            results[table] = (0, 0)

    # Verify financial tables
    print("\n" + "=" * 70)
    print("  Financial Precision Verification")
    print("=" * 70)

    for table in FINANCIAL_TABLES:
        if table in results and results[table][0] > 0:
            try:
                verify_financial_precision(sqlite_conn, pg_conn, table)
            except Exception as e:
                print(f"  └─ ✗ Verification failed: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("  Migration Summary")
    print("=" * 70)
    print(f"\n{'Table':<30} {'SQLite':<12} {'PostgreSQL':<12} {'Status':<10}")
    print("-" * 70)

    total_sqlite = 0
    total_pg = 0
    mismatched = []

    for table in ordered_tables:
        if table in results:
            sqlite_count, pg_count = results[table]
            total_sqlite += sqlite_count
            total_pg += pg_count

            if sqlite_count == pg_count:
                status = "✓ OK" if sqlite_count > 0 else "EMPTY"
            else:
                status = "✗ MISMATCH"
                mismatched.append(table)

            print(f"{table:<30} {sqlite_count:<12} {pg_count:<12} {status:<10}")

    print("-" * 70)
    print(f"{'TOTAL':<30} {total_sqlite:<12} {total_pg:<12}")

    if mismatched:
        print(f"\n⚠ WARNING: {len(mismatched)} tables have mismatched counts:")
        for table in mismatched:
            print(f"  - {table}")
    else:
        print("\n✓ SUCCESS: All tables migrated with matching counts!")

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "=" * 70)
    print("  Migration Complete")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrate SQLite data to PostgreSQL')
    parser.add_argument('--sqlite-path', help='Path to SQLite database (default: from .env or republic.db)')
    parser.add_argument('--no-truncate', action='store_true', help='Do not truncate tables before inserting')
    parser.add_argument('--pg-host', help='PostgreSQL host (default: from .env)')
    parser.add_argument('--pg-port', type=int, help='PostgreSQL port (default: from .env)')
    parser.add_argument('--pg-db', help='PostgreSQL database (default: from .env)')
    parser.add_argument('--pg-user', help='PostgreSQL user (default: from .env)')
    parser.add_argument('--pg-password', help='PostgreSQL password (default: from .env)')

    args = parser.parse_args()

    # Build pg_params if any CLI args provided
    pg_params = None
    if any([args.pg_host, args.pg_port, args.pg_db, args.pg_user, args.pg_password]):
        pg_params = {
            'host': args.pg_host or os.getenv('POSTGRES_HOST', 'localhost'),
            'port': args.pg_port or int(os.getenv('POSTGRES_PORT', 5432)),
            'database': args.pg_db or os.getenv('POSTGRES_DB', 'republic'),
            'user': args.pg_user or os.getenv('POSTGRES_USER', 'republic_user'),
            'password': args.pg_password or os.getenv('POSTGRES_PASSWORD', ''),
        }

    try:
        migrate(
            sqlite_path=args.sqlite_path,
            pg_params=pg_params,
            truncate_first=not args.no_truncate
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
