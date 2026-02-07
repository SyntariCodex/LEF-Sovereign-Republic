"""
reset_treasury.py

Performs a "Day Zero" reset of the LEF Treasury.
1. Wipes all Asset holdings.
2. Wipes all Trade History (Orders, Queue, PnL).
3. Resets Capital Buckets to Initial State ($10k DAI).

WARNING: DESTRUCTIVE ACTION.
"""

import sqlite3
import os
import sys

# Setup DB Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def wipe_treasury():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"💀 INITIATING DAY ZERO RESET on {DB_PATH}...")
    
    # 1. Wipe Assets
    c.execute("DELETE FROM assets")
    print("✅ Wiped 'assets' table.")
    
    # 2. Wipe Trade History
    c.execute("DELETE FROM trade_queue")
    print("✅ Wiped 'trade_queue' table.")
    
    try:
        c.execute("DELETE FROM orders") # Legacy table check
    except sqlite3.OperationalError: pass
    
    try:
        c.execute("DELETE FROM realized_pnl")
        print("✅ Wiped 'realized_pnl' table.")
    except sqlite3.OperationalError: pass

    try:
        c.execute("DELETE FROM profit_allocation")
        print("✅ Wiped 'profit_allocation' table.")
    except sqlite3.OperationalError: pass
    
    # 3. Reset Buckets
    c.execute("DELETE FROM stablecoin_buckets")
    print("✅ Wiped 'stablecoin_buckets' table.")
    
    # 4. Seed 10k DAI (Paper Money)
    # INJECTION_DAI = Active Trading Capital
    # SNW_LLC_USDC = Retained Profits (Start at 0)
    # IRS_USDT = Tax Reserve (Start at 0)
    
    buckets = [
        ('INJECTION_DAI', 10000.00),
        ('SNW_LLC_USDC', 0.00),
        ('IRS_USDT', 0.00),
        ('OPS_USDC', 0.00)
    ]
    
    c.executemany("INSERT INTO stablecoin_buckets (bucket_type, balance) VALUES (?, ?)", buckets)
    print("✅ Seeded $10,000 DAI into 'INJECTION_DAI'.")
    
    conn.commit()
    conn.close()
    
    print("\n✨ TREASURY RESET COMPLETE. WELCOME TO DAY ZERO.")

if __name__ == "__main__":
    confirm = input("Type 'RESET' to confirm wiping the treasury: ")
    if confirm == 'RESET':
        wipe_treasury()
    else:
        print("Cancelled.")
