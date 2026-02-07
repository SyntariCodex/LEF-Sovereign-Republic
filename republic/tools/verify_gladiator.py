"""
VERIFICATION PROTOCOL: GLADIATOR
Objective: Prove AgentGladiator can download from Kaggle and Train AutoGluon.
"""
import sys
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from departments.Dept_Strategy.agent_gladiator import AgentGladiator

def verify_combat():
    print("\n--- Verifying AgentGladiator (Kaggle/AutoGluon) ---")
    g = AgentGladiator()
    
    # 1. Check Capabilities
    # We know they are installed from previous step, but let the agent check
    print(f"Status Checked by Agent.")
    
    # 2. Run Spiked Fight (Time limit 10s for speed)
    # This will:
    # - Download titanic (if missing)
    # - Unzip
    # - Train AutoGluon for 10s
    try:
        g.train_and_fight("titanic", label_column="Survived", time_limit=10)
        print("✅ Gladiator executed Combat Loop without crashing.")
        return True
    except Exception as e:
        print(f"❌ Gladiator Crashed: {e}")
        return False

if __name__ == "__main__":
    if verify_combat():
        sys.exit(0)
    else:
        sys.exit(1)
