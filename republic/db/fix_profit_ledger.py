"""
Fix profit_ledger.last_updated — the one that was missed from fix_timestamps.py.
This was the original error Z saw. The psql command failed (not in PATH),
and fix_timestamps.py didn't include it. This script fixes it.

Run: python3 republic/db/fix_profit_ledger.py
"""

import os
import sys

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

conn_params = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'republic'),
    'user': os.getenv('POSTGRES_USER', 'republic_user'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

try:
    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Check current type
    cur.execute("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'profit_ledger' AND column_name = 'last_updated'
    """)
    row = cur.fetchone()

    if not row:
        print("  profit_ledger.last_updated column not found")
        sys.exit(1)

    if row[0] != 'text':
        print(f"  profit_ledger.last_updated is already {row[0]} — no fix needed")
    else:
        cur.execute("""
            ALTER TABLE profit_ledger
            ALTER COLUMN last_updated TYPE TIMESTAMP
            USING CASE
                WHEN last_updated IS NULL OR TRIM(last_updated) = '' THEN NULL
                ELSE last_updated::TIMESTAMP
            END
        """)
        cur.execute("ALTER TABLE profit_ledger ALTER COLUMN last_updated SET DEFAULT NOW()")
        print("  FIXED profit_ledger.last_updated — TEXT → TIMESTAMP")

    cur.close()
    conn.close()
    print("  Done.")

except psycopg2.OperationalError as e:
    print(f"  Cannot connect: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
