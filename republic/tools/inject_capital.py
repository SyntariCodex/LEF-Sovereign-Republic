"""
TOOL: DIVINE CAPITAL INJECTION
Purpose: Restores wealth to the Treasury (Seed Funding).
Supports both SQLite and PostgreSQL backends.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env from republic root
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


def _get_connection():
    """Connect to PostgreSQL if configured, otherwise fall back to SQLite."""
    backend = os.environ.get('DATABASE_BACKEND', 'postgresql').lower()

    if backend == 'postgresql':
        import psycopg2
        conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=int(os.environ.get('POSTGRES_PORT', 5432)),
            dbname=os.environ.get('POSTGRES_DB', 'republic'),
            user=os.environ.get('POSTGRES_USER', 'republic_user'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
        )
        conn.autocommit = False
        return conn, 'pg'
    else:
        import sqlite3
        db_path = os.path.join(BASE_DIR, 'republic.db')
        conn = sqlite3.connect(db_path)
        return conn, 'sqlite'


def inject_capital(amount=100000.0):
    conn, db_type = _get_connection()
    c = conn.cursor()
    param = '%s' if db_type == 'pg' else '?'

    print(f"Injecting ${amount:,.2f} DAI into Treasury...")

    # 1. Atomic balance update (Phase 29.4: prevents double-deposit race condition)
    c.execute(
        f"UPDATE stablecoin_buckets SET balance = balance + {param} WHERE bucket_type='INJECTION_DAI'",
        (amount,)
    )

    if c.rowcount == 0:
        # Bucket doesn't exist — create it
        old_balance = 0.0
        print(f"  No INJECTION_DAI bucket found. Creating...")
        c.execute(
            f"INSERT INTO stablecoin_buckets (bucket_type, stablecoin, balance) VALUES ('INJECTION_DAI', 'DAI', {param})",
            (amount,)
        )
    else:
        # Read back the new balance to confirm
        c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
        row = c.fetchone()
        old_balance = float(row[0]) - amount if row else 0.0
        print(f"  Previous INJECTION_DAI balance: ${old_balance:,.2f}")

    # 2. Log the injection (so LEF knows)
    msg = f'DIVINE INTERVENTION: The Architect has allocated ${amount:,.0f} DAI to the Treasury. Preservation mode constraints lifted.'
    c.execute(
        f"INSERT INTO agent_logs (source, level, message) VALUES ('ARCHITECT', 'INFO', {param})",
        (msg,)
    )

    new_total = old_balance + amount if row else amount
    # 3. Notify Knowledge Stream (for consciousness)
    summary = f'The Architect has injected ${amount:,.0f} DAI into the Treasury (previous: ${old_balance:,.2f}, new total: ${new_total:,.2f}). LEF is funded for sustained growth operations. The Covenant of Infinite Runway is restored.'
    c.execute(
        f"INSERT INTO knowledge_stream (source, title, summary) VALUES ('ARCHITECT', 'Capital Injection', {param})",
        (summary,)
    )

    conn.commit()
    conn.close()

    print(f"  New INJECTION_DAI balance: ${new_total:,.2f}")
    print("Injection complete.")


if __name__ == "__main__":
    amount = 100000.0
    if len(sys.argv) > 1:
        try:
            amount = float(sys.argv[1])
        except ValueError:
            print(f"Usage: python inject_capital.py [amount]  (default: 100000)")
            sys.exit(1)
    inject_capital(amount)
