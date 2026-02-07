"""
VERIFICATION PROTOCOL: REGRESSION TEST
Objective: Prove core RSI trading logic still functions.
"""
import sys
import os
import time
import redis
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from departments.Dept_Wealth.agent_coin_mgr import AgentStrategist

# Explicit DB Path (Hardcoded for Safety)
DB_PATH = "/Users/zmoore-macbook/Desktop/LEF Ai/fulcrum/republic.db"

def verify_rsi_trading():
    print("\n--- Verifying Core RSI Logic (Regression Check) ---")
    
    # 1. Setup Mock Market
    try:
        r = redis.Redis(decode_responses=True)
        r.ping()
    except (redis.RedisError, ConnectionError):
        print("❌ Redis Offline. Test Ignored.")
        return False
        
    r.set("rsi:TEST_COIN", 20.0)
    r.set("price:TEST_COIN", 100.0)
    
    # 2. Init Strategist with explicit path
    strat = AgentStrategist(db_path=DB_PATH)
    strat.watchlist = ['TEST_COIN']
    print(f"Mock Market Set: TEST_COIN RSI=20.0. DB: {DB_PATH}")
    
    # 3. Clean Queue
    conn = sqlite3.connect(strat.db_path)
    c = conn.cursor()
    c.execute("DELETE FROM trade_queue WHERE asset='TEST_COIN'")
    conn.commit()
    conn.close()
    
    # 4. Trigger Evaluation
    print("Triggering evaluate_market()...")
    strat.evaluate_market()
    
    # 5. Check Queue
    conn = sqlite3.connect(strat.db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM trade_queue WHERE asset='TEST_COIN' AND action='BUY'")
    order = c.fetchone()
    conn.close()
    
    if order:
        print(f"✅ Regression Passed: Order Generated for TEST_COIN. ID={order[0]}")
        return True
    else:
        print("❌ Regression Failed: No Order Generated.")
        return False

if __name__ == "__main__":
    if verify_rsi_trading():
        sys.exit(0)
    else:
        sys.exit(1)
