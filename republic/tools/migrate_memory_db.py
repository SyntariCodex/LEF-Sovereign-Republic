"""
Phase 33.5: Migrate memory.db tables to PostgreSQL republic database.

If memory.db exists, reads all tables and upserts rows into PostgreSQL.
If memory.db does NOT exist, reports that memory is already in republic.db/PostgreSQL.

Usage:
    python tools/migrate_memory_db.py
"""

import os
import sys
import json
import sqlite3
import shutil
import logging
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DB_PATH = os.path.join(BASE_DIR, 'memory.db')
BACKUP_PATH = MEMORY_DB_PATH + '.backup'

logger = logging.getLogger("MemoryMigration")


def migrate_memory_tables():
    """Migrate memory.db tables to PostgreSQL republic database."""

    # 1. Check if memory.db exists
    if not os.path.exists(MEMORY_DB_PATH):
        print(f"[MIGRATION] No memory.db found at {MEMORY_DB_PATH}")
        print("[MIGRATION] Memory data is already in the main republic database.")
        print("[MIGRATION] Nothing to migrate.")
        return {'status': 'skipped', 'reason': 'no memory.db found'}

    # 2. Backup before migration
    print(f"[MIGRATION] Backing up memory.db -> memory.db.backup")
    shutil.copy2(MEMORY_DB_PATH, BACKUP_PATH)

    # 3. Open SQLite connection
    sqlite_conn = sqlite3.connect(MEMORY_DB_PATH, timeout=30)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # 4. Discover tables
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in sqlite_cur.fetchall() if not row[0].startswith('sqlite_')]
    print(f"[MIGRATION] Found tables: {tables}")

    if not tables:
        print("[MIGRATION] No tables to migrate.")
        sqlite_conn.close()
        return {'status': 'skipped', 'reason': 'no tables in memory.db'}

    # 5. Connect to PostgreSQL
    try:
        import psycopg2
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            # Try individual env vars
            pg_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'republic'),
                'user': os.getenv('POSTGRES_USER', 'republic_user'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
            }
            pg_conn = psycopg2.connect(**pg_params)
        else:
            pg_conn = psycopg2.connect(DATABASE_URL)

        pg_cur = pg_conn.cursor()
    except ImportError:
        print("[MIGRATION] psycopg2 not installed. Cannot migrate to PostgreSQL.")
        sqlite_conn.close()
        return {'status': 'error', 'reason': 'psycopg2 not available'}
    except Exception as e:
        print(f"[MIGRATION] PostgreSQL connection failed: {e}")
        sqlite_conn.close()
        return {'status': 'error', 'reason': str(e)}

    # 6. Migrate each table
    results = {}
    for table in tables:
        try:
            # Get column info
            sqlite_cur.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in sqlite_cur.fetchall()]

            # Read all rows
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()

            if not rows:
                results[table] = {'rows': 0, 'status': 'empty'}
                continue

            # Ensure table exists in PostgreSQL (create if needed)
            col_defs = ", ".join(f"{col} TEXT" for col in columns)
            pg_cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} ({col_defs})
            """)

            # Upsert rows — use INSERT ON CONFLICT DO NOTHING if 'id' exists
            placeholders = ", ".join(["%s"] * len(columns))
            col_names = ", ".join(columns)

            if 'id' in columns:
                insert_sql = f"""
                    INSERT INTO {table} ({col_names})
                    VALUES ({placeholders})
                    ON CONFLICT (id) DO NOTHING
                """
            else:
                insert_sql = f"""
                    INSERT INTO {table} ({col_names})
                    VALUES ({placeholders})
                """

            migrated = 0
            for row in rows:
                try:
                    pg_cur.execute(insert_sql, tuple(row))
                    migrated += 1
                except Exception as row_err:
                    logger.debug(f"[MIGRATION] Row skip in {table}: {row_err}")
                    pg_conn.rollback()

            pg_conn.commit()
            results[table] = {'rows': migrated, 'total': len(rows), 'status': 'migrated'}
            print(f"[MIGRATION] {table}: {migrated}/{len(rows)} rows migrated")

        except Exception as e:
            results[table] = {'rows': 0, 'status': 'error', 'error': str(e)}
            print(f"[MIGRATION] {table}: ERROR - {e}")
            pg_conn.rollback()

    # 7. Cleanup
    sqlite_conn.close()
    pg_conn.close()

    print(f"\n[MIGRATION] Complete. Backup at {BACKUP_PATH}")
    print(f"[MIGRATION] Results: {json.dumps(results, indent=2)}")

    return {'status': 'complete', 'tables': results, 'backup': BACKUP_PATH}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = migrate_memory_tables()
    print(f"\nFinal status: {result['status']}")
