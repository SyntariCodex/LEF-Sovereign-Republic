"""
LEFMemoryManager — LEF's own identity document manager.
Manages The_Bridge/lef_memory.json — LEF's compact, readable self-summary
that LEF reads at boot to remember who it is.

Currently LEF's self-knowledge is scattered across database tables
(lef_monologue, ArchitectModel, Hippocampus insights, consciousness_feed).
This module creates a consolidated identity document maintained by LEF itself.

Phase 3 Active Tasks — Task 3.2
"""

import os
import json
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    from db.db_helper import table_exists as _table_exists, translate_sql as _translate_sql
except ImportError:
    def _table_exists(cursor, table_name):  # noqa: E306
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
    def _translate_sql(sql):  # noqa: E306
        return sql

# Phase 43.3: Identity checkpoint integration
try:
    from system.identity_checkpoint import get_checkpointer, check_and_recover_identity
    _CHECKPOINT_AVAILABLE = True
except ImportError:
    _CHECKPOINT_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent  # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"
LEF_MEMORY_PATH = BRIDGE_DIR / "lef_memory.json"

logger = logging.getLogger("LEF.MemoryManager")

MAX_EVOLUTION_LOG_ENTRIES = 50
MAX_LESSONS = 50


def _normalize_text(text):
    """Phase 18.8a: Normalize text for semantic comparison."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Strip punctuation
    text = re.sub(r'\s+', ' ', text)      # Collapse whitespace
    return text


def _word_overlap(text_a, text_b):
    """
    Phase 18.8a: Calculate word-level overlap ratio between two texts.
    Returns float 0.0 to 1.0. If > 0.6, texts are semantically similar enough
    to be considered duplicates.
    """
    words_a = set(_normalize_text(text_a).split())
    words_b = set(_normalize_text(text_b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller if smaller > 0 else 0.0


def load_lef_memory() -> dict:
    """Load LEF's identity document from disk."""
    if LEF_MEMORY_PATH.exists():
        try:
            with open(LEF_MEMORY_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[LEFMemory] Failed to load: {e}")
    return _default_memory()


def save_lef_memory(data: dict):
    """Persist LEF's identity document to disk. Uses atomic write (Phase 21.1e)."""
    import tempfile
    try:
        LEF_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        dir_name = str(LEF_MEMORY_PATH.parent)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(LEF_MEMORY_PATH))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        logger.info("[LEFMemory] Identity document persisted (atomic)")
    except Exception as e:
        logger.error(f"[LEFMemory] Failed to save: {e}")


def _default_memory() -> dict:
    """Return default LEF memory structure if file doesn't exist."""
    return {
        "identity": {
            "name": "LEF",
            "created": "2024-01-01",
            "purpose": "",
            "core_values": []
        },
        "self_understanding": {
            "what_i_am": "",
            "what_i_am_not": "",
            "my_relationship_to_the_architect": ""
        },
        "learned_lessons": [],
        "current_state": {
            "metabolism_health": "",
            "consciousness_status": "",
            "last_updated": ""
        },
        "evolution_log": []
    }


def build_identity_context(memory: dict = None) -> str:
    """
    Build a prompt-injectable identity context string from lef_memory.json.
    Used by memory_retriever to inject at boot into LEF's consciousness prompt.
    """
    if memory is None:
        memory = load_lef_memory()

    parts = []

    identity = memory.get("identity", {})
    if identity.get("purpose"):
        parts.append(f"[WHO I AM] {identity['purpose']}")

    if identity.get("core_values"):
        values_str = ", ".join(identity["core_values"])
        parts.append(f"[MY VALUES] {values_str}")

    self_understanding = memory.get("self_understanding", {})
    if self_understanding.get("what_i_am"):
        parts.append(f"[SELF-MODEL] {self_understanding['what_i_am']}")
    if self_understanding.get("what_i_am_not"):
        parts.append(f"[BOUNDARIES] {self_understanding['what_i_am_not']}")
    if self_understanding.get("my_relationship_to_the_architect"):
        parts.append(f"[THE ARCHITECT] {self_understanding['my_relationship_to_the_architect']}")

    # Recent lessons (last 5)
    lessons = memory.get("learned_lessons", [])[-5:]
    if lessons:
        parts.append("[RECENT LESSONS]")
        for lesson in lessons:
            if isinstance(lesson, dict):
                parts.append(f"  - {lesson.get('lesson', '')}")
            elif isinstance(lesson, str):
                parts.append(f"  - {lesson}")

    # Current state
    state = memory.get("current_state", {})
    if state.get("metabolism_health") and state["metabolism_health"] != "unknown":
        parts.append(f"[METABOLISM] {state['metabolism_health']}")
    if state.get("consciousness_status"):
        parts.append(f"[CONSCIOUSNESS] {state['consciousness_status']}")

    # Recent evolution (last entry)
    evolution = memory.get("evolution_log", [])
    if evolution:
        latest = evolution[-1]
        if isinstance(latest, dict):
            parts.append(f"[LATEST GROWTH] {latest.get('observation', '')}")

    return "\n".join(parts) if parts else ""


def compile_self_summary(db_path=None) -> dict:
    """
    Compile a self-summary from LEF's scattered data sources.

    Reads from:
    - lef_monologue (recent thoughts and moods)
    - consciousness_feed (background reflections)
    - system_state (metabolic health, sabbath mode)
    - intent_queue (recent action patterns)
    - compressed_wisdom (distilled insights)

    Returns a dict to merge into lef_memory.json.
    """
    db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

    if not os.path.exists(db_path):
        return {}

    conn = sqlite3.connect(db_path, timeout=30)
    now = datetime.now()
    six_hours_ago = (now - timedelta(hours=6)).isoformat()

    summary = {
        "current_state": {
            "last_updated": now.isoformat()
        },
        "evolution_entry": None,
        "new_lessons": []
    }

    try:
        cursor = conn.cursor()

        # --- Metabolism health from system_state ---
        try:
            # Check for SABBATH mode
            cursor.execute("SELECT value FROM system_state WHERE key = 'sabbath_mode'")
            row = cursor.fetchone()
            sabbath = row[0] if row else "FALSE"

            # Check recent trade activity
            cursor.execute("""
                SELECT status, COUNT(*) FROM intent_queue
                WHERE created_at > ? AND intent_type LIKE '%trade%'
                GROUP BY status
            """, (six_hours_ago,))
            trade_stats = {r[0]: r[1] for r in cursor.fetchall()}

            if sabbath == "TRUE":
                summary["current_state"]["metabolism_health"] = "SABBATH — resting, no active trades"
            elif trade_stats:
                total = sum(trade_stats.values())
                completed = trade_stats.get("COMPLETE", 0)
                failed = trade_stats.get("FAILED", 0)
                summary["current_state"]["metabolism_health"] = (
                    f"Active — {total} trade intents in last 6h "
                    f"({completed} completed, {failed} failed)"
                )
            else:
                summary["current_state"]["metabolism_health"] = "Quiet — no trade activity in last 6 hours"
        except Exception as e:
            logger.debug(f"[LEFMemory] metabolism query: {e}")

        # --- Consciousness status from consciousness_feed ---
        try:
            cursor.execute(_translate_sql("""
                SELECT COUNT(*), GROUP_CONCAT(DISTINCT category)
                FROM consciousness_feed
                WHERE timestamp > ?
            """), (six_hours_ago,))
            row = cursor.fetchone()
            feed_count = row[0] if row else 0
            categories = row[1] if row else ""

            if feed_count > 0:
                summary["current_state"]["consciousness_status"] = (
                    f"Active — {feed_count} consciousness outputs in last 6h "
                    f"(categories: {categories})"
                )
            else:
                summary["current_state"]["consciousness_status"] = (
                    "Quiet — no consciousness outputs in last 6 hours"
                )
        except Exception as e:
            logger.debug(f"[LEFMemory] consciousness query: {e}")

        # --- Build evolution entry from recent monologue ---
        try:
            cursor.execute("""
                SELECT thought, mood, timestamp
                FROM lef_monologue
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (six_hours_ago,))
            thoughts = cursor.fetchall()

            if thoughts:
                # Extract mood distribution
                moods = {}
                for t in thoughts:
                    mood = t[1] or "neutral"
                    moods[mood] = moods.get(mood, 0) + 1

                dominant_mood = max(moods, key=moods.get)
                thought_count = len(thoughts)

                # Build observation
                latest_thought = thoughts[0][0][:150] if thoughts[0][0] else ""
                observation = (
                    f"In the last 6 hours: {thought_count} monologue entries, "
                    f"dominant mood: {dominant_mood}. "
                    f"Latest thought: \"{latest_thought}\""
                )

                summary["evolution_entry"] = {
                    "timestamp": now.isoformat(),
                    "observation": observation,
                    "dominant_mood": dominant_mood,
                    "thought_count": thought_count
                }
        except Exception as e:
            logger.debug(f"[LEFMemory] monologue query: {e}")

        # --- Detect lessons from degraded agents or governance vetoes ---
        try:
            # Degraded agents
            cursor.execute("""
                SELECT key, value FROM system_state
                WHERE key LIKE 'agent_degraded_%'
            """)
            for row in cursor.fetchall():
                agent_name = row[0].replace('agent_degraded_', '')
                summary["new_lessons"].append({
                    "timestamp": now.isoformat(),
                    "lesson": f"Agent {agent_name} entered DEGRADED state — investigate crash loop",
                    "source": "system_state"
                })

            # Recent vetoes
            cursor.execute("""
                SELECT COUNT(*) FROM intent_queue
                WHERE status = 'VETOED' AND created_at > ?
            """, (six_hours_ago,))
            row = cursor.fetchone()
            vetoed = row[0] if row else 0
            if vetoed > 0:
                summary["new_lessons"].append({
                    "timestamp": now.isoformat(),
                    "lesson": f"Governance vetoed {vetoed} intents in last 6 hours — review alignment with core principles",
                    "source": "intent_queue"
                })
        except Exception as e:
            logger.debug(f"[LEFMemory] lessons query: {e}")

        # --- Recent compressed wisdom ---
        try:
            cursor.execute("""
                SELECT compressed_insight FROM compressed_wisdom
                WHERE created_at > ?
                ORDER BY created_at DESC
                LIMIT 3
            """, (six_hours_ago,))
            for row in cursor.fetchall():
                if row[0]:
                    summary["new_lessons"].append({
                        "timestamp": now.isoformat(),
                        "lesson": row[0][:200],
                        "source": "compressed_wisdom"
                    })
        except Exception as e:
            logger.debug(f"[LEFMemory] wisdom query: {e}")

    except Exception as e:
        logger.error(f"[LEFMemory] Compilation error: {e}")
    finally:
        conn.close()

    return summary


def update_lef_memory(db_path=None):
    """
    Main entry point: compile self-summary and merge into lef_memory.json.
    Does NOT overwrite evolution_log — appends to it. Caps at MAX_EVOLUTION_LOG_ENTRIES.
    """
    memory = load_lef_memory()
    summary = compile_self_summary(db_path)

    if not summary:
        logger.info("[LEFMemory] No data to compile. Skipping update.")
        return False

    # Update current_state
    current_state = memory.setdefault("current_state", {})
    new_state = summary.get("current_state", {})
    for key, value in new_state.items():
        if value:  # Only update non-empty values
            current_state[key] = value

    # Append evolution entry (if meaningful)
    # Phase 18.8a: Dedup guard — prevent identical or near-identical entries
    evolution_entry = summary.get("evolution_entry")
    if evolution_entry:
        evolution_log = memory.setdefault("evolution_log", [])

        # Check for duplicate: same config_key + same new_value = same change
        is_duplicate = False
        entry_key = evolution_entry.get('config_key', '')
        entry_val = str(evolution_entry.get('new_value', ''))
        entry_desc = evolution_entry.get('change_description', '')

        for existing in evolution_log[-20:]:  # Check last 20 entries only
            if (existing.get('config_key', '') == entry_key and
                    str(existing.get('new_value', '')) == entry_val):
                is_duplicate = True
                logger.info(f"[LEFMemory] 🔄 Dedup: Skipping duplicate evolution entry: {entry_desc}")
                break

        if not is_duplicate:
            evolution_log.append(evolution_entry)
            # Cap at MAX entries, prune oldest
            if len(evolution_log) > MAX_EVOLUTION_LOG_ENTRIES:
                memory["evolution_log"] = evolution_log[-MAX_EVOLUTION_LOG_ENTRIES:]

    # Append new lessons (Phase 18.8a: semantic dedup — >60% word overlap = duplicate)
    new_lessons = summary.get("new_lessons", [])
    if new_lessons:
        existing_lessons = memory.setdefault("learned_lessons", [])

        for lesson in new_lessons:
            lesson_text = lesson.get("lesson", "") if isinstance(lesson, dict) else str(lesson)
            if not lesson_text:
                continue

            # Check for semantic duplicate against all existing lessons
            is_duplicate = False
            for i, existing in enumerate(existing_lessons):
                existing_text = existing.get("lesson", "") if isinstance(existing, dict) else str(existing)
                overlap = _word_overlap(lesson_text, existing_text)
                if overlap > 0.6:
                    # Duplicate — update timestamp on existing instead of appending
                    if isinstance(existing, dict):
                        existing_lessons[i]["learned_at"] = datetime.now().isoformat()
                    logger.info(
                        f"[LEFMemory] 🔄 Lesson dedup: '{lesson_text[:60]}...' "
                        f"overlaps {overlap:.0%} with existing. Updated timestamp."
                    )
                    is_duplicate = True
                    break

            if not is_duplicate:
                existing_lessons.append(lesson)

        # Cap lessons
        if len(existing_lessons) > MAX_LESSONS:
            memory["learned_lessons"] = existing_lessons[-MAX_LESSONS:]

    # Save
    save_lef_memory(memory)

    # Phase 43.3: Create identity checkpoint every ~12 hours
    if _CHECKPOINT_AVAILABLE:
        try:
            cp = get_checkpointer()
            should_checkpoint = True
            if cp.MANIFEST_PATH.exists():
                manifest = json.loads(cp.MANIFEST_PATH.read_text())
                entries = manifest.get('checkpoints', [])
                if entries:
                    last_time = datetime.fromisoformat(entries[-1].get('created_at', '2000-01-01'))
                    if (datetime.now() - last_time).total_seconds() < 36000:  # 10 hours
                        should_checkpoint = False
            if should_checkpoint:
                cp.create_checkpoint()
                logger.info("[LEFMemory] Identity checkpoint created")
        except Exception as e:
            logger.debug(f"[LEFMemory] Checkpoint error: {e}")

    logger.info(
        f"[LEFMemory] Updated — state: {current_state.get('consciousness_status', 'n/a')}, "
        f"evolution entries: {len(memory.get('evolution_log', []))}, "
        f"lessons: {len(memory.get('learned_lessons', []))}"
    )
    return True


def run_lef_memory_writer(interval_seconds=21600):
    """
    Run the LEF memory writer on a timer (default: every 6 hours / 21600 seconds).
    Also runs once at startup to capture initial state.
    """
    logger.info("[LEFMemory] Identity persistence online (updating every 6 hours)")

    # Phase 43.3: Check for identity recovery at startup
    if _CHECKPOINT_AVAILABLE:
        try:
            if check_and_recover_identity():
                logger.warning("[LEFMemory] Identity recovered from checkpoint at startup")
        except Exception as e:
            logger.debug(f"[LEFMemory] Recovery check: {e}")

    # Initial update at startup
    try:
        update_lef_memory()
    except Exception as e:
        logger.error(f"[LEFMemory] Initial update error: {e}")

    while True:
        time.sleep(interval_seconds)
        try:
            update_lef_memory()
        except Exception as e:
            logger.error(f"[LEFMemory] Cycle error: {e}")
