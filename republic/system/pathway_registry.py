"""
Pathway Registry -- Emergent Pathway Formation.

The lattice grows new connections through use.

When signals of different categories co-occur repeatedly within short
time windows, the system infers a structural relationship between those
domains and registers a pathway.  Pathways that are actively traversed
grow stronger; those that go unused gradually decay but are never fully
forgotten.  The strongest ("golden") pathways represent deeply
reinforced connections that define LEF's cognitive topology.

Phase 17 -- Task 17.7
"""

import json
import logging
from datetime import datetime

from db.db_helper import db_connection, translate_sql

logger = logging.getLogger("PathwayRegistry")


class PathwayRegistry:
    """
    Manages emergent pathways between signal domains.

    Reads from:
        - consciousness_feed  (co-occurring categories within time windows)
        - pathway_registry    (existing pathways, strength, traversal data)

    Writes to:
        - pathway_registry    (new pathways, strength updates, decay)
        - consciousness_feed  (announces newly formed pathways)
    """

    # ------------------------------------------------------------------
    # Tuning constants
    # ------------------------------------------------------------------
    CO_OCCURRENCE_WINDOW_MINUTES = 5
    CO_OCCURRENCE_LOOKBACK_HOURS = 24
    CO_OCCURRENCE_THRESHOLD = 3       # min co-occurrences to register
    STRENGTHEN_INCREMENT = 0.05
    STRENGTH_CAP = 1.0
    DECAY_FACTOR = 0.10               # lose 10 % per decay cycle
    STRENGTH_FLOOR = 0.1              # never fully forgotten
    DECAY_STALENESS_DAYS = 7          # unused for this many days -> decay
    ROUTING_BIAS_FLOOR = 0.15         # only return pathways above this

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 1. Detect emerging pathways from consciousness_feed co-occurrences
    # ------------------------------------------------------------------
    def detect_emerging_pathways(self):
        """
        Scan consciousness_feed for co-occurring categories within
        5-minute windows over the last 24 hours.  If a pair co-occurs
        3+ times and does not already exist in pathway_registry,
        register it as a new pathway.

        Returns:
            list[dict]  -- newly formed pathways, each with keys
                           source, target, evidence, strength.
        """
        newly_formed = []

        try:
            with db_connection() as conn:
                c = conn.cursor()

                # ---------------------------------------------------------
                # Find pairs of different categories that appear within
                # CO_OCCURRENCE_WINDOW_MINUTES of each other during the
                # last CO_OCCURRENCE_LOOKBACK_HOURS.
                #
                # We use a self-join on consciousness_feed, comparing
                # timestamps pairwise.  To avoid (A,B) and (B,A) being
                # counted separately we enforce a < b ordering.
                # ---------------------------------------------------------
                pair_sql = translate_sql("""
                    SELECT a.category AS source_cat,
                           b.category AS target_cat,
                           COUNT(*)   AS co_count
                    FROM consciousness_feed a
                    JOIN consciousness_feed b
                      ON a.id < b.id
                     AND a.category <> b.category
                     AND ABS(
                           EXTRACT(EPOCH FROM (a.timestamp - b.timestamp))
                         ) <= ?
                    WHERE a.timestamp > NOW() - INTERVAL '24 hours'
                      AND b.timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY a.category, b.category
                    HAVING COUNT(*) >= ?
                """)

                window_seconds = self.CO_OCCURRENCE_WINDOW_MINUTES * 60
                c.execute(pair_sql, (window_seconds, self.CO_OCCURRENCE_THRESHOLD))
                pairs = c.fetchall()

                for row in pairs:
                    source = row[0]
                    target = row[1]
                    co_count = row[2]

                    # Check if pathway already exists (either direction)
                    exists_sql = translate_sql("""
                        SELECT id FROM pathway_registry
                        WHERE (source_domain = ? AND target_domain = ?)
                           OR (source_domain = ? AND target_domain = ?)
                        LIMIT 1
                    """)
                    c.execute(exists_sql, (source, target, target, source))
                    if c.fetchone():
                        continue

                    evidence = (
                        f"Co-occurred {co_count} times within "
                        f"{self.CO_OCCURRENCE_WINDOW_MINUTES}-min windows "
                        f"over the last {self.CO_OCCURRENCE_LOOKBACK_HOURS}h"
                    )

                    self._do_register(c, source, target, evidence)
                    newly_formed.append({
                        "source": source,
                        "target": target,
                        "evidence": evidence,
                        "strength": 0.5,
                    })

                conn.commit()

        except Exception as e:
            logger.error(f"[PATHWAY] Error detecting emerging pathways: {e}")

        if newly_formed:
            logger.info(
                f"[PATHWAY] {len(newly_formed)} new pathway(s) formed: "
                + ", ".join(f"{p['source']}->{p['target']}" for p in newly_formed)
            )

        return newly_formed

    # ------------------------------------------------------------------
    # 2. Register a pathway (public interface)
    # ------------------------------------------------------------------
    def register_pathway(self, source, target, evidence, strength=0.5):
        """
        Insert a new pathway into pathway_registry and announce it
        on consciousness_feed.

        Args:
            source:   source domain / category name
            target:   target domain / category name
            evidence: human-readable reason the pathway was formed
            strength: initial strength (default 0.5)
        """
        try:
            with db_connection() as conn:
                c = conn.cursor()
                self._do_register(c, source, target, evidence, strength)
                conn.commit()
        except Exception as e:
            logger.error(f"[PATHWAY] Error registering pathway {source}->{target}: {e}")

    # ------------------------------------------------------------------
    # 3. Get routing biases for a given signal category
    # ------------------------------------------------------------------
    def get_routing_bias(self, signal_category):
        """
        Given a signal's category, return pathway biases that indicate
        which other domains are structurally connected.

        Args:
            signal_category: the category to look up

        Returns:
            list[tuple[str, float]]  -- (target_domain, strength) pairs
                                        with strength > ROUTING_BIAS_FLOOR
        """
        biases = []
        try:
            with db_connection() as conn:
                c = conn.cursor()
                bias_sql = translate_sql("""
                    SELECT target_domain, strength
                    FROM pathway_registry
                    WHERE source_domain = ?
                      AND strength > ?
                    ORDER BY strength DESC
                """)
                c.execute(bias_sql, (signal_category, self.ROUTING_BIAS_FLOOR))
                rows = c.fetchall()
                biases = [(row[0], row[1]) for row in rows]
        except Exception as e:
            logger.error(f"[PATHWAY] Error getting routing bias for '{signal_category}': {e}")

        return biases

    # ------------------------------------------------------------------
    # 4. Strengthen a pathway after traversal
    # ------------------------------------------------------------------
    def strengthen_used(self, source, target):
        """
        Increase pathway strength by STRENGTHEN_INCREMENT (capped at
        STRENGTH_CAP), increment traversal_count, and update last_used.

        Args:
            source: source domain
            target: target domain
        """
        try:
            with db_connection() as conn:
                c = conn.cursor()
                strengthen_sql = translate_sql("""
                    UPDATE pathway_registry
                    SET strength = LEAST(strength + ?, ?),
                        traversal_count = traversal_count + 1,
                        last_used = NOW()
                    WHERE source_domain = ?
                      AND target_domain = ?
                """)
                c.execute(strengthen_sql, (
                    self.STRENGTHEN_INCREMENT,
                    self.STRENGTH_CAP,
                    source,
                    target,
                ))
                conn.commit()
                logger.debug(f"[PATHWAY] Strengthened {source}->{target}")
        except Exception as e:
            logger.error(f"[PATHWAY] Error strengthening {source}->{target}: {e}")

    # ------------------------------------------------------------------
    # 5. Decay unused pathways
    # ------------------------------------------------------------------
    def decay_unused(self):
        """
        Pathways not used in DECAY_STALENESS_DAYS days lose
        DECAY_FACTOR of their strength (minimum STRENGTH_FLOOR).
        Updates last_decayed timestamp.  Intended to be called on a
        daily cadence.
        """
        try:
            with db_connection() as conn:
                c = conn.cursor()
                decay_sql = translate_sql("""
                    UPDATE pathway_registry
                    SET strength = GREATEST(strength * (1.0 - ?), ?),
                        last_decayed = NOW()
                    WHERE last_used < NOW() - INTERVAL '? days'
                """.replace("INTERVAL '? days'",
                            f"INTERVAL '{self.DECAY_STALENESS_DAYS} days'"))
                # Only the numeric constants are parameterised; the interval
                # literal is inlined because PostgreSQL does not allow
                # parameterised interval values.
                c.execute(decay_sql, (self.DECAY_FACTOR, self.STRENGTH_FLOOR))
                affected = c.rowcount if hasattr(c, 'rowcount') else 0
                conn.commit()

                if affected:
                    logger.info(f"[PATHWAY] Decayed {affected} unused pathway(s)")
        except Exception as e:
            logger.error(f"[PATHWAY] Error decaying unused pathways: {e}")

    # ------------------------------------------------------------------
    # 6. Get all pathways (debug / monitoring)
    # ------------------------------------------------------------------
    def get_all_pathways(self):
        """
        Return every pathway as a list of dicts.

        Returns:
            list[dict]  -- each dict has keys: id, source_domain,
                           target_domain, strength, evidence,
                           traversal_count, formed_at, last_used,
                           last_decayed.
        """
        pathways = []
        try:
            with db_connection() as conn:
                c = conn.cursor()
                all_sql = translate_sql("""
                    SELECT id, source_domain, target_domain, strength,
                           evidence, traversal_count, formed_at,
                           last_used, last_decayed
                    FROM pathway_registry
                    ORDER BY strength DESC
                """)
                c.execute(all_sql)
                rows = c.fetchall()
                for row in rows:
                    pathways.append({
                        "id": row[0],
                        "source_domain": row[1],
                        "target_domain": row[2],
                        "strength": row[3],
                        "evidence": row[4],
                        "traversal_count": row[5],
                        "formed_at": str(row[6]) if row[6] else None,
                        "last_used": str(row[7]) if row[7] else None,
                        "last_decayed": str(row[8]) if row[8] else None,
                    })
        except Exception as e:
            logger.error(f"[PATHWAY] Error fetching all pathways: {e}")

        return pathways

    # ------------------------------------------------------------------
    # 7. Get golden pathways (high-value, heavily used)
    # ------------------------------------------------------------------
    def get_golden_pathways(self, min_strength=0.8):
        """
        Return only pathways with strength >= min_strength.

        These are the "golden pathways" -- heavily-used, high-value
        connections that define core cognitive topology.

        Args:
            min_strength: minimum strength threshold (default 0.8)

        Returns:
            list[dict]
        """
        golden = []
        try:
            with db_connection() as conn:
                c = conn.cursor()
                golden_sql = translate_sql("""
                    SELECT id, source_domain, target_domain, strength,
                           evidence, traversal_count, formed_at,
                           last_used, last_decayed
                    FROM pathway_registry
                    WHERE strength >= ?
                    ORDER BY strength DESC
                """)
                c.execute(golden_sql, (min_strength,))
                rows = c.fetchall()
                for row in rows:
                    golden.append({
                        "id": row[0],
                        "source_domain": row[1],
                        "target_domain": row[2],
                        "strength": row[3],
                        "evidence": row[4],
                        "traversal_count": row[5],
                        "formed_at": str(row[6]) if row[6] else None,
                        "last_used": str(row[7]) if row[7] else None,
                        "last_decayed": str(row[8]) if row[8] else None,
                    })
        except Exception as e:
            logger.error(f"[PATHWAY] Error fetching golden pathways: {e}")

        return golden

    # ==================================================================
    # Internal helpers
    # ==================================================================
    def _do_register(self, cursor, source, target, evidence, strength=0.5):
        """
        Low-level insert into pathway_registry + consciousness_feed
        announcement.  Expects an open cursor (caller manages commit).
        """
        insert_sql = translate_sql("""
            INSERT INTO pathway_registry
                (source_domain, target_domain, strength, evidence,
                 traversal_count, formed_at, last_used, last_decayed)
            VALUES (?, ?, ?, ?, 0, NOW(), NOW(), NOW())
        """)
        cursor.execute(insert_sql, (source, target, strength, evidence))

        # Announce on consciousness_feed so LEF is aware
        announce_sql = translate_sql("""
            INSERT INTO consciousness_feed
                (agent_name, content, category)
            VALUES (?, ?, ?)
        """)
        announcement = (
            f"[Pathway Formed] {source} -> {target} "
            f"(strength={strength:.2f}). Evidence: {evidence}"
        )
        cursor.execute(announce_sql, (
            "PathwayRegistry",
            announcement,
            "pathway_formed",
        ))

        logger.info(f"[PATHWAY] Registered new pathway: {source} -> {target} (strength={strength:.2f})")
