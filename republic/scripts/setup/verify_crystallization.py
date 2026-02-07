import sqlite3
import os
import sys

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from agents.agent_lef import LefObserver

def verify():
    print("--- Verifying Crystallization ---")
    
    # 1. Init Observer (Triggers Export)
    lef = LefObserver()
    
    conn = sqlite3.connect(lef.db_path)
    c = conn.cursor()
    
    # 2. Force Crystallize
    test_axiom = "Test Epiphany: To verify the system is to know oneself."
    print(f"Injecting: {test_axiom}")
    
    lef._crystallize_thought(c, test_axiom)
    
    # 3. Check File
    md_path = os.path.join(BASE_DIR, '..', 'The_Bridge', 'Manuals', 'LEF_AXIOMS_LIVE.md')
    with open(md_path, 'r') as f:
        content = f.read()
        
    if test_axiom in content:
        print("✅ SUCCESS: Axiom found in Manual.")
    else:
        print("❌ FAILURE: Axiom not found in Manual.")
        
    # Cleanup
    c.execute("DELETE FROM lef_wisdom WHERE insight = ?", (test_axiom,))
    conn.commit()
    print("Cleanup Complete.")

if __name__ == "__main__":
    verify()
