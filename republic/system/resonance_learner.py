"""
Resonance Learner — calibrates ResonanceFilter thresholds based on outcomes.

Tracks:
  - Signals that PASSED the filter -> did they lead to positive/negative reverb?
  - The distribution of scores near the threshold boundary

If passed signals consistently lead to negative reverb -> raise threshold
  (LEF is being too permissive, letting noise through)
If the system seems to be missing important patterns -> lower threshold
  (LEF is filtering too aggressively)

Reads from: resonance_log, reverb_log
Writes to: resonance_config.json (threshold adjustments)
Constraints:
  - Threshold range: [0.3, 0.9] — never fully open, never fully closed
  - Maximum adjustment per cycle: +/-0.02
  - Minimum 10 data points before any adjustment
  - All adjustments logged to consciousness_feed

Phase 11.2 of The Learning Loop.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("ResonanceLearner")

# Bounds
THRESHOLD_MIN = 0.3
THRESHOLD_MAX = 0.9
ADJUSTMENT_UP = 0.02     # Raise threshold (stricter)
ADJUSTMENT_DOWN = -0.01   # Lower threshold (more permissive)
MIN_DATA_POINTS = 10
DEFAULT_THRESHOLD = 0.6


class ResonanceLearner:
    """
    Calibrates ResonanceFilter thresholds based on reverb outcomes.

    Called by Body Two (SovereignReflection) every 5th cycle.
    Cross-references resonance_log entries with reverb_log outcomes
    to determine if the filter is too permissive or too strict.
    """

    def __init__(self, db_connection_func, config_path=None):
        """
        Args:
            db_connection_func: callable returning DB connection context manager
            config_path: path to resonance_config.json
        """
        self.db_connection = db_connection_func
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "resonance_config.json"
        )
        self._ensure_config()
        self._ensure_table()

    def _ensure_config(self):
        """Ensure resonance_config.json exists with defaults."""
        if not os.path.exists(self.config_path):
            default_config = {
                "pass_threshold": DEFAULT_THRESHOLD,
                "golden_threshold": 0.8,
                "last_calibration": None,
                "calibration_count": 0
            }
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info("[RESONANCE_LEARNER] Created default resonance_config.json")
            except Exception as e:
                logger.error(f"[RESONANCE_LEARNER] Could not create config: {e}")

    def _ensure_table(self):
        """Ensure resonance_log table exists."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS resonance_log (
                        id SERIAL PRIMARY KEY,
                        signal_source TEXT,
                        signal_content TEXT,
                        resonance_score REAL,
                        passed_filter BOOLEAN,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("[RESONANCE_LEARNER] resonance_log table ready")
        except Exception as e:
            logger.debug(f"[RESONANCE_LEARNER] Table creation note: {e}")

    def calibrate(self):
        """
        Main calibration method. Called by Body Two every 5th cycle.

        1. Join resonance_log entries with reverb_log outcomes
        2. Calculate "filter accuracy" — percentage of passed signals that led to
           neutral-or-positive outcomes
        3. Adjust threshold based on accuracy
        4. Persist to resonance_config.json
        5. Log to consciousness_feed
        """
        try:
            accuracy, data_points = self._calculate_filter_accuracy()

            if data_points < MIN_DATA_POINTS:
                logger.debug(f"[RESONANCE_LEARNER] Insufficient data ({data_points}/{MIN_DATA_POINTS}), skipping calibration")
                return

            adjustment = self._determine_adjustment(accuracy)
            if adjustment == 0.0:
                self._log_calibration(accuracy, data_points, None, "held")
                return

            config = self._load_config()
            old_threshold = config.get("pass_threshold", DEFAULT_THRESHOLD)
            new_threshold = self._clamp_threshold(old_threshold + adjustment)

            if abs(new_threshold - old_threshold) < 0.001:
                return  # Already at bounds

            config["pass_threshold"] = round(new_threshold, 3)
            config["last_calibration"] = datetime.now().isoformat()
            config["calibration_count"] = config.get("calibration_count", 0) + 1
            self._save_config(config)

            self._log_calibration(accuracy, data_points, {
                "old_threshold": old_threshold,
                "new_threshold": new_threshold,
                "adjustment": adjustment
            }, "adjusted")

        except Exception as e:
            logger.error(f"[RESONANCE_LEARNER] Calibration error: {e}")

    def _calculate_filter_accuracy(self):
        """
        Cross-reference resonance_log with reverb_log.

        Phase 33.8: Reduced join window from 48h to 12h with time decay.
        Recent events weighted higher via EXP decay on time delta.

        Returns: (accuracy_ratio, data_point_count)
        """
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Phase 33.8: Reduced window from 48h to 12h with time decay
                # decay_weight = EXP(-hours_between / 6) — halves every ~4h
                cursor.execute("""
                    SELECT
                        r.passed_filter,
                        rv.reverb_assessment,
                        COUNT(*),
                        AVG(EXP(-1.0 * EXTRACT(EPOCH FROM (rv.timestamp - r.timestamp)) / 21600)) as avg_decay
                    FROM resonance_log r
                    JOIN reverb_log rv ON
                        r.signal_source = rv.domain
                        AND r.timestamp BETWEEN
                            rv.timestamp - INTERVAL '12 hours'
                            AND rv.timestamp + INTERVAL '1 hour'
                    WHERE rv.reverb_assessment IS NOT NULL
                    GROUP BY r.passed_filter, rv.reverb_assessment
                """)
                rows = cursor.fetchall()

                if not rows:
                    return 0.0, 0

                passed_positive = 0.0
                passed_negative = 0.0
                total_passed = 0.0

                for passed, assessment, count, avg_decay in rows:
                    decay_weight = avg_decay if avg_decay else 1.0
                    weighted_count = count * decay_weight
                    if passed:
                        total_passed += weighted_count
                        if assessment in ("positive_reverb", "improvement", "neutral_reverb", "neutral", "silent"):
                            passed_positive += weighted_count
                        elif assessment in ("negative_reverb", "regression"):
                            passed_negative += weighted_count

                if total_passed < 0.01:
                    return 0.0, 0

                accuracy = passed_positive / total_passed
                return round(accuracy, 3), int(total_passed)

        except Exception as e:
            logger.debug(f"[RESONANCE_LEARNER] Accuracy calculation error: {e}")
            return 0.0, 0

    def _determine_adjustment(self, accuracy):
        """
        Determine threshold adjustment based on filter accuracy.

        accuracy < 0.5 -> raise threshold (too much noise getting through)
        accuracy > 0.8 -> lower threshold (may be filtering good signals)
        0.5-0.8 -> no change (healthy range)
        """
        if accuracy < 0.5:
            return ADJUSTMENT_UP  # +0.02 — stricter
        elif accuracy > 0.8:
            return ADJUSTMENT_DOWN  # -0.01 — slightly more permissive
        else:
            return 0.0  # Healthy range — hold

    def _clamp_threshold(self, threshold):
        """Apply bounds to threshold value."""
        return round(max(THRESHOLD_MIN, min(THRESHOLD_MAX, threshold)), 3)

    def _log_calibration(self, accuracy, data_points, adjustment_info, action):
        """Log calibration result to consciousness_feed."""
        try:
            if action == "held":
                content = (
                    f"[ResonanceLearner] Threshold held at {self._load_config().get('pass_threshold', DEFAULT_THRESHOLD)} "
                    f"(filter accuracy {accuracy:.2f} — healthy range, "
                    f"{data_points} data points)"
                )
            else:
                content = (
                    f"[ResonanceLearner] Threshold adjusted "
                    f"{adjustment_info['old_threshold']} -> {adjustment_info['new_threshold']} "
                    f"(filter accuracy {accuracy:.2f}, "
                    f"{data_points} data points)"
                )

            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, ("ResonanceLearner", content, "resonance_learning"))
                conn.commit()

            logger.info(f"[RESONANCE_LEARNER] {content}")

        except Exception as e:
            logger.error(f"[RESONANCE_LEARNER] Failed to log calibration: {e}")

    def _load_config(self):
        """Load resonance config from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {"pass_threshold": DEFAULT_THRESHOLD}

    def _save_config(self, config):
        """Save resonance config to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"[RESONANCE_LEARNER] Config save failed: {e}")


def log_resonance_signal(db_connection_func, source, content, score, passed):
    """
    Utility function to log a signal through the resonance filter.
    Called by ResonanceFilter.check_resonance() to record filter decisions.

    Args:
        db_connection_func: callable returning DB connection
        source: signal domain/source
        content: brief description of signal
        score: resonance score (0.0-1.0)
        passed: bool — did it pass the filter?
    """
    try:
        with db_connection_func() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resonance_log (signal_source, signal_content, resonance_score, passed_filter)
                VALUES (%s, %s, %s, %s)
            """, (source, content[:500] if content else "", score, passed))
            conn.commit()
    except Exception:
        pass  # Logging failure should not interrupt filter operation
