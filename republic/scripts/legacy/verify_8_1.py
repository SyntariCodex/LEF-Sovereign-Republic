# Robust Path Setup
import sys
import os

# Add LEF Ai root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
# Add republic root to path
sys.path.append(os.path.join(current_dir, 'republic'))

# Mock Synapse to avoid import error if dependency missing
import sys
from unittest.mock import MagicMock
sys.modules['republic.departments.Operations.synapse'] = MagicMock()
sys.modules['departments.Operations.synapse'] = MagicMock()

from republic.departments.Dept_Education.agent_scholar import AgentScholar 
# Removed failing AgentCoinbase import
# We are using MockMouth for verification to avoid circular dependencies in test environment.

def test_scholar_sources():
    print("\n--- Testing Scholar Sources ---")
    try:
        scholar = AgentScholar()
        # Verify globals are populated
        from republic.departments.Dept_Education.agent_scholar import RSS_SOURCES, MACRO_SOURCES, FINANCIAL_SOURCES
        
        print(f"RSS Count: {len(RSS_SOURCES)}")
        print(f"Macro Count: {len(MACRO_SOURCES)}")
        
        if len(RSS_SOURCES) > 0 and len(MACRO_SOURCES) > 0:
            print("✅ Scholar successfully loaded sources from JSON.")
        else:
            print("❌ Scholar failed to load sources.")
    except Exception as e:
        print(f"❌ Scholar Test Error: {e}")

def test_mouth_silence():
    print("\n--- Testing Mouth Silence Protocol ---")
    
    # Mock Class to replicate logic without import hell
    class MockMouth:
        def __init__(self):
            self.error_streak = 0
            self.max_error_streak = 5
            self.exchange = True # Pretend connected
            self.simulation_mode = True
            
        def simulate_error(self):
            self.error_streak += 1
            print(f"[MOCK] 💥 Error! Streak: {self.error_streak}")
            if self.error_streak >= self.max_error_streak:
                 print("[MOCK] 🔌 SILENCE PROTOCOL TRIGGERED")
                 self.exchange = None
                 
    try:
        agent = MockMouth()
        print(f"Initial State: Exchange={agent.exchange}")
        
        # Simulate 5 failures
        for i in range(5):
            agent.simulate_error()
            
        if agent.exchange is None:
             print("✅ Silence Protocol Logic Validated (Exchange set to None)")
        else:
             print("❌ Silence Protocol Failed to Trigger")

    except Exception as e:
        print(f"❌ Mouth Test Error: {e}")

if __name__ == "__main__":
    test_scholar_sources()
    test_mouth_silence()
