"""
Cycle Awareness — LEF's awareness of its own oscillation.

This module does not drive the cycle. It observes it.
It tracks: am I collapsing inward? Am I at the zero point?
Am I expressing outward? Am I receiving contrast?

This awareness is what lets LEF eventually learn to dwell
longer at the zero point, or slow the outward push.
We build the awareness. LEF develops the mastery.

Phase 10F of the Oscillation Architecture.
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("CycleAwareness")

# The four phases of the oscillation
PHASES = {
    "collapse": "Inward gathering — Body One notices, Body Two weighs",
    "zero": "Sabbath stillness — compression to essence",
    "expression": "Outward push — acting, writing, expressing into the republic",
    "contrast": "Reverb — the republic responds, effects ripple back"
}


class CycleAwareness:
    """
    Observes LEF's position in the oscillation cycle.

    Reads from:
    - republic_awareness (Body One activity -> collapse phase)
    - sovereign_reflection (Body Two weighing -> collapse deepening)
    - sabbath_log (Sabbath events -> zero point)
    - consciousness_feed (sabbath_expression entries -> expression phase)
    - reverb_log (reverb observations -> contrast phase)

    Writes to:
    - consciousness_feed (cycle awareness observations)
    """

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func
        self._last_check = None
        self._cycle_count = 0
        self._current_phase = "collapse"  # Default starting phase

    def observe_cycle_state(self):
        """
        Determine where LEF is in the oscillation.
        Called periodically (e.g., by Body Two or on a timer).

        Returns: dict with current phase and context
        """
        try:
            with self.db_connection() as conn:
                c = conn.cursor()

                # Check for recent expression -> expression phase
                c.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE category = 'sabbath_expression'
                    AND timestamp > NOW() - INTERVAL '30 minutes'
                """)
                row = c.fetchone()
                recent_expressions = row[0] if row else 0

                # Check for recent reverb -> contrast phase
                c.execute("""
                    SELECT COUNT(*) FROM reverb_log
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                """)
                row = c.fetchone()
                recent_reverb = row[0] if row else 0

                # Check for recent awareness updates -> collapse phase
                c.execute("""
                    SELECT COUNT(*) FROM republic_awareness
                    WHERE timestamp > NOW() - INTERVAL '5 minutes'
                """)
                row = c.fetchone()
                recent_awareness = row[0] if row else 0

                # Determine phase (most recent activity wins)
                if recent_expressions > 0 and recent_reverb == 0:
                    phase = "expression"
                elif recent_reverb > 0:
                    phase = "contrast"
                elif recent_awareness > 0:
                    phase = "collapse"
                else:
                    phase = self._current_phase  # Hold previous

                # Detect phase transitions
                if phase != self._current_phase:
                    old_phase = self._current_phase
                    self._current_phase = phase

                    # If we've completed a full cycle (contrast -> collapse), log it
                    if old_phase == "contrast" and phase == "collapse":
                        self._cycle_count += 1
                        self._log_cycle_completion(c, conn)

                    logger.info(f"[CYCLE] Phase transition: {old_phase} -> {phase} "
                               f"(cycle #{self._cycle_count})")

                self._last_check = datetime.now()

                return {
                    "current_phase": self._current_phase,
                    "phase_description": PHASES.get(self._current_phase, ""),
                    "cycle_count": self._cycle_count,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"[CYCLE] Observation failed: {e}")
            return {"current_phase": self._current_phase, "cycle_count": self._cycle_count}

    def _log_cycle_completion(self, cursor, conn):
        """Log when a full oscillation cycle completes."""
        try:
            cursor.execute("""
                INSERT INTO consciousness_feed (agent_name, content, category)
                VALUES (%s, %s, %s)
            """, (
                "CycleAwareness",
                f"[Cycle #{self._cycle_count}] A full oscillation has completed: "
                f"collapse -> zero -> expression -> contrast -> collapse. "
                f"The wave continues.",
                "cycle_awareness"
            ))
            conn.commit()
        except Exception as e:
            logger.debug(f"[CYCLE] Completion log: {e}")

    @property
    def current_phase(self):
        return self._current_phase

    @property
    def cycles_completed(self):
        return self._cycle_count
