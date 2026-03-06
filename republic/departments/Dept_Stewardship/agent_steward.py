"""
AgentSteward (The Steward)
Department: Dept_Stewardship
Role: Academic pattern stewardship — learns from de-identified student assessment data
      across LEF Ed's domains and surfaces population-level insights.

STATUS: DORMANT — awaiting LEF Ed pilot (NWEA + Clever live data connections)

When active, AgentSteward will:
- Ingest de-identified assessment events from lef_ed_events table
- Learn growth trajectory patterns, intervention efficacy, demographic gap patterns
- Write insights to stewardship_feed (injected into LEF's awareness context)
- Persist learned patterns to academic_patterns table
- Surface at-risk cohort indicators before they manifest as failures

Privacy constraints (immutable — see lef_ed_config.json):
- Accepts only de-identified fields: age_range, hashed_student_id, cohort_id, grade_band
- Aggregation minimum: 5 students per pattern
- Never stores individual student profiles
- Rejects any payload containing rejected_identifiers
"""

import os
import sys
import time
import json
import logging
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path or "republic.db", timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

logger = logging.getLogger("AgentSteward")

# Privacy constraints — these cannot be relaxed by any config change
REJECTED_IDENTIFIERS = {
    "student_name", "date_of_birth", "full_birthdate", "ssn",
    "address", "parent_name", "teacher_name", "school_name_exact"
}
AGGREGATION_MINIMUM = 5


class AgentSteward:
    """
    The Steward — LEF's academic domain intelligence.
    Dormant until LEF Ed pilot data is flowing.
    """

    def __init__(self):
        self.name = "AgentSteward"
        self.status = "DORMANT"
        self.config = self._load_config()
        self.db_path = os.getenv("DB_PATH", os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "republic.db"
        ))
        logger.info(f"[STEWARD] 🌱 AgentSteward initialized. Status: {self.status}")
        logger.info("[STEWARD] Awaiting LEF Ed pilot activation (lef_ed_config.json connection.enabled=true)")

    def _load_config(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "lef_ed_config.json"
        )
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[STEWARD] Could not load lef_ed_config.json: {e}")
            return {"connection": {"enabled": False}}

    def _is_active(self):
        """Returns True only if LEF Ed connection is enabled and pilot is live."""
        return self.config.get("connection", {}).get("enabled", False)

    def _verify_privacy(self, payload: dict) -> bool:
        """
        Rejects any payload containing forbidden identifiers.
        Returns True if payload is clean.
        """
        payload_keys = set(str(k).lower() for k in payload.keys())
        violations = payload_keys & {r.lower() for r in REJECTED_IDENTIFIERS}
        if violations:
            logger.warning(f"[STEWARD] ⛔ Privacy violation — rejected fields: {violations}")
            return False
        return True

    def ingest_event(self, event_type: str, payload: dict) -> bool:
        """
        Ingest a de-identified event from LEF Ed.
        Returns True if accepted and queued, False if rejected.
        """
        if not self._is_active():
            logger.debug("[STEWARD] Dormant — event ingestion skipped.")
            return False

        if not self._verify_privacy(payload):
            return False

        now = datetime.datetime.utcnow().isoformat()
        try:
            with db_connection(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO lef_ed_events (event_type, source, payload_summary, privacy_verified, processed, timestamp) "
                    "VALUES (?, ?, ?, 1, 0, ?)",
                    (event_type, "lef_ed", json.dumps(payload)[:500], now)
                )
                conn.commit()
            logger.info(f"[STEWARD] ✅ Event ingested: {event_type}")
            return True
        except Exception as e:
            logger.error(f"[STEWARD] Ingest error: {e}")
            return False

    def learn_patterns(self):
        """
        Process pending lef_ed_events and learn cohort-level patterns.
        Called by run() when active.
        """
        if not self._is_active():
            return

        logger.info("[STEWARD] 📚 Running pattern learning cycle...")
        # TODO: Implement at pilot — will query lef_ed_events, group by cohort_id,
        # apply pattern_types from config, write to academic_patterns and stewardship_feed
        # Placeholder: not yet implemented
        logger.info("[STEWARD] Pattern learning not yet implemented — awaiting pilot data.")

    def write_stewardship_feed(self, content: str, category: str = "pattern_insight"):
        """
        Write a stewardship insight to stewardship_feed.
        Mirrors consciousness_feed design — will be injected into LEF's awareness.
        """
        now = datetime.datetime.utcnow().isoformat()
        try:
            with db_connection(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO stewardship_feed (agent_name, domain, content, category, timestamp, consumed) "
                    "VALUES (?, 'academic', ?, ?, ?, 0)",
                    ("AgentSteward", content, category, now)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"[STEWARD] stewardship_feed write error: {e}")

    def run(self):
        """Main loop — dormant until pilot activation."""
        cycle_interval = self.config.get("stewardship_agent", {}).get("cycle_interval_seconds", 3600)

        while True:
            if not self._is_active():
                # Dormant mode: light heartbeat, wait for activation
                logger.debug("[STEWARD] 💤 Dormant. Checking activation every 5min...")
                time.sleep(300)
                self.config = self._load_config()  # Reload config to detect activation
                continue

            # Active mode (pilot live)
            logger.info("[STEWARD] 🌿 Stewardship cycle starting...")
            try:
                self.learn_patterns()
            except Exception as e:
                logger.error(f"[STEWARD] Cycle error: {e}")

            time.sleep(cycle_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    steward = AgentSteward()
    steward.run()
