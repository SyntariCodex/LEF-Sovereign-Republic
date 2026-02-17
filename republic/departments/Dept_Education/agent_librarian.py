"""
AgentLibrarian (The Memory Keeper)
Department: Dept_Education
Role: System Archivist, Log Rotation, Knowledge Curation, and Hippocampus Archiving.

Enhanced to integrate with:
- Hippocampus (ClaudeContextManager) - Archives reasoning patterns
- Compressed Wisdom - Preserves distilled insights
"""

import os
import time
import zipfile
import shutil
import logging
import json
import sqlite3
import tempfile
from datetime import datetime

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


# Path Discovery
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
LOG_DIR = os.path.join(os.path.dirname(BASE_DIR), 'logs') 
if not os.path.exists(LOG_DIR): TENTATIVE_LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'republic.log')

# Archive Targets
ARCHIVE_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'republic_archives')
MEMORY_ARCHIVE = os.path.join(ARCHIVE_ROOT, 'memory_snapshots')
WISDOM_ARCHIVE = os.path.join(ARCHIVE_ROOT, 'wisdom_archive')

# Hippocampus Memory Path
MEMORY_PATH = os.path.join(BASE_DIR, 'departments', 'Dept_Consciousness', 'claude_memory.json')

class AgentLibrarian:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("LIBRARIAN")
        
        # Ensure Archive directories exist
        for path in [ARCHIVE_ROOT, MEMORY_ARCHIVE, WISDOM_ARCHIVE]:
            os.makedirs(path, exist_ok=True)
            
        self.logger.info(f"[LIBRARIAN] 📚 Memory Keeper Online. Archives: {ARCHIVE_ROOT}")

    def run_cycle(self):
        """
        The Maintenance Cycle.
        1. Rotating Logs (if too big).
        2. Organizing Library files.
        3. Archiving Hippocampus memory (weekly snapshot).
        4. Archiving compressed wisdom.
        """
        self.logger.info("[LIBRARIAN] 🧹 Starting Cleanup Cycle...")
        
        self._rotate_logs()
        self._organize_library()
        self._archive_hippocampus_memory()
        self._archive_compressed_wisdom()

    def _rotate_logs(self):
        """
        Checks republic.log size. If > 5MB, moves it to /logs/archive/.
        """
        try:
            if not os.path.exists(LOG_FILE): return
            
            size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
            if size_mb > 5.0:
                self.logger.info(f"[LIBRARIAN] 📜 Log File Large ({size_mb:.2f}MB). Rotating...")
                
                timestamp = int(time.time())
                archive_name = f"republic_log_{timestamp}.txt"
                archive_dir = os.path.join(LOG_DIR, "archive")
                os.makedirs(archive_dir, exist_ok=True)
                
                target_path = os.path.join(archive_dir, archive_name)
                
                # Copy then Truncate
                shutil.copy2(LOG_FILE, target_path)
                with open(LOG_FILE, 'w') as f:
                    f.write(f"--- Log Rotated by Librarian at {time.ctime()} ---\n")
                    
                # Zip to save space
                with zipfile.ZipFile(target_path + ".zip", 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(target_path, archive_name)
                os.remove(target_path)
                
                self.logger.info("[LIBRARIAN] ✅ Log Rotated & Zipped.")
        except Exception as e:
            self.logger.error(f"[LIBRARIAN] Log Rotation Failed: {e}")

    def _organize_library(self):
        """
        Scans 'The_Bridge/Library' and organizes loose files by type.
        """
        library_path = os.path.join(ARCHIVE_ROOT, "..", "The_Bridge", "Library")
        if not os.path.exists(library_path):
            return
        
        try:
            pdf_folder = os.path.join(library_path, "pdfs")
            docs_folder = os.path.join(library_path, "docs")
            archive_folder = os.path.join(library_path, "archive")
            
            for folder in [pdf_folder, docs_folder, archive_folder]:
                os.makedirs(folder, exist_ok=True)
            
            for item in os.listdir(library_path):
                item_path = os.path.join(library_path, item)
                if os.path.isdir(item_path):
                    continue
                
                if item.lower().endswith('.pdf'):
                    shutil.move(item_path, os.path.join(pdf_folder, item))
                    self.logger.info(f"[LIBRARIAN] 📂 Moved PDF: {item}")
                elif item.lower().endswith(('.md', '.txt')):
                    shutil.move(item_path, os.path.join(docs_folder, item))
                    self.logger.info(f"[LIBRARIAN] 📂 Moved doc: {item}")
                    
        except Exception as e:
            self.logger.error(f"[LIBRARIAN] Library organization failed: {e}")

    # ==================== HIPPOCAMPUS INTEGRATION ====================
    
    def _archive_hippocampus_memory(self):
        """
        Weekly snapshot of Claude's hippocampus memory.
        Preserves reasoning patterns and insights for long-term archival.
        """
        try:
            if not os.path.exists(MEMORY_PATH):
                return
                
            # Check if weekly snapshot already exists
            today = datetime.now().strftime("%Y-%m-%d")
            week_num = datetime.now().isocalendar()[1]
            year = datetime.now().year
            snapshot_name = f"hippocampus_W{week_num}_{year}.json"
            snapshot_path = os.path.join(MEMORY_ARCHIVE, snapshot_name)
            
            if os.path.exists(snapshot_path):
                return  # Already archived this week
            
            # Load and archive hippocampus memory
            with open(MEMORY_PATH, 'r') as f:
                memory = json.load(f)
            
            # Add archive metadata
            archive_entry = {
                "archived_at": datetime.now().isoformat(),
                "week": week_num,
                "year": year,
                "memory_snapshot": memory,
                "stats": {
                    "insights_count": len(memory.get('insights', [])),
                    "journal_entries": len(memory.get('reasoning_journal', {}).get('entries', [])),
                    "conversation_count": memory.get('conversation_count', 0)
                }
            }
            
            # Phase 35: Atomic write — tempfile + os.replace
            fd, tmp_path = tempfile.mkstemp(dir=MEMORY_ARCHIVE, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(archive_entry, f, indent=2)
                os.replace(tmp_path, snapshot_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

            self.logger.info(f"[LIBRARIAN] 🧠 Hippocampus snapshot archived: {snapshot_name}")
            
            # Prune old reasoning journal entries (keep last 50)
            self._prune_reasoning_journal()
            
        except Exception as e:
            self.logger.error(f"[LIBRARIAN] Hippocampus archival failed: {e}")

    def _prune_reasoning_journal(self):
        """
        Prune reasoning journal to prevent unbounded growth.
        Keeps the most recent 50 entries.
        """
        try:
            if not os.path.exists(MEMORY_PATH):
                return
                
            with open(MEMORY_PATH, 'r') as f:
                memory = json.load(f)
            
            journal = memory.get('reasoning_journal', {})
            entries = journal.get('entries', [])
            
            if len(entries) > 50:
                # Keep only the most recent 50
                memory['reasoning_journal']['entries'] = entries[-50:]

                # Phase 35: Atomic write — tempfile + os.replace
                mem_dir = os.path.dirname(MEMORY_PATH)
                fd, tmp_path = tempfile.mkstemp(dir=mem_dir, suffix='.tmp')
                try:
                    with os.fdopen(fd, 'w') as f:
                        json.dump(memory, f, indent=2)
                    os.replace(tmp_path, MEMORY_PATH)
                except Exception:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    raise

                pruned = len(entries) - 50
                self.logger.info(f"[LIBRARIAN] ✂️ Pruned {pruned} old reasoning entries")
                
        except Exception as e:
            self.logger.debug(f"[LIBRARIAN] Journal pruning skipped: {e}")

    def _archive_compressed_wisdom(self):
        """
        Archive compressed wisdom entries to long-term storage.
        Creates monthly archives from the database.
        """
        try:
            if not os.path.exists(DB_PATH):
                return
            
            # Check if monthly archive exists
            month = datetime.now().strftime("%Y-%m")
            archive_name = f"wisdom_{month}.json"
            archive_path = os.path.join(WISDOM_ARCHIVE, archive_name)
            
            if os.path.exists(archive_path):
                return  # Already archived this month
            
            with db_connection(DB_PATH) as conn:
                c = conn.cursor()
                
                # Check if compressed_wisdom table exists
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compressed_wisdom'")
                if not c.fetchone():
                    return
                
                # Fetch all wisdom entries
                c.execute("""
                    SELECT wisdom_type, summary, source_type, confidence, created_at
                    FROM compressed_wisdom
                    ORDER BY created_at
                """)
                rows = c.fetchall()
            
            if not rows:
                return
            
            # Create archive
            archive_entry = {
                "archived_at": datetime.now().isoformat(),
                "month": month,
                "wisdom_count": len(rows),
                "entries": [
                    {
                        "wisdom_type": row[0],
                        "summary": row[1],
                        "source_type": row[2],
                        "confidence": row[3],
                        "created_at": row[4]
                    }
                    for row in rows
                ]
            }
            
            # Phase 35: Atomic write — tempfile + os.replace
            fd, tmp_path = tempfile.mkstemp(dir=WISDOM_ARCHIVE, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(archive_entry, f, indent=2)
                os.replace(tmp_path, archive_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

            self.logger.info(f"[LIBRARIAN] 💎 Wisdom archive created: {archive_name} ({len(rows)} entries)")
            
        except Exception as e:
            self.logger.error(f"[LIBRARIAN] Wisdom archival failed: {e}")

    # ==================== KNOWLEDGE CATALOGING ====================
    
    def catalog_knowledge(self, source: str, content: str, category: str = "general"):
        """
        Add a knowledge entry to The Canon (long-term knowledge base).
        Called by other agents to preserve important learnings.
        """
        try:
            the_canon_path = os.path.join(ARCHIVE_ROOT, "the_canon.json")
            
            if os.path.exists(the_canon_path):
                with open(the_canon_path, 'r') as f:
                    canon = json.load(f)
            else:
                canon = {"entries": [], "created": datetime.now().isoformat()}
            
            canon["entries"].append({
                "source": source,
                "content": content,
                "category": category,
                "cataloged_at": datetime.now().isoformat()
            })

            # Phase 35: Atomic write — tempfile + os.replace
            canon_dir = os.path.dirname(the_canon_path)
            fd, tmp_path = tempfile.mkstemp(dir=canon_dir, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(canon, f, indent=2)
                os.replace(tmp_path, the_canon_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

            self.logger.info(f"[LIBRARIAN] 📖 Knowledge cataloged from {source}: {content[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"[LIBRARIAN] Cataloging failed: {e}")
            return False

    def run(self):
        self.logger.info("[LIBRARIAN] 🕯️  Vigilance Active.")
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                self.logger.error(f"[LIBRARIAN] Cycle Error: {e}")
            
            time.sleep(3600)  # Run every hour

if __name__ == "__main__":
    agent = AgentLibrarian()
    agent.run()
