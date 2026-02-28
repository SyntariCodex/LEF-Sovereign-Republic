"""
Table Maintenance — Phase 21, Tasks 21.1b, 21.1c, 21.1d

Periodic cleanup for high-growth tables:
  - consciousness_feed: consumed entries > 14 days (preserving sacred categories)
  - agent_logs: all entries > 7 days
  - action_training_log: entries > 30 days (archived to training_summary first)

Runs every 6 hours. Called from main.py as a SafeThread.
"""

import time
import logging
import sqlite3

logger = logging.getLogger("TableMaintenance")

# Use centralized db_helper
try:
    from db.db_helper import db_connection, translate_sql
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or 'republic.db', timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

    def translate_sql(sql):
        return sql


# Sacred categories that should never be auto-deleted
SACRED_CATEGORIES = frozenset({
    'season_summary', 'wisdom_extraction', 'wisdom_applied',
    'existential_threat', 'emergency_cleared',
})

CYCLE_INTERVAL = 6 * 3600  # 6 hours


def run_maintenance_cycle():
    """
    Execute a single maintenance cycle across all tracked tables.

    Returns dict with counts of rows affected.
    """
    results = {
        'consciousness_feed_deleted': 0,
        'agent_logs_deleted': 0,
        'action_training_archived': 0,
        'action_training_deleted': 0,
    }

    try:
        with db_connection() as conn:
            c = conn.cursor()

            # ----------------------------------------------------------
            # 21.1b: consciousness_feed — delete consumed > 14 days
            #        AND unconsumed > 30 days (stale, never read)
            # ----------------------------------------------------------
            try:
                sacred_placeholders = ','.join('?' for _ in SACRED_CATEGORIES)
                # Consumed entries: 14-day window
                sql_consumed = translate_sql(
                    f"DELETE FROM consciousness_feed "
                    f"WHERE consumed = 1 "
                    f"AND timestamp < datetime('now', '-14 days') "
                    f"AND category NOT IN ({sacred_placeholders})"
                )
                c.execute(sql_consumed, tuple(SACRED_CATEGORIES))
                consumed_deleted = c.rowcount

                # Unconsumed entries: 30-day window — stale observations
                # that were never injected. Keeps the feed from being a
                # perpetually-growing backlog that dilutes recent signal.
                sql_unconsumed = translate_sql(
                    f"DELETE FROM consciousness_feed "
                    f"WHERE consumed = 0 "
                    f"AND timestamp < datetime('now', '-30 days') "
                    f"AND category NOT IN ({sacred_placeholders})"
                )
                c.execute(sql_unconsumed, tuple(SACRED_CATEGORIES))
                unconsumed_deleted = c.rowcount

                results['consciousness_feed_deleted'] = consumed_deleted + unconsumed_deleted
                if results['consciousness_feed_deleted'] > 0:
                    logger.info(
                        "[MAINTENANCE] consciousness_feed: deleted %d consumed (>14d) + %d unconsumed (>30d)",
                        consumed_deleted, unconsumed_deleted
                    )
            except Exception as e:
                logger.warning("[MAINTENANCE] consciousness_feed cleanup error: %s", e)

            # ----------------------------------------------------------
            # 21.1c: agent_logs — delete > 7 days
            # ----------------------------------------------------------
            try:
                c.execute(translate_sql(
                    "DELETE FROM agent_logs "
                    "WHERE timestamp < datetime('now', '-7 days')"
                ))
                results['agent_logs_deleted'] = c.rowcount
                if c.rowcount > 0:
                    logger.info(
                        "[MAINTENANCE] agent_logs: deleted %d entries > 7 days",
                        c.rowcount
                    )
            except Exception as e:
                logger.warning("[MAINTENANCE] agent_logs cleanup error: %s", e)

            # ----------------------------------------------------------
            # 21.1d: action_training_log — archive then delete > 30 days
            # ----------------------------------------------------------
            try:
                # Archive: summarize stats before deletion
                c.execute(translate_sql("""
                    SELECT agent_name, action_type,
                           AVG(reward), COUNT(*),
                           SUM(CASE WHEN reward > 0 THEN 1 ELSE 0 END),
                           SUM(CASE WHEN reward <= 0 THEN 1 ELSE 0 END),
                           MIN(timestamp), MAX(timestamp)
                    FROM action_training_log
                    WHERE timestamp < datetime('now', '-30 days')
                    GROUP BY agent_name, action_type
                """))
                summaries = c.fetchall()
                for row in summaries:
                    c.execute(translate_sql("""
                        INSERT INTO training_summary
                        (agent_name, action_type, avg_reward, total_count,
                         positive_count, negative_count, period_start, period_end)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """), row)
                results['action_training_archived'] = len(summaries)

                # Delete archived entries
                c.execute(translate_sql(
                    "DELETE FROM action_training_log "
                    "WHERE timestamp < datetime('now', '-30 days')"
                ))
                results['action_training_deleted'] = c.rowcount
                if c.rowcount > 0:
                    logger.info(
                        "[MAINTENANCE] action_training_log: archived %d groups, "
                        "deleted %d entries > 30 days",
                        len(summaries), c.rowcount
                    )
            except Exception as e:
                logger.warning("[MAINTENANCE] action_training_log cleanup error: %s", e)

            conn.commit()

        # Log summary to consciousness_feed
        total_deleted = (
            results['consciousness_feed_deleted']
            + results['agent_logs_deleted']
            + results['action_training_deleted']
        )
        if total_deleted > 0:
            try:
                with db_connection() as conn2:
                    c2 = conn2.cursor()
                    c2.execute(translate_sql(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight) "
                        "VALUES (?, ?, ?, ?)"
                    ), (
                        "TableMaintenance",
                        (
                            f"Maintenance cycle complete: "
                            f"consciousness_feed={results['consciousness_feed_deleted']}, "
                            f"agent_logs={results['agent_logs_deleted']}, "
                            f"action_training_log={results['action_training_deleted']} "
                            f"(archived {results['action_training_archived']} groups)"
                        ),
                        "system_maintenance",
                        0.3,
                    ))
                    conn2.commit()
            except Exception:
                pass

    except Exception as e:
        logger.error("[MAINTENANCE] Cycle failed: %s", e)

    return results


def run_maintenance_loop():
    """
    Main loop — runs maintenance cycle every 6 hours.
    Designed to be launched as a SafeThread from main.py.
    """
    logger.info("[MAINTENANCE] Table maintenance thread started (interval=%ds)", CYCLE_INTERVAL)

    while True:
        try:
            # Brainstem heartbeat
            try:
                from system.brainstem import brainstem_heartbeat
                brainstem_heartbeat("TableMaintenance", status="maintenance_cycle")
            except Exception:
                pass

            results = run_maintenance_cycle()
            logger.info("[MAINTENANCE] Cycle results: %s", results)

        except Exception as e:
            logger.error("[MAINTENANCE] Loop error: %s", e)

        time.sleep(CYCLE_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running one-time maintenance cycle...")
    results = run_maintenance_cycle()
    print(f"Results: {results}")
