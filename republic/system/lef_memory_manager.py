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

BASE_DIR = Path(__file__).parent.parent  # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"
LEF_MEMORY_PATH = BRIDGE_DIR / "lef_memory.json"

logger = logging.getLogger("LEF.MemoryManager")

MAX_EVOLUTION_LOG_ENTRIES = 50
MAX_LESSONS = 50


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
    """Persist LEF's identity document to disk."""
    try:
        LEF_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEF_MEMORY_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("[LEFMemory] Identity document persisted")
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
            cursor.execute("""
                SELECT COUNT(*), GROUP_CONCAT(DISTINCT category)
                FROM consciousness_feed
                WHERE timestamp > ?
            """, (six_hours_ago,))
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
    evolution_entry = summary.get("evolution_entry")
    if evolution_entry:
        evolution_log = memory.setdefault("evolution_log", [])
        evolution_log.append(evolution_entry)
        # Cap at MAX entries, prune oldest
        if len(evolution_log) > MAX_EVOLUTION_LOG_ENTRIES:
            memory["evolution_log"] = evolution_log[-MAX_EVOLUTION_LOG_ENTRIES:]

    # Append new lessons (deduplicate by lesson text)
    new_lessons = summary.get("new_lessons", [])
    if new_lessons:
        existing_lessons = memory.setdefault("learned_lessons", [])
        existing_texts = set()
        for l in existing_lessons:
            if isinstance(l, dict):
                existing_texts.add(l.get("lesson", ""))
            elif isinstance(l, str):
                existing_texts.add(l)

        for lesson in new_lessons:
            lesson_text = lesson.get("lesson", "") if isinstance(lesson, dict) else str(lesson)
            if lesson_text and lesson_text not in existing_texts:
                existing_lessons.append(lesson)
                existing_texts.add(lesson_text)

        # Cap lessons
        if len(existing_lessons) > MAX_LESSONS:
            memory["learned_lessons"] = existing_lessons[-MAX_LESSONS:]

    # Save
    save_lef_memory(memory)

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
