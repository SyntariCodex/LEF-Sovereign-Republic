import os
import sys

# Phase 37: Use env-based DB path (TLS-03) + db_connection (TLS-05)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # republic/
sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


def seed_wealth():
    print(f"[SEED] Connecting to Database: {DB_PATH}")

    # Phase 37: Use db_connection context manager — no connection leak (TLS-05)
    with db_connection(DB_PATH) as conn:
        c = conn.cursor()

        # 1. Ensure Table Exists
        c.execute('''CREATE TABLE IF NOT EXISTS stablecoin_buckets
                     (id INTEGER PRIMARY KEY,
                      bucket_type TEXT UNIQUE,
                      stablecoin TEXT,
                      purpose TEXT,
                      balance REAL DEFAULT 0,
                      interest_rate REAL DEFAULT 0,
                      last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

        # 2. Insert Default Buckets (Safe Insert)
        buckets = [
            ('IRS_USDT', 'USDT', 'Tax Payments - IRS Compliance', 0.0, 0.0),
            ('SNW_LLC_USDC', 'USDC', 'SNW/LLC Operations - Interest Bearing', 0.0, 0.04),
            ('INJECTION_DAI', 'DAI', 'Capital Injections - DeFi Native', 10000.0, 0.03)
        ]

        print("[SEED] Injecting Buckets...")
        try:
            from db.db_helper import ignore_insert_sql
            sql = ignore_insert_sql('stablecoin_buckets',
                                    ['bucket_type', 'stablecoin', 'purpose', 'balance', 'interest_rate'],
                                    'bucket_type')
        except ImportError:
            sql = "INSERT OR IGNORE INTO stablecoin_buckets (bucket_type, stablecoin, purpose, balance, interest_rate) VALUES (?, ?, ?, ?, ?)"

        for b in buckets:
            c.execute(sql, b)

            # Force update balance for Injection, just in case it existed but was 0
            if b[0] == 'INJECTION_DAI':
                c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type = ?",
                          (10000.0, 'INJECTION_DAI'))

        conn.commit()

        # 3. Verify
        c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
        rows = c.fetchall()
        print("[SEED] Current Balances:")
        for r in rows:
            print(f"   - {r[0]}: ${r[1]:.2f}")

    print("[SEED] Wealth Injection Complete.")

if __name__ == "__main__":
    seed_wealth()
