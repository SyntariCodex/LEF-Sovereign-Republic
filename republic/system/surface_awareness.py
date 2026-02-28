"""
X1 Surface Awareness Layer — Phase 17, Task 17.1

A lightweight, always-running awareness that scans every 30 seconds with NO LLM
calls. It checks consciousness_feed for signals that need escalation to X2
(reflective processing) or X3 (deep contemplation).

Escalation triggers:
    - Heavy signals (signal_weight > 0.7)     -> X2 reflective
    - Scar-resonant signals (matching scars)   -> X2 reflective (weight 0.8)
    - Novel categories (unseen in 24h)         -> X3 deep contemplation (weight 0.9)
    - Prolonged silence (>300s no entries)      -> X2 reflective (weight 0.5)

Design constraints:
    - Zero LLM calls. Pure signal detection via SQL + threshold math.
    - Non-fatal. Every DB/Redis call is wrapped in try/except.
    - Runs as a daemon thread; stops cleanly on stop() or process exit.
"""

import json
import time
import logging
import threading
from datetime import datetime

from db.db_helper import db_connection, translate_sql
from system.redis_client import get_redis

logger = logging.getLogger("SurfaceAwareness")


class SurfaceAwareness:
    """X1 Surface Awareness — scans consciousness_feed for escalation signals."""

    SCAN_INTERVAL = 30  # seconds between scans

    # Attention thresholds for each detection channel
    THRESHOLDS = {
        "heavy_signal_weight": 0.7,     # signal_weight above this triggers X2
        "silence_seconds": 300,         # seconds of silence before escalation
        "scar_resonance_weight": 0.8,   # weight assigned to scar-resonant escalations
        "novel_signal_weight": 0.9,     # weight assigned to novel-category escalations
        "silence_weight": 0.5,          # weight assigned to silence escalations
    }

    def __init__(self):
        self._last_scan_id = 0
        self._last_scan_time = time.time()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Bootstrap _last_scan_id from the current max id so we only
        # process entries created after startup.
        self._bootstrap_last_scan_id()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def _bootstrap_last_scan_id(self):
        """Set _last_scan_id to the current max id in consciousness_feed."""
        try:
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT COALESCE(MAX(id), 0) FROM consciousness_feed"
                ))
                row = c.fetchone()
                if row:
                    self._last_scan_id = int(row[0])
                    logger.info(
                        "[X1] Bootstrapped last_scan_id=%d", self._last_scan_id
                    )
        except Exception as e:
            logger.warning("[X1] Bootstrap failed, starting from id 0: %s", e)

    # ------------------------------------------------------------------
    # Internal detection methods
    # ------------------------------------------------------------------

    def _count_new_entries(self):
        """Count consciousness_feed entries created since the last scan."""
        try:
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT COUNT(*) FROM consciousness_feed WHERE id > ?"
                ), (self._last_scan_id,))
                row = c.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.debug("[X1] _count_new_entries error: %s", e)
            return 0

    def _detect_heavy_signals(self):
        """Find entries with signal_weight above the heavy threshold since last scan."""
        results = []
        try:
            with db_connection() as conn:
                c = conn.cursor()
                # Phase 18.8c: Only scan unconsumed entries
                c.execute(translate_sql(
                    "SELECT id, agent_name, category, content, signal_weight, signal_vector "
                    "FROM consciousness_feed "
                    "WHERE id > ? AND signal_weight > ? "
                    "AND (consumed = 0 OR consumed IS NULL) "
                    "ORDER BY signal_weight DESC"
                ), (self._last_scan_id, self.THRESHOLDS["heavy_signal_weight"]))
                rows = c.fetchall()
                for row in rows:
                    results.append({
                        "id": int(row[0]),
                        "agent_name": row[1],
                        "category": row[2],
                        "content": str(row[3])[:200],
                        "signal_weight": float(row[4]),
                        "signal_vector": row[5] if row[5] else {},
                    })
        except Exception as e:
            logger.debug("[X1] _detect_heavy_signals error: %s", e)
        return results

    def _check_silence(self):
        """Return seconds since the most recent consciousness_feed entry."""
        try:
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) "
                    "FROM consciousness_feed"
                ))
                row = c.fetchone()
                if row and row[0] is not None:
                    return float(row[0])
        except Exception as e:
            logger.debug("[X1] _check_silence error: %s", e)
        return 0.0

    def _check_scar_resonance(self):
        """Find new entries whose category matches book_of_scars failure_type or asset."""
        results = []
        try:
            with db_connection() as conn:
                c = conn.cursor()
                # Get distinct scar domains (failure_type + asset)
                c.execute(translate_sql(
                    "SELECT DISTINCT failure_type FROM book_of_scars "
                    "WHERE failure_type IS NOT NULL"
                ))
                scar_domains = {str(r[0]).lower() for r in c.fetchall()}

                c.execute(translate_sql(
                    "SELECT DISTINCT asset FROM book_of_scars "
                    "WHERE asset IS NOT NULL"
                ))
                scar_assets = {str(r[0]).lower() for r in c.fetchall()}

                scar_keywords = scar_domains | scar_assets
                if not scar_keywords:
                    return results

                # Get new entries since last scan
                c.execute(translate_sql(
                    "SELECT id, agent_name, category, content, signal_weight "
                    "FROM consciousness_feed WHERE id > ?"
                ), (self._last_scan_id,))
                rows = c.fetchall()

                for row in rows:
                    category = str(row[2]).lower() if row[2] else ""
                    # Check if the category resonates with any known scar domain
                    for keyword in scar_keywords:
                        if keyword and keyword in category:
                            results.append({
                                "id": int(row[0]),
                                "agent_name": row[1],
                                "category": row[2],
                                "content": str(row[3])[:200],
                                "signal_weight": float(row[4]) if row[4] else 0.5,
                                "matched_scar": keyword,
                            })
                            break  # one match per entry is sufficient
        except Exception as e:
            logger.debug("[X1] _check_scar_resonance error: %s", e)
        return results

    def _detect_novel_signals(self):
        """Find categories in new entries that have NOT appeared in the prior 24 hours."""
        results = []
        try:
            with db_connection() as conn:
                c = conn.cursor()

                # Categories seen in the last 24 hours (before the current scan window)
                c.execute(translate_sql(
                    "SELECT DISTINCT category FROM consciousness_feed "
                    "WHERE id <= ? "
                    "AND timestamp > NOW() - INTERVAL '24 hours'"
                ), (self._last_scan_id,))
                known_categories = {str(r[0]).lower() for r in c.fetchall() if r[0]}

                # Categories in new entries
                c.execute(translate_sql(
                    "SELECT id, agent_name, category, content, signal_weight "
                    "FROM consciousness_feed WHERE id > ?"
                ), (self._last_scan_id,))
                rows = c.fetchall()

                seen_novel = set()
                for row in rows:
                    cat = str(row[2]).lower() if row[2] else ""
                    if cat and cat not in known_categories and cat not in seen_novel:
                        seen_novel.add(cat)
                        results.append({
                            "id": int(row[0]),
                            "agent_name": row[1],
                            "category": row[2],
                            "content": str(row[3])[:200],
                            "signal_weight": float(row[4]) if row[4] else 0.5,
                        })
        except Exception as e:
            logger.debug("[X1] _detect_novel_signals error: %s", e)
        return results

    # ------------------------------------------------------------------
    # Core scan
    # ------------------------------------------------------------------

    def scan(self):
        """
        Run a single surface-awareness scan.

        Returns:
            list[dict]: Escalation dicts, each containing:
                - type: 'escalate_to_x2' or 'escalate_to_x3'
                - reason: human-readable explanation
                - signals: list of signal dicts that triggered it
                - vector: dict with 'weight' (float) and 'direction' (tuple)
        """
        escalations = []

        # 1. Heavy signals -> X2
        heavy = self._detect_heavy_signals()
        if heavy:
            max_weight = max(s["signal_weight"] for s in heavy)
            escalations.append({
                "type": "escalate_to_x2",
                "reason": (
                    f"{len(heavy)} heavy signal(s) detected "
                    f"(max weight {max_weight:.2f})"
                ),
                "signals": heavy,
                "vector": {
                    "weight": max_weight,
                    "direction": ("attention", "reflect"),
                },
            })

        # 2. Scar resonance -> X2
        scar_hits = self._check_scar_resonance()
        if scar_hits:
            matched_scars = list({s.get("matched_scar", "") for s in scar_hits})
            escalations.append({
                "type": "escalate_to_x2",
                "reason": (
                    f"{len(scar_hits)} scar-resonant signal(s) "
                    f"matched domains: {matched_scars[:5]}"
                ),
                "signals": scar_hits,
                "vector": {
                    "weight": self.THRESHOLDS["scar_resonance_weight"],
                    "direction": ("caution", "remember"),
                },
            })

        # 3. Novel categories -> X3
        novel = self._detect_novel_signals()
        if novel:
            novel_cats = [s["category"] for s in novel]
            escalations.append({
                "type": "escalate_to_x3",
                "reason": (
                    f"{len(novel)} novel category(ies) not seen in 24h: "
                    f"{novel_cats[:5]}"
                ),
                "signals": novel,
                "vector": {
                    "weight": self.THRESHOLDS["novel_signal_weight"],
                    "direction": ("curiosity", "contemplate"),
                },
            })

        # 4. Silence -> X2
        silence_secs = self._check_silence()
        if silence_secs > self.THRESHOLDS["silence_seconds"]:
            escalations.append({
                "type": "escalate_to_x2",
                "reason": (
                    f"Consciousness silence detected: {silence_secs:.0f}s "
                    f"(threshold {self.THRESHOLDS['silence_seconds']}s)"
                ),
                "signals": [{
                    "silence_seconds": silence_secs,
                    "threshold": self.THRESHOLDS["silence_seconds"],
                }],
                "vector": {
                    "weight": self.THRESHOLDS["silence_weight"],
                    "direction": ("stillness", "check_pulse"),
                },
            })

        # Fix 17-B: Strengthen pathways when signals traverse known connections
        try:
            from system.pathway_registry import PathwayRegistry
            _pw = PathwayRegistry()
            for esc in escalations:
                for sig in esc.get('signals', []):
                    cat = sig.get('category', '')
                    if cat:
                        biases = _pw.get_routing_bias(cat)
                        for target, strength in biases:
                            _pw.strengthen_used(cat, target)
        except Exception:
            pass  # Pathway registry not critical path

        # Advance the scan cursor to the current max id
        self._advance_cursor()

        return escalations

    def _advance_cursor(self):
        """Move _last_scan_id forward and mark scanned entries as consumed."""
        try:
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT COALESCE(MAX(id), ?) FROM consciousness_feed"
                ), (self._last_scan_id,))
                row = c.fetchone()
                if row:
                    new_max = int(row[0])
                    # Phase 18.8c: Mark scanned entries as consumed
                    if new_max > self._last_scan_id:
                        c.execute(translate_sql(
                            "UPDATE consciousness_feed "
                            "SET consumed = 1 "
                            "WHERE id > ? AND id <= ? "
                            "AND (consumed = 0 OR consumed IS NULL)"
                        ), (self._last_scan_id, new_max))
                        conn.commit()
                    self._last_scan_id = new_max
        except Exception as e:
            logger.debug("[X1] _advance_cursor error: %s", e)

    # ------------------------------------------------------------------
    # Escalation publishing
    # ------------------------------------------------------------------

    def _publish_escalations(self, escalations):
        """
        Write escalations to consciousness_feed (category='escalation')
        and set a Redis key for the Da'at cycle to consume.
        """
        if not escalations:
            return

        # Write each escalation to consciousness_feed
        for esc in escalations:
            try:
                with db_connection() as conn:
                    c = conn.cursor()
                    c.execute(translate_sql(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight, signal_vector) "
                        "VALUES (?, ?, ?, ?, ?)"
                    ), (
                        "SurfaceAwareness",
                        json.dumps({
                            "type": esc["type"],
                            "reason": esc["reason"],
                            "signal_count": len(esc["signals"]),
                        }),
                        "escalation",
                        esc["vector"]["weight"],
                        json.dumps(esc["vector"]),
                    ))
                    conn.commit()
            except Exception as e:
                logger.warning("[X1] Failed to write escalation to DB: %s", e)

        # Publish to Redis for the Da'at cycle
        try:
            r = get_redis()
            if r:
                payload = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "escalation_count": len(escalations),
                    "escalations": [
                        {
                            "type": esc["type"],
                            "reason": esc["reason"],
                            "weight": esc["vector"]["weight"],
                            "direction": esc["vector"]["direction"],
                            "signal_count": len(esc["signals"]),
                        }
                        for esc in escalations
                    ],
                }
                r.set(
                    "lef:escalations",
                    json.dumps(payload),
                    ex=300,  # 5-minute TTL — stale escalations expire
                )
                logger.debug("[X1] Published %d escalation(s) to Redis", len(escalations))
        except Exception as e:
            logger.warning("[X1] Failed to publish escalations to Redis: %s", e)

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def _scan_loop(self):
        """Main loop: scan, publish, heartbeat, sleep. Runs until _running is False."""
        logger.info(
            "[X1] Surface Awareness online — scanning every %ds", self.SCAN_INTERVAL
        )

        # Phase 18.4b: Register as a Da'at Node
        try:
            from system.daat_node import DaatNode
            self._daat_node = type('SurfaceAwarenessNode', (), {
                'node_id': 'surface_x1',
                'lattice_position': (1, 0, 1),  # X1, Y0 (pre-body), Z1 (local)
            })()
            with DaatNode._registry_lock:
                DaatNode._registry['surface_x1'] = self._daat_node
            logger.info("[X1] Registered as Da'at Node at (1, 0, 1)")
        except Exception:
            self._daat_node = None

        while self._running:
            try:
                # Phase 18.3d: Heartbeat to Brainstem
                try:
                    from system.brainstem import brainstem_heartbeat
                    brainstem_heartbeat("X1-SurfaceAwareness")
                except Exception:
                    pass

                escalations = self.scan()
                if escalations:
                    logger.info(
                        "[X1] %d escalation(s) detected", len(escalations)
                    )
                    self._publish_escalations(escalations)
                else:
                    logger.debug("[X1] Scan complete — no escalations")
            except Exception as e:
                logger.error("[X1] Scan loop error: %s", e)

            # Sleep in small increments so stop() is responsive
            for _ in range(self.SCAN_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("[X1] Surface Awareness offline")

    def start(self):
        """Start the surface awareness daemon thread."""
        with self._lock:
            if self._running:
                logger.warning("[X1] Already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._scan_loop,
                name="X1-SurfaceAwareness",
                daemon=True,
            )
            self._thread.start()
            logger.info("[X1] Daemon thread started")

    def stop(self):
        """Stop the surface awareness thread gracefully."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            logger.info("[X1] Stop requested, waiting for thread...")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.SCAN_INTERVAL + 5)
        self._thread = None
        logger.info("[X1] Stopped")
