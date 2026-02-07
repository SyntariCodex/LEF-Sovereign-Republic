import os
import json
import shutil
import time
from datetime import datetime

# Optional: Google Gemini Support
try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from republic.utils.notifier import Notifier
except ImportError:
    from utils.notifier import Notifier
except:
    Notifier = None

# The Builder (Dept of Engineering)
# "The Hand of the King"
# Mission: Execute Signed Laws (Proposals) by writing code.

# Load Environment Variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
    print(f"[BUILDER] Loading .env from: {env_path}")
    load_dotenv(env_path)
except ImportError:
    print("[BUILDER] python-dotenv not installed.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAWS_DIR = os.path.join(BASE_DIR, 'governance', 'laws')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'governance', 'archive')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups', 'pre_build')

class AgentBuilder:
    def __init__(self):
        print("[BUILDER] 👷 Session Open. Checking for Laws...")
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        
        print(f"[BUILDER] DEBUG: Google Key Present? {bool(self.google_key)}")
        print(f"[BUILDER] DEBUG: Google Lib Available? {GOOGLE_AVAILABLE}")
        
        
        self.brain_type = None
        
        if self.google_key and GOOGLE_AVAILABLE:
            genai.configure(api_key=self.google_key)
            # Verified Model Name from debug_gemini.py (gemini-flash-latest)
            self.model = genai.GenerativeModel('gemini-flash-latest')
            self.brain_type = "GOOGLE_GEMINI"
            print("[BUILDER] 🧠 Connected to Google Brain (Gemini Flash Latest).")
            
        elif self.api_key:
            self.brain_type = "OPENAI/ANTHROPIC"
            print("[BUILDER] 🧠 Connected to LLM via Standard API.")
            
        else:
             print("[BUILDER] ⚠️  WARNING: No API Key found. I have no brain. I can only perform basic file moves.")

    def run_build_cycle(self):
        """
        Scans 'laws/' for Signed Bills.
        Executes them.
        """
        # Ensure backup dir exists
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        laws = [f for f in os.listdir(LAWS_DIR) if f.endswith('.json')]
        
        if not laws:
            print("[BUILDER] No new laws to execute.")
            return

        for filename in laws:
            filepath = os.path.join(LAWS_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    law = json.load(f)
                
                print(f"[BUILDER] 🏗️  Executing Law: {law.get('id')} - {law.get('title')}")
                
                # EXECUTION LOGIC
                success = self._execute_law(law)
                
                if success:
                    print(f"[BUILDER] ✅ SUCCESS. Archive Law.")
                    self._archive_law(filepath, law, "EXECUTED")
                else:
                    print(f"[BUILDER] ❌ FAILED. Marking as Defective.")
                    self._archive_law(filepath, law, "FAILED_BUILD")

            except Exception as e:
                print(f"[BUILDER] Error executing law {filename}: {e}")

    def _execute_law(self, law):
        """
        The Core Logic.
        1. Parse Technical Spec.
        2. Backup Targets.
        3. Apply Changes.
        """
        tech_spec = law.get('technical_spec', {})
        target_files = tech_spec.get('target_files', [])
        changes = tech_spec.get('changes', [])
        
        # 1. Backup
        for target in target_files:
            if target == "TBD - Needs Analyst": continue
            
            abs_path = os.path.join(BASE_DIR, target)
            if os.path.exists(abs_path):
                backup_name = f"{os.path.basename(target)}.{int(time.time())}.bak"
                shutil.copy(abs_path, os.path.join(BACKUP_DIR, backup_name))
                print(f"[BUILDER] 🛡️  Backed up {target}")

        # 2. Check Capacity
        if not (self.api_key or self.google_key):
            print("[BUILDER] 🛑 I cannot write code without an API Key. Please provide KEY in .env")
            return False

        # 3. Apply Changes
        print(f"[BUILDER] 🔧 Applying {len(changes)} changes...")
        
        # TRI-CAMERAL UPGRADE: The Evolution (Simulation)
        try:
            from republic.agents.agent_simulator import AgentSimulator
            # Mock strategy config for the simulator based on the Law
            sim_config = {"name": law.get('id', 'Unknown Law'), "changes": changes}
            simulator = AgentSimulator(strategy_config=sim_config)
            
            print(f"[BUILDER] 💤 Entering Dream State (Simulation) for {law.get('id')}...")
            simulation_result = simulator.verify(duration_hours=1) # 1 Hour Dream
            
            if simulation_result.get('status') != 'COMPLETED' or simulation_result.get('total_pnl', 0) < 0:
                print(f"[BUILDER] 🛑 Expectation of Loss! Simulation Failed: {simulation_result}")
                
                # NOTIFY FAILURE
                if Notifier:
                     Notifier().send(f"**BUILD VETOED**\nLaw: {law.get('id')}\nReason: Simulation Failed (Dream of Loss)", context="BUILDER", severity="WARNING")
                return False
            
            print(f"[BUILDER] ✨ Dream Successful (P/L: ${simulation_result.get('total_pnl')}). Waking up to deploy.")
            
        except ImportError:
            print("[BUILDER] ⚠️ Simulator not found. Skipping Dream State.")
        except Exception as e:
            print(f"[BUILDER] ⚠️ Simulation Error: {e}. Proceeding with caution.")

        # REAL LOGIC:
        if self.brain_type == "GOOGLE_GEMINI":
            # Generate Code
            for target in target_files:
                prompt = f"""
                You are a Senior Python Engineer for an Autonomous AI System.
                Your task is to write the code for file: '{target}'
                
                Requirements & Changes:
                {json.dumps(changes, indent=2)}
                
                Constraints:
                - Return ONLY the raw python code.
                - No markdown formatting (no ```python blocks).
                - Include standard imports.
                - Ensure robust error handling.
                """
                try:
                    print(f"[BUILDER] 🧠 Generating code for {target}...")
                    response = self.model.generate_content(prompt)
                    code = response.text
                    
                    # Clean Markdown if Gemini ignores instruction
                    if code.startswith("```"):
                        code = code.split('\n', 1)[1]
                    if code.endswith("```"):
                        code = code.rsplit('\n', 1)[0]
                    
                    # Write Code
                    full_path = os.path.join(BASE_DIR, target)
                    # Ensure dir exists
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, 'w') as f:
                        f.write(code)
                        
                    print(f"[BUILDER] 💾 Wrote {target} via Gemini.")
                except Exception as e:
                    print(f"[BUILDER] ⚡ Brain Error: {e}")
                    return False
            return True
            
        return True

    def _archive_law(self, old_path, data, status):
        data['status'] = status
        filename = os.path.basename(old_path)
        new_path = os.path.join(ARCHIVE_DIR, filename)
        with open(new_path, 'w') as f:
            json.dump(data, f, indent=4)
        os.remove(old_path)

if __name__ == "__main__":
    builder = AgentBuilder()
    builder.run_build_cycle()
