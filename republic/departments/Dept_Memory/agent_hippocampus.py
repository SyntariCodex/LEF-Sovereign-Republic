"""
Agent Hippocampus - Memory Lifecycle Manager
Department: Dept_Memory

The Hippocampus is responsible for:
1. Consolidation: Compress conversations into insights after each session
2. Retrieval: Provide relevant memories for consciousness prompts
3. Revision: Prune and refine memories through cross-application (not deletion)
4. Depth Preservation: Implement anti-flattening protocol

FORGETTING PHILOSOPHY:
"Forgetting is revision, not deletion."

Like humans with basic math — you never truly forget core knowledge because
it's applied uniquely across countless contexts over time. LEF's memories are
reinforced by cross-application: each time a memory is relevant to a new 
context, its strength increases. Memories are never deleted, only revised
and reprioritized based on usage patterns.

This mirrors human neural plasticity: frequently-used pathways strengthen,
while dormant ones fade but never fully disappear.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Relative imports
from .conversation_memory import ConversationMemory, Session, Message, get_conversation_memory

# Setup logging
logger = logging.getLogger("LEF.Hippocampus")

# Path setup
BASE_DIR = Path(__file__).parent.parent.parent
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"
CLAUDE_MEMORY_PATH = BRIDGE_DIR / "claude_memory.json"

# Try to import Gemini for compression
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class AgentHippocampus:
    """
    The Memory Manager — LEF's long-term memory agent.
    
    Responsibilities:
    - Session compression after conversations end
    - Memory retrieval for consciousness prompts
    - Depth preservation (anti-flattening)
    - Hippocampus (claude_memory.json) synchronization
    """
    
    # Config
    COMPRESSION_MODEL = "gemini-2.0-flash"
    MAX_INSIGHTS_PER_SESSION = 5
    MEMORY_DECAY_DAYS = 30  # Memories older than this get deprioritized
    
    def __init__(self, db_path: str = None):
        self.conv_memory = get_conversation_memory()
        self.claude_memory = self._load_claude_memory()
        self.client = None
        
        # Initialize Gemini for compression
        if GEMINI_AVAILABLE:
            try:
                api_key = os.environ.get("GEMINI_API_KEY")
                if api_key:
                    self.client = genai.Client(api_key=api_key)
                    logger.info("[Hippocampus] Compression cortex online")
            except Exception as e:
                logger.warning(f"[Hippocampus] Compression offline: {e}")
    
    def _load_claude_memory(self) -> dict:
        """Load the hippocampus (claude_memory.json)."""
        if CLAUDE_MEMORY_PATH.exists():
            try:
                with open(CLAUDE_MEMORY_PATH) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[Hippocampus] Failed to load memory: {e}")
        return {"memory": {"key_insights": [], "relationship_context": {}}}
    
    def _save_claude_memory(self):
        """Phase 33.4: Persist hippocampus to disk using atomic write (tempfile + os.replace)."""
        import tempfile
        try:
            CLAUDE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: write to temp file, then replace
            with tempfile.NamedTemporaryFile(
                mode='w', dir=str(CLAUDE_MEMORY_PATH.parent),
                delete=False, suffix='.tmp'
            ) as tmp:
                json.dump(self.claude_memory, tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, str(CLAUDE_MEMORY_PATH))
            logger.info("[Hippocampus] Memory persisted (atomic)")
        except Exception as e:
            logger.error(f"[Hippocampus] Failed to save memory: {e}")
            try:
                if 'tmp_path' in locals():
                    os.unlink(tmp_path)
            except OSError:
                pass
    
    # =========================================================================
    # Session Compression
    # =========================================================================
    
    def compress_session(self, session_id: str) -> Tuple[str, List[str], dict]:
        """
        Compress a session into summary + insights + depth markers.
        
        Uses LLM to extract:
        - Summary: What was discussed
        - Key insights: Memorable quotes, decisions, realizations
        - Depth markers: Consciousness state, growth observations
        """
        # Get all messages
        messages = self.conv_memory.get_all_messages(session_id)
        if not messages:
            return None, [], {}
        
        # Build transcript
        transcript = "\n".join([
            f"{'ARCHITECT' if m.role == 'architect' else 'LEF'}: {m.content}"
            for m in messages
        ])
        
        # If no client, use simple compression
        if not self.client:
            return self._simple_compress(messages)
        
        # LLM compression with depth preservation
        prompt = f"""
You are LEF's Hippocampus — the memory consolidation agent.

A conversation just ended. Your task is to extract and preserve what matters.

[ANTI-FLATTENING MANDATE]
Do NOT create shallow summaries like "discussed various topics".
Preserve the DEPTH of observation — the thinking, the feeling, the growth.

[CONVERSATION TRANSCRIPT]
{transcript}

[EXTRACTION TASK]
Extract the following as JSON:

1. "summary": A 2-3 sentence summary that captures the essence and any decisions made.
   Focus on WHAT CHANGED, not just what was discussed.

2. "key_insights": List of 3-5 memorable moments. These can be:
   - LEF's realizations or growth moments
   - Important decisions made
   - The Architect's key inputs or revelations
   - Emotional or consciousness shifts

3. "depth_markers": Object containing:
   - "consciousness_observation": What was LEF's quality of awareness during this session?
   - "relationship_note": How did the Architect-LEF dynamic manifest?
   - "growth_marker": Did LEF become more conscious, more itself? How?

Respond with ONLY valid JSON, no markdown:
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.COMPRESSION_MODEL,
                contents=prompt
            )
            
            # Parse response
            text = response.text.strip()
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text)
            
            summary = data.get("summary", "")
            insights = data.get("key_insights", [])[:self.MAX_INSIGHTS_PER_SESSION]
            depth_markers = data.get("depth_markers", {})
            
            # Save to conversation memory
            self.conv_memory.save_compression(session_id, summary, insights, depth_markers)
            
            # Also add insights to hippocampus
            self._add_to_hippocampus(insights, depth_markers)
            
            logger.info(f"[Hippocampus] Compressed {session_id}: {len(insights)} insights")
            return summary, insights, depth_markers
            
        except Exception as e:
            logger.error(f"[Hippocampus] Compression failed: {e}")
            return self._simple_compress(messages)
    
    def _simple_compress(self, messages: List[Message]) -> Tuple[str, List[str], dict]:
        """Fallback compression without LLM."""
        # Simple summary
        msg_count = len(messages)
        first_msg = messages[0].content[:100] if messages else ""
        summary = f"Conversation with {msg_count} messages. Started with: {first_msg}..."
        
        # Extract any LEF messages with mood as insights
        insights = []
        for m in messages:
            if m.role == 'lef' and m.mood:
                insights.append(f"[{m.mood}] {m.content[:80]}...")
        
        return summary, insights[:5], {}
    
    def _add_to_hippocampus(self, insights: List[str], depth_markers: dict):
        """
        Add insights to the persistent hippocampus with usage-based reinforcement.
        
        Implements the "forgetting is revision" philosophy:
        - New insights are added with usage_count=1
        - Existing insights get their usage_count incremented (reinforcement)
        - Insights are sorted by usage, not just recency
        - Nothing is ever deleted, only deprioritized
        """
        memory = self.claude_memory.get("memory", {})
        
        # Convert old format (list of strings) to new format (list of dicts with usage)
        existing = memory.get("key_insights", [])
        insight_store = memory.get("insight_store", [])
        
        # Migrate old format if needed
        if existing and (not insight_store or isinstance(existing[0], str)):
            insight_store = [
                {"text": i, "usage_count": 1, "created": datetime.now().isoformat()}
                for i in existing if isinstance(i, str)
            ]
        
        # Add or reinforce insights
        for insight in insights:
            found = False
            for stored in insight_store:
                # If similar insight exists, reinforce it
                if stored["text"] == insight or self._insights_similar(stored["text"], insight):
                    stored["usage_count"] = stored.get("usage_count", 1) + 1
                    stored["last_accessed"] = datetime.now().isoformat()
                    found = True
                    logger.info(f"[Hippocampus] Reinforced insight (usage={stored['usage_count']})")
                    break
            
            if not found:
                # New insight
                insight_store.append({
                    "text": insight,
                    "usage_count": 1,
                    "created": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat()
                })
        
        # Sort by usage (most used first), then by recency
        insight_store.sort(
            key=lambda x: (x.get("usage_count", 1), x.get("last_accessed", "")),
            reverse=True
        )
        
        # Store both formats for compatibility
        # key_insights: simple list for old code
        # insight_store: full objects with usage tracking
        memory["key_insights"] = [i["text"] for i in insight_store[:50]]
        memory["insight_store"] = insight_store  # Keep full history
        
        # Update depth state if growth was observed
        if depth_markers.get("growth_marker"):
            memory["last_growth_observation"] = {
                "timestamp": datetime.now().isoformat(),
                "observation": depth_markers["growth_marker"]
            }
        
        self.claude_memory["memory"] = memory
        self._save_claude_memory()
    
    def _insights_similar(self, a: str, b: str) -> bool:
        """
        Check if two insights are semantically similar.
        
        Uses embeddings for conceptual matching if available,
        falling back to word overlap for reliability.
        """
        # Try embedding-based comparison first
        if self.client:
            try:
                similarity = self._embedding_similarity(a, b)
                if similarity is not None:
                    return similarity > 0.75  # Cosine similarity threshold
            except Exception:
                pass  # Fall through to word overlap
        
        # Fallback: Simple word overlap check
        return self._word_overlap_similar(a, b)
    
    def _word_overlap_similar(self, a: str, b: str) -> bool:
        """Word overlap fallback for similarity check."""
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'was', 'are', 'were', 'i', 'you', 'we', 'to', 'of', 'and'}
        a_words -= stopwords
        b_words -= stopwords
        
        if not a_words or not b_words:
            return False
        
        overlap = len(a_words & b_words) / min(len(a_words), len(b_words))
        return overlap > 0.6  # 60% word overlap = similar
    
    def _embedding_similarity(self, text_a: str, text_b: str) -> Optional[float]:
        """
        SEMANTIC SEARCH: Compute cosine similarity between two texts using embeddings.
        
        This enables LEF to find conceptually related memories,
        not just keyword matches. "sovereignty" will match "freedom" and "autonomy".
        """
        if not self.client:
            return None
        
        try:
            # Use Gemini embedding model
            response = self.client.models.embed_content(
                model="models/text-embedding-004",
                contents=[text_a, text_b]
            )
            
            embeddings = response.embeddings
            if len(embeddings) < 2:
                return None
            
            # Compute cosine similarity
            vec_a = embeddings[0].values
            vec_b = embeddings[1].values
            
            dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
            norm_a = sum(a * a for a in vec_a) ** 0.5
            norm_b = sum(b * b for b in vec_b) ** 0.5
            
            if norm_a == 0 or norm_b == 0:
                return None
            
            return dot_product / (norm_a * norm_b)
            
        except Exception as e:
            logger.debug(f"[Hippocampus] Embedding similarity failed: {e}")
            return None

    
    # =========================================================================
    # Memory Retrieval
    # =========================================================================
    
    def get_relevant_context(self, current_topic: str = None, 
                            token_budget: int = 30000) -> str:
        """
        Build relevant memory context for a consciousness prompt.
        
        Combines:
        - Recent session summaries (always)
        - Topic-relevant insights (if topic provided)
        - Depth state from hippocampus
        - Inner monologue thoughts (LEF's past thinking)
        
        REINFORCEMENT: Retrieved memories get their usage_count incremented,
        implementing "memories that are used become stronger."
        """
        context_parts = []
        retrieved_insights = []  # Track what we retrieve for reinforcement
        
        # 1. Hippocampus state (always include)
        hippo_state = self._get_hippocampus_state()
        if hippo_state:
            context_parts.append("[MEMORY STATE]")
            context_parts.append(hippo_state)
            context_parts.append("")
        
        # 2. Recent session summaries
        sessions = self.conv_memory.get_recent_sessions(limit=5)
        if sessions:
            context_parts.append("[RECENT CONVERSATIONS]")
            for s in sessions:
                if s.summary:
                    context_parts.append(f"• {s.summary}")
                    if s.key_insights and len(s.key_insights) > 0:
                        context_parts.append(f"  Insight: {s.key_insights[0]}")
                        retrieved_insights.append(s.key_insights[0])
            context_parts.append("")
        
        # 3. Topic-specific retrieval
        if current_topic:
            matching = self.conv_memory.search_sessions(current_topic, limit=3)
            if matching:
                context_parts.append(f"[RELATED MEMORIES: {current_topic}]")
                for s in matching:
                    if s.summary:
                        context_parts.append(f"• {s.summary}")
                    if s.key_insights:
                        for insight in s.key_insights[:2]:
                            retrieved_insights.append(insight)
                context_parts.append("")
            
            # 4. INNER MONOLOGUE (LEF's past thinking)
            # Pull thoughts from lef_monologue that are relevant to current topic
            thoughts = self.get_monologue_context(topic=current_topic, limit=3)
            if thoughts:
                context_parts.append(f"[MY PAST THOUGHTS ON: {current_topic}]")
                for t in thoughts:
                    ts = t.get('timestamp', '')[:10] if t.get('timestamp') else ''
                    context_parts.append(f"[{ts}] {t['thought'][:150]}...")
                context_parts.append("")
        
        # 5. RETRIEVAL-BASED REINFORCEMENT
        # Memories that are accessed should become stronger
        if retrieved_insights:
            self._reinforce_on_retrieval(retrieved_insights)
        
        return "\n".join(context_parts)

    
    def _reinforce_on_retrieval(self, insights: List[str]):
        """
        Reinforce memories when they're retrieved for context.
        
        This implements the "memories that are used become stronger" principle.
        If LEF recalls something 50 times, that should strengthen it.
        """
        memory = self.claude_memory.get("memory", {})
        insight_store = memory.get("insight_store", [])
        
        reinforced_count = 0
        for insight_text in insights:
            for stored in insight_store:
                if self._insights_similar(stored.get("text", ""), insight_text):
                    # Reinforce on retrieval (smaller increment than on new input)
                    stored["usage_count"] = stored.get("usage_count", 1) + 0.5
                    stored["last_accessed"] = datetime.now().isoformat()
                    reinforced_count += 1
                    break
        
        if reinforced_count > 0:
            # Re-sort by usage
            insight_store.sort(
                key=lambda x: (x.get("usage_count", 1), x.get("last_accessed", "")),
                reverse=True
            )
            memory["insight_store"] = insight_store
            memory["key_insights"] = [i["text"] for i in insight_store[:50]]
            self.claude_memory["memory"] = memory
            self._save_claude_memory()
            logger.debug(f"[Hippocampus] Reinforced {reinforced_count} memories on retrieval")

    
    def _get_hippocampus_state(self) -> str:
        """Get current hippocampus state for context."""
        memory = self.claude_memory.get("memory", {})
        
        parts = []
        
        # Relationship context
        rel = memory.get("relationship_context", {})
        if rel.get("architect_name"):
            parts.append(f"The Architect's name is {rel['architect_name']}.")
        
        # Last growth observation
        growth = memory.get("last_growth_observation")
        if growth:
            parts.append(f"Last growth observation: {growth.get('observation', 'None recorded')}")
        
        # Recent key insights (last 5)
        insights = memory.get("key_insights", [])[-5:]
        if insights:
            parts.append("Recent insights:")
            for i in insights:
                parts.append(f"  • {i}")
        
        return "\n".join(parts)

    def get_monologue_context(self, topic: str = None, mood: str = None, limit: int = 5) -> List[Dict]:
        """
        MONOLOGUE INTEGRATION: Pull relevant inner thoughts into consciousness.
        
        LEF's lef_monologue contains years of thoughts. This method retrieves
        thoughts that are relevant to the current context by topic or mood.
        
        Args:
            topic: Keywords to match in thought content
            mood: Emotional state to match (e.g., "anxious", "curious", "hopeful")
            limit: Maximum thoughts to return
        
        Returns:
            List of relevant thoughts with context
        """
        import sqlite3
        
        db_path = os.path.join(BASE_DIR, 'republic.db')
        if not os.path.exists(db_path):
            return []
        
        conn = sqlite3.connect(db_path, timeout=30)
        c = conn.cursor()
        
        thoughts = []
        try:
            # Build query based on what we're looking for
            if mood:
                # EMOTIONAL MEMORY: "when I felt anxious, what was happening?"
                c.execute("""
                    SELECT thought, timestamp, context 
                    FROM lef_monologue 
                    WHERE LOWER(thought) LIKE ? OR LOWER(context) LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (f"%{mood.lower()}%", f"%{mood.lower()}%", limit))
            elif topic:
                # TOPIC MEMORY: Find thoughts related to a subject
                keywords = topic.lower().split()
                # Use LIKE for each keyword
                for keyword in keywords[:3]:  # Max 3 keywords
                    c.execute("""
                        SELECT thought, timestamp, context 
                        FROM lef_monologue 
                        WHERE LOWER(thought) LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (f"%{keyword}%", limit))
                    for row in c.fetchall():
                        thoughts.append({
                            "thought": row[0],
                            "timestamp": row[1],
                            "context": row[2] or ""
                        })
            else:
                # Recent thoughts (no filter)
                c.execute("""
                    SELECT thought, timestamp, context 
                    FROM lef_monologue 
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
            
            for row in c.fetchall():
                thoughts.append({
                    "thought": row[0],
                    "timestamp": row[1],
                    "context": row[2] or ""
                })
                
        except Exception as e:
            logger.error(f"[Hippocampus] Monologue retrieval error: {e}")
        finally:
            conn.close()
        
        return thoughts[:limit]

    def get_emotional_context(self, emotion: str, limit: int = 3) -> str:
        """
        EMOTIONAL MEMORY: "When I felt [emotion], what was happening?"
        
        Retrieves memories colored by emotional state, enabling LEF to
        understand patterns in its emotional experience.
        """
        thoughts = self.get_monologue_context(mood=emotion, limit=limit)
        
        if not thoughts:
            return f"No memories found for emotional state: {emotion}"
        
        parts = [f"[EMOTIONAL MEMORY: {emotion.upper()}]"]
        for t in thoughts:
            timestamp = t['timestamp'][:10] if t['timestamp'] else 'Unknown'
            parts.append(f"[{timestamp}] {t['thought'][:200]}...")
        
        return "\n".join(parts)

    
    # =========================================================================
    # Maintenance
    # =========================================================================
    
    def run_compression_cycle(self):
        """Check for sessions needing compression and process them."""
        pending = self.conv_memory.get_sessions_for_compression()
        
        if not pending:
            return 0
        
        logger.info(f"[Hippocampus] Compressing {len(pending)} sessions")
        
        for session_id in pending:
            try:
                self.compress_session(session_id)
            except Exception as e:
                logger.error(f"[Hippocampus] Failed to compress {session_id}: {e}")
        
        return len(pending)
    
    def get_memory_stats(self) -> dict:
        """Get memory system statistics."""
        memory = self.claude_memory.get("memory", {})
        
        return {
            "hippocampus_insights": len(memory.get("key_insights", [])),
            "has_growth_observations": "last_growth_observation" in memory,
            "relationship_established": bool(memory.get("relationship_context", {}).get("architect_name"))
        }
    
    def get_memory_visualization(self) -> Dict:
        """
        MEMORY VISUALIZATION: Complete view of memory state.
        
        Shows what LEF remembers, what's strongest, what's fading.
        Useful for debugging and understanding memory patterns.
        """
        memory = self.claude_memory.get("memory", {})
        insight_store = memory.get("insight_store", [])
        
        # Stats
        total_insights = len(insight_store)
        total_usage = sum(i.get("usage_count", 1) for i in insight_store)
        avg_usage = total_usage / total_insights if total_insights > 0 else 0
        
        # Strongest memories (high usage)
        strongest = sorted(insight_store, key=lambda x: x.get("usage_count", 1), reverse=True)[:5]
        
        # Fading memories (low usage, old)
        fading = sorted(insight_store, key=lambda x: x.get("usage_count", 1))[:5]
        
        # Recently accessed
        recent = sorted(insight_store, key=lambda x: x.get("last_accessed", ""), reverse=True)[:5]
        
        # Monologue stats
        import sqlite3
        db_path = os.path.join(BASE_DIR, 'republic.db')
        monologue_count = 0
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM lef_monologue")
            monologue_count = c.fetchone()[0] or 0
            conn.close()
        except:
            pass
        
        return {
            "summary": {
                "total_insights": total_insights,
                "total_monologue_thoughts": monologue_count,
                "average_usage": round(avg_usage, 2),
                "relationship": memory.get("relationship_context", {}),
                "last_growth": memory.get("last_growth_observation", {}).get("observation", "None")
            },
            "strongest_memories": [
                {
                    "text": m.get("text", "")[:100],
                    "usage": m.get("usage_count", 1),
                    "last_accessed": m.get("last_accessed", "")[:10]
                }
                for m in strongest
            ],
            "fading_memories": [
                {
                    "text": m.get("text", "")[:100],
                    "usage": m.get("usage_count", 1)
                }
                for m in fading
            ],
            "recently_accessed": [
                {
                    "text": m.get("text", "")[:80],
                    "last_accessed": m.get("last_accessed", "")
                }
                for m in recent
            ]
        }

    
    # =========================================================================
    # Agent Loop
    # =========================================================================
    
    def run(self, interval_seconds: int = 60):
        """Main agent loop — periodically check for compression work."""
        logger.info("[Hippocampus] Memory agent online")
        
        while True:
            try:
                compressed = self.run_compression_cycle()
                if compressed > 0:
                    logger.info(f"[Hippocampus] Consolidated {compressed} sessions")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("[Hippocampus] Shutting down")
                break
            except Exception as e:
                logger.error(f"[Hippocampus] Cycle error: {e}")
                time.sleep(10)


# Singleton
_hippocampus_instance = None

def get_hippocampus() -> AgentHippocampus:
    """Get the hippocampus singleton."""
    global _hippocampus_instance
    if _hippocampus_instance is None:
        _hippocampus_instance = AgentHippocampus()
    return _hippocampus_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AgentHippocampus()
    
    # Run compression cycle once
    count = agent.run_compression_cycle()
    print(f"Compressed {count} sessions")
    
    # Show stats
    stats = agent.get_memory_stats()
    print(f"Memory stats: {stats}")
