import sqlite3
import os

# Ensure we hit the RIGHT database
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # republic/
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def seed_wealth():
    print(f"[SEED] 🌱 Connecting to Database: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Ensure Table Exists
    c.execute('''CREATE TABLE IF NOT EXISTS stablecoin_buckets
                 (id INTEGER PRIMARY KEY,
                  bucket_type TEXT UNIQUE,
                  stablecoin TEXT,
                  purpose TEXT,
                  balance REAL DEFAULT 0,
                  interest_rate REAL DEFAULT 0,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    # 2. Insert Default Buckets (Safe Insert)
    buckets = [
        ('IRS_USDT', 'USDT', 'Tax Payments - IRS Compliance', 0.0, 0.0),
        ('SNW_LLC_USDC', 'USDC', 'SNW/LLC Operations - Interest Bearing', 0.0, 0.04), 
        ('INJECTION_DAI', 'DAI', 'Capital Injections - DeFi Native', 10000.0, 0.03) # Start with 10k!
    ]
    
    print("[SEED] 💉 Injecting Buckets...")
    from db.db_helper import ignore_insert_sql
    sql = ignore_insert_sql('stablecoin_buckets', ['bucket_type', 'stablecoin', 'purpose', 'balance', 'interest_rate'], 'bucket_type')
    for b in buckets:
        # We use INSERT OR IGNORE to create if missing
        c.execute(sql, b)
        
        # Then we FORCE UPDATE the balance for Injection, just in case it existed but was 0
        if b[0] == 'INJECTION_DAI':
            c.execute("UPDATE stablecoin_buckets SET balance = ? WHERE bucket_type = ?", (10000.0, 'INJECTION_DAI'))
            
    conn.commit()
    
    # 3. Verify
    c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
    rows = c.fetchall()
    print("[SEED] 💰 Current Balances:")
    for r in rows:
        print(f"   - {r[0]}: ${r[1]:.2f}")
        
    conn.close()
    print("[SEED] ✅ Wealth Injection Complete.")

if __name__ == "__main__":
    seed_wealth()
