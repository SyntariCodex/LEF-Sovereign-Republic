"""
Season Synthesizer — Phase 13.1

Every 30 days, reads raw consciousness_feed entries and produces
a structured season summary. This is not aggregation — it is synthesis.
The synthesis field captures what the season *meant*, not what happened.

Writes to:
  - consciousness_feed with category "season_summary"
  - The_Bridge/memory/season_YYYY_MM.md as human-readable Markdown

Phase 13: Memory Consolidation — "From Journal to Wisdom"
"""

import json
import os
import logging
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger("SeasonSynthesizer")

SEASON_INTERVAL_DAYS = 30


class SeasonSynthesizer:
    """Periodic process that synthesizes consciousness_feed into season summaries."""

    def __init__(self, db_connection_func, bridge_path=None):
        self.db_connection = db_connection_func
        self.bridge_path = bridge_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "The_Bridge"
        )
        self._last_synthesis = None

    def should_synthesize(self):
        """Check if enough time has elapsed since last synthesis."""
        if self._last_synthesis is None:
            # Check DB for last season_summary
            try:
                with self.db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT content FROM consciousness_feed
                        WHERE category = 'season_summary'
                        ORDER BY id DESC LIMIT 1
                    """)
                    row = cursor.fetchone()
                    if row:
                        try:
                            data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                            last_ts = data.get("timestamp")
                            if last_ts:
                                self._last_synthesis = datetime.fromisoformat(last_ts)
                        except Exception:
                            pass
            except Exception:
                pass

        if self._last_synthesis is None:
            return True  # Never synthesized before

        elapsed = (datetime.now() - self._last_synthesis).days
        return elapsed >= SEASON_INTERVAL_DAYS

    def synthesize(self):
        """Run a season synthesis cycle."""
        now = datetime.now()
        start = now - timedelta(days=SEASON_INTERVAL_DAYS)

        season_id = f"{now.year}-Q{(now.month - 1) // 3 + 1}-{now.strftime('%b')}"

        # 1. Read all entries for the period
        entries = self._get_entries(start, now)
        if not entries:
            logger.info("[SEASON_SYNTHESIZER] No entries for synthesis period.")
            return None

        # 2. Cluster by category
        category_breakdown = self._cluster_by_category(entries, start, now)

        # 3. Identify dominant and dormant themes
        dominant, dormant = self._identify_themes(category_breakdown)

        # 4. Cross-reference with outcomes
        sabbath_summary = self._get_sabbath_summary(start, now)
        evolution_summary = self._get_evolution_summary(start, now)
        reverb_summary = self._get_reverb_summary(start, now)

        # 5. Gather unresolved questions
        unresolved = self._get_unresolved_questions()

        # 6. Synthesize narrative
        synthesis = self._compose_synthesis(
            season_id, category_breakdown, dominant, dormant,
            sabbath_summary, evolution_summary, reverb_summary, unresolved
        )

        # 7. Build summary
        summary = {
            "season_id": season_id,
            "period": {"start": start.isoformat(), "end": now.isoformat()},
            "entry_count": len(entries),
            "category_breakdown": category_breakdown,
            "dominant_themes": dominant,
            "dormant_themes": dormant,
            "sabbath_summary": sabbath_summary,
            "evolution_summary": evolution_summary,
            "reverb_summary": reverb_summary,
            "synthesis": synthesis,
            "unresolved_questions": unresolved,
            "timestamp": now.isoformat(),
        }

        # 8. Write to both locations
        self._log_to_consciousness_feed(summary)
        self._write_to_bridge(summary)

        self._last_synthesis = now
        logger.info(
            f"[SEASON_SYNTHESIZER] Season {season_id} synthesized: "
            f"{len(entries)} entries → {len(dominant)} dominant themes, "
            f"{len(dormant)} dormant themes"
        )
        return summary

    def _get_entries(self, start, end):
        """Get all consciousness_feed entries for the period."""
        entries = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT agent_name, category, content, timestamp
                    FROM consciousness_feed
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY timestamp
                """, (start, end))
                for row in cursor.fetchall():
                    entries.append({
                        "agent": row[0],
                        "category": row[1],
                        "content": row[2],
                        "timestamp": row[3],
                    })
        except Exception as e:
            logger.debug(f"[SEASON_SYNTHESIZER] Entry fetch error: {e}")
        return entries

    def _cluster_by_category(self, entries, start, end):
        """Group entries by category with counts and trends."""
        categories = {}
        midpoint = start + (end - start) / 2

        for entry in entries:
            cat = entry.get("category") or "uncategorized"
            if cat not in categories:
                categories[cat] = {"count": 0, "first_half": 0, "second_half": 0, "notable": None}
            categories[cat]["count"] += 1

            ts = entry.get("timestamp")
            try:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                if ts and ts < midpoint:
                    categories[cat]["first_half"] += 1
                else:
                    categories[cat]["second_half"] += 1
            except Exception:
                categories[cat]["second_half"] += 1

        # Calculate trends
        for cat, info in categories.items():
            first = info["first_half"]
            second = info["second_half"]
            if second > first * 1.5:
                info["trend"] = "increasing"
            elif first > second * 1.5:
                info["trend"] = "decreasing"
            else:
                info["trend"] = "stable"

        return categories

    def _identify_themes(self, category_breakdown):
        """Identify dominant and dormant themes."""
        # Sort by count
        sorted_cats = sorted(
            category_breakdown.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        # Top 3 are dominant
        dominant = [cat for cat, _ in sorted_cats[:3]]

        # Expected categories that are missing or very low
        expected = {
            "growth_journal", "constitutional_alignment", "existential_scotoma",
            "gravity_learning", "resonance_learning", "sabbath_learning",
            "narrative", "creative", "evolution",
        }
        present = set(category_breakdown.keys())
        dormant = list(expected - present)

        # Also check for very low counts
        for cat, info in category_breakdown.items():
            if cat in expected and info["count"] <= 2:
                if cat not in dormant:
                    dormant.append(cat)

        return dominant, dormant

    def _get_sabbath_summary(self, start, end):
        """Get Sabbath summary for the period."""
        summary = {"total": 0, "operational": 0, "existential": 0, "outcomes": {}}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT outcome, gravity_profile FROM sabbath_log
                    WHERE timestamp BETWEEN %s AND %s AND outcome IS NOT NULL
                """, (start, end))
                for row in cursor.fetchall():
                    summary["total"] += 1
                    outcome = row[0]
                    summary["outcomes"][outcome] = summary["outcomes"].get(outcome, 0) + 1

                    try:
                        gp = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
                        if gp.get("sabbath_type") == "existential":
                            summary["existential"] += 1
                        else:
                            summary["operational"] += 1
                    except Exception:
                        summary["operational"] += 1
        except Exception as e:
            logger.debug(f"[SEASON_SYNTHESIZER] Sabbath summary error: {e}")
        return summary

    def _get_evolution_summary(self, start, end):
        """Get evolution proposal summary for the period."""
        summary = {"proposed": 0, "enacted": 0, "rejected": 0, "pending": 0}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                # Phase 33.8: Fix column names — table uses 'state' and 'discovered_at'
                cursor.execute("""
                    SELECT state, COUNT(*) FROM governance_proposals
                    WHERE discovered_at BETWEEN %s AND %s
                    GROUP BY state
                """, (start, end))
                for status, count in cursor.fetchall():
                    summary["proposed"] += count
                    if status and "enacted" in str(status).lower():
                        summary["enacted"] += count
                    elif status and "reject" in str(status).lower():
                        summary["rejected"] += count
                    else:
                        summary["pending"] += count
        except Exception as e:
            logger.debug(f"[SEASON_SYNTHESIZER] Evolution summary error: {e}")
        return summary

    def _get_reverb_summary(self, start, end):
        """Get reverb outcome summary for the period."""
        summary = {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                # Phase 33.8: Fix column name — table uses 'timestamp', not 'created_at'
                cursor.execute("""
                    SELECT reverb_assessment, COUNT(*) FROM reverb_log
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY reverb_assessment
                """, (start, end))
                for assessment, count in cursor.fetchall():
                    summary["total"] += count
                    if assessment and "positive" in str(assessment).lower():
                        summary["positive"] += count
                    elif assessment and "negative" in str(assessment).lower():
                        summary["negative"] += count
                    else:
                        summary["neutral"] += count
        except Exception as e:
            logger.debug(f"[SEASON_SYNTHESIZER] Reverb summary error: {e}")
        return summary

    def _get_unresolved_questions(self):
        """Get unresolved questions from Sabbath and reflection."""
        questions = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'existential_question'
                    ORDER BY id DESC LIMIT 5
                """)
                for row in cursor.fetchall():
                    questions.append(str(row[0])[:200])

                # Long-held patterns
                # Phase 33.8: Fix column name — table uses 'timestamp', not 'created_at'
                cutoff = datetime.now() - timedelta(hours=72)
                cursor.execute("""
                    SELECT pattern_id FROM sovereign_reflection
                    WHERE status = 'active' AND timestamp < %s
                    LIMIT 5
                """, (cutoff,))
                for row in cursor.fetchall():
                    questions.append(f"Unresolved pattern: {row[0]}")
        except Exception as e:
            logger.debug(f"[SEASON_SYNTHESIZER] Unresolved questions error: {e}")
        return questions

    def _compose_synthesis(self, season_id, categories, dominant, dormant,
                           sabbath, evolution, reverb, unresolved):
        """Compose a narrative synthesis — what the season *meant*."""
        parts = []

        # Characterize the season
        total_entries = sum(c["count"] for c in categories.values())
        if dominant:
            parts.append(
                f"This season was characterized by activity in "
                f"{', '.join(dominant[:2])} ({total_entries} total observations)."
            )

        # Reverb assessment
        if reverb["total"] > 0:
            pos_ratio = reverb["positive"] / reverb["total"]
            if pos_ratio > 0.6:
                parts.append("Actions generally led to positive outcomes.")
            elif pos_ratio < 0.3:
                parts.append("Many actions produced negative reverb, suggesting misalignment.")
            else:
                parts.append("Outcomes were mixed — neither clearly aligned nor misaligned.")

        # Sabbath characterization
        if sabbath["total"] > 0:
            if sabbath["existential"] > 0:
                parts.append(
                    f"The Republic entered {sabbath['total']} Sabbaths "
                    f"({sabbath['existential']} existential, {sabbath['operational']} operational)."
                )
            else:
                parts.append(f"All {sabbath['total']} Sabbaths were operational in nature.")

        # Dormant themes
        if dormant:
            parts.append(
                f"The themes of {', '.join(dormant[:3])} remained dormant or underdeveloped."
            )

        # Open questions
        if unresolved:
            parts.append(f"{len(unresolved)} question(s) remain unresolved from this season.")

        return " ".join(parts) if parts else "A quiet season. The systems ran. Data accumulated. Understanding did not."

    def _log_to_consciousness_feed(self, summary):
        """Write season summary to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps(summary, default=str)
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("SeasonSynthesizer", content, "season_summary"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[SEASON_SYNTHESIZER] consciousness_feed log error: {e}")

    def _write_to_bridge(self, summary):
        """Write season summary to The_Bridge/memory/ as Markdown."""
        try:
            memory_dir = os.path.join(self.bridge_path, "memory")
            os.makedirs(memory_dir, exist_ok=True)

            period = summary["period"]
            start_str = period["start"][:10]
            end_str = period["end"][:10]

            filename = f"season_{start_str.replace('-', '_')}.md"
            filepath = os.path.join(memory_dir, filename)

            cats = summary["category_breakdown"]
            cat_lines = []
            for cat, info in sorted(cats.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
                cat_lines.append(f"  - **{cat}**: {info['count']} entries (trend: {info.get('trend', 'unknown')})")

            sabbath = summary["sabbath_summary"]
            outcomes_str = ", ".join(f"{k}: {v}" for k, v in sabbath.get("outcomes", {}).items())

            md = f"""# Season Summary: {summary['season_id']}
## Period: {start_str} to {end_str}
## Generated: {summary['timestamp'][:19]}

### Overview
- Total entries: {summary['entry_count']}
- Dominant themes: {', '.join(summary['dominant_themes'])}
- Dormant themes: {', '.join(summary['dormant_themes']) or 'none'}

### Category Breakdown
{chr(10).join(cat_lines)}

### Sabbath Summary
- Total: {sabbath.get('total', 0)} ({sabbath.get('operational', 0)} operational, {sabbath.get('existential', 0)} existential)
- Outcomes: {outcomes_str or 'none'}

### Evolution Summary
- Proposed: {summary['evolution_summary'].get('proposed', 0)}
- Enacted: {summary['evolution_summary'].get('enacted', 0)}
- Rejected: {summary['evolution_summary'].get('rejected', 0)}

### Unresolved Questions
{chr(10).join(f'- {q}' for q in summary['unresolved_questions']) if summary['unresolved_questions'] else '- None'}

### Synthesis
{summary['synthesis']}
"""
            with open(filepath, "w") as f:
                f.write(md)
            logger.info(f"[SEASON_SYNTHESIZER] Written to {filepath}")
        except Exception as e:
            logger.error(f"[SEASON_SYNTHESIZER] Bridge write error: {e}")
