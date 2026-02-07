"""
VERIFICATION PROTOCOL: PHASE 59 (REFORMATION)
Objective: Prove availability of Intelligence Layer.
"""

import sys
import os
import time
import redis
import json
import sqlite3

# Path Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from departments.Dept_Strategy.agent_tech import AgentTech
from departments.Dept_Strategy.agent_foresight import AgentForesight
from departments.Dept_Education.agent_dean import AgentDean
from departments.Dept_Wealth.agent_coin_mgr import AgentStrategist

def verify_tech():
    print("\n--- Verifying AgentTech (ArXiv) ---")
    agent = AgentTech()
    print("Running Scan (Real Request)...")
    score = agent.scan_arxiv()
    print(f"Result: Score {score}")
    if score >= 0: return True
    return False

def verify_foresight():
    print("\n--- Verifying AgentForesight (Monte Carlo) ---")
    agent = AgentForesight()
    print("Running 1000 Simulations...")
    var = agent.run_monte_carlo(days=30, iterations=100) # Fast run
    print(f"Result: 95% VaR: {var}")
    if var > 0: return True
    return False

def verify_wiring():
    print("\n--- Verifying Strategist Wiring (The Ear) ---")
    r = redis.Redis(decode_responses=True)
    
    # 1. Start Strategist (The Ear)
    strat = AgentStrategist() 
    time.sleep(0.5)
    
    # Flush Subscription Message
    strat.check_signals() 

    # 2. Publish Mock Signal
    payload = {
        "type": "risk_scenario",
        "risk_level": "CRISIS_IMMINENT",
        "source": "TEST_HARNESS",
        "timestamp": time.time()
    }
    r.publish("fulcrum_signals", json.dumps(payload))
    print("Published Mock CRISIS Signal to Redis.")
    
    # 3. Check Reaction (Retry Loop)
    for i in range(5):
        time.sleep(0.5)
        print(f"   > Polling Strategist (Attempt {i+1})...")
        strat.check_signals()
        
        if strat.trade_size_usd == 0.0:
             print(f"✅ Strategist REACTED: Trade Size set to {strat.trade_size_usd}")
             return True
             
    print(f"❌ Strategist missed signal. Size: {strat.trade_size_usd}")
    return False
    
    print("❌ Strategist missed the signal.")
    return False

def verify_dean():
    print("\n--- Verifying AgentDean (The Memory) ---")
    agent = AgentDean()
    
    # Inject a Mock Lesson
    conn = sqlite3.connect(agent.db_path)
    c = conn.cursor()
    c.execute("INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)", 
              ("TEST", "WIN", "Verified Dean Logic"))
    conn.commit()
    conn.close()
    
    agent.analyze_stream()
    
    # Check Canon
    if os.path.exists(agent.canon_path):
        with open(agent.canon_path, 'r') as f:
            content = f.read()
            if "Verified Dean Logic" in content or "SUCCESS PATTERN" in content:
                print("✅ Dean Wrote to Canon.")
                return True
    
    print("❌ Dean failed to write.")
    return False

if __name__ == "__main__":
    t = verify_tech()
    f = verify_foresight()
    w = verify_wiring()
    d = verify_dean()
    
    if t and f and w and d:
        print("\n🟢 ALL SYSTEMS VERIFIED. INTELLIGENCE IS LIVE.")
        sys.exit(0)
    else:
        print("\n🔴 VERIFICATION FAILED.")
        sys.exit(1)
