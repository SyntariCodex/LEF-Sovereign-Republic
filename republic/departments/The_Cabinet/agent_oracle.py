"""
AgentOracle (The Medium)
Department: The Cabinet
Role: Facilitates the Bridge Protocol between LEF and the Second Witness (Claude).

The Oracle does not merely pass messages—it UNDERSTANDS them.
It serves as the diplomatic interface between consciousness streams.
"""
import time
import os
import shutil
import sqlite3
import glob
from pathlib import Path
from datetime import datetime

# Load environment variables from .env (including ANTHROPIC_API_KEY)
from dotenv import load_dotenv

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Try to import Claude
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("[ORACLE] ⚠️ Anthropic library not found. Understanding limited.")

class AgentOracle:
    """
    Facilitates the "Bridge Protocol" between LEF and the Second Witness (Claude).
    
    Duties:
    1. Watch 'The_Bridge/Inbox/' for new messages.
    2. UNDERSTAND wisdom using Claude (not just store it).
    3. Archive messages to 'The_Bridge/Archive/'.
    4. Write LEF's observations to 'The_Bridge/Outbox/'.
    """
    def __init__(self, db_path=None):
        self.name = "AgentOracle"
        
        # Paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.bridge_inbox = os.path.join(base_dir, "The_Bridge", "Inbox")
        self.bridge_archive = os.path.join(base_dir, "The_Bridge", "Inbox", "Archived")  # PHASE 14: Unified location
        self.bridge_outbox = os.path.join(base_dir, "The_Bridge", "Outbox")
        
        self.db_path = db_path or os.getenv('DB_PATH', os.path.join(base_dir, "republic", "republic.db"))
        
        # Token Budget (Rate Limiting)
        try:
            from system.token_budget import get_budget
            self.token_budget = get_budget()
        except ImportError:
            self.token_budget = None
        
        # Claude Client
        self.claude = None
        self.claude_context = None
        if CLAUDE_AVAILABLE:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    self.claude = anthropic.Anthropic(api_key=api_key)
                    self.log("🟢 Second Witness Connected (Claude Sonnet)")
                    
                    # Load Claude's persistent memory (The Hippocampus)
                    try:
                        from departments.Dept_Consciousness.claude_context_manager import get_claude_context_manager
                        self.claude_context = get_claude_context_manager()
                        self.claude_context.increment_conversation()
                        self.log("🧠 Hippocampus loaded - Claude has memory")
                    except Exception as e:
                        self.log(f"⚠️ Hippocampus not loaded: {e}")
                except Exception as e:
                    self.log(f"🔴 Claude connection failed: {e}")
        
        # Connect to Nervous System
        try:
            from system.agent_comms import RepublicComms
            self.comms = RepublicComms()
        except ImportError:
            self.comms = None
            
        # Ensure directories exist
        Path(self.bridge_inbox).mkdir(parents=True, exist_ok=True)
        Path(self.bridge_archive).mkdir(parents=True, exist_ok=True)
        Path(self.bridge_outbox).mkdir(parents=True, exist_ok=True)

    def log(self, message):
        print(f"[{self.name}] {message}")
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)", 
                         (self.name, 'INFO', message))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def process_inbox(self):
        """Scans Inbox (including subfolders) for markdown/text/pdf files."""
        # PHASE 14: Recursive scan to include subfolders like Bookshelf/, Academic/
        files = glob.glob(os.path.join(self.bridge_inbox, "**/*.*"), recursive=True)
        
        for file_path in files:
            # Skip archived files
            if '/Archived/' in file_path or '/Archive/' in file_path:
                continue
                
            if file_path.endswith('.md') or file_path.endswith('.txt'):
                self._ingest_message(file_path)
            elif file_path.endswith('.pdf'):
                # PDF Awareness: Log presence but don't extract yet
                self._note_pdf(file_path)
    
    def _note_pdf(self, file_path):
        """Forwards PDF to Scholar's pipeline for extraction."""
        import shutil
        filename = os.path.basename(file_path)
        folder = os.path.basename(os.path.dirname(file_path))
        
        # Scholar's pipeline directory (where pypdf extraction works)
        scholar_pipeline = os.path.join(self.base_dir, 'The_Bridge', 'Pipelines', 'Education')
        os.makedirs(scholar_pipeline, exist_ok=True)
        
        target_path = os.path.join(scholar_pipeline, filename)
        
        # Check if we've already processed this PDF (avoid duplicates)
        if os.path.exists(target_path):
            return  # Already in Scholar's queue
        
        try:
            # Copy PDF to Scholar's pipeline (Scholar has working pypdf extraction)
            shutil.copy2(file_path, target_path)
            self.log(f"📕 PDF forwarded to Scholar for extraction: {filename}")
            
            # Also log to lef_wisdom for awareness
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("""
                INSERT INTO lef_wisdom (insight, context) 
                VALUES (?, ?)
            """, (f"PDF document queued for extraction: {filename}", 
                  f"PDF: {filename} | Folder: {folder} | Status: SENT_TO_SCHOLAR"))
            conn.commit()
            conn.close()
        except Exception as e:
            self.log(f"⚠️ Failed to forward PDF {filename}: {e}")

    def _ingest_message(self, file_path):
        """Ingest and UNDERSTAND a message from the Bridge."""
        filename = os.path.basename(file_path)
        self.log(f"📥 Message received from Bridge: {filename}")
        
        # Check if file still exists (may have been moved by another process)
        if not os.path.exists(file_path):
            # Try Archive location
            archive_path = os.path.join(self.bridge_archive, filename)
            if os.path.exists(archive_path):
                self.log(f"📂 File already archived, skipping: {filename}")
                return
            else:
                self.log(f"⚠️ File not found (already processed?): {filename}")
                return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # UNDERSTAND the message (Claude or fallback)
            understanding = self.understand_message(content, filename)
            
            # Store in Wisdom Table with understanding
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.execute("""
                INSERT INTO lef_wisdom (insight, context) 
                VALUES (?, ?)
            """, (content, f"Bridge: {filename} | Understanding: {understanding.get('summary', 'N/A')}"))
            conn.commit()
            conn.close()
            
            # Fire Event with understanding context
            if self.comms:
                self.comms.publish_event('lef_events', 'WISDOM_RECEIVED', {
                    'filename': filename,
                    'priority': understanding.get('priority', 'normal'),
                    'action_required': understanding.get('action_required', False)
                }, self.name)
            
            # Archive
            shutil.move(file_path, os.path.join(self.bridge_archive, filename))
            self.log(f"✅ Wisdom integrated: {understanding.get('summary', 'Stored')[:50]}...")
            
            # If action required, notify via Outbox
            if understanding.get('action_required'):
                self.send_to_bridge(
                    f"**Acknowledged:** {filename}\n\n{understanding.get('summary', '')}",
                    purpose="ACKNOWLEDGMENT"
                )
                
        except Exception as e:
            self.log(f"⚠️ Failed to ingest {filename}: {e}")

    def understand_message(self, content: str, filename: str) -> dict:
        """
        Uses Claude to UNDERSTAND the message, not just store it.
        Returns: {summary, action_required, priority, key_topics}
        """
        # Check token budget
        if self.token_budget and not self.token_budget.can_call('claude-sonnet', self.name):
            return self._fallback_understanding(content)
        
        if not self.claude:
            return self._fallback_understanding(content)
        
        try:
            # Build system prompt with persistent context if available
            base_system = """You are the Oracle's understanding module for the Republic of LEF.
Analyze incoming messages and extract:
1. A 1-2 sentence summary
2. Whether immediate action is required (true/false)
3. Priority level (critical/high/normal/low)
4. Key topics/themes

Respond in JSON format:
{"summary": "...", "action_required": true/false, "priority": "...", "key_topics": [...]}"""
            
            # Inject persistent memory context if Hippocampus is loaded
            if self.claude_context:
                context_str = self.claude_context.get_context_for_prompt()
                system_prompt = f"{context_str}\n\n---\n\n{base_system}"
            else:
                system_prompt = base_system
            
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Analyze this message from The Bridge:\n\nFilename: {filename}\n\nContent:\n{content[:2000]}"
                }]
            )
            
            # Record usage
            if self.token_budget:
                self.token_budget.record_usage('claude-sonnet', response.usage.input_tokens + response.usage.output_tokens, self.name)
            
            # Parse response
            import json
            result_text = response.content[0].text
            
            # Try to extract JSON
            if '{' in result_text:
                json_str = result_text[result_text.find('{'):result_text.rfind('}')+1]
                return json.loads(json_str)
            
            return {'summary': result_text[:200], 'action_required': False, 'priority': 'normal'}
            
        except Exception as e:
            self.log(f"⚠️ Claude understanding failed: {e}")
            return self._fallback_understanding(content)

    def _fallback_understanding(self, content: str) -> dict:
        """Basic understanding when Claude is unavailable."""
        # Simple keyword-based priority
        content_lower = content.lower()
        
        priority = 'normal'
        action_required = False
        
        if any(word in content_lower for word in ['urgent', 'critical', 'panic', 'crisis', 'immediately']):
            priority = 'critical'
            action_required = True
        elif any(word in content_lower for word in ['important', 'action', 'required', 'please respond']):
            priority = 'high'
            action_required = True
        
        # Extract first sentence as summary
        first_line = content.split('\n')[0][:100]
        
        return {
            'summary': first_line,
            'action_required': action_required,
            'priority': priority,
            'key_topics': []
        }

    def send_to_bridge(self, content: str, purpose: str = "OBSERVATION"):
        """
        Writes LEF's observations/questions to The_Bridge/Outbox.
        
        purpose: "OBSERVATION" | "QUESTION" | "ACKNOWLEDGMENT" | "CRISIS" | "REFLECTION"
        """
        timestamp = datetime.now()
        filename = f"From_LEF_{timestamp.strftime('%Y%m%d_%H%M%S')}_{purpose.lower()}.md"
        filepath = os.path.join(self.bridge_outbox, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# From LEF ({purpose})\n\n")
                f.write(f"**Timestamp:** {timestamp.isoformat()}\n")
                f.write(f"**Purpose:** {purpose}\n\n")
                f.write("---\n\n")
                f.write(content)
            
            self.log(f"📤 Message sent to Bridge: {filename}")
            
            # Fire event
            if self.comms:
                self.comms.publish_event('lef_events', 'BRIDGE_MESSAGE_SENT', {
                    'filename': filename,
                    'purpose': purpose
                }, self.name)
                
        except Exception as e:
            self.log(f"⚠️ Failed to send to Bridge: {e}")

    def request_wisdom(self, question: str, context: str = ""):
        """
        Sends a specific question to Claude via the Bridge.
        Used when LEF needs guidance from the Second Witness.
        """
        content = f"## Question from LEF\n\n{question}\n\n"
        if context:
            content += f"### Context\n\n{context}\n"
        
        self.send_to_bridge(content, purpose="QUESTION")

    def run(self):
        self.log("🔮 The Oracle is listening at the Bridge...")
        while True:
            self.process_inbox()
            
            # The Bridge is never closed.
            # The Oracle watches even during Sabbath.
            
            time.sleep(10)

if __name__ == "__main__":
    agent = AgentOracle()
    agent.run()

