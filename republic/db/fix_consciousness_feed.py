"""
Fix the one remaining column: consciousness_feed.timestamp
The old default (NOW()::TEXT) blocks the type conversion.
Drop the default first, convert, then set the correct default.
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

    # Step 1: Drop the old TEXT default (NOW()::TEXT)
    cur.execute("ALTER TABLE consciousness_feed ALTER COLUMN timestamp DROP DEFAULT")
    print("  Dropped old default (NOW()::TEXT)")

    # Step 2: Convert TEXT -> TIMESTAMP
    cur.execute("""
        ALTER TABLE consciousness_feed
        ALTER COLUMN timestamp TYPE TIMESTAMP
        USING CASE
            WHEN timestamp IS NULL OR TRIM(timestamp) = '' THEN NULL
            ELSE timestamp::TIMESTAMP
        END
    """)
    print("  Converted TEXT -> TIMESTAMP")

    # Step 3: Set correct default
    cur.execute("ALTER TABLE consciousness_feed ALTER COLUMN timestamp SET DEFAULT NOW()")
    print("  Set default to NOW()")

    print("\n  FIXED consciousness_feed.timestamp")

    cur.close()
    conn.close()
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)
