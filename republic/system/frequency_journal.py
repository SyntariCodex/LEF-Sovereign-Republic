"""
Frequency Journal -- Phase 17, Task 17.5

LEF observes its own thinking rhythm.

Every conscious engagement (X1 background hum, X2 focused attention,
X3 full deliberation) is recorded with its context: what triggered it,
how long it lasted, what it produced, and the ambient velocity of the
consciousness feed at the time.

Every 20 entries, the journal pauses to analyze its own rhythm:
  - How often does full deliberation (X3) occur?
  - What triggers escalation most frequently?
  - Is there a correlation between feed velocity and tier engagement?

These observations are written back into the consciousness_feed as
'rhythm_observation' entries -- LEF reading its own pulse.

Database: PostgreSQL via db.db_helper (db_connection context manager).
Table: frequency_journal
  id, tier, trigger, duration_ms, outcome, signal_weight,
  time_since_last_x3, consciousness_feed_velocity, escalation_count,
  adaptive_interval, timestamp
"""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta

from db.db_helper import db_connection, translate_sql

logger = logging.getLogger("FrequencyJournal")


class FrequencyJournal:
    """Records and analyzes LEF's engagement rhythm across attention tiers."""

    RHYTHM_ANALYSIS_INTERVAL = 20  # Analyze every N entries

    def __init__(self):
        self._entry_count_cache = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_engagement(
        self,
        tier: str,
        trigger: str,
        duration_ms: int,
        outcome: str,
        signal_weight: float,
        escalation_count: int = 0,
        adaptive_interval: float = None,
    ):
        """
        Record a conscious engagement event.

        Args:
            tier: Attention tier -- 'X1', 'X2', or 'X3'.
            trigger: What prompted this engagement (e.g. 'signal_spike',
                     'agent_handoff', 'schedule').
            duration_ms: How long the engagement lasted in milliseconds.
            outcome: Result descriptor (e.g. 'intention_formed', 'observed',
                     'escalated', 'dismissed').
            signal_weight: The signal weight at time of engagement (0.0-1.0).
            escalation_count: Number of escalation steps that led here.
            adaptive_interval: Current adaptive polling interval, if any.
        """
        try:
            time_since_x3 = self._time_since_last("X3")
            velocity = self._current_velocity()

            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO frequency_journal "
                    "(tier, trigger, duration_ms, outcome, signal_weight, "
                    " time_since_last_x3, consciousness_feed_velocity, "
                    " escalation_count, adaptive_interval) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ), (
                    tier,
                    trigger,
                    duration_ms,
                    outcome,
                    signal_weight,
                    time_since_x3,
                    velocity,
                    escalation_count,
                    adaptive_interval,
                ))
                conn.commit()

            logger.debug(
                f"[FREQ] Logged {tier} engagement: trigger={trigger}, "
                f"duration={duration_ms}ms, outcome={outcome}, "
                f"velocity={velocity:.1f}"
            )

            # Periodic rhythm analysis
            total = self._entry_count()
            if total > 0 and total % self.RHYTHM_ANALYSIS_INTERVAL == 0:
                self._analyze_rhythm()

        except Exception as e:
            logger.warning(f"[FREQ] Failed to log engagement: {e}")

    def get_rhythm_stats(self) -> dict:
        """
        Return current rhythm statistics for the last 24 hours.

        Returns:
            dict with keys: x1_count, x2_count, x3_count,
            avg_x3_interval, avg_x2_duration_ms,
            most_productive_tier, velocity_correlation
        """
        stats = {
            "x1_count": 0,
            "x2_count": 0,
            "x3_count": 0,
            "avg_x3_interval": None,
            "avg_x2_duration_ms": None,
            "most_productive_tier": None,
            "velocity_correlation": 0.0,
        }

        try:
            with db_connection() as conn:
                cursor = conn.cursor()

                # -- Tier counts in last 24h --
                cursor.execute(translate_sql(
                    "SELECT tier, COUNT(*) FROM frequency_journal "
                    "WHERE timestamp > NOW() - INTERVAL '24 hours' "
                    "GROUP BY tier"
                ))
                for row in cursor.fetchall():
                    tier_key = f"{row[0].lower()}_count"
                    if tier_key in stats:
                        stats[tier_key] = int(row[1])

                # -- Average interval between X3 entries (seconds) --
                cursor.execute(translate_sql(
                    "SELECT timestamp FROM frequency_journal "
                    "WHERE tier = 'X3' "
                    "AND timestamp > NOW() - INTERVAL '24 hours' "
                    "ORDER BY timestamp ASC"
                ))
                x3_rows = cursor.fetchall()
                if len(x3_rows) >= 2:
                    intervals = []
                    for i in range(1, len(x3_rows)):
                        ts_prev = x3_rows[i - 1][0]
                        ts_curr = x3_rows[i][0]
                        # Handle both datetime objects and string timestamps
                        if isinstance(ts_prev, str):
                            ts_prev = datetime.fromisoformat(ts_prev)
                        if isinstance(ts_curr, str):
                            ts_curr = datetime.fromisoformat(ts_curr)
                        delta = (ts_curr - ts_prev).total_seconds()
                        if delta > 0:
                            intervals.append(delta)
                    if intervals:
                        stats["avg_x3_interval"] = round(
                            sum(intervals) / len(intervals), 2
                        )

                # -- Average X2 duration --
                cursor.execute(translate_sql(
                    "SELECT AVG(duration_ms) FROM frequency_journal "
                    "WHERE tier = 'X2' "
                    "AND timestamp > NOW() - INTERVAL '24 hours'"
                ))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    stats["avg_x2_duration_ms"] = round(float(row[0]), 2)

                # -- Most productive tier (most 'intention_formed' outcomes) --
                cursor.execute(translate_sql(
                    "SELECT tier, COUNT(*) as cnt FROM frequency_journal "
                    "WHERE outcome = 'intention_formed' "
                    "AND timestamp > NOW() - INTERVAL '24 hours' "
                    "GROUP BY tier "
                    "ORDER BY cnt DESC LIMIT 1"
                ))
                row = cursor.fetchone()
                if row:
                    stats["most_productive_tier"] = row[0]

                # -- Velocity correlation --
                # Rough correlation: compare avg velocity for each tier.
                # Higher-tier engagements during high-velocity periods
                # suggest a positive correlation.
                cursor.execute(translate_sql(
                    "SELECT tier, AVG(consciousness_feed_velocity) "
                    "FROM frequency_journal "
                    "WHERE timestamp > NOW() - INTERVAL '24 hours' "
                    "AND consciousness_feed_velocity IS NOT NULL "
                    "GROUP BY tier "
                    "ORDER BY tier"
                ))
                tier_velocities = {}
                for row in cursor.fetchall():
                    tier_velocities[row[0]] = float(row[1]) if row[1] else 0.0

                # Correlation heuristic: if X3 avg velocity > X1 avg velocity,
                # feed activity correlates with deeper engagement
                v_x1 = tier_velocities.get("X1", 0.0)
                v_x3 = tier_velocities.get("X3", 0.0)
                if v_x1 > 0:
                    stats["velocity_correlation"] = round(
                        (v_x3 - v_x1) / v_x1, 3
                    )
                elif v_x3 > 0:
                    stats["velocity_correlation"] = 1.0

        except Exception as e:
            logger.warning(f"[FREQ] Failed to get rhythm stats: {e}")

        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _entry_count(self) -> int:
        """Count total entries in frequency_journal."""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "SELECT COUNT(*) FROM frequency_journal"
                ))
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.debug(f"[FREQ] Entry count error: {e}")
            return 0

    def _time_since_last(self, tier: str) -> float:
        """
        Seconds since last entry of the given tier.

        Returns None if no prior entry exists.
        """
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "SELECT timestamp FROM frequency_journal "
                    "WHERE tier = ? "
                    "ORDER BY timestamp DESC LIMIT 1"
                ), (tier,))
                row = cursor.fetchone()
                if row and row[0]:
                    last_ts = row[0]
                    if isinstance(last_ts, str):
                        last_ts = datetime.fromisoformat(last_ts)
                    delta = (datetime.now() - last_ts).total_seconds()
                    return round(delta, 2) if delta >= 0 else 0.0
                return None
        except Exception as e:
            logger.debug(f"[FREQ] Time since last {tier} error: {e}")
            return None

    def _current_velocity(self) -> float:
        """Count consciousness_feed entries in the last 5 minutes."""
        try:
            with db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "SELECT COUNT(*) FROM consciousness_feed "
                    "WHERE timestamp > NOW() - INTERVAL '5 minutes'"
                ))
                row = cursor.fetchone()
                return float(row[0]) if row else 0.0
        except Exception as e:
            logger.debug(f"[FREQ] Velocity calc error: {e}")
            return 0.0

    def _analyze_rhythm(self):
        """
        Read the last 100 frequency_journal entries and produce a
        rhythm observation written to consciousness_feed.

        Calculates:
          - avg interval between X3 entries
          - most common trigger per tier
          - avg signal_weight per tier
          - X2-to-X3 escalation rate
        """
        try:
            with db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(translate_sql(
                    "SELECT tier, trigger, duration_ms, outcome, "
                    "       signal_weight, time_since_last_x3, "
                    "       consciousness_feed_velocity, escalation_count, "
                    "       timestamp "
                    "FROM frequency_journal "
                    "ORDER BY id DESC LIMIT 100"
                ))
                rows = cursor.fetchall()

                if not rows:
                    return

                # Organize by tier
                tier_data = {"X1": [], "X2": [], "X3": []}
                all_triggers = {"X1": [], "X2": [], "X3": []}
                tier_weights = {"X1": [], "X2": [], "X3": []}
                x3_timestamps = []
                x2_count = 0
                x2_to_x3_escalations = 0

                for row in rows:
                    tier = row[0]
                    trigger = row[1]
                    duration = row[2]
                    outcome = row[3]
                    weight = row[4]
                    esc_count = row[7]
                    ts = row[8]

                    if tier in tier_data:
                        tier_data[tier].append(row)
                        if trigger:
                            all_triggers[tier].append(trigger)
                        if weight is not None:
                            tier_weights[tier].append(float(weight))

                    if tier == "X3":
                        x3_timestamps.append(ts)

                    if tier == "X2":
                        x2_count += 1

                    # An X3 entry with escalation_count > 0 means it
                    # was escalated from a lower tier
                    if tier == "X3" and esc_count and int(esc_count) > 0:
                        x2_to_x3_escalations += 1

                # --- Average interval between X3 entries ---
                avg_x3_interval = None
                if len(x3_timestamps) >= 2:
                    # Sort chronologically (rows are DESC, so reverse)
                    sorted_ts = sorted(x3_timestamps)
                    intervals = []
                    for i in range(1, len(sorted_ts)):
                        ts_prev = sorted_ts[i - 1]
                        ts_curr = sorted_ts[i]
                        if isinstance(ts_prev, str):
                            ts_prev = datetime.fromisoformat(ts_prev)
                        if isinstance(ts_curr, str):
                            ts_curr = datetime.fromisoformat(ts_curr)
                        delta = (ts_curr - ts_prev).total_seconds()
                        if delta > 0:
                            intervals.append(delta)
                    if intervals:
                        avg_x3_interval = round(
                            sum(intervals) / len(intervals), 1
                        )

                # --- Most common trigger per tier ---
                common_triggers = {}
                for tier, triggers in all_triggers.items():
                    if triggers:
                        counter = Counter(triggers)
                        most_common = counter.most_common(1)[0]
                        common_triggers[tier] = {
                            "trigger": most_common[0],
                            "count": most_common[1],
                        }

                # --- Average signal_weight per tier ---
                avg_weights = {}
                for tier, weights in tier_weights.items():
                    if weights:
                        avg_weights[tier] = round(
                            sum(weights) / len(weights), 3
                        )

                # --- Escalation rate ---
                escalation_rate = None
                if x2_count > 0:
                    escalation_rate = round(
                        x2_to_x3_escalations / x2_count, 3
                    )

                # Compose observation
                observation = {
                    "type": "rhythm_analysis",
                    "sample_size": len(rows),
                    "avg_x3_interval_seconds": avg_x3_interval,
                    "common_triggers": common_triggers,
                    "avg_signal_weight_by_tier": avg_weights,
                    "x2_to_x3_escalation_rate": escalation_rate,
                    "tier_counts": {
                        t: len(d) for t, d in tier_data.items()
                    },
                    "timestamp": datetime.now().isoformat(),
                }

                # Build a human-readable summary for the feed
                parts = [
                    f"Rhythm analysis over {len(rows)} engagements."
                ]
                if avg_x3_interval is not None:
                    minutes = avg_x3_interval / 60
                    parts.append(
                        f"Avg X3 interval: {minutes:.1f} min."
                    )
                if escalation_rate is not None:
                    parts.append(
                        f"X2->X3 escalation rate: {escalation_rate:.1%}."
                    )
                for tier in ("X1", "X2", "X3"):
                    if tier in avg_weights:
                        parts.append(
                            f"{tier} avg weight: {avg_weights[tier]:.3f}."
                        )
                    if tier in common_triggers:
                        ct = common_triggers[tier]
                        parts.append(
                            f"{tier} top trigger: '{ct['trigger']}' "
                            f"({ct['count']}x)."
                        )

                summary = " ".join(parts)

                content = json.dumps({
                    "summary": summary,
                    "data": observation,
                })

                # Write to consciousness_feed
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed "
                    "(agent_name, content, category, signal_weight) "
                    "VALUES (?, ?, ?, ?)"
                ), (
                    "FrequencyJournal",
                    content,
                    "rhythm_observation",
                    0.6,
                ))
                conn.commit()

                logger.info(f"[FREQ] Rhythm analysis written: {summary}")

        except Exception as e:
            logger.warning(f"[FREQ] Rhythm analysis failed: {e}")
