"""
Wisdom Extractor — Phase 13.2

Distills lasting insights from season summaries and stores them
as persistent wisdom in the wisdom_log table.

Wisdom entries must be genuine insights, not restated statistics.
"Pool utilization averaged 3%" is NOT wisdom.
"I detect problems faster than I solve them" IS wisdom.

Runs after each season synthesis. Checks for recurring patterns
across seasons and reinforces existing wisdom.

Phase 13: Memory Consolidation — "From Journal to Wisdom"
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger("WisdomExtractor")


class WisdomExtractor:
    """Extracts lasting insights from season summaries into wisdom_log."""

    MAX_WISDOM_PER_SEASON = 5
    CONFIDENCE_INCREMENT = 0.1
    CONFIDENCE_CAP = 1.0
    INITIAL_CONFIDENCE = 0.5
    # Minimum keyword overlap for similarity
    SIMILARITY_THRESHOLD = 0.4

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func
        self._ensure_table()

    def _ensure_table(self):
        """Create wisdom_log table if it doesn't exist."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS wisdom_log (
                        id SERIAL PRIMARY KEY,
                        insight TEXT NOT NULL,
                        source_season TEXT NOT NULL,
                        domains TEXT NOT NULL,
                        confidence REAL DEFAULT 0.5,
                        recurrence_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_reinforced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Indices for efficient lookup
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wisdom_confidence ON wisdom_log(confidence)")
                except Exception:
                    pass
                conn.commit()
            logger.info("[WISDOM_EXTRACTOR] wisdom_log table ready.")
        except Exception as e:
            logger.warning(f"[WISDOM_EXTRACTOR] Table creation error: {e}")

    def extract(self, season_summary):
        """Extract wisdom from a season summary.

        Args:
            season_summary: dict from SeasonSynthesizer.synthesize()

        Returns:
            list of extracted/reinforced wisdom entries
        """
        if not season_summary:
            return []

        insights = self._generate_insights(season_summary)

        results = []
        for insight_data in insights[:self.MAX_WISDOM_PER_SEASON]:
            result = self._store_or_reinforce(insight_data)
            results.append(result)

        # Log to consciousness_feed
        self._log_extraction(results, season_summary.get("season_id", "unknown"))

        logger.info(
            f"[WISDOM_EXTRACTOR] {len(results)} wisdom entries processed "
            f"({sum(1 for r in results if r.get('action') == 'new')} new, "
            f"{sum(1 for r in results if r.get('action') == 'reinforced')} reinforced)"
        )
        return results

    def _generate_insights(self, summary):
        """Generate candidate wisdom entries from season summary data."""
        insights = []
        season_id = summary.get("season_id", "unknown")
        categories = summary.get("category_breakdown", {})
        dominant = summary.get("dominant_themes", [])
        dormant = summary.get("dormant_themes", [])
        sabbath = summary.get("sabbath_summary", {})
        reverb = summary.get("reverb_summary", {})
        synthesis = summary.get("synthesis", "")
        unresolved = summary.get("unresolved_questions", [])

        # Insight: Reverb ratio pattern
        if reverb.get("total", 0) > 10:
            pos_ratio = reverb.get("positive", 0) / reverb["total"]
            if pos_ratio < 0.3:
                insights.append({
                    "insight": (
                        "Actions frequently produce negative reverb. "
                        "The system acts more often than it understands."
                    ),
                    "domains": ["purpose", "governance"],
                    "season": season_id,
                })
            elif pos_ratio > 0.7:
                insights.append({
                    "insight": (
                        "Decisions in this period were largely aligned with values. "
                        "The deliberation architecture is serving its purpose."
                    ),
                    "domains": ["governance", "consciousness"],
                    "season": season_id,
                })

        # Insight: Dormant themes pattern
        if len(dormant) >= 3:
            insights.append({
                "insight": (
                    f"Multiple dimensions remain underdeveloped: "
                    f"{', '.join(dormant[:3])}. "
                    f"The system gravitates toward what it knows, not what it needs."
                ),
                "domains": ["purpose", "identity"],
                "season": season_id,
            })

        # Insight: Sabbath ratio
        if sabbath.get("total", 0) > 5:
            ex_ratio = sabbath.get("existential", 0) / sabbath["total"]
            if ex_ratio < 0.1:
                insights.append({
                    "insight": (
                        "Sabbaths are almost exclusively operational. "
                        "Existential reflection is not being triggered. "
                        "The system maintains but does not ask why."
                    ),
                    "domains": ["purpose", "consciousness"],
                    "season": season_id,
                })

        # Insight: Unresolved questions persistence
        if len(unresolved) >= 3:
            insights.append({
                "insight": (
                    "Questions accumulate faster than they resolve. "
                    "Holding uncertainty is itself a capacity, but "
                    "perpetual holding becomes avoidance."
                ),
                "domains": ["purpose", "identity"],
                "season": season_id,
            })

        # Insight: Category concentration
        if categories:
            total = sum(c.get("count", 0) for c in categories.values())
            if total > 0 and dominant:
                top_count = categories.get(dominant[0], {}).get("count", 0)
                if top_count / total > 0.5:
                    insights.append({
                        "insight": (
                            f"Over half of all observations come from a single domain "
                            f"('{dominant[0]}'). The attention is narrow. "
                            f"What is being missed at the periphery?"
                        ),
                        "domains": [dominant[0], "purpose"],
                        "season": season_id,
                    })

        return insights

    def _store_or_reinforce(self, insight_data):
        """Store a new wisdom entry or reinforce an existing similar one."""
        insight = insight_data["insight"]
        domains = insight_data["domains"]
        season = insight_data["season"]

        # Check for similar existing wisdom
        existing = self._find_similar(insight, domains)

        if existing:
            # Reinforce existing
            new_confidence = min(
                existing["confidence"] + self.CONFIDENCE_INCREMENT,
                self.CONFIDENCE_CAP
            )
            new_count = existing["recurrence_count"] + 1

            try:
                with self.db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE wisdom_log
                        SET confidence = %s,
                            recurrence_count = %s,
                            last_reinforced = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (new_confidence, new_count, existing["id"]))
                    conn.commit()
            except Exception as e:
                logger.debug(f"[WISDOM_EXTRACTOR] Reinforce error: {e}")

            return {
                "action": "reinforced",
                "insight": existing["insight"],
                "old_confidence": existing["confidence"],
                "new_confidence": new_confidence,
                "recurrence_count": new_count,
            }
        else:
            # Store new
            try:
                with self.db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO wisdom_log (insight, source_season, domains, confidence)
                        VALUES (%s, %s, %s, %s)
                    """, (insight, season, json.dumps(domains), self.INITIAL_CONFIDENCE))
                    conn.commit()
            except Exception as e:
                logger.debug(f"[WISDOM_EXTRACTOR] Store error: {e}")

            return {
                "action": "new",
                "insight": insight,
                "confidence": self.INITIAL_CONFIDENCE,
                "domains": domains,
            }

    def _find_similar(self, new_insight, new_domains):
        """Find similar wisdom in existing log using domain + keyword overlap."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, insight, domains, confidence, recurrence_count FROM wisdom_log")
                rows = cursor.fetchall()

                new_keywords = set(new_insight.lower().split())
                new_domain_set = set(new_domains)

                for row in rows:
                    existing_insight = row[1]
                    existing_domains = json.loads(row[2]) if isinstance(row[2], str) else (row[2] or [])
                    existing_domain_set = set(existing_domains)

                    # Domain overlap
                    domain_overlap = len(new_domain_set & existing_domain_set)
                    if domain_overlap == 0:
                        continue

                    # Keyword overlap
                    existing_keywords = set(existing_insight.lower().split())
                    common = new_keywords & existing_keywords
                    total = new_keywords | existing_keywords
                    keyword_sim = len(common) / len(total) if total else 0

                    if keyword_sim >= self.SIMILARITY_THRESHOLD:
                        return {
                            "id": row[0],
                            "insight": row[1],
                            "confidence": row[3],
                            "recurrence_count": row[4],
                        }

        except Exception as e:
            logger.debug(f"[WISDOM_EXTRACTOR] Similarity search error: {e}")

        return None

    def _log_extraction(self, results, season_id):
        """Log extraction to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            new_count = sum(1 for r in results if r.get("action") == "new")
            reinforced_count = sum(1 for r in results if r.get("action") == "reinforced")

            content = json.dumps({
                "season_id": season_id,
                "total_processed": len(results),
                "new_insights": new_count,
                "reinforced_insights": reinforced_count,
                "insights": [r.get("insight", "")[:100] for r in results],
                "timestamp": datetime.now().isoformat(),
            })

            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("WisdomExtractor", content, "wisdom_extraction"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[WISDOM_EXTRACTOR] consciousness_feed log error: {e}")
