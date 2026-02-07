
import os
import sys

# Add root path (one level up from republic/)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add LEF Ai/fulcrum
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # Add LEF Ai

from republic.agents.agent_cio import AgentCIO

def test_shield():
    print("🛡️ TESTING THE SHIELD (RISK ENGINE)...")
    cio = AgentCIO()
    
    # 1. Run Logic (Should trigger Harvest)
    print("Running CIO Risk Check...")
    cio._consult_risk_engine()
    
    # 2. Check Trade Queue
    import sqlite3
    conn = sqlite3.connect('fulcrum/republic.db')
    c = conn.cursor()
    c.execute("SELECT asset, action, amount, status, reason FROM trade_queue WHERE status='PENDING' ORDER BY id DESC")
    print("\n📝 PENDING TRADES:")
    for row in c.fetchall():
        print(row)
        
    conn.close()

if __name__ == "__main__":
    test_shield()
