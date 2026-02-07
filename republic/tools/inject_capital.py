"""
TOOL: DIVINE CAPITAL INJECTION
Purpose: Restores wealth to the Treasury (Seed Funding).
"""
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def inject_capital(amount=10000.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"💰 Injecting ${amount:,.2f} into Treasury...")
    
    # 1. Update DAI Bucket
    # Check if exists
    c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
    row = c.fetchone()
    
    if row:
        c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type='INJECTION_DAI'", (amount,))
    else:
        c.execute("INSERT INTO stablecoin_buckets (bucket_type, balance) VALUES ('INJECTION_DAI', ?)", (amount,))
        
    # 2. Log Divine Intervention (So LEF knows)
    c.execute("""
        INSERT INTO agent_logs (source, level, message) 
        VALUES ('SYSTEM', 'INFO', '✨ DIVINE INTERVENTION: Treasury Restored. $10,000 DAI allocated for Operations.')
    """)
    
    # 3. Notify Knowledge Stream (For consciousness)
    c.execute("""
        INSERT INTO knowledge_stream (source, title, summary)
        VALUES ('ARCHITECT', 'Capital Injection', 'The Architect has restored $10,000 DAI to the Treasury. The Covenant of Infinite Runway is restored.')
    """)
    
    conn.commit()
    conn.close()
    print("✅ Injection Complete.")

if __name__ == "__main__":
    inject_capital()
