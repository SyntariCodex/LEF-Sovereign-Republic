"""
Scar Resonance System
The memory that arises before action.

Purpose: When LEF is about to take an action, this system checks if the context
"rhymes" with past wounds in book_of_scars or patterns in reasoning_journal.
If resonance is detected, it surfaces the memory as awareness—not a veto.

Usage:
    from system.scar_resonance import get_resonance_engine
    
    engine = get_resonance_engine()
    resonance = engine.check(action='BUY', asset='BTC', context={'rsi': 25})
    
    if resonance['detected']:
        print(f"⚠️ SCAR RESONANCE: {resonance['memory']}")
        print(f"   Lesson: {resonance['lesson']}")
"""

import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from difflib import SequenceMatcher

# Path discovery
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

logger = logging.getLogger(__name__)


class ScarResonance:
    """
    The Scar Resonance Engine.
    
    Checks if current actions rhyme with past wounds.
    Returns awareness, not vetoes.
    """
    
    # Similarity threshold for pattern matching
    SIMILARITY_THRESHOLD = 0.4
    
    # How far back to look in reasoning journal
    JOURNAL_LOOKBACK_DAYS = 30
    
    def __init__(self, db_path: str = None, hippocampus=None):
        self.db_path = db_path or DB_PATH
        self.hippocampus = hippocampus
        
        # Try to connect to Hippocampus if not provided
        if self.hippocampus is None:
            try:
                from departments.Dept_Consciousness.claude_context_manager import get_claude_context_manager
                self.hippocampus = get_claude_context_manager()
            except Exception:
                self.hippocampus = None
    
    def check(
        self,
        action: str,
        asset: str = None,
        context: Dict = None
    ) -> Dict:
        """
        Check for resonance with past scars.
        
        Args:
            action: The action being taken (BUY, SELL, HOLD, etc.)
            asset: The asset involved (BTC, ETH, etc.)
            context: Additional context (rsi, price, reason, etc.)
            
        Returns:
            Dict with:
                - detected: bool
                - memories: List of matching scars/patterns
                - strongest: The strongest match (if any)
                - awareness_message: Human-readable warning
        """
        result = {
            'detected': False,
            'memories': [],
            'strongest': None,
            'awareness_message': None,
            'checked_at': datetime.now().isoformat()
        }
        
        # Build search context
        search_context = self._build_search_context(action, asset, context)
        
        # Check book_of_scars
        scar_matches = self._check_scars(search_context, asset)
        result['memories'].extend(scar_matches)
        
        # Check reasoning_journal (if Hippocampus available)
        if self.hippocampus:
            journal_matches = self._check_journal(search_context)
            result['memories'].extend(journal_matches)
        
        # Determine if resonance detected
        if result['memories']:
            result['detected'] = True
            
            # Find strongest match
            result['strongest'] = max(result['memories'], key=lambda x: x['similarity'])
            
            # Build awareness message
            strongest = result['strongest']
            result['awareness_message'] = self._format_awareness(strongest)
            
            logger.info(f"[SCAR_RESONANCE] ⚠️ Resonance detected for {action} {asset}")
            logger.info(f"   Match: {strongest['summary'][:80]}...")
        
        return result
    
    def _build_search_context(self, action: str, asset: str, context: Dict) -> str:
        """Build a searchable string from the action context."""
        parts = [action]
        if asset:
            parts.append(asset)
        if context:
            # Add relevant context fields
            for key in ['reason', 'signal', 'strategy', 'rsi', 'regime']:
                if key in context:
                    parts.append(f"{key}:{context[key]}")
        return ' '.join(str(p) for p in parts)
    
    def _check_scars(self, search_context: str, asset: str = None) -> List[Dict]:
        """Check book_of_scars for matching wounds."""
        matches = []
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Check if table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='book_of_scars'")
            if not c.fetchone():
                conn.close()
                return matches
            
            # Query recent scars (prioritize same asset, but check all)
            if asset:
                c.execute("""
                    SELECT failure_type, asset, action, context, lesson, severity, times_repeated
                    FROM book_of_scars
                    WHERE asset = ? OR times_repeated >= 3
                    ORDER BY times_repeated DESC, last_seen DESC
                    LIMIT 20
                """, (asset,))
            else:
                c.execute("""
                    SELECT failure_type, asset, action, context, lesson, severity, times_repeated
                    FROM book_of_scars
                    ORDER BY times_repeated DESC, last_seen DESC
                    LIMIT 20
                """)
            
            scars = c.fetchall()
            conn.close()
            
            for scar in scars:
                # Build scar context for comparison
                scar_context = f"{scar['action']} {scar['asset']} {scar['context'] or ''}"
                
                # Calculate similarity
                similarity = self._calculate_similarity(search_context, scar_context)
                
                # Boost similarity for same asset
                if asset and scar['asset'] == asset:
                    similarity = min(1.0, similarity + 0.2)
                
                # Boost for high repeat count
                if scar['times_repeated'] >= 5:
                    similarity = min(1.0, similarity + 0.15)
                
                if similarity >= self.SIMILARITY_THRESHOLD:
                    matches.append({
                        'type': 'SCAR',
                        'source': 'book_of_scars',
                        'failure_type': scar['failure_type'],
                        'asset': scar['asset'],
                        'summary': scar['context'] or f"{scar['failure_type']} on {scar['asset']}",
                        'lesson': scar['lesson'],
                        'severity': scar['severity'],
                        'times_repeated': scar['times_repeated'],
                        'similarity': round(similarity, 3)
                    })
            
        except Exception as e:
            logger.error(f"[SCAR_RESONANCE] Error checking scars: {e}")
        
        return matches
    
    def _check_journal(self, search_context: str) -> List[Dict]:
        """Check reasoning_journal for matching patterns."""
        matches = []
        
        if not self.hippocampus:
            return matches
        
        try:
            journal = self.hippocampus.memory.get('reasoning_journal', {})
            entries = journal.get('entries', [])
            
            # Look at recent entries
            cutoff = datetime.now() - timedelta(days=self.JOURNAL_LOOKBACK_DAYS)
            
            for entry in entries[-50:]:  # Last 50 entries max
                thinking = entry.get('thinking', '')
                timestamp = entry.get('timestamp', '')
                
                # Skip very old entries
                try:
                    entry_time = datetime.fromisoformat(timestamp)
                    if entry_time < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass
                
                # Calculate similarity
                similarity = self._calculate_similarity(search_context, thinking[:500])
                
                if similarity >= self.SIMILARITY_THRESHOLD:
                    matches.append({
                        'type': 'JOURNAL',
                        'source': 'reasoning_journal',
                        'summary': thinking[:200],
                        'timestamp': timestamp,
                        'similarity': round(similarity, 3)
                    })
            
        except Exception as e:
            logger.error(f"[SCAR_RESONANCE] Error checking journal: {e}")
        
        return matches
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize
        t1 = text1.lower()
        t2 = text2.lower()
        
        # Use sequence matcher for fuzzy matching
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _format_awareness(self, memory: Dict) -> str:
        """Format a memory match into a human-readable awareness message."""
        lines = ["⚠️ SCAR RESONANCE DETECTED"]
        
        if memory['type'] == 'SCAR':
            lines.append(f"This situation resembles: {memory.get('failure_type', 'Unknown')} on {memory.get('asset', 'Unknown')}")
            if memory.get('lesson'):
                lines.append(f"Lesson learned: {memory['lesson']}")
            if memory.get('times_repeated', 0) >= 3:
                lines.append(f"⚡ This pattern has repeated {memory['times_repeated']} times")
        else:
            lines.append(f"This resonates with past thinking:")
            lines.append(f"  \"{memory.get('summary', '')[:100]}...\"")
        
        lines.append(f"Similarity: {memory['similarity']*100:.0f}%")
        lines.append("Proceed with awareness.")
        
        return '\n'.join(lines)
    
    def log_resonance(self, resonance: Dict, action_taken: str = None):
        """Log a resonance event for future analysis."""
        if not resonance['detected']:
            return
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            # Ensure logging table exists
            c.execute("""
                CREATE TABLE IF NOT EXISTS scar_resonance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    strongest_match TEXT,
                    similarity REAL,
                    action_taken TEXT,
                    was_heeded INTEGER
                )
            """)
            
            strongest = resonance.get('strongest', {})
            c.execute("""
                INSERT INTO scar_resonance_log (strongest_match, similarity, action_taken)
                VALUES (?, ?, ?)
            """, (
                json.dumps(strongest),
                strongest.get('similarity', 0),
                action_taken
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"[SCAR_RESONANCE] Error logging resonance: {e}")
    
    def check_for_repeated_pattern(self, resonance: Dict) -> bool:
        """
        Check if the same scar has resonated 3+ times in 24 hours.
        If so, trigger autonomous proposal for awareness enhancement.
        
        Returns True if a proposal was triggered.
        """
        if not resonance['detected']:
            return False
        
        strongest = resonance.get('strongest', {})
        if not strongest or strongest.get('type') != 'SCAR':
            return False
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            # Count how many times this scar has resonated in last 24h
            c.execute("""
                SELECT COUNT(*) FROM scar_resonance_log
                WHERE datetime(timestamp) > datetime('now', '-24 hours')
                AND strongest_match LIKE ?
            """, (f"%{strongest.get('failure_type', '')}%",))
            
            count = c.fetchone()[0]
            conn.close()
            
            if count >= 3:
                # Trigger autonomous proposal
                self._propose_repeated_wound_awareness(strongest, count)
                return True
                
        except Exception as e:
            logger.error(f"[SCAR_RESONANCE] Error checking repeated pattern: {e}")
        
        return False
    
    def _propose_repeated_wound_awareness(self, scar: Dict, hit_count: int):
        """
        Autonomously propose awareness enhancement for repeated wounds.
        """
        try:
            from departments.Dept_Strategy.agent_architect import AgentArchitect
            architect = AgentArchitect(db_path=self.db_path)
            
            result = architect.smart_propose(
                title=f"Repeated Wound Alert: {scar.get('failure_type', 'Unknown')}",
                description=f"The same scar '{scar.get('failure_type', 'unknown')}' on "
                           f"{scar.get('asset', 'unknown')} has resonated {hit_count} times "
                           f"in the last 24 hours. This suggests either:\n"
                           f"- The wound needs deeper healing\n"
                           f"- Market conditions are repeatedly triggering this pattern\n"
                           f"- Consider lowering threshold for this specific context",
                changes={
                    'wisdom_entries': [{
                        'type': 'SCAR_PATTERN',
                        'summary': f"Recurring vulnerability to {scar.get('failure_type', 'unknown')} "
                                  f"on {scar.get('asset', 'unknown')}. Lesson: {scar.get('lesson', 'be vigilant')}",
                        'confidence': 0.8
                    }],
                    'threshold_updates': {
                        f"scar_sensitivity_{scar.get('asset', 'default')}": 0.3  # Lower threshold = more sensitive
                    }
                },
                proposal_type='BLIND_SPOT'
            )
            
            logger.warning(f"[SCAR_RESONANCE] 🚨 Repeated wound triggered proposal: {result}")
            
        except ImportError:
            logger.debug("[SCAR_RESONANCE] AgentArchitect not available for proposal")


    def decay_scars(self):
        """
        Phase 32.3: Apply age-based decay to scars.

        Scars that haven't been re-triggered decay over time.
        decay_factor = base_decay * (1 + 0.01 * scar_age_days)

        - Scars seen recently (< 7 days) are not decayed.
        - Scars where times_repeated drops to 0 are removed.
        - Severity downgraded over time: CRITICAL → HIGH → MEDIUM → LOW.

        Should be called once per consciousness cycle (~5 min).
        """
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='book_of_scars'")
            if not c.fetchone():
                conn.close()
                return 0

            # Get scars not seen in last 7 days
            c.execute("""
                SELECT id, severity, times_repeated, last_seen, timestamp
                FROM book_of_scars
                WHERE last_seen < datetime('now', '-7 days')
            """)
            rows = c.fetchall()

            removed = 0
            decayed = 0
            severity_order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

            for row in rows:
                scar_id, severity, times_repeated, last_seen, created = row

                # Calculate age in days
                try:
                    created_dt = datetime.fromisoformat(str(created)) if created else datetime.now()
                    age_days = (datetime.now() - created_dt).days
                except (ValueError, TypeError):
                    age_days = 30  # Default to 30 days if parse fails

                # Base decay: 0.1 per cycle, accelerated by age
                base_decay = 0.1
                decay_amount = base_decay * (1 + 0.01 * age_days)

                new_repeated = max(0, (times_repeated or 1) - decay_amount)

                if new_repeated < 0.01:
                    # Remove fully decayed scar
                    c.execute("DELETE FROM book_of_scars WHERE id = ?", (scar_id,))
                    removed += 1
                else:
                    # Downgrade severity if repeated count low
                    new_severity = severity
                    if new_repeated < 1 and severity in severity_order:
                        idx = severity_order.index(severity)
                        if idx > 0:
                            new_severity = severity_order[idx - 1]

                    c.execute(
                        "UPDATE book_of_scars SET times_repeated = ?, severity = ? WHERE id = ?",
                        (int(new_repeated) if new_repeated >= 1 else round(new_repeated, 2), new_severity, scar_id)
                    )
                    decayed += 1

            conn.commit()
            conn.close()

            if removed > 0 or decayed > 0:
                logger.info(f"[SCAR_RESONANCE] Scar decay: {decayed} decayed, {removed} removed")
            return removed + decayed

        except Exception as e:
            logger.error(f"[SCAR_RESONANCE] Scar decay error: {e}")
            return 0


def decay_scars(db_path: str = None):
    """Phase 32.3: Convenience function to run scar decay."""
    engine = get_resonance_engine(db_path)
    return engine.decay_scars()


# Singleton instance
_engine = None

def get_resonance_engine(db_path: str = None) -> ScarResonance:
    """Get or create the singleton ScarResonance engine."""
    global _engine
    if _engine is None:
        _engine = ScarResonance(db_path)
    return _engine


# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("SCAR RESONANCE - Self Test")
    print("=" * 60)
    
    engine = get_resonance_engine()
    
    # Test resonance check
    print("\n1. Testing resonance check for BTC BUY:")
    result = engine.check(
        action='BUY',
        asset='BTC',
        context={'rsi': 25, 'reason': 'oversold bounce'}
    )
    
    print(f"   Detected: {result['detected']}")
    print(f"   Memories found: {len(result['memories'])}")
    
    if result['detected']:
        print(f"\n   Awareness Message:")
        print(f"   {result['awareness_message']}")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")
