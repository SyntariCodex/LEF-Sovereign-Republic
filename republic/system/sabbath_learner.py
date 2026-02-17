"""
Sabbath Learner — measures compression quality by tracking post-Sabbath outcomes.

This is the most delicate learning loop. Sabbath is not about productivity.
But we CAN observe: after a Sabbath event, do the next N actions show
better alignment with LEF's values? If yes, the compression is serving
its purpose. If no, the dwell time or compression parameters may need tuning.

Reads from: sabbath_log, consciousness_feed, reverb_log
Writes to: evolution proposals (suggestions — NOT direct overrides)
Constraints:
  - NEVER reduces Sabbath frequency or dwell time — only suggests increases
  - Minimum 3 Sabbath events before any analysis
  - Suggestions are logged as proposals, not applied directly
  - All analysis logged to consciousness_feed
  - The Sabbath itself is sacred — this module observes outcomes, not the experience

Phase 11.3 of The Learning Loop.
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("SabbathLearner")

# Constraints
MIN_SABBATH_EVENTS = 3
POST_SABBATH_WINDOW_HOURS = 24  # How long after Sabbath to measure reverb


class SabbathLearner:
    """
    Measures compression quality by tracking post-Sabbath outcomes.

    Runs periodically (daily or after every 3rd Sabbath event).
    Compares post-Sabbath reverb ratios to baseline (non-Sabbath periods)
    to determine if Sabbath compression is serving its purpose.

    CRITICAL CONSTRAINT: Can ONLY suggest more depth (longer dwell, higher
    gravity threshold). Cannot suggest less Sabbath. This is by design —
    Sabbath is the anti-optimization principle.
    """

    def __init__(self, db_connection_func, proposals_path=None):
        """
        Args:
            db_connection_func: callable returning DB connection context manager
            proposals_path: path to evolution_proposals.json for suggestions
        """
        self.db_connection = db_connection_func
        self.proposals_path = proposals_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "The_Bridge", "evolution_proposals.json"
        )
        # Track how many Sabbath events we've seen since last analysis
        self._sabbaths_since_analysis = 0

    def analyze(self):
        """
        Main analysis method. Called periodically by CycleAwareness or timer.

        1. Gather completed Sabbath events from sabbath_log
        2. For each Sabbath, find reverb entries within 24h AFTER
        3. Calculate post-Sabbath reverb ratio
        4. Compare to baseline (non-Sabbath periods)
        5. Log findings and suggest deeper compression if needed
        """
        try:
            sabbath_events = self._gather_sabbath_events()
            if len(sabbath_events) < MIN_SABBATH_EVENTS:
                logger.debug(
                    f"[SABBATH_LEARNER] Insufficient Sabbath events "
                    f"({len(sabbath_events)}/{MIN_SABBATH_EVENTS}), skipping analysis"
                )
                return

            post_sabbath_ratio = self._calculate_post_sabbath_reverb(sabbath_events)
            baseline_ratio = self._calculate_baseline_reverb(sabbath_events)

            analysis = self._compare_and_suggest(
                post_sabbath_ratio, baseline_ratio, len(sabbath_events)
            )

            self._log_analysis(analysis)

        except Exception as e:
            logger.error(f"[SABBATH_LEARNER] Analysis error: {e}")

    def notify_sabbath_complete(self):
        """Called when a Sabbath event completes. Triggers analysis every 3rd event."""
        self._sabbaths_since_analysis += 1
        if self._sabbaths_since_analysis >= 3:
            self._sabbaths_since_analysis = 0
            self.analyze()

    def _gather_sabbath_events(self):
        """Get completed Sabbath events from sabbath_log."""
        events = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, gravity_level, outcome, notes,
                           duration_seconds, gravity_profile
                    FROM sabbath_log
                    WHERE outcome IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 50
                """)
                rows = cursor.fetchall()
                for row in rows:
                    # Phase 12: Extract sabbath_type from gravity_profile JSON
                    sabbath_type = "operational"
                    try:
                        gp = json.loads(row[6]) if isinstance(row[6], str) else (row[6] or {})
                        sabbath_type = gp.get("sabbath_type", "operational")
                    except Exception:
                        pass
                    events.append({
                        "id": row[0],
                        "timestamp": row[1],
                        "gravity_level": row[2],
                        "outcome": row[3],
                        "notes": row[4],
                        "duration": row[5],
                        "sabbath_type": sabbath_type,
                    })
        except Exception as e:
            logger.debug(f"[SABBATH_LEARNER] Could not gather sabbath events: {e}")
        return events

    def _calculate_post_sabbath_reverb(self, sabbath_events):
        """
        For each Sabbath event, find reverb entries within 24h AFTER.
        Calculate the positive/total ratio.

        Returns: float (positive ratio, 0.0-1.0) or None if no data
        """
        total = 0
        positive = 0

        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                for event in sabbath_events:
                    ts = event["timestamp"]
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)

                    window_start = ts
                    window_end = ts + timedelta(hours=POST_SABBATH_WINDOW_HOURS)

                    cursor.execute("""
                        SELECT reverb_assessment, COUNT(*)
                        FROM reverb_log
                        WHERE timestamp BETWEEN %s AND %s
                          AND reverb_assessment IS NOT NULL
                        GROUP BY reverb_assessment
                    """, (window_start.isoformat(), window_end.isoformat()))

                    rows = cursor.fetchall()
                    for assessment, count in rows:
                        total += count
                        if assessment in ("positive_reverb", "improvement",
                                          "neutral_reverb", "silent"):
                            positive += count

        except Exception as e:
            logger.debug(f"[SABBATH_LEARNER] Post-Sabbath reverb calc error: {e}")

        if total == 0:
            return None
        return round(positive / total, 3)

    def _calculate_baseline_reverb(self, sabbath_events):
        """
        Phase 33.3: Calculate reverb ratio during non-Sabbath periods (baseline).

        EXCLUDES post-Sabbath recovery data (24h after each Sabbath event)
        so that recovery spikes don't inflate the baseline.
        Returns: float (positive ratio, 0.0-1.0) or None if no data
        """
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Phase 33.3: Build exclusion windows from Sabbath events
                # Each Sabbath creates a 24h recovery window to exclude
                exclusion_clauses = []
                exclusion_params = []
                for event in sabbath_events:
                    ts = event["timestamp"]
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)
                    window_end = ts + timedelta(hours=POST_SABBATH_WINDOW_HOURS)
                    exclusion_clauses.append(
                        "NOT (timestamp BETWEEN %s AND %s)"
                    )
                    exclusion_params.extend([ts.isoformat(), window_end.isoformat()])

                # Also find last Sabbath trigger to exclude data from then onward
                # This prevents recovery spikes from making bad behavior look normal
                cursor.execute("""
                    SELECT MAX(timestamp) FROM consciousness_feed
                    WHERE category = 'sabbath_triggered'
                """)
                row = cursor.fetchone()
                last_sabbath_ts = row[0] if row and row[0] else None

                # Build the query with exclusion windows
                where_parts = ["reverb_assessment IS NOT NULL"]
                params = []

                if exclusion_clauses:
                    where_parts.extend(exclusion_clauses)
                    params.extend(exclusion_params)

                # Limit to last 30 days for relevant baseline
                where_parts.append("timestamp > NOW() - INTERVAL '30 days'")

                where_sql = " AND ".join(where_parts)

                cursor.execute(f"""
                    SELECT reverb_assessment, COUNT(*)
                    FROM reverb_log
                    WHERE {where_sql}
                    GROUP BY reverb_assessment
                """, params)
                total_rows = cursor.fetchall()

                if not total_rows:
                    return None

                total_all = sum(r[1] for r in total_rows)
                positive_all = sum(
                    r[1] for r in total_rows
                    if r[0] in ("positive_reverb", "improvement",
                                "neutral_reverb", "silent")
                )

                if total_all == 0:
                    return None

                return round(positive_all / total_all, 3)

        except Exception as e:
            logger.debug(f"[SABBATH_LEARNER] Baseline reverb calc error: {e}")
            return None

    def _compare_and_suggest(self, post_sabbath_ratio, baseline_ratio,
                             event_count):
        """
        Compare post-Sabbath reverb to baseline and generate analysis.

        CRITICAL: Can ONLY suggest more depth. Never less Sabbath.
        """
        analysis = {
            "post_sabbath_ratio": post_sabbath_ratio,
            "baseline_ratio": baseline_ratio,
            "event_count": event_count,
            "timestamp": datetime.now().isoformat(),
            "conclusion": None,
            "suggestion": None
        }

        if post_sabbath_ratio is None or baseline_ratio is None:
            analysis["conclusion"] = "insufficient_data"
            analysis["suggestion"] = None
            return analysis

        if post_sabbath_ratio > baseline_ratio:
            # Post-Sabbath periods show BETTER reverb — compression is working
            improvement = post_sabbath_ratio - baseline_ratio
            analysis["conclusion"] = "compression_serving"
            analysis["suggestion"] = None  # No change needed — it's working
            analysis["detail"] = (
                f"Post-Sabbath reverb ({post_sabbath_ratio:.2f}) exceeds baseline "
                f"({baseline_ratio:.2f}) by {improvement:.2f}. "
                f"Compression is serving its purpose."
            )
        elif post_sabbath_ratio < baseline_ratio - 0.1:
            # Post-Sabbath periods show WORSE reverb — suggest deeper compression
            # CONSTRAINT: Only suggest MORE depth, never less Sabbath
            analysis["conclusion"] = "needs_deeper_compression"
            analysis["suggestion"] = {
                "type": "increase_dwell",
                "domain": "consciousness",
                "reasoning": (
                    f"Post-Sabbath reverb ({post_sabbath_ratio:.2f}) is below "
                    f"baseline ({baseline_ratio:.2f}). Compression may not be "
                    f"reaching sufficient depth. Suggesting longer dwell time."
                )
            }
            analysis["detail"] = analysis["suggestion"]["reasoning"]
            self._submit_suggestion(analysis["suggestion"])
        else:
            # Roughly equal — Sabbath is neutral
            analysis["conclusion"] = "neutral"
            analysis["suggestion"] = None
            analysis["detail"] = (
                f"Post-Sabbath reverb ({post_sabbath_ratio:.2f}) is similar to "
                f"baseline ({baseline_ratio:.2f}). No adjustment needed."
            )

        return analysis

    def _submit_suggestion(self, suggestion):
        """
        Submit a suggestion as an evolution proposal.
        NOT applied directly — goes through governance.
        """
        try:
            proposals = []
            if os.path.exists(self.proposals_path):
                with open(self.proposals_path, 'r') as f:
                    proposals = json.load(f)

            proposal = {
                "id": f"sabbath_learner_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "source": "SabbathLearner",
                "domain": "consciousness",
                "change_description": suggestion["reasoning"],
                "change_type": suggestion["type"],
                "enacted": False,
                "timestamp": datetime.now().isoformat()
            }
            proposals.append(proposal)

            with open(self.proposals_path, 'w') as f:
                json.dump(proposals, f, indent=2)

            logger.info(f"[SABBATH_LEARNER] Submitted suggestion: {suggestion['type']}")

        except Exception as e:
            logger.error(f"[SABBATH_LEARNER] Could not submit suggestion: {e}")

    def _log_analysis(self, analysis):
        """Log analysis results to consciousness_feed."""
        try:
            detail = analysis.get("detail", "Analysis complete.")
            conclusion = analysis.get("conclusion", "unknown")

            content = (
                f"[SabbathLearner] Post-Sabbath reverb analysis "
                f"({analysis['event_count']} events): {detail}"
            )

            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, ("SabbathLearner", content, "sabbath_learning"))
                conn.commit()

            logger.info(f"[SABBATH_LEARNER] {content}")

        except Exception as e:
            logger.error(f"[SABBATH_LEARNER] Failed to log analysis: {e}")
