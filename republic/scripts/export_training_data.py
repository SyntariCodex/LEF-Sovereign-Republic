import sqlite3
import csv
import os
import sys

# EXPORT TRAINING DATA
# Exports critical memory tables to CSV for use in the External Brain (Colab).

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'republic', 'republic.db')
EXPORT_DIR = os.path.join(BASE_DIR, 'The_Bridge', 'Data_Export')

def export_table(table_name):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get all data
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()
        
        # Get headers
        headers = [description[0] for description in c.description]
        
        # Write to CSV
        filename = os.path.join(EXPORT_DIR, f"{table_name}.csv")
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        print(f"✅ Exported {len(rows)} rows from {table_name} to {filename}")
        conn.close()
        
    except Exception as e:
        print(f"❌ Error exporting {table_name}: {e}")

if __name__ == "__main__":
    print(f"🚀 Starting Data Export...")
    print(f"📍 Database: {DB_PATH}")
    print(f"📍 Target: {EXPORT_DIR}")
    
    # 1. Export Signals (The Senses)
    export_table('signal_history')
    
    # 2. Export Regimes (The Perceived Context)
    export_table('regime_history')
    
    # 3. Export Trades (The Actions)
    export_table('trade_queue')

    # 4. Export Profits (The Results)
    export_table('profit_allocation')
    
    print("✨ Export Complete.")
