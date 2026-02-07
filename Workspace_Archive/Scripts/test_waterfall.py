
import sqlite3
import os
import sys

# Hack to import from sibling directory
sys.path.append(os.path.join(os.getcwd(), 'fulcrum'))
from agents.fulcrum_master import FulcrumMaster

def test_waterfall():
    print("🧪 TESTING WEALTH WATERFALL logic...")
    
    # 1. Get Initial Balances
    db_path = 'fulcrum/republic.db' if os.path.exists('fulcrum/republic.db') else 'republic.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    def get_bal(b_type):
        c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type=?", (b_type,))
        row = c.fetchone()
        return row[0] if row else 0.0
        
    start_inj = get_bal('INJECTION_DAI')
    start_dyn = get_bal('DYNASTY_DAI')
    
    print(f"Checking Start Balances:")
    print(f"  Hunter (INJECTION_DAI): ${start_inj:,.2f}")
    print(f"  Dynasty (DYNASTY_DAI): ${start_dyn:,.2f}")
    
    # 2. Simulate Profit
    PROFIT = 1000.0
    print(f"\n🌊 Simulating $1,000 Profit Event (Source: HUNTER)...")
    
    master = FulcrumMaster()
    # Force DB Path to match environment
    master.db_path = 'fulcrum/republic.db' if os.path.exists('fulcrum/republic.db') else 'republic.db'
    print(f"DEBUG: Master using DB: {master.db_path}")
    
    # Mock trade_id = 99999
    master.allocate_waterfall_profits(99999, PROFIT, 'HUNTER')
    
    # 3. Check End Balances
    end_inj = get_bal('INJECTION_DAI')
    end_dyn = get_bal('DYNASTY_DAI')
    
    print(f"\nChecking End Balances:")
    print(f"  Hunter (INJECTION_DAI): ${end_inj:,.2f} (+${end_inj - start_inj:.2f})")
    print(f"  Dynasty (DYNASTY_DAI): ${end_dyn:,.2f} (+${end_dyn - start_dyn:.2f})")
    
    # 4. Assertions
    expected_inj = PROFIT * 0.40
    expected_dyn = PROFIT * 0.60
    
    if abs((end_inj - start_inj) - expected_inj) < 0.01:
        print("✅ Hunter Split Correct (40%)")
    else:
        print("❌ Hunter Split Failed")
        
    if abs((end_dyn - start_dyn) - expected_dyn) < 0.01:
        print("✅ Dynasty Split Correct (60%)")
    else:
        print("❌ Dynasty Split Failed")

if __name__ == "__main__":
    test_waterfall()
