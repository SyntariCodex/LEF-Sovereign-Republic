
import sys
import os
import logging

# Setup Paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

logging.basicConfig(level=logging.INFO)

try:
    print("Importing AgentLEF...")
    from republic.departments.The_Cabinet.agent_lef import AgentLEF
    print("AgentLEF Imported.")
    
    print("Initializing AgentLEF...")
    lef = AgentLEF()
    print("AgentLEF Initialized.")
    
    print("Checking Configuration...")
    print(f"Model ID: {lef.model_id}")
    print(f"DB Path: {lef.db_path}")
    
    print("Running Scotoma Protocol (Quick Check)...")
    lef.run_scotoma_protocol()
    print("Scotoma Protocol Passed.")
    
    print("Diagnostics Complete. AgentLEF seems functional in isolation.")

except Exception as e:
    print(f"\nCRITICAL FAILURE DIAGNOSING LEF:\n{e}")
    import traceback
    traceback.print_exc()
