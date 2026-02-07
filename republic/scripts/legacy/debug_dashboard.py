
import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'republic/republic.db')

def get_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    data = {}
    
    # Buckets
    try:
        c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
        buckets = dict(c.fetchall())
        data['snw'] = {
            'llc': buckets.get('SNW_LLC_USDC', 0.0),
            'tax': buckets.get('IRS_USDT', 0.0),
            'inj': buckets.get('INJECTION_DAI', 0.0)
        }
    except Exception as e:
        data['error'] = str(e)
        
    conn.close()
    return data

print(json.dumps(get_data(), indent=2))
