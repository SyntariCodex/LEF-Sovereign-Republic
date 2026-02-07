
import os
import sys
import sqlite3
import json
import time
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Add paths
sys.path.append(os.path.abspath('.'))

# Import Agents
from republic.departments.The_Cabinet.agent_treasury import AgentTreasury
from republic.departments.The_Cabinet.agent_attorney_general import AgentAttorneyGeneral
from republic.departments.The_Cabinet.agent_chief_of_staff import AgentChiefOfStaff

DB_PATH = "republic.db"

def test_treasury():
    print("\n--- TESTING TREASURY ---")
    treasury = AgentTreasury(db_path=DB_PATH)
    
    # Run Cycle
    climate = treasury.assess_macro_climate()
    print(f"Climate: {climate}")
    
    strategy = treasury.formulate_strategy(climate)
    print(f"Strategy: {strategy}")
    
    treasury.broadcast_signal(strategy)
    
    # Verify File
    sig_path = "The_Bridge/Pipelines/Wealth/strategy_signal.json"
    if os.path.exists(sig_path):
        print("✅ SUCCESS: strategy_signal.json created.")
        with open(sig_path, 'r') as f:
            print(f"   Content: {f.read()[:50]}...")
    else:
        print("❌ FAIL: No signal file found.")

def test_attorney():
    print("\n--- TESTING ATTORNEY GENERAL ---")
    ag = AgentAttorneyGeneral(db_path=DB_PATH)
    
    # 1. Inject Draft Law
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO laws (title, content, status) VALUES (?, ?, ?)", 
              ("Test Act 101", "Be it resolved that we test.", "DRAFT"))
    lid = c.lastrowid
    conn.commit()
    conn.close()
    print(f"Injected Draft Law ID: {lid}")
    
    # 2. Run Review
    ag.review_drafts()
    
    # 3. Check Status
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM laws WHERE id=?", (lid,))
    status = c.fetchone()[0]
    conn.close()
    
    if status == 'ACTIVE':
        print(f"✅ SUCCESS: Law {lid} status is {status}.")
    else:
        print(f"❌ FAIL: Law {lid} status is {status}.")

def test_chief():
    print("\n--- TESTING CHIEF OF STAFF ---")
    chief = AgentChiefOfStaff()
    
    # 1. Create Dummy Bill
    bill = {"title": "Fund Operations", "target_department": "WEALTH"}
    bill_path = "The_Bridge/Inbox/test_bill.json"
    
    if not os.path.exists("The_Bridge/Inbox"): os.makedirs("The_Bridge/Inbox")
    
    with open(bill_path, 'w') as f:
        json.dump(bill, f)
    print(f"Created {bill_path}")
    
    # 2. Run Process
    chief.process_inbox()
    
    # 3. Verify Move
    dest_path = "The_Bridge/Pipelines/Wealth/test_bill.json"
    if os.path.exists(dest_path):
        print("✅ SUCCESS: Bill routed to Wealth Pipeline.")
        # Cleanup
        os.remove(dest_path)
    else:
        print("❌ FAIL: Bill not found in target pipeline.")

if __name__ == "__main__":
    test_treasury()
    test_attorney()
    test_chief()
