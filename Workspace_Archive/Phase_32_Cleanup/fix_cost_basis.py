import sqlite3

db_path = "republic.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Fixing Cost Basis ---")

# Fix ETH
c.execute("UPDATE assets SET avg_buy_price = 3000.0 WHERE symbol='ETH'")
print(f"Fixed ETH: {c.rowcount} rows")

# Fix SOL
c.execute("UPDATE assets SET avg_buy_price = 140.0 WHERE symbol='SOL'")
print(f"Fixed SOL: {c.rowcount} rows")

# Fix ADA
c.execute("UPDATE assets SET avg_buy_price = 0.80 WHERE symbol='ADA'")
print(f"Fixed ADA: {c.rowcount} rows")

# Fix LINK
c.execute("UPDATE assets SET avg_buy_price = 15.0 WHERE symbol='LINK'")
print(f"Fixed LINK: {c.rowcount} rows")

# Fix POL (Matic)
c.execute("UPDATE assets SET avg_buy_price = 0.50 WHERE symbol='POL'")
print(f"Fixed POL: {c.rowcount} rows")

# Fix LTC
c.execute("UPDATE assets SET avg_buy_price = 80.0 WHERE symbol='LTC'")
print(f"Fixed LTC: {c.rowcount} rows")

conn.commit()
conn.close()
print("--- Database Repaired ---")
