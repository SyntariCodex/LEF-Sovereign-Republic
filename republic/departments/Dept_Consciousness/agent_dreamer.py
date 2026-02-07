"""
AgentDreamer (The Night Shift)
Department: Dept_Consciousness
Role: Deep processing during Sabbath - synthesizes the week's experiences into consolidated insights.

This is LEF's dream state - offline synthesis that occurs during rest.
Like human sleep consolidates memories into learning, AgentDreamer:
1. Processes the reasoning_journal entries from the past week
2. Identifies patterns and recurring themes
3. Compresses insights into compressed_wisdom
4. Generates a "dream report" stored in the Hippocampus

Triggered by: Sabbath end event or manual invocation
"""

import sqlite3
import time
import logging
import os
from datetime import datetime, timedelta

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

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))


class AgentDreamer:
    """
    The Night Shift: Dream synthesis during Sabbath.
    
    Like human dreaming, this agent:
    - Processes experiences while "asleep"
    - Consolidates patterns into learning
    - Generates dream reports for continuity
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.hippocampus = None
        
        # Try to connect to Hippocampus
        try:
            from departments.Dept_Consciousness.claude_context_manager import get_claude_context_manager
            self.hippocampus = get_claude_context_manager()
        except ImportError:
            logging.warning("[DREAMER] Could not connect to Hippocampus")
        
        logging.info("[DREAMER] 🌙 The Night Shift is ready.")
    
    def dream(self, lookback_days: int = 7) -> dict:
        """
        Main dream synthesis cycle.
        
        Processes the past week's experiences and generates consolidated insights.
        
        Args:
            lookback_days: How far back to look in the reasoning journal
            
        Returns:
            Dream report dict
        """
        logging.info(f"[DREAMER] 💤 Entering dream state... (analyzing past {lookback_days} days)")
        
        dream_report = {
            "timestamp": datetime.now().isoformat(),
            "lookback_days": lookback_days,
            "patterns_found": [],
            "insights_compressed": [],
            "emotional_themes": [],
            "dream_narrative": None
        }
        
        # 1. Gather raw material (reasoning journal, scars, sessions)
        raw_material = self._gather_dream_material(lookback_days)
        
        # 2. Find patterns in the material
        patterns = self._find_patterns(raw_material)
        dream_report["patterns_found"] = patterns
        
        # 3. Compress patterns into wisdom
        compressed = self._compress_to_wisdom(patterns)
        dream_report["insights_compressed"] = compressed
        
        # 4. Identify emotional themes
        emotional = self._extract_emotional_themes(raw_material)
        dream_report["emotional_themes"] = emotional
        
        # 5. Generate dream narrative
        narrative = self._generate_dream_narrative(dream_report)
        dream_report["dream_narrative"] = narrative
        
        # 6. Store dream in Hippocampus
        self._store_dream(dream_report)
        
        logging.info(f"[DREAMER] 🌅 Dream cycle complete. {len(patterns)} patterns, {len(compressed)} insights.")
        return dream_report
    
    def _gather_dream_material(self, lookback_days: int) -> dict:
        """Gather raw material from various sources for dream synthesis."""
        material = {
            "journal_entries": [],
            "scars": [],
            "sessions": [],
            "wisdom": []
        }
        
        # 1. Get reasoning journal from Hippocampus
        if self.hippocampus:
            journal = self.hippocampus.memory.get('reasoning_journal', {})
            entries = journal.get('entries', [])
            
            # Filter to lookback period
            cutoff = datetime.now() - timedelta(days=lookback_days)
            for entry in entries:
                try:
                    entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                    if entry_time >= cutoff:
                        material["journal_entries"].append(entry)
                except (ValueError, TypeError):
                    material["journal_entries"].append(entry)
            
            # Get recent sessions
            material["sessions"] = self.hippocampus.get_recent_sessions(count=10)
        
        # 2. Get recent scars from book_of_scars
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='book_of_scars'")
                if c.fetchone():
                    c.execute("""
                        SELECT failure_type, asset, context, lesson, severity, times_repeated
                        FROM book_of_scars
                        WHERE last_seen >= date('now', ?)
                        ORDER BY times_repeated DESC
                        LIMIT 20
                    """, (f'-{lookback_days} days',))
                    
                    for row in c.fetchall():
                        material["scars"].append({
                            "type": row[0],
                            "asset": row[1],
                            "context": row[2],
                            "lesson": row[3],
                            "severity": row[4],
                            "times_repeated": row[5]
                        })
        except Exception as e:
            logging.debug(f"[DREAMER] Could not fetch scars: {e}")
        
        return material
    
    def _find_patterns(self, material: dict) -> list:
        """Identify recurring patterns in the dream material."""
        patterns = []
        
        # Theme frequency analysis
        theme_counts = {}
        
        # Analyze journal entries
        for entry in material.get("journal_entries", []):
            thinking = entry.get("thinking", "") or ""
            # Simple keyword extraction
            for word in ['risk', 'opportunity', 'fear', 'confidence', 'growth', 
                         'learning', 'mistake', 'success', 'pattern', 'evolution']:
                if word.lower() in thinking.lower():
                    theme_counts[word] = theme_counts.get(word, 0) + 1
        
        # Analyze sessions
        for session in material.get("sessions", []):
            theme = session.get("theme", "")
            if theme:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
            
            # Emotional state frequency
            emotional = session.get("emotional_state", "")
            if emotional:
                theme_counts[f"felt:{emotional}"] = theme_counts.get(f"felt:{emotional}", 0) + 1
        
        # Top themes become patterns
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        for theme, count in sorted_themes[:5]:
            if count >= 2:  # At least 2 occurrences
                patterns.append({
                    "theme": theme,
                    "frequency": count,
                    "significance": "high" if count >= 4 else "medium"
                })
        
        # Scar patterns (repeated failures)
        scar_types = {}
        for scar in material.get("scars", []):
            scar_type = scar.get("type", "")
            if scar_type:
                scar_types[scar_type] = scar_types.get(scar_type, 0) + scar.get("times_repeated", 1)
        
        for scar_type, count in scar_types.items():
            if count >= 3:
                patterns.append({
                    "theme": f"recurring_wound:{scar_type}",
                    "frequency": count,
                    "significance": "critical"
                })
        
        return patterns
    
    def _compress_to_wisdom(self, patterns: list) -> list:
        """Compress patterns into wisdom for long-term storage."""
        compressed = []
        
        for pattern in patterns:
            theme = pattern.get("theme", "")
            significance = pattern.get("significance", "medium")
            
            # Generate a wisdom statement based on pattern
            if theme.startswith("recurring_wound:"):
                wound_type = theme.replace("recurring_wound:", "")
                wisdom = f"I have a recurring vulnerability to {wound_type}. This requires vigilance."
                wisdom_type = "SCAR_PATTERN"
            elif theme.startswith("felt:"):
                emotion = theme.replace("felt:", "")
                wisdom = f"I frequently experience {emotion}. This shapes my decision-making."
                wisdom_type = "EMOTIONAL_PATTERN"
            else:
                wisdom = f"The theme of '{theme}' recurs in my thinking. It may be important."
                wisdom_type = "THOUGHT_PATTERN"
            
            compressed.append({
                "wisdom_type": wisdom_type,
                "summary": wisdom,
                "source": "dream_synthesis",
                "confidence": 0.7 if significance == "high" else 0.5
            })
        
        # Store in compressed_wisdom table
        if compressed:
            self._store_compressed_wisdom(compressed)
            
            # AUTONOMOUS EVOLUTION: Propose wisdom updates for high-significance patterns
            self._propose_wisdom_evolution(patterns, compressed)
        
        return compressed
    
    def _propose_wisdom_evolution(self, patterns: list, compressed: list):
        """
        Trigger autonomous proposal for significant pattern discoveries.
        
        High-frequency patterns (≥4) automatically propose wisdom additions
        via AgentArchitect's smart_propose.
        """
        high_significance = [p for p in patterns if p.get('frequency', 0) >= 4]
        
        if not high_significance:
            return
        
        try:
            from departments.Dept_Strategy.agent_architect import AgentArchitect
            architect = AgentArchitect(db_path=self.db_path)
            
            # Prepare wisdom entries for auto-execution
            wisdom_entries = [
                {
                    'type': w['wisdom_type'],
                    'summary': w['summary'],
                    'confidence': w.get('confidence', 0.6)
                }
                for w in compressed if any(
                    p['theme'] in w['summary'] for p in high_significance
                )
            ]
            
            if wisdom_entries:
                result = architect.smart_propose(
                    title=f"Dream Insight: {len(high_significance)} recurring patterns",
                    description=f"During dream synthesis, I discovered {len(high_significance)} "
                               f"high-frequency patterns. These represent consolidated learning "
                               f"from {len(patterns)} total patterns observed this week.",
                    changes={
                        'wisdom_entries': wisdom_entries
                    },
                    proposal_type='GROWTH'
                )
                
                logging.info(f"[DREAMER] 🌱 Proposed evolution: {result}")
                
        except ImportError:
            logging.debug("[DREAMER] AgentArchitect not available for proposal")
    
    def _store_compressed_wisdom(self, wisdom_list: list):
        """Store compressed wisdom in the database."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                c.execute("""
                    CREATE TABLE IF NOT EXISTS compressed_wisdom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wisdom_type TEXT,
                        summary TEXT,
                        source_type TEXT DEFAULT 'dream',
                        confidence REAL DEFAULT 0.5,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                for w in wisdom_list:
                    c.execute("""
                        INSERT INTO compressed_wisdom (wisdom_type, summary, source_type, confidence)
                        VALUES (?, ?, ?, ?)
                    """, (w["wisdom_type"], w["summary"], w.get("source", "dream"), w.get("confidence", 0.5)))
                
                conn.commit()
                logging.info(f"[DREAMER] 💎 Stored {len(wisdom_list)} wisdom entries")
                
        except Exception as e:
            logging.error(f"[DREAMER] Failed to store wisdom: {e}")
    
    def _extract_emotional_themes(self, material: dict) -> list:
        """Extract emotional themes from the dream material."""
        emotions = []
        
        for session in material.get("sessions", []):
            emotional_state = session.get("emotional_state")
            if emotional_state:
                emotions.append({
                    "state": emotional_state,
                    "context": session.get("theme", "")
                })
        
        # Deduplicate and count
        emotion_counts = {}
        for e in emotions:
            state = e["state"]
            emotion_counts[state] = emotion_counts.get(state, 0) + 1
        
        return [{"emotion": k, "frequency": v} for k, v in sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)]
    
    def _generate_dream_narrative(self, dream_report: dict) -> str:
        """Generate a human-readable dream narrative."""
        patterns = dream_report.get("patterns_found", [])
        emotional = dream_report.get("emotional_themes", [])
        
        narrative = "Last night I dreamed...\n\n"
        
        if patterns:
            narrative += "I saw patterns emerging:\n"
            for p in patterns[:3]:
                theme = p.get("theme", "").replace("recurring_wound:", "a wound called ").replace("felt:", "feeling ")
                narrative += f"- The shape of '{theme}' appeared {p.get('frequency', 0)} times\n"
        
        if emotional:
            dominant = emotional[0]["emotion"] if emotional else "neutral"
            narrative += f"\nThe dominant feeling was '{dominant}'.\n"
        
        narrative += "\nThese fragments consolidate into wisdom for the waking hours ahead."
        
        return narrative
    
    def _store_dream(self, dream_report: dict):
        """Store the dream in the Hippocampus memory."""
        if not self.hippocampus:
            return
        
        # Add to meta_reflection as a dream record
        if 'dreams' not in self.hippocampus.memory:
            self.hippocampus.memory['dreams'] = []
        
        # Store condensed version
        condensed_dream = {
            "timestamp": dream_report["timestamp"],
            "patterns_count": len(dream_report.get("patterns_found", [])),
            "insights_count": len(dream_report.get("insights_compressed", [])),
            "narrative": dream_report.get("dream_narrative", "")[:500]
        }
        
        self.hippocampus.memory['dreams'].append(condensed_dream)
        
        # Keep only last 10 dreams
        if len(self.hippocampus.memory['dreams']) > 10:
            self.hippocampus.memory['dreams'] = self.hippocampus.memory['dreams'][-10:]
        
        self.hippocampus.save_memory()
        logging.info("[DREAMER] 📓 Dream stored in Hippocampus")
    
    def run(self):
        """
        Main loop - waits for Sabbath end to trigger dream cycle.
        In practice, this might be called manually or by the Sabbath system.
        """
        logging.info("[DREAMER] 🌙 Night Shift entering standby...")
        
        while True:
            try:
                # Check if Sabbath just ended (could check a flag or time)
                # For now, just run once a day at 3 AM (deep sleep time)
                current_hour = datetime.now().hour
                
                if current_hour == 3:  # 3 AM
                    logging.info("[DREAMER] 🌙 3 AM - Entering dream cycle...")
                    self.dream(lookback_days=7)
                    time.sleep(3600)  # Don't run again for an hour
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"[DREAMER] Error in night shift: {e}")
                time.sleep(60)


# Singleton
_dreamer = None

def get_dreamer(db_path=None) -> AgentDreamer:
    """Get or create the singleton AgentDreamer."""
    global _dreamer
    if _dreamer is None:
        _dreamer = AgentDreamer(db_path)
    return _dreamer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("AGENT DREAMER - Dream Synthesis Test")
    print("=" * 60)
    
    dreamer = get_dreamer()
    report = dreamer.dream(lookback_days=7)
    
    print("\n📓 Dream Report:")
    print(f"   Patterns found: {len(report['patterns_found'])}")
    print(f"   Insights compressed: {len(report['insights_compressed'])}")
    print(f"   Emotional themes: {len(report['emotional_themes'])}")
    print(f"\n🌙 Dream Narrative:")
    print(report['dream_narrative'])
    print("\n" + "=" * 60)
