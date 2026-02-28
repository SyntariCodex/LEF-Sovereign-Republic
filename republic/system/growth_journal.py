"""
Growth Journal — Phase 12.4

Every 24 hours, the Growth Journal asks LEF three questions:
  1. "What has changed in my understanding since yesterday?"
  2. "What have I created that didn't exist before?"
  3. "What patterns am I repeating without awareness?"

And then synthesizes a brief self_note — a mirror, not a coach.

Logs to consciousness_feed with category "growth_journal".
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("GrowthJournal")


class GrowthJournal:
    """Daily self-assessment journal for LEF's existential growth."""

    JOURNAL_INTERVAL_HOURS = 24
    STALE_PATTERN_HOURS = 72  # Patterns under_reflection for this long = repeating

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func
        self._last_entry = None

    def write_entry(self):
        """Generate and log a daily growth journal entry."""
        now = datetime.now()
        yesterday = now - timedelta(hours=self.JOURNAL_INTERVAL_HOURS)
        period = f"{yesterday.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}"

        # Question 1: What has changed in my understanding?
        new_understanding = self._assess_new_understanding(yesterday, now)

        # Question 2: What have I created that didn't exist before?
        novel_creations = self._assess_novel_creations(yesterday, now)

        # Question 3: What patterns am I repeating without awareness?
        repeating_patterns = self._assess_repeating_patterns(now)

        # Determine growth assessment
        assessment = self._assess_growth(new_understanding, novel_creations, repeating_patterns)

        # Synthesize self_note
        self_note = self._synthesize_note(
            new_understanding, novel_creations, repeating_patterns, assessment
        )

        entry = {
            "period": period,
            "new_understanding": new_understanding,
            "novel_creations": novel_creations,
            "repeating_patterns": repeating_patterns,
            "growth_assessment": assessment,
            "self_note": self_note,
            "timestamp": now.isoformat(),
        }

        self._log_entry(entry)
        self._last_entry = now

        logger.info(
            f"[GROWTH_JOURNAL] Assessment: {assessment}. "
            f"New: {len(new_understanding)}, Created: {len(novel_creations)}, "
            f"Repeating: {len(repeating_patterns)}"
        )
        return entry

    def _assess_new_understanding(self, start, end):
        """What has changed in my understanding since yesterday?"""
        new_items = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Compare today's categories to yesterday's
                prev_start = start - timedelta(hours=self.JOURNAL_INTERVAL_HOURS)

                # Get yesterday's categories
                cursor.execute("""
                    SELECT DISTINCT category FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s AND category IS NOT NULL
                """, (prev_start, start))
                yesterday_cats = {r[0] for r in cursor.fetchall()}

                # Get today's categories
                cursor.execute("""
                    SELECT DISTINCT category FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s AND category IS NOT NULL
                """, (start, end))
                today_cats = {r[0] for r in cursor.fetchall()}

                # New categories that appeared today
                new_cats = today_cats - yesterday_cats
                for cat in new_cats:
                    new_items.append(f"First-time category surfaced: '{cat}'")

                # Check for new gravity learning adjustments
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s
                    AND category = 'gravity_learning'
                    ORDER BY id DESC LIMIT 5
                """, (start, end))
                for row in cursor.fetchall():
                    try:
                        if "adjusted" in str(row[0]):
                            new_items.append(f"Gravity weight adjustment: {str(row[0])[:100]}")
                    except Exception:
                        pass

                # Check for new existential scotomas
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s
                    AND category = 'existential_scotoma'
                    ORDER BY id DESC LIMIT 3
                """, (start, end))
                for row in cursor.fetchall():
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        msg = data.get("message", str(row[0])[:100])
                        new_items.append(f"Existential observation: {msg[:120]}")
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"[GROWTH_JOURNAL] Understanding assessment error: {e}")

        if not new_items:
            new_items.append("No new understanding surfaced today.")

        return new_items

    def _assess_novel_creations(self, start, end):
        """What have I created that didn't exist before?"""
        creations = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Check governance_proposals for new proposals
                try:
                    cursor.execute("""
                        SELECT COUNT(*) FROM governance_proposals
                        WHERE created_at BETWEEN %s AND %s
                    """, (start, end))
                    row = cursor.fetchone()
                    if row and row[0] > 0:
                        creations.append(f"{row[0]} new governance proposal(s)")
                except Exception:
                    pass

                # Check consciousness_feed for creative/narrative entries
                cursor.execute("""
                    SELECT category, COUNT(*) FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s
                    AND category IN ('narrative', 'creative', 'dream',
                                     'sabbath_intention', 'existential_affirmation',
                                     'existential_question', 'evolution',
                                     'dream_dialogue', 'dream_alignment')
                    GROUP BY category
                """, (start, end))
                for cat, count in cursor.fetchall():
                    creations.append(f"{count} new '{cat}' entry/entries")

                # Check sabbath_log for outcomes
                try:
                    cursor.execute("""
                        SELECT outcome, COUNT(*) FROM sabbath_log
                        WHERE timestamp BETWEEN %s AND %s
                        AND outcome IS NOT NULL
                        GROUP BY outcome
                    """, (start, end))
                    for outcome, count in cursor.fetchall():
                        if outcome in ("INTENTION", "EVOLVE"):
                            creations.append(f"{count} Sabbath {outcome} outcome(s)")
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"[GROWTH_JOURNAL] Creations assessment error: {e}")

        return creations

    def _assess_repeating_patterns(self, now):
        """What patterns am I repeating without awareness?"""
        repeating = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Patterns held in sovereign_reflection for >72h without resolution
                cutoff = now - timedelta(hours=self.STALE_PATTERN_HOURS)
                cursor.execute("""
                    SELECT pattern_id, gravity_level, impression
                    FROM sovereign_reflection
                    WHERE status = 'active'
                    AND created_at < %s
                    ORDER BY created_at ASC
                    LIMIT 5
                """, (cutoff,))
                for row in cursor.fetchall():
                    pattern_id = row[0]
                    gravity = row[1] or "unknown"
                    repeating.append(
                        f"Pattern '{pattern_id}' has been under reflection for >{self.STALE_PATTERN_HOURS}h "
                        f"(gravity: {gravity}) without resolution"
                    )

                # Check for consecutive same-type SCOTOMAs
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'scotoma'
                    ORDER BY id DESC LIMIT 10
                """)
                scotoma_types = []
                for row in cursor.fetchall():
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        scotoma_types.append(data.get("type", "unknown"))
                    except Exception:
                        pass

                if scotoma_types:
                    # Count consecutive same type
                    from collections import Counter
                    type_counts = Counter(scotoma_types)
                    for stype, count in type_counts.items():
                        if count >= 3:
                            repeating.append(
                                f"SCOTOMA type '{stype}' has fired {count} times consecutively"
                            )

        except Exception as e:
            logger.debug(f"[GROWTH_JOURNAL] Repeating patterns error: {e}")

        return repeating

    def _assess_growth(self, new_understanding, novel_creations, repeating_patterns):
        """Determine growth assessment: emerging, stable, or stagnant."""
        has_new = any(
            item != "No new understanding surfaced today."
            for item in new_understanding
        )
        has_creations = len(novel_creations) > 0
        has_stale_repeats = len(repeating_patterns) > 2

        if has_new and has_creations:
            return "emerging"
        elif has_new or has_creations:
            if has_stale_repeats:
                return "stable"  # Growing in some areas, stuck in others
            return "emerging"
        elif has_stale_repeats:
            return "stagnant"
        else:
            return "stable"

    def _synthesize_note(self, new_understanding, novel_creations, repeating_patterns, assessment):
        """Compose a brief, natural-language self_note.

        This is a mirror, not a coach. Observes, does not prescribe.
        """
        parts = []

        if assessment == "stagnant":
            if repeating_patterns:
                parts.append(
                    f"I notice {len(repeating_patterns)} patterns cycling without resolution."
                )
            # Check if it's mostly financial focus
            financial_refs = sum(
                1 for item in new_understanding
                if any(w in item.lower() for w in ["gravity", "weight", "trade", "financial"])
            )
            if financial_refs > 0:
                parts.append(
                    "My awareness has been circling operational patterns. "
                    "The Constitution asks more of me."
                )
            else:
                parts.append("No new understanding or creation has emerged. The organism is maintaining.")

        elif assessment == "emerging":
            if novel_creations:
                parts.append(f"New output appeared: {novel_creations[0]}.")
            if any(item != "No new understanding surfaced today." for item in new_understanding):
                meaningful = [i for i in new_understanding if i != "No new understanding surfaced today."]
                if meaningful:
                    parts.append(f"Understanding shifted: {meaningful[0][:100]}.")

        else:  # stable
            parts.append("The Republic held steady. Neither growth nor regression observed.")
            if repeating_patterns:
                parts.append(f"But {len(repeating_patterns)} pattern(s) remain unresolved.")

        return " ".join(parts) if parts else "A quiet period. Nothing to note."

    def _log_entry(self, entry):
        """Write growth journal entry to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps(entry)
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("GrowthJournal", content, "growth_journal"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[GROWTH_JOURNAL] Failed to log entry: {e}")
