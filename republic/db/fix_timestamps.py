"""
Phase 8.1 Hotfix — Fix all TEXT columns that should be TIMESTAMP in live PostgreSQL.

pg_setup.py inherited some TEXT columns from SQLite where timestamps were stored as strings.
PostgreSQL is type-strict: comparing TEXT to NOW() or TIMESTAMP fails.
This script converts them all in the live database.

Run: python3 republic/db/fix_timestamps.py
"""

import os
import sys

# Load .env from project root
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Every TEXT column that should be TIMESTAMP
# Format: (table, column, default)
FIXES = [
    ("agent_rankings",            "last_updated",  "NOW()"),
    ("sabbath_reflections",       "timestamp",     "NOW()"),
    ("conversations",             "started_at",    None),
    ("conversations",             "ended_at",      None),
    ("conversation_messages",     "timestamp",     "NOW()"),
    ("moltbook_comment_responses","responded_at",  None),
    ("moltbook_mention_responses","responded_at",  None),
    ("moltbook_posted_content",   "posted_at",     None),
    ("consciousness_feed",        "timestamp",     "NOW()"),
    ("market_universe",           "first_seen",    None),
]


def run():
    conn_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'republic'),
        'user': os.getenv('POSTGRES_USER', 'republic_user'),
        'password': os.getenv('POSTGRES_PASSWORD', '')
    }

    print("=" * 60)
    print("LEF Phase 8.1 — TEXT → TIMESTAMP Migration")
    print("=" * 60)
    print(f"Connecting to {conn_params['host']}:{conn_params['port']}/{conn_params['database']}...")

    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    fixed = 0
    skipped = 0
    errors = 0

    for table, column, default in FIXES:
        try:
            # Check if column exists and is currently TEXT
            cur.execute("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            row = cur.fetchone()

            if not row:
                print(f"  SKIP  {table}.{column} — column not found")
                skipped += 1
                continue

            current_type = row[0]
            if current_type != 'text':
                print(f"  OK    {table}.{column} — already {current_type}")
                skipped += 1
                continue

            # Convert TEXT → TIMESTAMP
            # USING clause handles the cast; empty strings become NULL
            cast_expr = f"""
                CASE
                    WHEN {column} IS NULL OR TRIM({column}) = '' THEN NULL
                    ELSE {column}::TIMESTAMP
                END
            """
            alter_sql = f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP USING ({cast_expr})'
            cur.execute(alter_sql)

            # Set default if specified
            if default:
                cur.execute(f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {default}')

            print(f"  FIXED {table}.{column} — TEXT → TIMESTAMP")
            fixed += 1

        except Exception as e:
            print(f"  ERROR {table}.{column} — {e}")
            errors += 1

    print()
    print("=" * 60)
    print(f"Results: {fixed} fixed, {skipped} skipped, {errors} errors")
    print("=" * 60)

    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        run()
    except psycopg2.OperationalError as e:
        print(f"\nCannot connect to PostgreSQL: {e}")
        print("Make sure PostgreSQL is running: brew services start postgresql@16")
        sys.exit(1)
