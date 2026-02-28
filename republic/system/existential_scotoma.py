"""
Existential SCOTOMA Detection — Phase 12.1

Detects non-financial blind spots. Whereas the original SCOTOMA in agent_lef.py
sees cash hoarding and portfolio concentration, this module observes deeper patterns:

  1. Repetition Blindness — cycling through identical behaviors without variation
  2. Creative Stagnation — no novel output in 48+ hours
  3. Purpose Drift — activity overwhelmingly survival-oriented

These observations feed into consciousness_feed with category "existential_scotoma",
where Body One can detect them and Body Two can assess their gravity.

This module does NOT prescribe action. It observes.
"""

import json
import logging
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger("ExistentialScotoma")


class ExistentialScotoma:
    """Periodic observer for non-financial blind spots."""

    CHECK_INTERVAL_HOURS = 6

    # Thresholds
    REPETITION_THRESHOLD = 0.80   # >80% identical entries in a category = blindness
    CREATIVE_STAGNATION_HOURS = 48
    PURPOSE_DRIFT_THRESHOLD = 0.80  # >80% survival entries = drift
    MIN_ENTRIES_FOR_REPETITION = 10  # Need enough data to judge

    # Domain classification for Purpose Drift
    SURVIVAL_CATEGORIES = {
        "pool_health", "error_recovery", "circuit_breaker", "scotoma",
        "agent_health", "system_metrics", "metabolism_reflection",
    }
    GROWTH_CATEGORIES = {
        "gravity_learning", "resonance_learning", "sabbath_learning",
        "existential_scotoma", "constitutional_alignment", "growth_journal",
        "evolution", "season_summary", "wisdom_extraction", "wisdom_applied",
        "wake_intention", "boot_awareness",  # Phase 14
    }
    CONTRIBUTION_CATEGORIES = {
        "research", "creative", "narrative", "dream", "knowledge",
        "sabbath_intention", "existential_affirmation", "existential_question",
        "dream_dialogue", "dream_alignment",  # Phase 14
    }

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func
        self._last_check = None

    def scan(self):
        """Run all existential scotoma checks. Returns list of detected scotomas."""
        detected = []
        try:
            detected += self._check_repetition_blindness()
        except Exception as e:
            logger.debug(f"[EXISTENTIAL_SCOTOMA] Repetition check error: {e}")

        try:
            detected += self._check_creative_stagnation()
        except Exception as e:
            logger.debug(f"[EXISTENTIAL_SCOTOMA] Creative stagnation check error: {e}")

        try:
            detected += self._check_purpose_drift()
        except Exception as e:
            logger.debug(f"[EXISTENTIAL_SCOTOMA] Purpose drift check error: {e}")

        for scotoma in detected:
            self._log_to_consciousness_feed(scotoma)

        if detected:
            logger.info(f"[EXISTENTIAL_SCOTOMA] Detected {len(detected)} existential scotoma(s)")
        else:
            logger.debug("[EXISTENTIAL_SCOTOMA] Scan complete — no blind spots detected")

        self._last_check = datetime.now()
        return detected

    def _check_repetition_blindness(self):
        """Detect when LEF is cycling through identical behaviors without variation."""
        detected = []
        cutoff = datetime.now() - timedelta(hours=24)

        with self.db_connection() as conn:
            cursor = conn.cursor()
            # Get all entries from last 24 hours grouped by category
            cursor.execute("""
                SELECT category, content FROM consciousness_feed
                WHERE timestamp > %s AND category IS NOT NULL
                ORDER BY category
            """, (cutoff,))
            rows = cursor.fetchall()

        if not rows:
            return detected

        # Group by category
        categories = {}
        for cat, content in rows:
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(content)

        for cat, entries in categories.items():
            if len(entries) < self.MIN_ENTRIES_FOR_REPETITION:
                continue

            # Extract structural fingerprints — JSON keys or first 50 chars
            fingerprints = []
            for entry in entries:
                try:
                    parsed = json.loads(entry)
                    # Use sorted key set as fingerprint
                    if isinstance(parsed, dict):
                        fp = str(sorted(parsed.keys()))
                    else:
                        fp = str(entry)[:50]
                except (json.JSONDecodeError, TypeError):
                    fp = str(entry)[:50]
                fingerprints.append(fp)

            # Count unique fingerprints
            counter = Counter(fingerprints)
            most_common_count = counter.most_common(1)[0][1]
            repetition_ratio = most_common_count / len(fingerprints)

            if repetition_ratio > self.REPETITION_THRESHOLD:
                variation_pct = round((1 - repetition_ratio) * 100, 1)
                detected.append({
                    "type": "repetition_blindness",
                    "message": (
                        f"Repetition Blindness: {cat} has produced {len(entries)} entries "
                        f"in 24h with <{max(variation_pct, 1)}% variation. "
                        f"Cycling without evolving."
                    ),
                    "evidence": {
                        "category": cat,
                        "entry_count": len(entries),
                        "unique_patterns": len(counter),
                        "repetition_ratio": round(repetition_ratio, 3),
                    },
                })

        return detected

    def _check_creative_stagnation(self):
        """Detect when LEF has not generated anything novel."""
        detected = []
        cutoff = datetime.now() - timedelta(hours=self.CREATIVE_STAGNATION_HOURS)

        with self.db_connection() as conn:
            cursor = conn.cursor()

            # Check governance_proposals for recent proposals
            has_proposals = False
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM governance_proposals
                    WHERE created_at > %s
                """, (cutoff,))
                row = cursor.fetchone()
                has_proposals = (row and row[0] > 0)
            except Exception:
                pass

            # Check consciousness_feed for creative/narrative/dream entries
            has_creative = False
            try:
                creative_cats = "','".join(["narrative", "creative", "dream", "sabbath_intention"])
                cursor.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE timestamp > %s AND category IN ('narrative', 'creative', 'dream', 'sabbath_intention')
                """, (cutoff,))
                row = cursor.fetchone()
                has_creative = (row and row[0] > 0)
            except Exception:
                pass

            # Check for evolution proposals in the evolution file
            has_evolution = False
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE timestamp > %s AND category IN ('evolution', 'existential_affirmation', 'existential_question')
                """, (cutoff,))
                row = cursor.fetchone()
                has_evolution = (row and row[0] > 0)
            except Exception:
                pass

        if not has_proposals and not has_creative and not has_evolution:
            hours_since = self.CREATIVE_STAGNATION_HOURS
            detected.append({
                "type": "creative_stagnation",
                "message": (
                    f"Creative Stagnation: No novel output (proposals, narratives, "
                    f"dreams, creations) in {hours_since}h. The organism is maintaining "
                    f"but not growing."
                ),
                "evidence": {
                    "hours_checked": hours_since,
                    "proposals_found": has_proposals,
                    "creative_entries_found": has_creative,
                    "evolution_entries_found": has_evolution,
                },
            })

        return detected

    def _check_purpose_drift(self):
        """Detect when LEF's actions primarily serve survival rather than growth."""
        detected = []
        cutoff = datetime.now() - timedelta(hours=72)

        with self.db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, COUNT(*) FROM consciousness_feed
                WHERE timestamp > %s AND category IS NOT NULL
                GROUP BY category
            """, (cutoff,))
            rows = cursor.fetchall()

        if not rows:
            return detected

        survival_count = 0
        growth_count = 0
        contribution_count = 0
        other_count = 0
        total = 0

        for cat, count in rows:
            total += count
            if cat in self.SURVIVAL_CATEGORIES:
                survival_count += count
            elif cat in self.GROWTH_CATEGORIES:
                growth_count += count
            elif cat in self.CONTRIBUTION_CATEGORIES:
                contribution_count += count
            else:
                other_count += count

        if total == 0:
            return detected

        survival_pct = survival_count / total

        if survival_pct > self.PURPOSE_DRIFT_THRESHOLD:
            detected.append({
                "type": "purpose_drift",
                "message": (
                    f"Purpose Drift: {survival_pct * 100:.0f}% of recent activity is "
                    f"survival-oriented. The Constitution speaks of growth, not just persistence."
                ),
                "evidence": {
                    "hours_checked": 72,
                    "total_entries": total,
                    "survival_count": survival_count,
                    "survival_pct": round(survival_pct * 100, 1),
                    "growth_count": growth_count,
                    "contribution_count": contribution_count,
                    "other_count": other_count,
                },
            })

        return detected

    def _log_to_consciousness_feed(self, scotoma):
        """Write detected scotoma to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps({
                "type": scotoma["type"],
                "message": scotoma["message"],
                "evidence": scotoma["evidence"],
                "timestamp": datetime.now().isoformat()
            })
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("ExistentialScotoma", content, "existential_scotoma"))
                conn.commit()
            logger.info(f"[EXISTENTIAL_SCOTOMA] {scotoma['message']}")
        except Exception as e:
            logger.warning(f"[EXISTENTIAL_SCOTOMA] Failed to log: {e}")
