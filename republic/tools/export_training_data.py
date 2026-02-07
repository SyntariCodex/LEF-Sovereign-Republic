
import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime

# CONFIG
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, "republic.db"))
EXPORT_DIR = os.path.join(BASE_DIR, "The_Bridge", "Data_Export")

def export_data():
    print(f"[BRAIN_LINK] 🧠 Connecting to {DB_PATH}...")
    
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 1. TRADE HISTORY (Performance)
        print("[BRAIN_LINK] Exporting Trade History...")
        try:
            df_trades = pd.read_sql_query("SELECT * FROM trade_history", conn)
            df_trades.to_csv(os.path.join(EXPORT_DIR, "trade_history.csv"), index=False)
        except Exception as e:
            print(f"  - Failed: {e}")

        # 2. REGIME HISTORY (Sentiment/Teleonomy)
        print("[BRAIN_LINK] Exporting Regime History...")
        try:
            df_regime = pd.read_sql_query("SELECT * FROM regime_history", conn)
            df_regime.to_csv(os.path.join(EXPORT_DIR, "regime_history.csv"), index=False)
        except Exception as e:
            print(f"  - Failed: {e}")
            
        # 3. KNOWLEDGE STREAM (Text Data for NLP)
        print("[BRAIN_LINK] Exporting Knowledge Stream...")
        try:
            # Limit to last 1000 entries to keep size manageable
            df_kn = pd.read_sql_query("SELECT timestamp, source, title, summary, sentiment_score FROM knowledge_stream ORDER BY id DESC LIMIT 1000", conn)
            df_kn.to_csv(os.path.join(EXPORT_DIR, "knowledge_stream.csv"), index=False)
        except Exception as e:
            print(f"  - Failed: {e}")
            
        # 4. PRICE HISTORY (If available)
        # Note: We might not have a dedicated price_history table if we relied on runtime.
        # Check if assets table has useful snapshot data?
        print("[BRAIN_LINK] Exporting Asset Snapshot...")
        try:
            df_assets = pd.read_sql_query("SELECT * FROM assets", conn)
            df_assets.to_csv(os.path.join(EXPORT_DIR, "assets_snapshot.csv"), index=False)
        except Exception as e:
            print(f"  - Failed: {e}")

        conn.close()
        print(f"[BRAIN_LINK] ✅ Export Complete. Data is waiting in 'The_Bridge/Data_Export'.")
        
    except Exception as e:
        print(f"[BRAIN_LINK] ❌ Critical DB Error: {e}")

if __name__ == "__main__":
    export_data()
