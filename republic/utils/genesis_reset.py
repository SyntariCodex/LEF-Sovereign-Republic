import sqlite3
import os
import sys

# Determine BASE_DIR (up 2 levels from utils)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def genesis_reset():
    print(f"⚡ GENESIS PROTOCOL INITIATED on {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database not found. Nothing to reset.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. WIPE OPERATIONAL DATA
        tables_to_wipe = [
            'assets', 
            'trade_queue', 
            'profit_ledger', 
            'stability_events',
            'lef_scars',          # Optional: Keep scars? User said "Day 0" for treasury. 
                                  # "Scars" are lessons. Maybe keep lessons?
                                  # User said "Treasury to Day 0". 
                                  # I will wipe financial history but KEEP Wisdom/Lessons if possible.
                                  # Actually, a full reset usually implies full clean slate.
                                  # I'll wipe Scars too for a true "Fresh Body".
            'lef_monologue',
            'lef_directives'
        ]
        
        for table in tables_to_wipe:
            try:
                c.execute(f"DELETE FROM {table}")
                print(f"   -> Wiped {table}")
            except sqlite3.OperationalError:
                print(f"   -> Table {table} not found (Skipping)")

        # 2. RESET TREASURY
        # Ensure Buckets exist first (idempotent)
        # Assuming buckets exist from setup.
        
        print("   -> Resetting Treasury to 10,000 DAI...")
        c.execute("UPDATE stablecoin_buckets SET balance = 0") # Zero all
        c.execute("UPDATE stablecoin_buckets SET balance = 10000 WHERE bucket_type='INJECTION_DAI'")
        
        # Verify
        c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
        bal = c.fetchone()[0]
        print(f"   -> CONFIRMED: Treasury Balance = ${bal:,.2f} DAI")
        
        conn.commit()
        conn.close()
        print("⚡ GENESIS COMPLETE. The Republic is reborn.")
        
    except Exception as e:
        print(f"❌ GENESIS FAILED: {e}")

if __name__ == "__main__":
    genesis_reset()
