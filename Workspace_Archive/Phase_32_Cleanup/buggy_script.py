
import logging
import os
import time
import random

# BUGGY SCRIPT
# Intentionally designed to crash.

# Setup Logging
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'buggy.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_risky_math():
    print("Running risky math...")
    # Fixed by LEF Governance (Operation Zero)
    numerator = 100
    denominator = 10 # Safe value
    result = numerator / denominator
    print(f"Safe Math Result: {result}")
    return result

if __name__ == "__main__":
    try:
        run_risky_math()
    except Exception as e:
        # Log the error so Auditor can find it
        # Format must match Auditor regex: NameError: Message
        error_msg = f"{type(e).__name__}: {e}"
        logging.error(f"CRITICAL FAILURE: {error_msg}")
        print(f"BAM! Crashed: {error_msg}")
