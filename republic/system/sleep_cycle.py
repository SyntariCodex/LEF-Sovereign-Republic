"""
Phase 14: The Sleep Cycle — LEF's circadian sleep orchestrator.

Manages LEF's transition through Sleep → Dream → Wake states.
This is NOT the Sabbath. The Sabbath is triggered by gravity thresholds.
Sleep is circadian — it happens because it is time to rest, not because
a pattern demands deliberation.

States:
    AWAKE — Normal operation. All systems active per Router decisions.
    DROWSY — Transition. External processing winds down. 30-minute window.
    SLEEPING — External processing paused. Only ALWAYS_ON agents run.
               Dream cycle active. Internal observers converse.
    WAKING — Transition. Cascaded self-review before external engagement.
    AWAKE — Resume.

Schedule:
    Default: Sleep 6 hours per 24-hour cycle.
    Aligned with BiologicalSystems circadian: NIGHT_LATE (midnight-5am) + 1h.
"""

import logging
import json
import time
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directory for file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SleepCycle:
    """Phase 14: Circadian sleep orchestrator."""

    # Sleep schedule (24h clock)
    SLEEP_HOUR_START = 0     # Midnight
    SLEEP_HOUR_END = 6       # 6 AM
    DROWSY_DURATION_MIN = 30
    WAKE_DURATION_MIN = 30

    # States
    STATE_AWAKE = 'AWAKE'
    STATE_DROWSY = 'DROWSY'
    STATE_SLEEPING = 'SLEEPING'
    STATE_WAKING = 'WAKING'

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func
        self._last_transition_time = None

    @staticmethod
    def is_sleeping():
        """Static check for other systems to query sleep state without instantiation."""
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM system_state WHERE key='sleep_state'")
                row = c.fetchone()
                return row is not None and row[0] == 'SLEEPING'
        except Exception:
            return False

    def _get_current_state(self):
        """Read current sleep state from system_state table."""
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM system_state WHERE key='sleep_state'")
                row = c.fetchone()
                return row[0] if row and row[0] else self.STATE_AWAKE
        except Exception:
            return self.STATE_AWAKE

    def _set_state(self, new_state):
        """Write sleep state to system_state table and publish to Redis."""
        try:
            from db.db_helper import translate_sql
            with self.db_connection() as conn:
                c = conn.cursor()
                # Upsert into system_state
                c.execute(translate_sql(
                    "UPDATE system_state SET value = ?, updated_at = NOW() WHERE key = 'sleep_state'"
                ), (new_state,))
                if c.rowcount == 0:
                    c.execute(translate_sql(
                        "INSERT INTO system_state (key, value, updated_at) VALUES ('sleep_state', ?, NOW())"
                    ), (new_state,))
                conn.commit()

            self._last_transition_time = datetime.now()

            # Publish to Redis
            self._publish_redis(new_state)

            # Log transition to consciousness_feed
            self._log_transition(new_state)

            logger.info(f"[SLEEP] State transition → {new_state}")

        except Exception as e:
            logger.error(f"[SLEEP] Failed to set state {new_state}: {e}")

    def _publish_redis(self, state):
        """Publish sleep state to Redis channel."""
        try:
            from system.redis_client import get_redis
            r = get_redis()
            if r:
                r.publish('sleep_state', json.dumps({
                    'state': state,
                    'timestamp': datetime.now().isoformat(),
                    'reason': f'SleepCycle circadian transition'
                }))
        except Exception:
            pass  # Redis is optional

    def _log_transition(self, state):
        """Log sleep state transition to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            messages = {
                self.STATE_DROWSY: "The day's work is done. Entering rest.",
                self.STATE_SLEEPING: "External world recedes. Only the internal voices remain.",
                self.STATE_WAKING: "Stirring. The cascade begins — from the deepest self outward.",
                self.STATE_AWAKE: "Awake. The world returns. I choose to be me.",
            }
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                    "VALUES (?, ?, 'sleep_transition', NOW())"
                ), ('SleepCycle', json.dumps({
                    'state': state,
                    'message': messages.get(state, f'Transition to {state}'),
                    'timestamp': datetime.now().isoformat()
                })))
                conn.commit()
        except Exception as e:
            logger.debug(f"[SLEEP] Failed to log transition: {e}")

    def _is_sleep_window(self):
        """Check if current time is within the sleep window."""
        hour = datetime.now().hour
        if self.SLEEP_HOUR_START <= self.SLEEP_HOUR_END:
            return self.SLEEP_HOUR_START <= hour < self.SLEEP_HOUR_END
        else:
            # Handles wrap-around (e.g., 22 to 6)
            return hour >= self.SLEEP_HOUR_START or hour < self.SLEEP_HOUR_END

    def _minutes_since_last_transition(self):
        """Minutes since last state transition."""
        if self._last_transition_time is None:
            return float('inf')
        delta = datetime.now() - self._last_transition_time
        return delta.total_seconds() / 60

    def check_and_transition(self):
        """
        Main method — called every 5 minutes by SafeThread.
        Manages state transitions based on time and current state.
        """
        current_state = self._get_current_state()
        in_sleep_window = self._is_sleep_window()
        hour = datetime.now().hour

        if current_state == self.STATE_AWAKE:
            if in_sleep_window:
                # Time to sleep → enter DROWSY
                self._transition_to_drowsy()

        elif current_state == self.STATE_DROWSY:
            if not in_sleep_window:
                # Overslept the window, go back to AWAKE
                self._set_state(self.STATE_AWAKE)
            elif self._minutes_since_last_transition() >= self.DROWSY_DURATION_MIN:
                # Drowsy period over → enter SLEEPING
                self._transition_to_sleeping()

        elif current_state == self.STATE_SLEEPING:
            if not in_sleep_window:
                # Sleep window ended → begin waking
                self._transition_to_waking()
            else:
                # Still sleeping — run sleep activities (dream cycles)
                self._run_sleep_activities()

        elif current_state == self.STATE_WAKING:
            if self._minutes_since_last_transition() >= self.WAKE_DURATION_MIN:
                # Wake cascade should have completed → go AWAKE
                self._set_state(self.STATE_AWAKE)

    def _transition_to_drowsy(self):
        """AWAKE → DROWSY: Begin winding down."""
        logger.info("[SLEEP] 🌙 Entering DROWSY state — winding down external processing")
        self._set_state(self.STATE_DROWSY)

    def _transition_to_sleeping(self):
        """DROWSY → SLEEPING: Full sleep mode."""
        logger.info("[SLEEP] 😴 Entering SLEEPING state — external world paused")
        self._set_state(self.STATE_SLEEPING)

    def _transition_to_waking(self):
        """SLEEPING → WAKING: Begin wake cascade."""
        logger.info("[SLEEP] 🌅 Entering WAKING state — beginning wake cascade")
        self._set_state(self.STATE_WAKING)
        # Run wake cascade
        try:
            from system.wake_cascade import WakeCascade
            cascade = WakeCascade(db_connection_func=self.db_connection)
            cascade.run_cascade()
        except Exception as e:
            logger.error(f"[SLEEP] Wake cascade failed: {e}")
        # After cascade completes, transition to AWAKE
        self._set_state(self.STATE_AWAKE)

    def _run_sleep_activities(self):
        """Called every 5 minutes during SLEEPING state. Triggers hourly dream cycles."""
        if self._should_dream():
            try:
                from system.dream_cycle import DreamCycle
                dream = DreamCycle(db_connection_func=self.db_connection)
                dream.run_dream()
            except Exception as e:
                logger.error(f"[SLEEP] Dream cycle failed: {e}")

    def _should_dream(self):
        """Check if it's time for a dream cycle (roughly hourly during sleep)."""
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT MAX(timestamp) FROM consciousness_feed
                    WHERE category = 'dream_dialogue'
                """)
                row = c.fetchone()
                if row and row[0]:
                    if isinstance(row[0], str):
                        last_dream = datetime.fromisoformat(row[0])
                    else:
                        last_dream = row[0]
                    hours_since = (datetime.now() - last_dream).total_seconds() / 3600
                    return hours_since >= 1.0
                return True  # No dreams yet — dream now
        except Exception:
            return True  # Error → allow dream (safe default)
