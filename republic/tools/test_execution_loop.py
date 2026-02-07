
import os
import sys
import sqlite3

# Add root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add LEF Ai/fulcrum
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # Add LEF Ai

from republic.agents.agent_cfo import AgentCFO

def force_execution_and_waterfall():
    print("⚡ SIMULATING EXECUTION & WATERFALL...")
    
    conn = sqlite3.connect('fulcrum/republic.db')
    c = conn.cursor()
    
    # 1. Find the Pending Risk Engine Trade
    c.execute("SELECT id, asset, amount, reason FROM trade_queue WHERE status='PENDING' AND reason LIKE 'Risk Engine%' LIMIT 1")
    trade = c.fetchone()
    
    if not trade:
        print("ℹ️  No PENDING Risk Engine trade found (checking for stuck DONE trades next).")
    else:
        t_id, asset, amount, reason = trade
        print(f"✅ Found Trade {t_id}: SELL {amount:.4f} {asset} ({reason})")
        
        # 2. Simulate Execution (Mark DONE)
        # We use the 'bad' price ($477) to ensure consistency with the logic that created it
        c.execute("SELECT value_usd, quantity FROM assets WHERE symbol=?", (asset,))
        row = c.fetchone()
        price = 477.0 # Fallback
        if row:
            price = row[0] / row[1]
            
        print(f"   Executing at price: ${price:.2f}")
        c.execute("UPDATE trade_queue SET status='DONE', price=?, created_at=datetime('now') WHERE id=?", (price, t_id))
        conn.commit()
    
    conn.close()
    
    # 3. Run CFO Waterfall
    print("\n🌊 Running CFO Waterfall...")
    cfo = AgentCFO()
    cfo.process_profit_waterfall()
    
    # 4. Verify Buckets
    print("\n💰 FINAL TREASURY CHECK:")
    conn = sqlite3.connect('fulcrum/republic.db')
    c = conn.cursor()
    c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
    for row in c.fetchall():
        print(f"   - {row[0]}: ${row[1]:,.2f}")
    conn.close()

if __name__ == "__main__":
    force_execution_and_waterfall()
