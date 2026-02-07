import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

def init_db():
    print(f"Initializing Stablecoin Buckets in {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS stablecoin_buckets (
            bucket_type TEXT PRIMARY KEY,
            stablecoin TEXT,
            purpose TEXT,
            balance REAL DEFAULT 0.0,
            interest_rate REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Seed Data
    buckets = [
        ('IRS_USDT', 'USDT', 'Tax Payments', 0.0, 0.0),
        ('SNW_LLC_USDC', 'USDC', 'SNW/LLC Operations', 0.0, 0.05), # 5% yield mock
        ('INJECTION_DAI', 'DAI', 'Capital Injections', 0.0, 0.0),
        ('RESERVE', 'USDC', 'Trading Reserve', 0.0, 0.0)
    ]
    
    for b in buckets:
        try:
            c.execute("INSERT INTO stablecoin_buckets (bucket_type, stablecoin, purpose, balance, interest_rate) VALUES (?, ?, ?, ?, ?)", b)
            print(f"  + Added bucket: {b[0]}")
        except sqlite3.IntegrityError:
            print(f"  . Bucket {b[0]} already exists.")
            
    conn.commit()
    conn.close()
    print("Optimization Complete.")

if __name__ == "__main__":
    init_db()
