import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'config.json')

def reset_simulation():
    print("[RESET] 🔄 Wiping Simulation Data for Day 0 Restart...")
    
    # 1. Reset Database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Clear History
        c.execute("DELETE FROM trade_history")
        c.execute("DELETE FROM trade_queue")
        c.execute("DELETE FROM profit_allocation")
        c.execute("DELETE FROM signal_history")
        c.execute("DELETE FROM regime_history")
        c.execute("DELETE FROM migration_log")
        
        # WIPE CONSCIOUSNESS (Tabula Rasa for Precision Mode)
        c.execute("DELETE FROM knowledge_stream")
        c.execute("DELETE FROM lef_monologue")
        print("[RESET] 🧠 Consciousness Wiped (Old Memories/Poetry Removed).")
        
        # Reset Stablecoin Buckets
        c.execute("UPDATE stablecoin_buckets SET balance = 0 WHERE bucket_type = 'IRS_USDT'")
        c.execute("UPDATE stablecoin_buckets SET balance = 0 WHERE bucket_type = 'SNW_LLC_USDC'")
        c.execute("UPDATE stablecoin_buckets SET balance = 10000 WHERE bucket_type = 'INJECTION_DAI'")
        
        # WIPE ASSETS (True Day 0)
        c.execute("DELETE FROM assets")
        
        conn.commit()
        conn.close()
        print("[RESET] ✅ Database Wiped (Trades Cleared, Balances Reset).")
        
    except Exception as e:
        print(f"[RESET] ❌ Error resetting DB: {e}")

    # 2. Reset Config (Nueral Plasticity Reset)
    # The agent 'learned' to be scared (0.99 confidence). We must heal it.
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            
        # Reset Critical Thresholds
        config['thresholds']['buy_signal_confidence'] = 0.80
        config['thresholds']['teleonomy_dynasty_threshold'] = 0.70 # Keep our diversity fix
        
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
            
        print("[RESET] ✅ Config Reset (Confidence -> 0.80).")
        
    except Exception as e:
        print(f"[RESET] ❌ Error resetting Config: {e}")

if __name__ == "__main__":
    reset_simulation()
