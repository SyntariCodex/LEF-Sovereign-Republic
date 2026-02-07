
import sqlite3
import os

DB_PATH = 'fulcrum/republic.db'

def reset_simulation():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    print("⚠️  INITIATING SYSTEM RESET...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # 1. Clear Operational Tables
        tables_to_clear = ['assets', 'trade_queue', 'profit_allocation', 'trade_history', 'signal_history', 'regime_history']
        for table in tables_to_clear:
            try:
                c.execute(f"DELETE FROM {table}")
                print(f"   - Cleared {table}")
            except sqlite3.OperationalError:
                print(f"   - Table {table} not found (skipping)")

        # 2. Reset Stablecoin Buckets
        print("   - Resetting Wallets...")
        c.execute("UPDATE stablecoin_buckets SET balance = 0")
        
        # 3. Inject Seed Capital
        seed_amount = 100000.0
        c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type = 'INJECTION_DAI'", (seed_amount,))
        c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type = 'SNW_LLC_USDC'", (seed_amount,))
        
        print(f"   - 💸 Injected ${seed_amount:,.2f} Seed Capital into INJECTION_DAI & SNW_LLC_USDC")
        
        # 4. Reset Directives/Proposals
        c.execute("DELETE FROM snw_proposals")
        c.execute("DELETE FROM lef_directives")
        print("   - Cleared Governance Logs")

        conn.commit()
        print("✅ SYSTEM RESET COMPLETE. LEF IS REBORN.")
        
    except Exception as e:
        print(f"❌ ERROR DURING RESET: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_simulation()
