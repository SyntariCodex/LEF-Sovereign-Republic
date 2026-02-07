
import os
import sys
import time

# Add parent directory to path to import republic modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from republic.departments.Dept_Strategy.agent_tech import AgentTech

def force_scan():
    print("🚀 Triggering Manual Hackathon Scan...")
    
    agent = AgentTech()
    
    # 1. Run Hackathon Scan
    print("   - Scanning Devpost/Kaggle (Simulated)...")
    agent.scan_hackathons()
    
    print("✅ Scan Complete. Check 'republic.db' for new 'research_topics'.")

if __name__ == "__main__":
    force_scan()
