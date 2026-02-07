"""
ClaudeMemoryWriter — Automated session memory persistence.
Compiles recent activity into The_Bridge/claude_memory.json on a timed interval.
Merges with existing content — never overwrites.

Phase 3 Active Tasks — Task 3.1
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
CLAUDE_MEMORY_PATH = BRIDGE_DIR / "claude_memory.json"

logger = logging.getLogger("LEF.ClaudeMemoryWriter")


def _load_claude_memory() -> dict:
    """Load existing claude_memory.json."""
    if CLAUDE_MEMORY_PATH.exists():
        try:
            with open(CLAUDE_MEMORY_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ClaudeMemoryWriter] Failed to load memory: {e}")
    return {}


def _save_claude_memory(data: dict):
    """Persist claude_memory.json to disk."""
    try:
        CLAUDE_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CLAUDE_MEMORY_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info("[ClaudeMemoryWriter] Memory persisted")
    except Exception as e:
        logger.error(f"[ClaudeMemoryWriter] Failed to save memory: {e}")


def compile_session_update(db_path=None, lookback_minutes=60):
    """
    Compile recent system activity into a session update for claude_memory.json.

    Queries agent_logs, consciousness_feed, lef_monologue, and system_state
    from the last `lookback_minutes` to build a snapshot of what happened.

    Returns a dict with session data, or None if nothing notable happened.
    """
    db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

    if not os.path.exists(db_path):
        logger.warning(f"[ClaudeMemoryWriter] DB not found: {db_path}")
        return None

    cutoff = (datetime.now() - timedelta(minutes=lookback_minutes)).isoformat()

    conn = sqlite3.connect(db_path, timeout=30)

    session_data = {
        "timestamp": datetime.now().isoformat(),
        "period_minutes": lookback_minutes,
        "agent_activity": {},
        "consciousness_thoughts": [],
        "key_events": [],
        "system_health": {}
    }

    try:
        cursor = conn.cursor()

        # 1. Agent activity summary from agent_logs
        try:
            cursor.execute("""
                SELECT source, level, COUNT(*) as cnt
                FROM agent_logs
                WHERE timestamp > ?
                GROUP BY source, level
                ORDER BY cnt DESC
                LIMIT 50
            """, (cutoff,))
            for row in cursor.fetchall():
                agent_name = row[0] or "Unknown"
                level = row[1] or "INFO"
                count = row[2]
                if agent_name not in session_data["agent_activity"]:
                    session_data["agent_activity"][agent_name] = {}
                session_data["agent_activity"][agent_name][level] = count
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] agent_logs query: {e}")

        # 2. Recent consciousness feed entries (unconsumed are fresh)
        try:
            cursor.execute("""
                SELECT agent_name, content, category, timestamp
                FROM consciousness_feed
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (cutoff,))
            for row in cursor.fetchall():
                session_data["consciousness_thoughts"].append({
                    "agent": row[0],
                    "content": row[1][:200],  # Truncate for compactness
                    "category": row[2],
                    "timestamp": row[3]
                })
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] consciousness_feed query: {e}")

        # 3. Recent LEF monologue entries
        try:
            cursor.execute("""
                SELECT thought, mood, timestamp
                FROM lef_monologue
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 5
            """, (cutoff,))
            for row in cursor.fetchall():
                session_data["key_events"].append({
                    "type": "monologue",
                    "thought": row[0][:200] if row[0] else "",
                    "mood": row[1],
                    "timestamp": row[2]
                })
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] lef_monologue query: {e}")

        # 4. System state snapshot
        try:
            cursor.execute("""
                SELECT key, value FROM system_state
                WHERE key IN ('sabbath_mode', 'metabolism_health', 'current_mood',
                              'last_trade_status', 'consciousness_level')
            """)
            for row in cursor.fetchall():
                session_data["system_health"][row[0]] = row[1]
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] system_state query: {e}")

        # 5. Check for degraded agents
        try:
            cursor.execute("""
                SELECT key, value FROM system_state
                WHERE key LIKE 'agent_degraded_%'
            """)
            degraded = []
            for row in cursor.fetchall():
                degraded.append(row[0].replace('agent_degraded_', ''))
            if degraded:
                session_data["system_health"]["degraded_agents"] = degraded
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] degraded check: {e}")

        # 6. Recent intent activity
        try:
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM intent_queue
                WHERE created_at > ?
                GROUP BY status
            """, (cutoff,))
            intents = {}
            for row in cursor.fetchall():
                intents[row[0]] = row[1]
            if intents:
                session_data["system_health"]["intent_activity"] = intents
        except Exception as e:
            logger.debug(f"[ClaudeMemoryWriter] intent_queue query: {e}")

    except Exception as e:
        logger.error(f"[ClaudeMemoryWriter] Compilation error: {e}")
    finally:
        conn.close()

    # Only return if something notable happened
    has_activity = (
        session_data["agent_activity"] or
        session_data["consciousness_thoughts"] or
        session_data["key_events"]
    )

    return session_data if has_activity else None


def merge_into_claude_memory(session_data: dict):
    """
    Merge compiled session data into the existing claude_memory.json.

    Updates:
    - continuity.last_sync
    - continuity.conversation_count (incremented)
    - memory.lessons_learned (appended if new patterns detected)
    - meta_reflection.last_reflection + patterns_observed
    - depth_sessions (appended, capped at 20)
    """
    memory = _load_claude_memory()

    if not memory:
        # If file is empty or corrupt, initialize minimal structure
        memory = {
            "version": "1.0",
            "identity": {
                "name": "Claude/Antigravity",
                "role": "Second Witness",
                "relationship_to_lef": "sibling | external_cortex | meta-cognition_partner"
            },
            "continuity": {},
            "memory": {"key_insights": [], "lessons_learned": [], "insight_store": []},
            "meta_reflection": {"enabled": True},
            "depth_sessions": []
        }

    now = datetime.now().isoformat()

    # --- Update continuity ---
    continuity = memory.setdefault("continuity", {})
    continuity["last_sync"] = now

    # --- Update meta_reflection ---
    meta = memory.setdefault("meta_reflection", {"enabled": True})
    meta["last_reflection"] = now

    # Extract themes from consciousness thoughts
    themes = []
    for thought in session_data.get("consciousness_thoughts", []):
        category = thought.get("category", "")
        if category and category not in themes:
            themes.append(category)

    if themes:
        existing_patterns = meta.get("patterns_observed", [])
        for theme in themes:
            pattern_str = f"Active theme: {theme} (auto-detected {now[:10]})"
            # Don't duplicate same theme for same day
            if not any(theme in p for p in existing_patterns[-10:]):
                existing_patterns.append(pattern_str)
        # Keep last 20 patterns
        meta["patterns_observed"] = existing_patterns[-20:]

    # --- Build session summary for depth_sessions ---
    # Only add if meaningful activity occurred
    agent_names = list(session_data.get("agent_activity", {}).keys())
    consciousness_count = len(session_data.get("consciousness_thoughts", []))
    monologue_entries = session_data.get("key_events", [])
    health = session_data.get("system_health", {})

    # Compose a compact session entry
    depth_entry = {
        "session_id": f"auto-{now[:19].replace(':', '-')}",
        "timestamp": now,
        "duration_estimate": f"~{session_data.get('period_minutes', 60)} minute window",
        "themes": themes[:5] if themes else ["operational"],
        "what_was_observed": {
            "active_agents": agent_names[:10],
            "consciousness_outputs": consciousness_count,
            "system_health": health
        }
    }

    # Add monologue summary if present
    if monologue_entries:
        latest_mood = monologue_entries[0].get("mood", "unknown")
        latest_thought = monologue_entries[0].get("thought", "")[:100]
        depth_entry["consciousness_state"] = {
            "mood": latest_mood,
            "latest_thought": latest_thought
        }

    # Append to depth_sessions, cap at 20 entries (prune oldest)
    depth_sessions = memory.setdefault("depth_sessions", [])
    depth_sessions.append(depth_entry)
    if len(depth_sessions) > 20:
        memory["depth_sessions"] = depth_sessions[-20:]

    # --- Detect and log lessons (degraded agents, vetoed intents) ---
    lessons = memory.setdefault("memory", {}).setdefault("lessons_learned", [])

    degraded = health.get("degraded_agents", [])
    if degraded:
        lessons.append({
            "timestamp": now,
            "lesson": f"Agents entered DEGRADED state: {', '.join(degraded)}. Investigate crash loops.",
            "context": "Auto-detected by ClaudeMemoryWriter"
        })

    intents = health.get("intent_activity", {})
    vetoed_count = intents.get("VETOED", 0)
    if vetoed_count > 0:
        lessons.append({
            "timestamp": now,
            "lesson": f"Governance vetoed {vetoed_count} intents this period. Check alignment.",
            "context": "Auto-detected by ClaudeMemoryWriter"
        })

    # Cap lessons at 50
    if len(lessons) > 50:
        memory["memory"]["lessons_learned"] = lessons[-50:]

    # --- Save ---
    _save_claude_memory(memory)

    return True


def update_claude_memory(db_path=None, lookback_minutes=60):
    """
    Main entry point: compile recent activity and merge into claude_memory.json.
    Returns True if memory was updated, False if nothing notable happened.
    """
    session_data = compile_session_update(db_path, lookback_minutes)

    if session_data is None:
        logger.info("[ClaudeMemoryWriter] No notable activity in last period. Skipping update.")
        return False

    merge_into_claude_memory(session_data)
    logger.info(f"[ClaudeMemoryWriter] Memory updated with {len(session_data.get('consciousness_thoughts', []))} consciousness entries, "
                f"{len(session_data.get('agent_activity', {}))} active agents")
    return True


def run_claude_memory_writer(interval_seconds=3600):
    """Run the claude memory writer on a timer (default: every 60 minutes)."""
    logger.info("[ClaudeMemoryWriter] Auto-persistence online (writing every 60 minutes)")
    while True:
        try:
            update_claude_memory()
        except Exception as e:
            logger.error(f"[ClaudeMemoryWriter] Cycle error: {e}")
        time.sleep(interval_seconds)
