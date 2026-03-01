
import warnings
# Filter warnings before importing libraries that might emit them
warnings.filterwarnings("ignore", category=FutureWarning)

import logging
import time
import os
import datetime
from dotenv import load_dotenv

# Import genai using new package
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Setup System
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# BRAIN DIR (Where task.md lives)
# We need to find the active brain session. 
# For now, we search for the .gemini dir
BRAIN_DIR = None
gemini_root = os.path.expanduser("~/.gemini/antigravity/brain")
if os.path.exists(gemini_root):
    # Find latest brain session
    sessions = sorted([os.path.join(gemini_root, d) for d in os.listdir(gemini_root) if os.path.isdir(os.path.join(gemini_root, d))], key=os.path.getmtime, reverse=True)
    if sessions:
        BRAIN_DIR = sessions[0]

# LOGS
LOG_FILE = os.path.join(os.path.dirname(BASE_DIR), 'republic.log')
if not os.path.exists(LOG_FILE): LOG_FILE = os.path.join(BASE_DIR, 'republic.log')

# Load Env
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), '.env'))

try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class AgentDreamer:
    """
    The Dreamer (The Evolutionary Engine).
    Wakes up at 03:00 AM.
    1. Reads the Plan (task.md).
    2. Reads the Memory (republic.log).
    3. Dreams of the Future (Proposes new tasks).
    """
    def __init__(self):
        self.logger = logging.getLogger("DREAMER")
        self.running = True
        self.last_dream_date = None
        
        # Configure Gemini
        self.client = None
        self.model_id = 'gemini-2.0-flash'
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key and GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
            self.logger.info("[DREAMER] 🟣 Subconscious Connected (Gemini 2.0).")
        else:
            self.logger.warning("[DREAMER] 🔴 Subconscious Silent (No API Key or package).")

    def run(self):
        self.logger.info("[DREAMER] 💤 Entering REM Cycle. Waiting for 03:00.")
        # Startup Dream (Optional: Dream on boot if missed?)
        # For now, stick to schedule.
        
        while self.running:
            try:
                now = datetime.datetime.now()
                force_dream = os.getenv("FORCE_DREAM", "False").lower() == "true"
                is_dream_time = (now.hour == 3 and now.minute == 0)
                today_str = now.strftime("%Y-%m-%d")
                
                if (is_dream_time or force_dream) and self.last_dream_date != today_str:
                    self._perform_evolutionary_dream()
                    self.last_dream_date = today_str
                    if force_dream: 
                         self.logger.info("[DREAMER] ⚡ Forced Event check complete.")
                         # Reset env var not possible in process, but we loop.
                
                time.sleep(60)

            except Exception as e:
                self.logger.error(f"[DREAMER] Nightmare: {e}")
                time.sleep(60)

    def _perform_evolutionary_dream(self):
        if not self.client: return
        self.logger.info("[DREAMER] 🌙 DREAMING OF EVOLUTION...")
        
        # Phase 35: Safety caps on file reads to prevent memory exhaustion
        MAX_TASK_SIZE_MB = 10
        MAX_JOURNAL_LINES = 1000

        # 1. Read The Map (Task.md) — capped at 10MB
        task_context = "No Plan Found."
        if BRAIN_DIR:
            task_path = os.path.join(BRAIN_DIR, 'task.md')
            if os.path.exists(task_path):
                file_size_mb = os.path.getsize(task_path) / (1024 * 1024)
                if file_size_mb > MAX_TASK_SIZE_MB:
                    task_context = f"[Task file too large: {file_size_mb:.1f}MB > {MAX_TASK_SIZE_MB}MB cap]"
                    self.logger.warning(f"[DREAMER] Task file too large ({file_size_mb:.1f}MB), skipping")
                else:
                    with open(task_path, 'r') as f:
                        task_context = f.read()

        # 2. Read The Reality (Logs) — capped at MAX_JOURNAL_LINES
        log_context = "No Memory."
        if os.path.exists(LOG_FILE):
             with open(LOG_FILE, 'r') as f:
                 log_context = "".join(f.readlines()[-MAX_JOURNAL_LINES:])

        # 3. Construct The Dream
        prompt = f"""
        SYSTEM: You are the Evolutionary Engine of the LEF Republic.
        
        [CONTEXT 1: THE PLAN (task.md)]
        {task_context}
        
        [CONTEXT 2: THE REALITY (Logs)]
        {log_context}
        
        TASK:
        Compare the Plan vs Reality.
        1. Are we failing a task marked as [x]? (Regressions).
        2. Are we succeeding at a task marked [ ]? (Progress).
        3. What is the MISSING Link? What agent logic is needed next?
        
        OUTPUT FORMAT (Markdown):
        # Dream Journal [{datetime.date.today()}]
        ## Regression Alert
        (If any)
        
        ## Evolutionary Proposal
        (Specific logic or task to add next)
        """
        
        try:
            response_text = None
            if _LLM_ROUTER:
                response_text = _LLM_ROUTER.generate(
                    prompt=prompt, agent_name='Dreamer',
                    context_label='DREAM_SYNTHESIS', timeout_seconds=90
                )
            if response_text is None and self.client:
                try:
                    from system.llm_router import call_with_timeout
                    response = call_with_timeout(
                        self.client.models.generate_content,
                        timeout_seconds=120,
                        model=self.model_id, contents=prompt
                    )
                    response_text = response.text.strip() if response and response.text else None
                except Exception as _e:
                    import logging
                    logging.debug(f"Legacy LLM fallback failed: {_e}")
            dream_content = response_text
            
            # 4. Write Dream Journal
            journal_path = os.path.join(BASE_DIR, 'dream_journal.md')
            with open(journal_path, 'a') as f:
                f.write(f"\n\n{dream_content}")
            
            self.logger.info("[DREAMER] ✨ Evolution Proposaled stored in 'dream_journal.md'.")
            
            # 5. Notify the Sovereign (LEF) - Via Log that LEF reads?
            # Or creating a Proposal file in Governance?
            # Let's create a Proposal for the House!
            self._create_bill_from_dream(dream_content)

        except Exception as e:
            self.logger.error(f"[DREAMER] Dream Failed: {e}")

    def _create_bill_from_dream(self, content):
        """
        Turns the dream into a Bill for Congress.
        """
        try:
            bill_id = f"BILL-DREAM-{int(time.time())}"
            proposal_dir = os.path.join(BASE_DIR, 'governance', 'proposals')
            if not os.path.exists(proposal_dir): os.makedirs(proposal_dir)
            
            path = os.path.join(proposal_dir, f"{bill_id}.json")
            
            import json
            bill = {
                "id": bill_id,
                "type": "EVOLUTION",
                "title": "Evolutionary update from Dream State",
                "description": content[:500], # Summary
                "technical_spec": {
                    "changes": [],
                    "description": "See Dream Journal for details."
                },
                "status": "DRAFT",
                "votes": {}
            }
            
            with open(path, 'w') as f:
                json.dump(bill, f, indent=4)
                
            self.logger.info(f"[DREAMER] 📜 Bill {bill_id} drafted for Congress.")
            
        except Exception as e:
             self.logger.error(f"[DREAMER] Bill Draft Error: {e}")

def run_dream_loop():
    """
    Entry point for main.py to start the Dreamer loop.
    """
    agent = AgentDreamer()
    agent.run()

if __name__ == "__main__":
    agent = AgentDreamer()
    # Mock Run
    os.environ["FORCE_DREAM"] = "True"
    agent.run()
