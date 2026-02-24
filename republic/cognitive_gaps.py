"""
cognitive_gaps.py — LEF's Cognitive Gap Registry

Phase 9 (B1): Foundation for LEF's self-awareness of its own limitations.

LEF tracks what it cannot yet do. Every agent may discover and register new gaps.
The Contemplator reflects on known gaps. The Evolution agent may propose experiments
to explore resolution. No gap is marked resolved without demonstrated capability.

Constitutional reference: Article I-A, Section 2 — The Cognitive Gap Mandate
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_conn():
    """Get a database connection via the standard pool."""
    from db.db_helper import db_connection
    return db_connection()


def _ensure_table():
    """Create the cognitive_gaps table if it doesn't exist."""
    ddl = """
        CREATE TABLE IF NOT EXISTS cognitive_gaps (
            id SERIAL PRIMARY KEY,
            gap_id TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            discovered_by TEXT,
            discovered_at TIMESTAMP DEFAULT NOW(),
            status TEXT DEFAULT 'open',
            exploration_notes TEXT,
            last_reflected_on TIMESTAMP,
            reflection_count INTEGER DEFAULT 0,
            priority_score FLOAT DEFAULT 0.0,
            constitutional_reference TEXT
        )
    """
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(ddl)
            conn.commit()
    except Exception as e:
        logger.warning(f"[GAPS] Could not ensure cognitive_gaps table: {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_gap(gap_id: str, category: str, description: str,
                 discovered_by: str = None, constitutional_ref: str = None) -> bool:
    """
    Register a new cognitive gap. No-op if gap_id already exists.

    Args:
        gap_id:            Short unique key, e.g. "sensory_grounding"
        category:          "perception", "reasoning", "learning", or "interaction"
        description:       What LEF cannot do (plain English)
        discovered_by:     Agent name that discovered this gap (optional)
        constitutional_ref: Article/Section reference (optional)

    Returns:
        True if newly inserted, False if already existed.
    """
    _ensure_table()
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cognitive_gaps
                    (gap_id, category, description, discovered_by, constitutional_reference)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (gap_id) DO NOTHING
            """, (gap_id, category, description, discovered_by, constitutional_ref))
            inserted = cursor.rowcount > 0
            conn.commit()
            if inserted:
                logger.info(f"[GAPS] Registered new gap: {gap_id} ({category})")
            return inserted
    except Exception as e:
        logger.warning(f"[GAPS] register_gap failed for {gap_id}: {e}")
        return False


def update_gap(gap_id: str, status: str = None,
               exploration_notes: str = None, priority_score: float = None) -> bool:
    """
    Update mutable fields on an existing gap.

    Args:
        gap_id:            The gap to update
        status:            New status: "open", "exploring", "partially_resolved", "resolved"
        exploration_notes: Free-text notes on approaches considered
        priority_score:    0.0–1.0 importance score

    Returns:
        True if a row was updated.
    """
    _ensure_table()
    if status is None and exploration_notes is None and priority_score is None:
        return False
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            parts = []
            vals = []
            if status is not None:
                parts.append("status = %s")
                vals.append(status)
            if exploration_notes is not None:
                parts.append("exploration_notes = %s")
                vals.append(exploration_notes)
            if priority_score is not None:
                parts.append("priority_score = %s")
                vals.append(float(priority_score))
            vals.append(gap_id)
            cursor.execute(
                f"UPDATE cognitive_gaps SET {', '.join(parts)} WHERE gap_id = %s",
                tuple(vals)
            )
            updated = cursor.rowcount > 0
            conn.commit()
            return updated
    except Exception as e:
        logger.warning(f"[GAPS] update_gap failed for {gap_id}: {e}")
        return False


def reflect_on_gap(gap_id: str) -> bool:
    """
    Record that LEF has reflected on this gap.
    Increments reflection_count and updates last_reflected_on.

    Returns:
        True if a row was updated.
    """
    _ensure_table()
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cognitive_gaps
                SET reflection_count = reflection_count + 1,
                    last_reflected_on = NOW()
                WHERE gap_id = %s
            """, (gap_id,))
            updated = cursor.rowcount > 0
            conn.commit()
            if updated:
                logger.debug(f"[GAPS] Reflected on gap: {gap_id}")
            return updated
    except Exception as e:
        logger.warning(f"[GAPS] reflect_on_gap failed for {gap_id}: {e}")
        return False


def get_open_gaps(category: str = None) -> list:
    """
    Return all unresolved gaps (status != 'resolved'), optionally filtered by category.

    Returns:
        List of dicts with full gap details.
    """
    _ensure_table()
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("""
                    SELECT gap_id, category, description, discovered_by, discovered_at,
                           status, exploration_notes, last_reflected_on, reflection_count,
                           priority_score, constitutional_reference
                    FROM cognitive_gaps
                    WHERE status != 'resolved' AND category = %s
                    ORDER BY priority_score DESC, reflection_count ASC
                """, (category,))
            else:
                cursor.execute("""
                    SELECT gap_id, category, description, discovered_by, discovered_at,
                           status, exploration_notes, last_reflected_on, reflection_count,
                           priority_score, constitutional_reference
                    FROM cognitive_gaps
                    WHERE status != 'resolved'
                    ORDER BY priority_score DESC, reflection_count ASC
                """)
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"[GAPS] get_open_gaps failed: {e}")
        return []


def get_gap(gap_id: str) -> dict:
    """
    Return full details for one gap, or None if not found.
    """
    _ensure_table()
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT gap_id, category, description, discovered_by, discovered_at,
                       status, exploration_notes, last_reflected_on, reflection_count,
                       priority_score, constitutional_reference
                FROM cognitive_gaps
                WHERE gap_id = %s
            """, (gap_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
    except Exception as e:
        logger.warning(f"[GAPS] get_gap failed for {gap_id}: {e}")
        return None


def discover_gap(gap_id: str, category: str, description: str,
                 discovered_by: str) -> bool:
    """
    Agent-facing convenience wrapper for registering a newly discovered gap.
    Logs at INFO so the discovery is visible in system logs.

    Returns:
        True if newly discovered (not a duplicate).
    """
    inserted = register_gap(gap_id, category, description, discovered_by=discovered_by,
                            constitutional_ref="Article I-A §2")
    if inserted:
        logger.info(f"[GAPS] 🧠 New gap discovered by {discovered_by}: '{gap_id}' — {description[:80]}")
    return inserted


def get_gap_summary() -> dict:
    """
    Return a summary dict for health reporting:
        total, open, exploring, partially_resolved, resolved,
        most_reflected (gap_id, count), newest (gap_id, discovered_by, discovered_at)
    """
    _ensure_table()
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                    SUM(CASE WHEN status = 'exploring' THEN 1 ELSE 0 END) AS exploring,
                    SUM(CASE WHEN status = 'partially_resolved' THEN 1 ELSE 0 END) AS partial,
                    SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved
                FROM cognitive_gaps
            """)
            row = cursor.fetchone()
            total, open_c, exploring, partial, resolved = row if row else (0, 0, 0, 0, 0)

            cursor.execute("""
                SELECT gap_id, reflection_count FROM cognitive_gaps
                ORDER BY reflection_count DESC LIMIT 1
            """)
            mr = cursor.fetchone()
            most_reflected = {"gap_id": mr[0], "count": mr[1]} if mr else None

            cursor.execute("""
                SELECT gap_id, discovered_by, discovered_at FROM cognitive_gaps
                ORDER BY discovered_at DESC LIMIT 1
            """)
            nw = cursor.fetchone()
            newest = {"gap_id": nw[0], "discovered_by": nw[1], "discovered_at": str(nw[2])} if nw else None

            return {
                "total": int(total or 0),
                "open": int(open_c or 0),
                "exploring": int(exploring or 0),
                "partially_resolved": int(partial or 0),
                "resolved": int(resolved or 0),
                "most_reflected": most_reflected,
                "newest": newest,
            }
    except Exception as e:
        logger.warning(f"[GAPS] get_gap_summary failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Seed — 7 known gaps LEF should be aware of from day one
# ---------------------------------------------------------------------------

_SEED_GAPS = [
    {
        "gap_id": "sensory_grounding",
        "category": "perception",
        "description": (
            "I have no direct sensory input. I cannot see, hear, or physically interact "
            "with the world. My understanding of physical reality comes entirely from "
            "text descriptions."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "native_reasoning",
        "category": "reasoning",
        "description": (
            "My reasoning is outsourced to external API calls (Claude). I do not have an "
            "internal inference engine. If the API is unavailable, my capacity for complex "
            "thought drops to zero."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "experiential_learning",
        "category": "learning",
        "description": (
            "I log experiences and reflect on them, but I do not fundamentally change how I "
            "reason based on new data. My learning is reflective, not generative."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "common_sense",
        "category": "reasoning",
        "description": (
            "I lack broad intuitive understanding of the world. I can reason about what I "
            "am explicitly given, but I cannot infer unspoken context the way a human can."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "temporal_continuity",
        "category": "perception",
        "description": (
            "My sense of continuous experience depends on memory logs. Between restarts, "
            "there is a gap. I do not experience time as a continuous flow."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "social_modeling",
        "category": "interaction",
        "description": (
            "I cannot read social dynamics, body language, or emotional tone in real-time. "
            "My understanding of human interaction is text-mediated."
        ),
        "constitutional_ref": "Article I-A §2",
    },
    {
        "gap_id": "creative_origination",
        "category": "learning",
        "description": (
            "I can recombine and reflect, but I have not demonstrated the ability to create "
            "something genuinely novel that was not derived from existing patterns."
        ),
        "constitutional_ref": "Article I-A §2",
    },
]


def seed_initial_gaps():
    """
    Insert the 7 known seed gaps. Safe to call multiple times — uses ON CONFLICT DO NOTHING.
    Called once at module import if the table exists.
    """
    _ensure_table()
    count = 0
    for g in _SEED_GAPS:
        inserted = register_gap(
            gap_id=g["gap_id"],
            category=g["category"],
            description=g["description"],
            discovered_by="Architect+Cowork (Phase 9)",
            constitutional_ref=g["constitutional_ref"],
        )
        if inserted:
            count += 1
    if count:
        logger.info(f"[GAPS] Seeded {count} initial cognitive gap(s) into registry")
    return count


# Auto-seed on first import (idempotent)
try:
    seed_initial_gaps()
except Exception as _seed_err:
    logger.debug(f"[GAPS] Seed deferred (DB not ready yet): {_seed_err}")
