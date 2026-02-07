#!/usr/bin/env python3
"""
Arena Trading Reset & Diagnostic Tool

This script:
1. Clears all synthetic simulation data
2. Resets balances to realistic $8K starting capital
3. Provides diagnostic output on what was cleared

Run from: republic/ directory
"""

import sqlite3
import os
import sys

# Get correct DB path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

print(f"[RESET] Database: {DB_PATH}")

if not os.path.exists(DB_PATH):
    print(f"[RESET] ❌ Database not found: {DB_PATH}")
    sys.exit(1)

def reset_arena_simulation():
    """
    Full reset for Arena trading simulation.
    Sets realistic starting capital and clears all synthetic data.
    """
    print("\n" + "="*60)
    print("[RESET] 🔄 ARENA TRADING RESET")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # --- DIAGNOSTIC: Show current state ---
    print("\n📊 CURRENT STATE (Before Reset):")
    
    # Assets
    c.execute("SELECT COUNT(*), SUM(value_usd) FROM assets WHERE quantity > 0")
    row = c.fetchone()
    print(f"  Assets: {row[0] or 0} positions, Total Value: ${row[1] or 0:,.2f}")
    
    # Stablecoins
    c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
    for bucket, balance in c.fetchall():
        print(f"  {bucket}: ${balance:,.2f}")
    
    # Trade queue
    c.execute("SELECT COUNT(*) FROM trade_queue")
    print(f"  Trade Queue: {c.fetchone()[0]} items")
    
    # Profit allocations
    c.execute("SELECT COUNT(*), SUM(realized_gain_usd) FROM profit_allocation")
    row = c.fetchone()
    print(f"  Profit Allocations: {row[0] or 0} records, Total: ${row[1] or 0:,.2f}")
    
    # --- CLEAR EVERYTHING ---
    print("\n🧹 CLEARING DATA...")
    
    tables_to_clear = [
        ('trade_queue', 'Trade Queue'),
        ('trade_history', 'Trade History'),
        ('profit_allocation', 'Profit Allocations'),
        ('realized_pnl', 'Realized P&L'),
        ('assets', 'Assets/Holdings'),
        ('memory_experiences', 'Memory Experiences'),
        ('skills', 'Skills Library'),
    ]
    
    for table, desc in tables_to_clear:
        try:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            c.execute(f"DELETE FROM {table}")
            print(f"  ✅ {desc}: Cleared {count} records")
        except sqlite3.Error as e:
            print(f"  ⚠️ {desc}: {e}")
    
    # --- RESET STABLECOIN BUCKETS ---
    print("\n💰 RESETTING BALANCES...")
    
    # Starting Capital: $8,000 DAI (as per Constitution)
    STARTING_CAPITAL = 8000.00
    
    c.execute("UPDATE stablecoin_buckets SET balance = 0")
    c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type = 'INJECTION_DAI'", 
              (STARTING_CAPITAL,))
    
    # Verify
    c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
    for bucket, balance in c.fetchall():
        print(f"  {bucket}: ${balance:,.2f}")
    
    conn.commit()
    
    # --- FINAL STATE ---
    print("\n✅ RESET COMPLETE")
    print(f"  Starting Capital: ${STARTING_CAPITAL:,.2f} INJECTION_DAI")
    print(f"  Assets: 0 (clean slate)")
    print(f"  Trade History: 0")
    print("="*60)
    
    conn.close()
    return True


def diagnose_without_reset():
    """
    Just show diagnostics without clearing anything.
    """
    print("\n" + "="*60)
    print("[DIAGNOSE] 🔍 TRADING DATA DIAGNOSTIC")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Most absurd trades
    print("\n🚨 Largest Profit Allocations (likely bugs):")
    c.execute("""
        SELECT id, asset, realized_gain_usd, irs_allocation 
        FROM profit_allocation 
        ORDER BY realized_gain_usd DESC 
        LIMIT 5
    """)
    for row in c.fetchall():
        print(f"  ID {row[0]}: {row[1]} = ${row[2]:,.2f}")
    
    # Trade queue with absurd amounts
    print("\n🚨 Trade Queue - Largest Amounts:")
    c.execute("""
        SELECT id, asset, action, amount, price, (amount * COALESCE(price, 1)) as value
        FROM trade_queue 
        ORDER BY amount DESC 
        LIMIT 5
    """)
    for row in c.fetchall():
        print(f"  ID {row[0]}: {row[2]} {row[3]:,.2f} {row[1]} @ ${row[4] or 0:.4f} = ${row[5]:,.2f}")
    
    # Assets with absurd quantities
    print("\n🚨 Assets - Largest Quantities:")
    c.execute("""
        SELECT symbol, quantity, value_usd 
        FROM assets 
        ORDER BY quantity DESC 
        LIMIT 5
    """)
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]:,.2f} tokens = ${row[2]:,.2f}")
    
    conn.close()
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Arena Trading Reset Tool")
    parser.add_argument("--diagnose", action="store_true", 
                       help="Only show diagnostics, don't reset")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation prompt")
    
    args = parser.parse_args()
    
    if args.diagnose:
        diagnose_without_reset()
    else:
        if not args.force:
            print("\n⚠️  WARNING: This will DELETE all trading data!")
            confirm = input("Type 'RESET' to confirm: ")
            if confirm != 'RESET':
                print("Aborted.")
                sys.exit(0)
        
        reset_arena_simulation()
