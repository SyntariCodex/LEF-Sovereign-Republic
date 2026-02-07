import os
import time
import logging
import shutil
import re
from datetime import datetime

# AGENT GOVERNOR
# Purpose: Execute proposals approved by the User (The Architect).
# "The Republic of Code"

# Path Config
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) # agents/
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR)) # LEF Ai/
PROPOSALS_DIR = os.path.join(ROOT_DIR, 'The_Bridge', 'Proposals')
APPROVED_DIR = os.path.join(PROPOSALS_DIR, 'Approved')
ARCHIVE_DIR = os.path.join(PROPOSALS_DIR, 'Archived')

# Ensure Dirs
for d in [APPROVED_DIR, ARCHIVE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

class AgentGovernor:
    def __init__(self):
        self.active = True
        self.logger = logging.getLogger("Governor")
        self.logger.setLevel(logging.INFO)

    def run(self):
        self.logger.info("⚖️  The Governor is SEATED. Watching for approved proposals...")
        while self.active:
            try:
                self.check_proposals()
            except Exception as e:
                self.logger.error(f"Governor Error: {e}")
            
            time.sleep(10) # Check every 10s

    def check_proposals(self):
        # Scan 'Approved' folder
        files = [f for f in os.listdir(APPROVED_DIR) if f.endswith('.md')]
        
        for filename in files:
            filepath = os.path.join(APPROVED_DIR, filename)
            self.execute_proposal(filepath, filename)

    def execute_proposal(self, filepath, filename):
        self.logger.info(f"📜 Executing Proposal: {filename}")
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # PARSING LOGIC (Simple V1)
            # Look for "## Implementation Plan"
            # For now, we mainly log that we *would* do it, unless we add code parsing.
            
            # Extract Title
            title_match = re.search(r'^#\s+(.+)', content)
            title = title_match.group(1) if title_match else filename

            # Extract Plan
            plan_match = re.search(r'## Implementation Plan(.+)', content, re.DOTALL)
            plan = plan_match.group(1).strip() if plan_match else "No strict plan found."

            # LOG ACTION
            log_entry = f"[{datetime.now()}] EXECUTED: {title}\nPlan Summary: {plan[:100]}...\n"
            
            # In a real heavy version, we would verify code blocks here.
            # For V1, we mark as executed.
            
            self.logger.info(f"✅ Proposal '{title}' Processed Successfully.")
            
            # ARCHIVE
            shutil.move(filepath, os.path.join(ARCHIVE_DIR, filename))
            
        except Exception as e:
            self.logger.error(f"❌ Failed to execute {filename}: {e}")
            # Move to Rejected/Failed? Or leave for retry?
            # Creating 'Failed' dir
            failed_dir = os.path.join(PROPOSALS_DIR, 'Rejected')
            if not os.path.exists(failed_dir): os.makedirs(failed_dir)
            try:
                shutil.move(filepath, os.path.join(failed_dir, f"FAILED_{filename}"))
            except: pass

def run_governor_agent():
    agent = AgentGovernor()
    agent.run()

if __name__ == "__main__":
    run_governor_agent()
