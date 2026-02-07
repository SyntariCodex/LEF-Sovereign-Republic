import sqlite3
import os
import sys

# Try to find the DB
DB_PATH = 'fulcrum_data/republic.db'
if not os.path.exists(DB_PATH):
    print(f"Error: {DB_PATH} not found locally.")
    DB_PATH = '/app/data/republic.db' # Docker path
    if not os.path.exists(DB_PATH):
        print("Error: Docker path not found either.")
        sys.exit(1)

print(f"Injecting Capital into: {DB_PATH}")

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Inject Capital into Buckets
    print("Funding Stablecoin Buckets...")
    c.execute("UPDATE stablecoin_buckets SET balance = 2500.0 WHERE bucket_type = 'SNW_LLC_USDC'")
    c.execute("UPDATE stablecoin_buckets SET balance = 12500.0 WHERE bucket_type = 'INJECTION_DAI'")
    
    # 2. Verify
    c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
    rows = c.fetchall()
    for r in rows:
        print(f" - {r[0]}: ${r[1]:,.2f}")
        
    conn.commit()
    conn.close()
    print("Injection Complete. System Solvency: RESTORED.")
    
except Exception as e:
    print(f"Injection Failed: {e}")
