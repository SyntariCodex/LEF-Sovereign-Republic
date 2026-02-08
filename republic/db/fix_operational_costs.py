"""
Phase 8.1 Hotfix — Create operational_costs table in live PostgreSQL.

This table was defined in schema_update_costs.py (SQLite) but never added to pg_setup.py.
The Da'at cycle queries it for runway calculation.

Run: python3 republic/db/fix_operational_costs.py
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

    print("Creating operational_costs table...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS operational_costs (
            id SERIAL PRIMARY KEY,
            cost_type TEXT,
            cost_usd REAL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    """)

    # Verify
    cur.execute("SELECT COUNT(*) FROM operational_costs")
    count = cur.fetchone()[0]
    print(f"✓ operational_costs table ready ({count} existing rows)")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
