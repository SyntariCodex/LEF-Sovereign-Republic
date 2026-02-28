"""
Emergency Stop Diagnostic & Reset Tool
=======================================
Run this on your machine from the republic/ directory:

    python clear_emergency_stop.py

It will:
  1. Show current portfolio value, high watermark, and drawdown
  2. Show current emergency stop status in Redis
  3. Check TableMaintenance thread heartbeat
  4. Ask you to confirm before clearing the stop
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # --- Redis check ---
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        redis_ok = True
    except Exception as e:
        print(f"[!] Redis not reachable: {e}")
        redis_ok = False
        r = None

    if redis_ok:
        stop_flag = r.get("system:emergency_stop")
        print("=" * 60)
        print(f"  EMERGENCY STOP STATUS:  {'ACTIVE' if stop_flag else 'CLEAR'}")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EMERGENCY STOP STATUS:  UNKNOWN (Redis unreachable)")
        print("=" * 60)

    # --- Database check ---
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
        import psycopg2

        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Portfolio NAV
        print("\n--- Portfolio Status ---")
        cur.execute("""
            SELECT key, value FROM system_state
            WHERE key IN ('high_watermark', 'portfolio_nav', 'circuit_breaker_level',
                          'emergency_stop_reason', 'last_nav_update')
            ORDER BY key
        """)
        rows = cur.fetchall()
        for key, val in rows:
            print(f"  {key}: {val}")

        # Current holdings value
        cur.execute("""
            SELECT symbol, quantity, value_usd
            FROM portfolio_holdings
            WHERE value_usd > 0
            ORDER BY value_usd DESC
            LIMIT 10
        """)
        holdings = cur.fetchall()
        if holdings:
            print("\n--- Top Holdings ---")
            total = 0
            for sym, qty, val in holdings:
                print(f"  {sym}: qty={qty}, value=${val:.2f}")
                total += float(val)
            print(f"  TOTAL: ${total:.2f}")
        else:
            print("\n  No holdings with value > 0 found")

        # Stablecoin buckets
        cur.execute("""
            SELECT bucket_name, balance_usd FROM stablecoin_buckets
            ORDER BY balance_usd DESC
        """)
        buckets = cur.fetchall()
        if buckets:
            print("\n--- Stablecoin Buckets ---")
            for name, bal in buckets:
                print(f"  {name}: ${float(bal):.2f}")

        # Recent trades
        cur.execute("""
            SELECT status, COUNT(*) FROM trade_queue
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY status ORDER BY COUNT(*) DESC
        """)
        trade_stats = cur.fetchall()
        if trade_stats:
            print("\n--- Trade Status (last 7 days) ---")
            for status, count in trade_stats:
                print(f"  {status}: {count}")

        # Drawdown calc
        cur.execute("SELECT value FROM system_state WHERE key = 'high_watermark'")
        hw_row = cur.fetchone()
        cur.execute("SELECT value FROM system_state WHERE key = 'portfolio_nav'")
        nav_row = cur.fetchone()
        if hw_row and nav_row:
            try:
                hw = float(hw_row[0])
                nav = float(nav_row[0])
                dd = ((nav - hw) / hw) * 100 if hw > 0 else 0
                print(f"\n--- Drawdown Calculation ---")
                print(f"  High Watermark: ${hw:.2f}")
                print(f"  Current NAV:    ${nav:.2f}")
                print(f"  Drawdown:       {dd:.2f}%")
                if dd <= -20:
                    print(f"  [!] Still below -20% threshold — stop would re-trigger!")
                else:
                    print(f"  [OK] Above -20% threshold — safe to clear")
            except (ValueError, TypeError):
                pass

        # TableMaintenance heartbeat
        print("\n--- TableMaintenance Thread ---")
        cur.execute("""
            SELECT value FROM system_state
            WHERE key = 'heartbeat_TableMaintenance'
        """)
        hb_row = cur.fetchone()
        if hb_row:
            print(f"  Last heartbeat: {hb_row[0]}")
        else:
            print("  No heartbeat record found")

        conn.close()

    except Exception as e:
        print(f"\n[!] Database check failed: {e}")

    # --- Offer to clear ---
    print("\n" + "=" * 60)
    response = input("Clear the emergency stop? (yes/no): ").strip().lower()
    if response in ("yes", "y"):
        if redis_ok:
            r.delete("system:emergency_stop")
            print("[OK] Emergency stop CLEARED in Redis")

            # Also try to reset circuit breaker level in DB
            try:
                conn = psycopg2.connect(db_url)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO system_state (key, value, updated_at)
                    VALUES ('circuit_breaker_level', '0', NOW())
                    ON CONFLICT (key) DO UPDATE SET value = '0', updated_at = NOW()
                """)
                cur.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category, signal_weight)
                    VALUES ('Architect', 'Emergency stop manually cleared by Architect Z. Portfolio review completed. Resuming operations.', 'emergency_cleared', 1.0)
                """)
                conn.commit()
                conn.close()
                print("[OK] Circuit breaker level reset to 0")
                print("[OK] Consciousness feed notified — LEF will know you cleared it")
            except Exception as e:
                print(f"[!] DB update failed (Redis cleared though): {e}")
        else:
            print("[!] Cannot clear — Redis not reachable")
            print("    Try manually: redis-cli DEL system:emergency_stop")
    else:
        print("Cancelled. Emergency stop remains active.")
        print("To clear manually: redis-cli DEL system:emergency_stop")


if __name__ == "__main__":
    main()
