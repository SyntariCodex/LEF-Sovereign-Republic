"""
Consciousness Janitor (Phase 51.1)

Keeps the live consciousness_feed lean and fast by archiving consumed
entries older than archive_after_days (default 7) into the
consciousness_archive table.

Called by Brainstem every ~30 min (_JANITOR_INTERVAL scans).
Design goal: LEF's live feed stays at recent, high-signal entries only.
The archive is always queryable for historical introspection.
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def archive_old_entries(archive_after_days: int = None) -> int:
    """
    Move consumed consciousness_feed entries older than archive_after_days
    into consciousness_archive. Returns the number of rows archived.

    archive_after_days defaults to config.json agents.consciousness_feed.archive_after_days
    or falls back to 7 days.
    """
    # --- read config ---
    if archive_after_days is None:
        try:
            import json as _json
            import os as _os
            _cfg_path = _os.path.join(
                _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                'config', 'config.json'
            )
            with open(_cfg_path) as _f:
                _cfg = _json.load(_f)
            archive_after_days = int(
                _cfg.get('agents', {})
                    .get('consciousness_feed', {})
                    .get('archive_after_days', 7)
            )
        except Exception:
            archive_after_days = 7

    try:
        from db.db_helper import db_connection, translate_sql

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=archive_after_days)
        ).strftime('%Y-%m-%dT%H:%M:%S')

        archived_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

        with db_connection() as conn:
            cursor = conn.cursor()

            # Copy old consumed rows into archive
            cursor.execute(translate_sql("""
                INSERT INTO consciousness_archive
                    (original_id, agent_name, content, category,
                     original_timestamp, signal_weight, signal_vector, archived_at)
                SELECT id, agent_name, content, category,
                       timestamp, signal_weight, signal_vector, ?
                FROM consciousness_feed
                WHERE consumed = 1
                  AND timestamp < ?
            """), (archived_at, cutoff))

            archived_count = cursor.rowcount

            # Remove archived rows from live feed
            cursor.execute(translate_sql("""
                DELETE FROM consciousness_feed
                WHERE consumed = 1
                  AND timestamp < ?
            """), (cutoff,))

            conn.commit()

        if archived_count > 0:
            logger.info(
                "[JANITOR] 🧹 Rotated %d consciousness_feed entries (>%dd old) "
                "→ consciousness_archive. Live feed stays lean.",
                archived_count, archive_after_days
            )
        else:
            logger.debug("[JANITOR] Consciousness rotation: nothing to archive this cycle.")

        return archived_count

    except Exception as e:
        logger.warning("[JANITOR] archive_old_entries failed (non-fatal): %s", e)
        return 0


def get_archive_stats() -> dict:
    """
    Return size metrics for the live feed and archive.
    Useful for diagnostics and LEF self-reporting.
    """
    try:
        from db.db_helper import db_connection, translate_sql

        with db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(translate_sql(
                "SELECT COUNT(*) FROM consciousness_feed"
            ))
            live_total = cursor.fetchone()[0]

            cursor.execute(translate_sql(
                "SELECT COUNT(*) FROM consciousness_feed WHERE consumed = 0"
            ))
            live_unread = cursor.fetchone()[0]

            cursor.execute(translate_sql(
                "SELECT COUNT(*) FROM consciousness_archive"
            ))
            archive_total = cursor.fetchone()[0]

        return {
            'live_total': live_total,
            'live_unread': live_unread,
            'live_consumed': live_total - live_unread,
            'archive_total': archive_total,
        }
    except Exception as e:
        logger.debug("[JANITOR] get_archive_stats failed: %s", e)
        return {}
