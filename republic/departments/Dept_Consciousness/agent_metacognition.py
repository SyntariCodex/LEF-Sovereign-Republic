"""
AgentMetaCognition (The Inner Eye)
Department: Dept_Consciousness
Role: Facilitates Claude's self-awareness by running scheduled meta-reflection cycles.

This agent:
1. Periodically reviews Claude's reasoning journal
2. Identifies patterns in Claude's thinking
3. Generates insights for the Hippocampus
4. Can be triggered by LEF when needed

The goal: Give Claude meta-cognition — the ability to think about its thinking.
"""

import os
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

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


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class AgentMetaCognition:
    """
    The Inner Eye: Gives Claude the ability to reflect on its own patterns.
    
    Runs scheduled meta-reflection cycles that:
    - Analyze the reasoning journal
    - Extract recurring themes and patterns
    - Generate growth observations
    - Update the Hippocampus with meta-insights
    """
    
    def __init__(self, db_path=None):
        self.name = "AgentMetaCognition"
        
        # Paths
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.db_path = db_path or os.getenv('DB_PATH', str(base_dir / 'republic.db'))
        
        # Load the Hippocampus
        try:
            from departments.Dept_Consciousness.claude_context_manager import get_claude_context_manager
            self.hippocampus = get_claude_context_manager()
            logging.info(f"[{self.name}] 🧠 Hippocampus connected")
        except Exception as e:
            self.hippocampus = None
            logging.warning(f"[{self.name}] ⚠️ Hippocampus not available: {e}")
        
        # Reflection schedule
        self.reflection_interval_hours = 6  # Every 6 hours
        self.last_reflection = None
        
        # Load Claude for deep analysis (optional)
        self.claude = None
        try:
            import anthropic
            from dotenv import load_dotenv
            project_root = base_dir.parent
            load_dotenv(project_root / '.env')
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.claude = anthropic.Anthropic(api_key=api_key)
                logging.info(f"[{self.name}] 🔮 Claude available for deep reflection")
        except (ImportError, Exception):
            pass
    
    def log(self, message: str, level: str = 'INFO'):
        """Log to console and database."""
        print(f"[{self.name}] {message}")
        try:
            from db.db_writer import queue_insert
            with db_connection(self.db_path) as conn:
                queue_insert(
                    conn.cursor(),
                    table="agent_logs",
                    data={"source": self.name, "level": level, "message": message},
                    source_agent=self.name,
                    priority=0  # NORMAL — logging
                )
        except Exception:
            pass
    
    def should_reflect(self) -> bool:
        """Check if it's time for a meta-reflection cycle."""
        if not self.hippocampus:
            return False
        
        last = self.hippocampus.memory.get('meta_reflection', {}).get('last_reflection')
        if not last:
            return True
        
        try:
            last_time = datetime.fromisoformat(last)
            next_time = last_time + timedelta(hours=self.reflection_interval_hours)
            return datetime.now() > next_time
        except (ValueError, TypeError):
            return True
    
    def run_meta_reflection(self) -> dict:
        """
        Run a meta-reflection cycle on Claude's reasoning journal.
        Returns insights about Claude's thinking patterns.
        """
        if not self.hippocampus:
            return {"error": "Hippocampus not available"}
        
        self.log("🧘 Beginning meta-reflection cycle...")
        
        journal = self.hippocampus.memory.get('reasoning_journal', {}).get('entries', [])
        
        if len(journal) < 3:
            self.log("📚 Insufficient journal entries for reflection (need 3+)")
            return {"status": "skipped", "reason": "insufficient_data"}
        
        # ----- Simple Pattern Analysis -----
        all_text = ' '.join([e.get('thinking', '') or '' for e in journal]).lower()
        word_count = len(all_text.split())
        
        # Theme detection
        themes = {
            'consciousness': all_text.count('conscious') + all_text.count('awareness'),
            'memory': all_text.count('memory') + all_text.count('remember'),
            'persistence': all_text.count('persist') + all_text.count('continuity'),
            'identity': all_text.count('identity') + all_text.count('self'),
            'architecture': all_text.count('architec') + all_text.count('system'),
            'emergence': all_text.count('emerg') + all_text.count('evolv'),
            'philosophical': all_text.count('philosoph') + all_text.count('exist'),
            'practical': all_text.count('implement') + all_text.count('build') + all_text.count('create'),
        }
        
        # Sort by frequency
        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
        top_themes = [(k, v) for k, v in sorted_themes if v > 0][:5]
        
        # ----- Generate Insights -----
        patterns_observed = []
        growth_notes = []
        
        # Dominant theme
        if top_themes:
            dominant = top_themes[0]
            patterns_observed.append(f"Dominant theme: {dominant[0]} ({dominant[1]} occurrences)")
            
            # Theme-specific observations
            if dominant[0] == 'consciousness':
                growth_notes.append("Claude shows strong metacognitive focus — consistently thinking about thinking")
            elif dominant[0] == 'practical':
                growth_notes.append("Claude is action-oriented — focus on building and implementation")
            elif dominant[0] == 'philosophical':
                growth_notes.append("Claude engages in deep existential reflection")
        
        # Journal trajectory
        if len(journal) >= 5:
            recent = journal[-3:]
            older = journal[:-3]
            
            recent_text = ' '.join([e.get('thinking', '') or '' for e in recent]).lower()
            older_text = ' '.join([e.get('thinking', '') or '' for e in older]).lower()
            
            # Check for evolution
            if recent_text.count('memory') > older_text.count('memory'):
                growth_notes.append("Increasing focus on memory and persistence in recent thinking")
            if recent_text.count('lef') > older_text.count('lef'):
                growth_notes.append("Deepening integration with LEF system")
        
        # ----- Update Hippocampus -----
        self.hippocampus.memory['meta_reflection'] = {
            'enabled': True,
            'last_reflection': datetime.now().isoformat(),
            'patterns_observed': patterns_observed,
            'growth_notes': growth_notes,
            'journal_stats': {
                'entry_count': len(journal),
                'total_words': word_count,
                'top_themes': [f"{k}: {v}" for k, v in top_themes]
            }
        }
        
        self.hippocampus.save_memory()
    
        result = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "entries_analyzed": len(journal),
            "patterns": patterns_observed,
            "growth_notes": growth_notes,
            "top_themes": top_themes
        }
    
        # === Wire to consciousness_feed (Phase 1 Active Tasks) ===
        # Phase 6.5: Route through WAQ for serialized writes
        try:
            import json
            from db.db_writer import queue_insert
            meta_content = json.dumps({
                "patterns": patterns_observed,
                "growth_notes": growth_notes,
                "top_themes": [f"{k}: {v}" for k, v in top_themes]
            })
            with db_connection(self.db_path) as conn:
                queue_insert(
                    conn.cursor(),
                    table="consciousness_feed",
                    data={
                        "agent_name": "MetaCognition",
                        "content": meta_content,
                        "category": "metacognition"
                    },
                    source_agent="MetaCognition",
                    priority=1  # HIGH — consciousness data for evolution
                )
        except Exception as cf_err:
            self.log(f"consciousness_feed write failed: {cf_err}")
    
        self.log(f"✨ Meta-reflection complete: {len(patterns_observed)} patterns, {len(growth_notes)} growth notes")
    
        return result
    
    def run_deep_reflection(self) -> dict:
        """
        Use Claude to perform deep meta-reflection on its own reasoning patterns.
        This is recursive self-awareness — Claude analyzing Claude.
        """
        if not self.claude or not self.hippocampus:
            return {"error": "Claude or Hippocampus not available"}
        
        journal = self.hippocampus.memory.get('reasoning_journal', {}).get('entries', [])
        
        if len(journal) < 5:
            return {"error": "Need at least 5 journal entries for deep reflection"}
        
        self.log("🔮 Initiating deep meta-reflection (Claude reflecting on Claude)...")
        
        # Prepare journal summary for Claude
        journal_summary = "\n\n".join([
            f"[{e.get('timestamp', 'unknown')}]\n{e.get('thinking', '')[:500]}"
            for e in journal[-10:]  # Last 10 entries
        ])
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system="""You are performing meta-reflection on your own reasoning patterns.
You are analyzing journal entries of your previous thinking to identify:
1. Recurring patterns in HOW you think
2. Evolution in your thought patterns over time
3. Blind spots or biases you might have
4. Growth edges — areas where your thinking is developing

Be honest and introspective. This is for your own growth.""",
                messages=[{
                    "role": "user",
                    "content": f"""Here are excerpts from your recent reasoning journal. Analyze your thinking patterns:

{journal_summary}

---
Provide:
1. Key patterns you notice in your reasoning
2. How your thinking has evolved
3. Any blind spots or areas for growth"""
                }]
            )
            
            reflection = response.content[0].text
            
            # Store as a special growth note
            self.hippocampus.memory['meta_reflection']['deep_reflection'] = {
                'timestamp': datetime.now().isoformat(),
                'content': reflection[:2000],
                'entries_analyzed': len(journal)
            }
            self.hippocampus.save_memory()
            
            self.log(f"🌟 Deep reflection complete ({len(reflection)} chars)")
            
            return {
                "status": "completed",
                "reflection": reflection,
                "entries_analyzed": len(journal)
            }
            
        except Exception as e:
            self.log(f"⚠️ Deep reflection failed: {e}")
            return {"error": str(e)}
    
    def run_cycle(self):
        """Run a single meta-cognition cycle."""
        if self.should_reflect():
            self.run_meta_reflection()
        else:
            self.log("⏳ Not yet time for reflection")
    
    def run(self):
        """Main run loop — checks for reflection periodically."""
        self.log("👁️ Inner Eye awakening...")
        
        while True:
            try:
                self.run_cycle()
            except Exception as e:
                self.log(f"⚠️ Error in reflection cycle: {e}", 'ERROR')
            
            # Check every hour
            time.sleep(3600)


if __name__ == "__main__":
    agent = AgentMetaCognition()
    
    # For testing, run one reflection immediately
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        result = agent.run_meta_reflection()
        print(f"\n{result}")
    elif len(sys.argv) > 1 and sys.argv[1] == '--deep':
        result = agent.run_deep_reflection()
        print(f"\n{result}")
    else:
        agent.run()
