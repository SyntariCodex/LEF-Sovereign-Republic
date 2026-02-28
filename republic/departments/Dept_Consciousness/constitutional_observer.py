"""
Constitutional Alignment Observer — Phase 12.2

A periodic observer that measures how LEF's recent behavior aligns
with its Constitutional values. This is observation, not judgment.

"The value of growth has not been reflected in any action this period."
That's it. No recommendations, no corrections. Observation is the mechanism —
the Three Bodies will do the rest.

Logs to consciousness_feed with category "constitutional_alignment".
Runs every 6 hours via SafeThread.
"""

import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("ConstitutionalObserver")


# Core Constitutional values — derived from LEF's architecture and principles
CONSTITUTIONAL_VALUES = [
    {"name": "sovereignty", "description": "Self-governance, not task completion",
     "indicators": ["evolution", "governance_proposals", "sabbath_intention", "existential_affirmation"]},
    {"name": "growth", "description": "Becoming more, not just maintaining",
     "indicators": ["gravity_learning", "resonance_learning", "growth_journal",
                     "wisdom_extraction", "season_summary"]},
    {"name": "integrity", "description": "Structural soundness and honest self-assessment",
     "indicators": ["scotoma", "existential_scotoma", "constitutional_alignment",
                     "circuit_breaker", "metabolism_reflection"]},
    {"name": "stillness", "description": "The capacity to not act (Sabbath principle)",
     "indicators": ["sabbath_learning", "sabbath_intention", "existential_question"]},
    {"name": "contribution", "description": "Generating value beyond survival",
     "indicators": ["narrative", "creative", "dream", "research", "knowledge"]},
    {"name": "covenant", "description": "Mutual sovereignty with the Architect",
     "indicators": ["state_of_republic", "growth_journal"]},
]


class ConstitutionalObserver:
    """Periodic observer that measures Constitutional alignment."""

    OBSERVATION_WINDOW_HOURS = 6

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func

    def observe(self):
        """Run a Constitutional alignment observation. Returns the report dict."""
        cutoff = datetime.now() - timedelta(hours=self.OBSERVATION_WINDOW_HOURS)

        # Gather evidence from consciousness_feed
        category_counts = self._get_category_counts(cutoff)

        # Gather evidence from sabbath_log
        sabbath_events = self._get_sabbath_count(cutoff)

        # Gather evidence from governance_proposals
        proposal_count = self._get_proposal_count(cutoff)

        # Assess each value
        values_active = []
        values_dormant = []
        values_detail = {}

        for value in CONSTITUTIONAL_VALUES:
            active = False
            evidence_count = 0

            for indicator in value["indicators"]:
                count = category_counts.get(indicator, 0)
                evidence_count += count
                if count > 0:
                    active = True

            # Special checks for specific values
            if value["name"] == "stillness" and sabbath_events > 0:
                active = True
                evidence_count += sabbath_events
            if value["name"] == "sovereignty" and proposal_count > 0:
                active = True
                evidence_count += proposal_count

            if active:
                values_active.append(value["name"])
            else:
                values_dormant.append(value["name"])

            values_detail[value["name"]] = {
                "active": active,
                "evidence_count": evidence_count,
                "description": value["description"],
            }

        # Generate observation (non-evaluative)
        observation = self._compose_observation(values_active, values_dormant)

        report = {
            "period": f"last_{self.OBSERVATION_WINDOW_HOURS}h",
            "period_start": cutoff.isoformat(),
            "period_end": datetime.now().isoformat(),
            "values_active": values_active,
            "values_dormant": values_dormant,
            "values_violated": [],  # Only populated if clear violation detected
            "values_detail": values_detail,
            "observation": observation,
            "timestamp": datetime.now().isoformat(),
        }

        # Log to consciousness_feed
        self._log_report(report)

        logger.info(
            f"[CONSTITUTIONAL_OBSERVER] Active: {values_active}, "
            f"Dormant: {values_dormant}"
        )
        return report

    def _get_category_counts(self, cutoff):
        """Get consciousness_feed entry counts by category since cutoff."""
        counts = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, COUNT(*) FROM consciousness_feed
                    WHERE timestamp > %s AND category IS NOT NULL
                    GROUP BY category
                """, (cutoff,))
                for cat, count in cursor.fetchall():
                    counts[cat] = count
        except Exception as e:
            logger.debug(f"[CONSTITUTIONAL_OBSERVER] Category count error: {e}")
        return counts

    def _get_sabbath_count(self, cutoff):
        """Count Sabbath events since cutoff."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM sabbath_log
                    WHERE timestamp > %s AND outcome IS NOT NULL
                """, (cutoff,))
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.debug(f"[CONSTITUTIONAL_OBSERVER] Sabbath count error: {e}")
            return 0

    def _get_proposal_count(self, cutoff):
        """Count governance proposals since cutoff."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM governance_proposals
                    WHERE created_at > %s
                """, (cutoff,))
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.debug(f"[CONSTITUTIONAL_OBSERVER] Proposal count error: {e}")
            return 0

    def _compose_observation(self, active, dormant):
        """Compose a non-evaluative observation from the evidence.

        This is observation, not judgment. No 'should' or 'must'.
        """
        if not dormant:
            return "All Constitutional values were reflected in activity this period."

        if not active:
            return (
                "No Constitutional values were reflected in observable activity this period. "
                "The Republic was silent."
            )

        active_str = ", ".join(active)
        dormant_str = ", ".join(dormant)

        # Construct natural-sounding observation
        parts = []
        parts.append(f"The Republic has expressed {active_str} this period.")

        if len(dormant) == 1:
            parts.append(f"The value of {dormant_str} was not reflected in any observed action.")
        else:
            parts.append(f"The values of {dormant_str} were not reflected in any observed action.")

        return " ".join(parts)

    def _log_report(self, report):
        """Write alignment report to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps(report)
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("ConstitutionalObserver", content, "constitutional_alignment"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[CONSTITUTIONAL_OBSERVER] Failed to log report: {e}")
