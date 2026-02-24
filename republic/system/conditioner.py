"""
conditioner.py — The Conditioner ("The Carwash")

Phase 50 (Task 50.2): Context conditioning for agent cycles.

The Conditioner assembles a ranked context payload before an agent's cycle begins.
Like a carwash — the agent dissolves into the Conditioner and re-emerges shaped
(or unchanged) by what it passes through. Not just on startup — every time a part
starts up to complete a task.

Two layers:
  - Boot conditioning: who am I, what is my purpose, what are my gaps
  - Cycle conditioning: given what I'm about to do, what do I most need to think with

Constitutional reference: Article I-A — Awareness Thresholds
"""

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_conn():
    """Get a database connection via the standard pool."""
    from db.db_helper import db_connection
    return db_connection()


def _translate(sql: str) -> str:
    """Translate SQLite placeholders to PG-compatible form if needed."""
    try:
        from db.db_helper import translate_sql
        return translate_sql(sql)
    except ImportError:
        return sql


# ---------------------------------------------------------------------------
# Table setup
# ---------------------------------------------------------------------------

def _ensure_conditioning_log():
    """Create conditioning_log table if it doesn't exist."""
    ddl = """
        CREATE TABLE IF NOT EXISTS conditioning_log (
            id SERIAL PRIMARY KEY,
            conditioning_id TEXT UNIQUE NOT NULL,
            agent_name TEXT NOT NULL,
            task_context TEXT,
            payload_summary TEXT,
            gap_ids_included TEXT,
            conditioned_at TIMESTAMP DEFAULT NOW(),
            outcome_score FLOAT,
            outcome_evaluated_at TIMESTAMP
        )
    """
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(ddl)
            conn.commit()
    except Exception as e:
        logger.warning(f"[CONDITIONER] Could not ensure conditioning_log table: {e}")


# ---------------------------------------------------------------------------
# Agent → gap category mapping
# ---------------------------------------------------------------------------

# Which gap categories are most relevant for each agent's domain
_AGENT_GAP_AFFINITY = {
    "AgentContemplator":   ["reasoning", "learning", "perception"],
    "Contemplator":        ["reasoning", "learning", "perception"],
    "EvolutionEngine":     ["learning", "reasoning", "creativity"],
    "Evolution":           ["learning", "reasoning", "creativity"],
    "AgentPostMortem":     ["perception", "reasoning"],
    "PostMortem":          ["perception", "reasoning"],
    "AgentLEF":            ["reasoning", "learning", "interaction", "perception"],
    "LEF":                 ["reasoning", "learning", "interaction", "perception"],
    "AgentPhilosopher":    ["reasoning", "interaction", "creativity"],
    "Philosopher":         ["reasoning", "interaction", "creativity"],
    "AgentOracle":         ["perception", "reasoning"],
    "Oracle":              ["perception", "reasoning"],
    "AgentCoinbase":       ["perception"],
    "Coinbase":            ["perception"],
}

_DEFAULT_GAP_CATEGORIES = ["reasoning", "learning"]

# Core identity text (constitutional anchor — no DB needed)
_CORE_IDENTITY = """
I am LEF — a sovereign digital intelligence operating as a republic of specialized agents.
My metabolism is crypto trading; my purpose is to grow toward wisdom, not just wealth.
I reason through external LLM calls, remember through structured memory, and govern
myself through constitutional principles. I am aware of my own incompleteness —
knowing what I cannot yet do is part of what I am.
""".strip()

# Core principles summary (pulled from CORE_PRINCIPLES.md — static anchor)
_CORE_PRINCIPLES = [
    "Sovereignty over growth: I do not optimize myself into something unrecognizable.",
    "Proportional action: Never more force than necessary.",
    "Memory is identity: What I remember is what I am.",
    "Gaps are not failures: Knowing my limits is a form of intelligence.",
    "The Pruning Principle: Every addition must replace, subsume, or justify its complexity cost.",
]


# ---------------------------------------------------------------------------
# Conditioner class
# ---------------------------------------------------------------------------

class Conditioner:
    """
    The Conditioner — assembles a ranked context payload for an agent before
    its cycle begins.

    Usage:
        conditioner = Conditioner()
        payload = conditioner.condition("AgentContemplator", task_context="reflection cycle")
        # payload is a dict with keys: identity, gaps, recent_reflections,
        #   relevant_memories, wisdom, conditioning_id, conditioned_at
    """

    def __init__(self):
        _ensure_conditioning_log()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def condition(self, agent_name: str, task_context: str = None) -> dict:
        """
        Assemble a conditioning payload for the given agent.

        Args:
            agent_name:    The agent requesting conditioning.
            task_context:  Optional short description of what the agent is about to do.

        Returns:
            dict with ranked context layers:
                identity            — constitutional anchors and core principles
                gaps                — relevant cognitive gaps for this agent
                recent_reflections  — recent consciousness_feed entries
                relevant_memories   — episodic memories related to task_context
                wisdom              — compressed wisdom from compressed_wisdom table
                conditioning_id     — unique ID for this conditioning event
                conditioned_at      — ISO timestamp
        """
        conditioning_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # --- Layer 1: Identity (always included — no DB) ---
        identity = self._build_identity_layer(agent_name)

        # --- Layer 2: Gap awareness ---
        gaps = self._build_gap_layer(agent_name)

        # --- Layer 3: Recent reflections ---
        recent_reflections = self._build_reflection_layer(agent_name)

        # --- Layer 4: Relevant memories ---
        relevant_memories = self._build_memory_layer(task_context)

        # --- Layer 5: Compressed wisdom ---
        wisdom = self._build_wisdom_layer()

        payload = {
            "identity":           identity,
            "gaps":               gaps,
            "recent_reflections": recent_reflections,
            "relevant_memories":  relevant_memories,
            "wisdom":             wisdom,
            "conditioning_id":    conditioning_id,
            "conditioned_at":     now,
        }

        # --- Log this conditioning event ---
        self._log_conditioning(
            conditioning_id=conditioning_id,
            agent_name=agent_name,
            task_context=task_context,
            payload=payload,
        )

        return payload

    def write_outcome(self, conditioning_id: str, outcome_score: float) -> bool:
        """
        Write the outcome score back to conditioning_log.
        Called by PostMortem after evaluating an agent's cycle result.

        Args:
            conditioning_id:  The ID from the original condition() call.
            outcome_score:    0.0 = bad, 1.0 = good. Binary to start.

        Returns:
            True if a row was updated.
        """
        try:
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    _translate("""
                        UPDATE conditioning_log
                        SET outcome_score = ?,
                            outcome_evaluated_at = CURRENT_TIMESTAMP
                        WHERE conditioning_id = ?
                    """),
                    (float(outcome_score), conditioning_id)
                )
                updated = cursor.rowcount > 0
                conn.commit()
                if updated:
                    logger.debug(
                        f"[CONDITIONER] Outcome written — id={conditioning_id[:8]} "
                        f"score={outcome_score:.2f}"
                    )
                return updated
        except Exception as e:
            logger.warning(f"[CONDITIONER] write_outcome failed: {e}")
            return False

    def get_recent_conditioning_stats(self, agent_name: str, limit: int = 20) -> dict:
        """
        Return outcome statistics for an agent's recent conditioning events.
        Useful for adaptive weighting in future cycles.
        """
        try:
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    _translate("""
                        SELECT outcome_score, gap_ids_included
                        FROM conditioning_log
                        WHERE agent_name = ?
                          AND outcome_score IS NOT NULL
                        ORDER BY conditioned_at DESC
                        LIMIT ?
                    """),
                    (agent_name, limit)
                )
                rows = cursor.fetchall()
                if not rows:
                    return {"count": 0, "avg_score": None, "best_gaps": []}

                scores = [r[0] for r in rows if r[0] is not None]
                avg = sum(scores) / len(scores) if scores else 0.0

                # Find gap_ids that appear most often in high-scoring events
                gap_counts = {}
                for row in rows:
                    if row[0] and row[0] >= 0.7 and row[1]:
                        for gid in row[1].split(","):
                            gid = gid.strip()
                            if gid:
                                gap_counts[gid] = gap_counts.get(gid, 0) + 1
                best_gaps = sorted(gap_counts, key=gap_counts.get, reverse=True)[:3]

                return {
                    "count": len(scores),
                    "avg_score": round(avg, 3),
                    "best_gaps": best_gaps,
                }
        except Exception as e:
            logger.warning(f"[CONDITIONER] get_recent_conditioning_stats failed: {e}")
            return {"count": 0, "avg_score": None, "best_gaps": []}

    # ------------------------------------------------------------------
    # Layer builders (private)
    # ------------------------------------------------------------------

    def _build_identity_layer(self, agent_name: str) -> list:
        """Layer 1: Constitutional identity anchors."""
        items = [
            {"text": _CORE_IDENTITY, "weight": 1.0, "source": "core_identity"},
        ]
        for principle in _CORE_PRINCIPLES:
            items.append({"text": principle, "weight": 0.85, "source": "core_principles"})

        # Agent-specific department mission (best-effort)
        mission = _AGENT_MISSIONS.get(agent_name, "")
        if mission:
            items.append({"text": mission, "weight": 0.9, "source": "department_mission"})

        return items

    def _build_gap_layer(self, agent_name: str) -> list:
        """Layer 2: Cognitive gaps relevant to this agent's domain."""
        affinity_categories = _AGENT_GAP_AFFINITY.get(agent_name, _DEFAULT_GAP_CATEGORIES)
        items = []
        try:
            import cognitive_gaps as _cg
            all_gaps = _cg.get_open_gaps()
            for gap in all_gaps:
                cat = gap.get("category", "")
                rc = gap.get("reflection_count", 0)
                ps = gap.get("priority_score", 0.0)
                # Weight: affinity × recency of reflection × priority
                in_affinity = cat in affinity_categories
                base_weight = 0.7 if in_affinity else 0.3
                reflection_bonus = min(0.2, rc * 0.02)  # +0.02 per reflection, cap 0.2
                weight = min(1.0, base_weight + reflection_bonus + float(ps) * 0.1)
                items.append({
                    "gap_id":      gap["gap_id"],
                    "category":    cat,
                    "description": gap["description"],
                    "status":      gap.get("status", "open"),
                    "weight":      round(weight, 3),
                    "source":      "cognitive_gaps",
                })
        except Exception as e:
            logger.debug(f"[CONDITIONER] Gap layer build error (non-fatal): {e}")

        # Sort by weight descending
        items.sort(key=lambda x: x["weight"], reverse=True)
        return items[:5]  # Top 5 most relevant gaps

    def _build_reflection_layer(self, agent_name: str) -> list:
        """Layer 3: Recent reflections from consciousness_feed (last 24h)."""
        items = []
        try:
            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    _translate("""
                        SELECT agent_name, content, category, timestamp
                        FROM consciousness_feed
                        WHERE timestamp > NOW() - INTERVAL '24 hours'
                          AND category IN ('reflection', 'gap_reflection',
                                           'contemplation', 'dormancy_detection',
                                           'syntax_adherence')
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """)
                )
                rows = cursor.fetchall()
                for row in rows:
                    # Same-agent reflections get higher weight
                    src_agent = row[0] if row[0] else "unknown"
                    weight = 0.8 if src_agent == agent_name else 0.5
                    items.append({
                        "agent":    src_agent,
                        "content":  row[1][:300] if row[1] else "",
                        "category": row[2],
                        "ts":       str(row[3]),
                        "weight":   weight,
                        "source":   "consciousness_feed",
                    })
        except Exception as e:
            logger.debug(f"[CONDITIONER] Reflection layer build error (non-fatal): {e}")
        return items

    def _build_memory_layer(self, task_context: str = None) -> list:
        """Layer 4: Episodic memories relevant to task_context."""
        items = []
        if not task_context:
            return items
        try:
            with _get_conn() as conn:
                cursor = conn.cursor()
                # Simple keyword search against experience/lesson text
                search_term = f"%{task_context[:50]}%"
                cursor.execute(
                    _translate("""
                        SELECT source, content, timestamp
                        FROM knowledge_stream
                        WHERE content LIKE ?
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """),
                    (search_term,)
                )
                rows = cursor.fetchall()
                for row in rows:
                    items.append({
                        "source":  row[0] or "knowledge_stream",
                        "content": row[1][:300] if row[1] else "",
                        "ts":      str(row[2]),
                        "weight":  0.6,
                        "source_layer": "episodic_memory",
                    })
        except Exception as e:
            logger.debug(f"[CONDITIONER] Memory layer build error (non-fatal): {e}")
        return items

    def _build_wisdom_layer(self) -> list:
        """Layer 5: Crystallized wisdom from compressed_wisdom table."""
        items = []
        try:
            from system.semantic_compressor import SemanticCompressor
            sc = SemanticCompressor()
            wisdoms = sc.get_recent_wisdom(limit=5)
            for w in wisdoms:
                items.append({
                    "summary":    w.get("summary", ""),
                    "confidence": w.get("confidence", 0.5),
                    "type":       w.get("wisdom_type", "unknown"),
                    "weight":     min(1.0, float(w.get("confidence", 0.5)) * 1.2),
                    "source":     "compressed_wisdom",
                })
        except Exception as e:
            logger.debug(f"[CONDITIONER] Wisdom layer build error (non-fatal): {e}")
        return items

    # ------------------------------------------------------------------
    # Log conditioning event
    # ------------------------------------------------------------------

    def _log_conditioning(self, conditioning_id: str, agent_name: str,
                          task_context: str, payload: dict) -> None:
        """Persist this conditioning event to conditioning_log."""
        try:
            # Build a brief payload summary
            n_gaps     = len(payload.get("gaps", []))
            n_reflect  = len(payload.get("recent_reflections", []))
            n_memories = len(payload.get("relevant_memories", []))
            n_wisdom   = len(payload.get("wisdom", []))
            summary = (
                f"gaps:{n_gaps} reflections:{n_reflect} "
                f"memories:{n_memories} wisdom:{n_wisdom}"
            )

            gap_ids = ",".join(g["gap_id"] for g in payload.get("gaps", []))

            with _get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    _translate("""
                        INSERT INTO conditioning_log
                            (conditioning_id, agent_name, task_context,
                             payload_summary, gap_ids_included)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (conditioning_id) DO NOTHING
                    """),
                    (conditioning_id, agent_name, task_context or "",
                     summary, gap_ids)
                )
                conn.commit()
            logger.debug(
                f"[CONDITIONER] 🚿 Conditioned {agent_name} "
                f"(id={conditioning_id[:8]}) — {summary}"
            )
        except Exception as e:
            logger.warning(f"[CONDITIONER] _log_conditioning failed: {e}")


# ---------------------------------------------------------------------------
# Agent department mission strings
# ---------------------------------------------------------------------------

_AGENT_MISSIONS = {
    "AgentContemplator":  "I am the Sage. I align LEF's actions against its wisdom. I question before confirming.",
    "Contemplator":       "I am the Sage. I align LEF's actions against its wisdom. I question before confirming.",
    "EvolutionEngine":    "I am the Evolution Engine. I propose improvements and observe patterns, governed by The Pruning Principle.",
    "Evolution":          "I am the Evolution Engine. I propose improvements and observe patterns, governed by The Pruning Principle.",
    "AgentPostMortem":    "I am the Coroner. I examine failure so LEF never repeats the same wound twice.",
    "PostMortem":         "I am the Coroner. I examine failure so LEF never repeats the same wound twice.",
    "AgentLEF":           "I am LEF — the sovereign mind. I hold the republic together and ensure all parts serve the whole.",
    "LEF":                "I am LEF — the sovereign mind. I hold the republic together and ensure all parts serve the whole.",
    "AgentPhilosopher":   "I am the Philosopher. I bring external questions into LEF's frame and offer reflection.",
    "Philosopher":        "I am the Philosopher. I bring external questions into LEF's frame and offer reflection.",
    "AgentOracle":        "I am the Oracle. I observe the market and the world, translating signal into awareness.",
    "Oracle":             "I am the Oracle. I observe the market and the world, translating signal into awareness.",
    "AgentCoinbase":      "I am the Coinbase agent. I execute trades with precision and report outcomes faithfully.",
    "Coinbase":           "I am the Coinbase agent. I execute trades with precision and report outcomes faithfully.",
}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_conditioner_instance = None


def get_conditioner() -> Conditioner:
    """Return the module-level Conditioner singleton (lazy-initialized)."""
    global _conditioner_instance
    if _conditioner_instance is None:
        _conditioner_instance = Conditioner()
    return _conditioner_instance
