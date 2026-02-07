
import sqlite3
import os

candidates = [
    "republic/republic.db",
    "republic/departments/republic.db",
    "republic.db",
    "fulcrum.db"
]

print("--- ORACLE SEARCH ---")
for db in candidates:
    if os.path.exists(db):
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute("SELECT sum(balance) FROM stablecoin_buckets")
            res = c.fetchone()
            val = res[0] if res else 0.0
            print(f"[{db}] Balance: ${val}")
            
            # Check for specifically INJECTION_DAI
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
            res2 = c.fetchone()
            dai = res2[0] if res2 else 0.0
            print(f"    -> INJECTION_DAI: ${dai}")
            
            conn.close()
        except Exception as e:
            print(f"[{db}] Error: {e}")
    else:
        print(f"[{db}] NOT FOUND")
