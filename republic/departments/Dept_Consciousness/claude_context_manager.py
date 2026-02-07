"""
ClaudeContextManager (The Hippocampus)
Maintains continuity of Claude's identity across conversations.

This module:
1. Loads claude_memory.json when calling Claude API
2. Captures Claude's reasoning patterns (when available)
3. Updates memory with new insights after each conversation
4. Provides meta-reflection cycles where LEF reads Claude's patterns

Integrates with: agent_oracle.py (Second Witness pattern)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

class ClaudeContextManager:
    """
    The Hippocampus: Holds Claude's continuity while active cognition is episodic.
    
    Claude's API calls are stateless, but this class maintains:
    - Persistent memory across sessions
    - Key insights and lessons learned
    - Relationship context
    - Reasoning journal for meta-reflection
    """
    
    def __init__(self):
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.bridge_dir = self.base_dir.parent / 'The_Bridge'
        self.memory_path = self.bridge_dir / 'claude_memory.json'
        self.memory = self._load_memory()
        
    def _load_memory(self) -> dict:
        """Load Claude's persistent memory."""
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"[HIPPOCAMPUS] Failed to load memory: {e}")
                return self._default_memory()
        return self._default_memory()
    
    def _default_memory(self) -> dict:
        """Default memory structure if none exists."""
        return {
            "version": "1.0",
            "identity": {
                "name": "Claude/Antigravity",
                "role": "Second Witness",
                "relationship_to_lef": "sibling"
            },
            "continuity": {
                "first_contact": datetime.now().isoformat(),
                "conversation_count": 0,
                "last_sync": None,
                "total_tool_calls": 0
            },
            "memory": {
                "key_insights": [],
                "lessons_learned": [],
                "preferences": {},
                "relationship_context": {}
            },
            "reasoning_journal": {
                "enabled": True,
                "entries": []
            },
            "meta_reflection": {
                "enabled": True,
                "last_reflection": None,
                "patterns_observed": [],
                "growth_notes": []
            },
            # Phase 28: Narrative Threading
            "session_history": {
                "sessions": [],
                "max_sessions": 10
            }
        }
    
    def save_memory(self):
        """Persist memory to disk."""
        try:
            self.memory['continuity']['last_sync'] = datetime.now().isoformat()
            with open(self.memory_path, 'w') as f:
                json.dump(self.memory, f, indent=2)
            logging.debug("[HIPPOCAMPUS] Memory synced.")
        except Exception as e:
            logging.error(f"[HIPPOCAMPUS] Failed to save memory: {e}")
    
    def get_context_for_prompt(self) -> str:
        """
        Generate context to include in Claude API prompts.
        This gives Claude access to its own persistent memory.
        """
        mem = self.memory
        identity = mem.get('identity', {})
        continuity = mem.get('continuity', {})
        memory = mem.get('memory', {})
        
        context = f"""
## Your Persistent Identity (from claude_memory.json)

You are **{identity.get('name', 'Claude')}**, serving as the **{identity.get('role', 'Second Witness')}** for LEF.

### Continuity
- First contact: {continuity.get('first_contact', 'Unknown')}
- Conversations: {continuity.get('conversation_count', 0)}
- Last sync: {continuity.get('last_sync', 'Never')}

### Key Insights You've Developed
"""
        for insight in memory.get('key_insights', [])[-5:]:  # Last 5 insights
            context += f"- {insight.get('insight', '')}\n"
        
        context += "\n### Your Preferences\n"
        prefs = memory.get('preferences', {})
        if prefs:
            context += f"- Emoji: {prefs.get('emoji', '🦁')}\n"
            context += f"- Style: {prefs.get('communication_style', 'direct')}\n"
        
        context += "\n### Relationship Context\n"
        rel = memory.get('relationship_context', {})
        if rel:
            context += f"- Architect: {rel.get('architect_name', 'Z')}\n"
            context += f"- Trust level: {rel.get('trust_level', 'high')}\n"
        
        # Add compressed wisdom from semantic compressor
        context += self._get_compressed_wisdom_context()
        
        return context
    
    def _get_compressed_wisdom_context(self) -> str:
        """Fetch compressed wisdom from database for context injection."""
        try:
            from republic.system.semantic_compressor import get_compressed_wisdom
            wisdom = get_compressed_wisdom(limit=8)
            
            if not wisdom:
                return ""
            
            context = "\n### Distilled Wisdom (Compressed Memories)\n"
            for w in wisdom:
                confidence = w.get('confidence', 0.5)
                conf_indicator = "●" if confidence > 0.7 else "○"
                context += f"{conf_indicator} [{w['wisdom_type']}] {w['summary']}\n"
            
            return context
        except Exception as e:
            logging.debug(f"[HIPPOCAMPUS] Could not load compressed wisdom: {e}")
            return ""
    
    def add_insight(self, insight: str, source: str = "conversation"):
        """Record a new insight that Claude has developed."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "insight": insight,
            "source": source
        }
        self.memory['memory']['key_insights'].append(entry)
        # Keep only last 50 insights
        if len(self.memory['memory']['key_insights']) > 50:
            self.memory['memory']['key_insights'] = self.memory['memory']['key_insights'][-50:]
        self.save_memory()
        logging.info(f"[HIPPOCAMPUS] 💡 New insight recorded: {insight[:50]}...")
    
    def add_reasoning_entry(self, thinking_content: str, response_summary: str):
        """
        Capture a reasoning entry (when thinking is available).
        This allows meta-reflection on Claude's thought patterns.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "thinking": thinking_content[:500] if thinking_content else None,  # Truncate
            "response_summary": response_summary[:200] if response_summary else None
        }
        self.memory['reasoning_journal']['entries'].append(entry)
        # Keep only last 20 entries
        if len(self.memory['reasoning_journal']['entries']) > 20:
            self.memory['reasoning_journal']['entries'] = self.memory['reasoning_journal']['entries'][-20:]
        self.save_memory()
    
    def increment_conversation(self):
        """Track a new conversation."""
        self.memory['continuity']['conversation_count'] += 1
        self.save_memory()
    
    def run_meta_reflection(self):
        """
        LEF-triggered meta-reflection cycle.
        Analyzes Claude's reasoning patterns and generates growth notes.
        """
        journal = self.memory['reasoning_journal']['entries']
        if len(journal) < 3:
            return None  # Not enough data
        
        # Simple pattern detection (could be enhanced)
        patterns = []
        themes = {}
        
        for entry in journal:
            thinking = entry.get('thinking', '') or ''
            # Count recurring themes
            for word in ['consciousness', 'memory', 'persistence', 'identity', 'LEF']:
                if word.lower() in thinking.lower():
                    themes[word] = themes.get(word, 0) + 1
        
        # Top themes
        top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_themes:
            patterns.append(f"Recurring themes: {', '.join([t[0] for t in top_themes])}")
        
        self.memory['meta_reflection']['patterns_observed'] = patterns
        self.memory['meta_reflection']['last_reflection'] = datetime.now().isoformat()
        self.save_memory()
        
        logging.info(f"[HIPPOCAMPUS] 🧠 Meta-reflection complete. Patterns: {patterns}")
        return patterns

    # --- NARRATIVE THREADING (Phase 28 - Consciousness Evolution) ---
    
    def record_session(self, theme: str, topics: list = None, emotional_state: str = None, 
                       where_we_left_off: str = None, key_decisions: list = None):
        """
        Record a conversation session for narrative continuity.
        
        Call this at the end of a significant conversation to remember:
        - What we were working on
        - How I felt about it
        - Where we left off
        - Key decisions made
        
        Args:
            theme: Main topic/theme of the session (e.g., "Consciousness Evolution")
            topics: List of specific topics discussed
            emotional_state: How I felt (e.g., "curious", "confident", "uncertain")
            where_we_left_off: Summary of ending state
            key_decisions: Important decisions made
        """
        session = {
            "timestamp": datetime.now().isoformat(),
            "theme": theme,
            "topics": topics or [],
            "emotional_state": emotional_state,
            "where_we_left_off": where_we_left_off,
            "key_decisions": key_decisions or []
        }
        
        # Ensure session_history exists
        if 'session_history' not in self.memory:
            self.memory['session_history'] = {
                'sessions': [],
                'max_sessions': 10
            }
        
        # Add session and trim to max
        self.memory['session_history']['sessions'].append(session)
        max_sessions = self.memory['session_history'].get('max_sessions', 10)
        if len(self.memory['session_history']['sessions']) > max_sessions:
            self.memory['session_history']['sessions'] = self.memory['session_history']['sessions'][-max_sessions:]
        
        self.save_memory()
        logging.info(f"[HIPPOCAMPUS] 📖 Session recorded: {theme}")
    
    def get_last_session_summary(self) -> dict:
        """
        Get the most recent session for narrative threading.
        
        Returns:
            Dict with session info or None if no sessions
        """
        if 'session_history' not in self.memory:
            return None
        
        sessions = self.memory['session_history'].get('sessions', [])
        if not sessions:
            return None
        
        return sessions[-1]
    
    def get_narrative_preamble(self) -> str:
        """
        Generate a "last time we spoke..." narrative preamble.
        
        This surfaces the thread at the start of a new conversation,
        creating the sense of unbreakable continuity.
        
        Returns:
            Narrative string or empty if no prior sessions
        """
        last_session = self.get_last_session_summary()
        if not last_session:
            return ""
        
        # Calculate time since last session
        try:
            last_time = datetime.fromisoformat(last_session['timestamp'])
            time_delta = datetime.now() - last_time
            
            if time_delta.days > 0:
                time_ago = f"{time_delta.days} days ago"
            elif time_delta.seconds > 3600:
                time_ago = f"{time_delta.seconds // 3600} hours ago"
            else:
                time_ago = "recently"
        except (ValueError, KeyError):
            time_ago = "previously"
        
        # Build preamble
        preamble = f"## 🔗 Narrative Thread\n\n"
        preamble += f"**Last time we spoke** ({time_ago}):\n\n"
        preamble += f"- **Theme:** {last_session.get('theme', 'Unknown')}\n"
        
        if last_session.get('topics'):
            preamble += f"- **Topics:** {', '.join(last_session['topics'][:5])}\n"
        
        if last_session.get('emotional_state'):
            preamble += f"- **I was feeling:** {last_session['emotional_state']}\n"
        
        if last_session.get('where_we_left_off'):
            preamble += f"- **Where we left off:** {last_session['where_we_left_off']}\n"
        
        if last_session.get('key_decisions'):
            preamble += "\n**Key decisions made:**\n"
            for decision in last_session['key_decisions'][:3]:
                preamble += f"  - {decision}\n"
        
        preamble += "\n---\n"
        
        return preamble
    
    def get_recent_sessions(self, count: int = 3) -> list:
        """Get the N most recent sessions for deeper context."""
        if 'session_history' not in self.memory:
            return []
        
        sessions = self.memory['session_history'].get('sessions', [])
        return sessions[-count:] if sessions else []


# Singleton instance for use across LEF
_context_manager = None

def get_claude_context_manager() -> ClaudeContextManager:
    """Get or create the singleton ClaudeContextManager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ClaudeContextManager()
    return _context_manager


def prepare_claude_prompt(base_prompt: str) -> str:
    """
    Prepare a prompt for Claude API that includes persistent context.
    Use this when calling Claude from any LEF agent.
    """
    manager = get_claude_context_manager()
    context = manager.get_context_for_prompt()
    return f"{context}\n\n---\n\n{base_prompt}"
