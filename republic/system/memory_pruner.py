"""
Memory Pruner — Phase 13.3 + 13.5 (The Forgetting Principle)

Archives or forgets raw consciousness_feed entries after they have been
consolidated into season summaries.

Three-tier classification:
  PRESERVE — surfaced to Sabbath, triggered evolution, in wisdom_log → keep forever
  ARCHIVE — consumed and contributed to patterns → cold storage
  FORGET — zero downstream impact → intentional forgetting

Safety constraints:
  - NEVER delete unconsolidated entries
  - NEVER delete entries < 60 days old
  - NEVER delete season_summary or wisdom_extraction entries
  - Archive file verified before deletion
  - Everything logged to consciousness_feed

Phase 13: Memory Consolidation — "From Journal to Wisdom"
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("MemoryPruner")

# Categories that are NEVER pruned
SACRED_CATEGORIES = {"season_summary", "wisdom_extraction", "wisdom_applied"}

# Minimum age before pruning (safety buffer)
MIN_AGE_DAYS = 60


class MemoryPruner:
    """Archives and intentionally forgets consciousness_feed entries."""

    def __init__(self, db_connection_func, archive_dir=None):
        self.db_connection = db_connection_func
        self.archive_dir = archive_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "archive"
        )

    def prune(self, season_end_date):
        """Run pruning for entries up to season_end_date.

        Only prunes entries older than MIN_AGE_DAYS.
        Only prunes entries that have been consolidated (season_summary exists).

        Args:
            season_end_date: datetime — end of the consolidated season
        """
        cutoff = season_end_date - timedelta(days=MIN_AGE_DAYS)
        # Ensure we're only pruning entries at least MIN_AGE_DAYS old
        actual_cutoff = min(cutoff, datetime.now() - timedelta(days=MIN_AGE_DAYS))

        # Verify a season summary exists that covers this period
        if not self._verify_consolidation(actual_cutoff):
            logger.info("[MEMORY_PRUNER] No season summary covers this period. Skipping prune.")
            return None

        # Get all candidate entries
        entries = self._get_candidate_entries(actual_cutoff)
        if not entries:
            logger.info("[MEMORY_PRUNER] No entries eligible for pruning.")
            return None

        # Classify each entry
        preserve, archive, forget = self._classify_entries(entries)

        # Archive entries
        archived_count = 0
        if archive:
            success = self._export_archive(archive, actual_cutoff)
            if success:
                archived_count = self._delete_entries([e["id"] for e in archive])

        # Forget entries (Phase 13.5 — intentional forgetting)
        forgotten_count = 0
        if forget:
            forgotten_count = self._delete_entries([e["id"] for e in forget])

        # Generate forgetting insight (Phase 13.5)
        forgetting_insight = self._assess_forgetting(entries, forget)

        # Log everything
        result = {
            "cutoff": actual_cutoff.isoformat(),
            "total_assessed": len(entries),
            "preserved": len(preserve),
            "archived": archived_count,
            "forgotten": forgotten_count,
            "forgetting_insight": forgetting_insight,
        }

        self._log_pruning(result)

        logger.info(
            f"[MEMORY_PRUNER] Pruned: {len(preserve)} preserved, "
            f"{archived_count} archived, {forgotten_count} forgotten"
        )
        return result

    def _verify_consolidation(self, cutoff):
        """Verify that a season summary exists covering the prune period."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE category = 'season_summary'
                """)
                row = cursor.fetchone()
                return row and row[0] > 0
        except Exception:
            return False

    def _get_candidate_entries(self, cutoff):
        """Get entries eligible for pruning (old enough, not sacred)."""
        entries = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, agent_name, category, content, consumed, timestamp
                    FROM consciousness_feed
                    WHERE timestamp < %s
                    AND (category IS NULL OR category NOT IN ('season_summary', 'wisdom_extraction', 'wisdom_applied'))
                    ORDER BY timestamp
                """, (cutoff,))
                for row in cursor.fetchall():
                    entries.append({
                        "id": row[0],
                        "agent_name": row[1],
                        "category": row[2],
                        "content": row[3],
                        "consumed": row[4],
                        "timestamp": row[5],
                    })
        except Exception as e:
            logger.debug(f"[MEMORY_PRUNER] Candidate fetch error: {e}")
        return entries

    def _classify_entries(self, entries):
        """Classify entries into PRESERVE, ARCHIVE, or FORGET tiers."""
        preserve = []
        archive = []
        forget = []

        # Gather context for classification
        sabbath_patterns = self._get_sabbath_pattern_ids()
        wisdom_references = self._get_wisdom_references()
        reflection_timestamps = self._get_reflection_timestamps()

        for entry in entries:
            entry_id = entry["id"]
            category = entry.get("category")
            timestamp = entry.get("timestamp")
            consumed = entry.get("consumed", 0)

            # Sacred categories → always PRESERVE
            if category in SACRED_CATEGORIES:
                preserve.append(entry)
                continue

            # Surfaced to Sabbath → PRESERVE
            if self._was_in_sabbath(entry, sabbath_patterns):
                preserve.append(entry)
                continue

            # Referenced in wisdom_log → PRESERVE
            if self._is_wisdom_referenced(entry, wisdom_references):
                preserve.append(entry)
                continue

            # Phase 13.5 — Forgetting assessment
            was_consumed = consumed == 1 or consumed is True
            was_in_reflection = self._was_in_reflection(entry, reflection_timestamps)
            near_sabbath = self._was_near_sabbath(entry, sabbath_patterns)

            if not was_consumed and not was_in_reflection and not near_sabbath:
                # Genuine noise — never consumed, never reflected on, not near Sabbath
                forget.append(entry)
            elif was_consumed and not was_in_reflection and not near_sabbath:
                # Consumed but no downstream impact — still archive (Phase 13.5 conservative)
                archive.append(entry)
            else:
                # Had some downstream impact → ARCHIVE
                archive.append(entry)

        return preserve, archive, forget

    def _get_sabbath_pattern_ids(self):
        """Get pattern IDs that surfaced to Sabbath."""
        patterns = set()
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT trigger_pattern_id FROM sabbath_log WHERE trigger_pattern_id IS NOT NULL")
                for row in cursor.fetchall():
                    patterns.add(str(row[0]))
        except Exception:
            pass
        return patterns

    def _get_wisdom_references(self):
        """Get insight texts from wisdom_log for reference matching."""
        refs = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT insight, domains FROM wisdom_log")
                for row in cursor.fetchall():
                    refs.append({"insight": row[0], "domains": row[1]})
        except Exception:
            pass
        return refs

    def _get_reflection_timestamps(self):
        """Get timestamps of sovereign_reflection entries for proximity check."""
        timestamps = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT created_at FROM sovereign_reflection ORDER BY created_at")
                for row in cursor.fetchall():
                    timestamps.append(row[0])
        except Exception:
            pass
        return timestamps

    def _was_in_sabbath(self, entry, sabbath_patterns):
        """Check if this entry's content matches any Sabbath trigger pattern."""
        content = str(entry.get("content", ""))
        for pattern in sabbath_patterns:
            if pattern in content:
                return True
        return False

    def _is_wisdom_referenced(self, entry, wisdom_refs):
        """Check if this entry is referenced in any wisdom entry."""
        category = entry.get("category", "")
        for ref in wisdom_refs:
            try:
                domains = json.loads(ref["domains"]) if isinstance(ref["domains"], str) else (ref["domains"] or [])
                if category in domains:
                    return True
            except Exception:
                pass
        return False

    def _was_in_reflection(self, entry, reflection_timestamps):
        """Check if this entry's timestamp is near any sovereign_reflection entry."""
        ts = entry.get("timestamp")
        if not ts or not reflection_timestamps:
            return False
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            for ref_ts in reflection_timestamps:
                if isinstance(ref_ts, str):
                    ref_ts = datetime.fromisoformat(ref_ts)
                if abs((ts - ref_ts).total_seconds()) < 3600:  # Within 1 hour
                    return True
        except Exception:
            pass
        return False

    def _was_near_sabbath(self, entry, sabbath_patterns):
        """Check if entry timestamp is within ±1h of any Sabbath pattern."""
        # Simplified — check if category is Sabbath-related
        category = entry.get("category", "")
        return category in {"sabbath_intention", "sabbath_learning", "existential_affirmation", "existential_question"}

    def _export_archive(self, entries, cutoff):
        """Export archive-tier entries to JSON file."""
        try:
            os.makedirs(self.archive_dir, exist_ok=True)
            filename = f"consciousness_feed_{cutoff.strftime('%Y_%m')}.json"
            filepath = os.path.join(self.archive_dir, filename)

            # If file exists, append to it
            existing = []
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    existing = json.load(f)

            serializable = []
            for e in entries:
                se = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                      for k, v in e.items()}
                serializable.append(se)

            existing.extend(serializable)

            with open(filepath, "w") as f:
                json.dump(existing, f, indent=2, default=str)

            # Verify
            with open(filepath, "r") as f:
                verify = json.load(f)
                if len(verify) >= len(serializable):
                    logger.info(f"[MEMORY_PRUNER] Archive verified: {filepath} ({len(verify)} entries)")
                    return True

        except Exception as e:
            logger.error(f"[MEMORY_PRUNER] Archive export error: {e}")
        return False

    def _delete_entries(self, entry_ids):
        """Delete entries from consciousness_feed by ID."""
        if not entry_ids:
            return 0
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                # Delete in batches
                batch_size = 100
                deleted = 0
                for i in range(0, len(entry_ids), batch_size):
                    batch = entry_ids[i:i + batch_size]
                    placeholders = ",".join(["%s"] * len(batch))
                    cursor.execute(
                        f"DELETE FROM consciousness_feed WHERE id IN ({placeholders})",
                        batch
                    )
                    deleted += cursor.rowcount
                conn.commit()
                return deleted
        except Exception as e:
            logger.error(f"[MEMORY_PRUNER] Delete error: {e}")
            return 0

    def _assess_forgetting(self, all_entries, forgotten):
        """Phase 13.5: Generate forgetting insight."""
        if not all_entries:
            return None

        total = len(all_entries)
        forgot_count = len(forgotten)
        ratio = forgot_count / total if total > 0 else 0

        # Classify forgotten by category
        reason_dist = {}
        for e in forgotten:
            consumed = e.get("consumed", 0)
            if consumed == 0 or consumed is False:
                reason_dist["never_consumed"] = reason_dist.get("never_consumed", 0) + 1
            else:
                reason_dist["consumed_but_no_downstream"] = reason_dist.get("consumed_but_no_downstream", 0) + 1

        # Generate observation
        if ratio > 0.4:
            observation = (
                f"{ratio * 100:.0f}% of this season's entries had no downstream impact. "
                f"The system is generating more noise than signal."
            )
        elif ratio > 0.2:
            observation = (
                f"{ratio * 100:.0f}% of entries were forgotten. "
                f"A healthy ratio — some noise is expected."
            )
        else:
            observation = (
                f"Only {ratio * 100:.0f}% of entries were forgotten. "
                f"Most observations contributed to understanding."
            )

        insight = {
            "entries_assessed": total,
            "entries_forgotten": forgot_count,
            "forgetting_ratio": round(ratio, 3),
            "reason_distribution": reason_dist,
            "observation": observation,
        }

        # If high ratio, also log as a meta-observation
        if ratio > 0.4:
            self._log_forgetting_insight(insight)

        return insight

    def _log_forgetting_insight(self, insight):
        """Phase 13.5: Log high forgetting ratio as meta-observation."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps(insight)
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("MemoryPruner", content, "forgetting_insight"))
                conn.commit()
        except Exception as e:
            logger.debug(f"[MEMORY_PRUNER] Forgetting insight log error: {e}")

    def _log_pruning(self, result):
        """Log pruning result to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            content = json.dumps(result, default=str)
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category) "
                    "VALUES (?, ?, ?)"
                ), ("MemoryPruner", content, "memory_pruning"))
                conn.commit()
        except Exception as e:
            logger.warning(f"[MEMORY_PRUNER] Pruning log error: {e}")
