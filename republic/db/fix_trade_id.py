"""
Phase 8.2 Hotfix — Fix realized_pnl.trade_id from TEXT to INTEGER.

The JOIN between realized_pnl.trade_id (TEXT) and trade_queue.id (INTEGER)
fails in PostgreSQL: "operator does not exist: text = integer"

Run: python3 republic/db/fix_trade_id.py
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


def run():
    conn_params = {
        'host': os.environ.get('POSTGRES_HOST', 'localhost'),
        'port': int(os.environ.get('POSTGRES_PORT', 5432)),
        'dbname': os.environ.get('POSTGRES_DB', 'republic'),
        'user': os.environ.get('POSTGRES_USER', 'republic_user'),
        'password': os.environ.get('POSTGRES_PASSWORD', ''),
    }

    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    print("Fixing realized_pnl.trade_id: TEXT → INTEGER...")

    cur.execute("""
        ALTER TABLE realized_pnl
        ALTER COLUMN trade_id TYPE INTEGER
        USING CASE
            WHEN trade_id IS NULL THEN NULL
            WHEN trade_id = '' THEN NULL
            ELSE trade_id::INTEGER
        END
    """)

    print("✓ realized_pnl.trade_id is now INTEGER")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
