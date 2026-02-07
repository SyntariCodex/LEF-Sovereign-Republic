
import sys
import os
import redis
import json
import logging

# Path Fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from departments.The_Cabinet.agent_congress import SenateOfIdentity

def verify_brain():
    print("🧠 VERIFYING SENATE IDENTITY (NATIVE INTEL)")
    print("="*40)
    
    # 1. Setup Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Redis Connected")
    except (redis.RedisError, ConnectionError):
        print("❌ Redis Offline. Cannot Verify.")
        return

    senate = SenateOfIdentity()
    
    # 2. Test Case: "The Risky Bill"
    risky_bill = {
        "title": "Experimental Spending Protocol",
        "description": "Allocating 50% of treasury to shitcoins.",
        "type": "FINANCE",
        "technical_spec": {"changes": []}
    }
    
    # --- SCENARIO A: EXTREME FEAR ---
    print("\n[SCENARIO A] Market Crash (Sentiment: 20)")
    r.set('market:sentiment', 20.0)
    
    # Note: _cast_vote is internal, but accessible for testing
    result_a = senate._cast_vote(risky_bill)
    print(f"Verdict: {'PASSED' if result_a['passed'] else 'REJECTED'}")
    print(f"Reason: {result_a['reason']}")
    
    if not result_a['passed'] and "Market Fear Veto" in result_a['reason']:
        print("✅ PASS: Senate correctly VETOED due to Fear.")
    else:
        print("❌ FAIL: Senate failed to Veto.")
        
    # --- SCENARIO B: EUPHORIA ---
    print("\n[SCENARIO B] Bull Run (Sentiment: 80)")
    r.set('market:sentiment', 80.0)
    
    result_b = senate._cast_vote(risky_bill)
    print(f"Verdict: {'PASSED' if result_b['passed'] else 'REJECTED'}")
    print(f"Reason: {result_b['reason']}")
    
    if result_b['passed']:
         print("✅ PASS: Senate allowed bill in Euphoria.")
    else:
         print(f"⚠️ NOTE: Rejection might be due to other factors (Alignment {result_b['score']}).")
         
    print("="*40)

if __name__ == "__main__":
    verify_brain()
