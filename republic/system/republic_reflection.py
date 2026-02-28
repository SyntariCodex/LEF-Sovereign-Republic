"""
Republic Reflection — Body One of the Three-Body Reflection Architecture.

The republic's peripheral nervous system. Always running, always noticing.
Does not analyze. Does not propose. Does not act. Just attends.

Design doc: LEF Ai Projects/Phase - Three-Body Reflection Architecture.md
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger("RepublicReflection")


class RepublicReflection:
    """
    Continuous peripheral awareness of the republic's state.

    Reads from:
    - consciousness_feed (agent introspections)
    - book_of_scars (failure history)
    - agent_logs (agent activity and errors)
    - system_state (if available)

    Outputs to:
    - republic_awareness table (rolling state snapshot)

    Other bodies read from republic_awareness. This body writes to it.
    """

    def __init__(self, db_connection_func, cycle_interval=60):
        """
        Args:
            db_connection_func: callable that returns a DB connection (from db_pool)
            cycle_interval: seconds between awareness cycles (default 60)
        """
        self.db_connection = db_connection_func
        self.cycle_interval = cycle_interval
        self._cycle_number = 0
        self._running = False
        self._thread = None

        # Pattern memory — survives across cycles within a session
        self._pattern_memory = {}  # pattern_key -> {count, first_seen, last_seen, domain}
        self._PATTERN_WINDOW_HOURS = 24  # How far back to look for patterns
        self._NOTICING_THRESHOLD = 3    # How many recurrences before surfacing to Body Two

    def start(self):
        """Start the reflection loop as a background thread."""
        if self._running:
            logger.warning("[BODY ONE] Already running.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="RepublicReflection")
        self._thread.start()
        logger.info("[BODY ONE] Republic Reflection started. Peripheral awareness active.")

    def stop(self):
        """Stop the reflection loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[BODY ONE] Republic Reflection stopped.")

    def _run_loop(self):
        """Main loop — runs until stopped."""
        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"[BODY ONE] Cycle error: {e}")
            time.sleep(self.cycle_interval)

    def _run_cycle(self):
        """Single awareness cycle. Read, notice, record."""
        self._cycle_number += 1

        # Phase 1: Read from all sources (each tolerates failure independently)
        consciousness_patterns = []
        scar_activity = {}
        agent_health = {}
        health_signals = {}

        with self.db_connection() as conn:
            c = conn.cursor()
            try:
                consciousness_patterns = self._read_consciousness_feed(c)
            except Exception:
                conn.rollback()
                c = conn.cursor()
            try:
                scar_activity = self._read_scar_activity(c)
            except Exception:
                conn.rollback()
                c = conn.cursor()
            try:
                agent_health = self._read_agent_health(c)
            except Exception:
                conn.rollback()
                c = conn.cursor()
            try:
                health_signals = self._read_health_signals(c)
            except Exception:
                conn.rollback()
                c = conn.cursor()

            # Phase 2: Detect patterns from whatever data we gathered
            active_patterns = self._detect_patterns(
                consciousness_patterns, scar_activity, agent_health, health_signals
            )

            # Phase 3: Write awareness state (clean transaction)
            self._write_awareness(c, active_patterns, scar_activity, agent_health, health_signals)

            conn.commit()

        if self._cycle_number % 10 == 0:  # Log every 10th cycle to avoid noise
            logger.info(f"[BODY ONE] Cycle {self._cycle_number}: {len(active_patterns)} active patterns")

    def _read_consciousness_feed(self, cursor):
        """Read recent consciousness entries. Notice themes, not details."""
        cursor.execute("""
            SELECT agent_name, category, COUNT(*) as cnt
            FROM consciousness_feed
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY agent_name, category
            ORDER BY cnt DESC
        """)
        rows = cursor.fetchall()
        return [{"agent": r[0], "category": r[1], "count": r[2]} for r in rows]

    def _read_scar_activity(self, cursor):
        """Read recent scar entries. Notice which domains are hurting."""
        cursor.execute("""
            SELECT failure_type, asset, times_repeated, severity
            FROM book_of_scars
            WHERE last_seen > NOW() - INTERVAL '24 hours'
            ORDER BY times_repeated DESC
        """)
        rows = cursor.fetchall()
        activity = {}
        for r in rows:
            domain = r[0]  # failure_type as domain key
            if domain not in activity:
                activity[domain] = {"count": 0, "assets": [], "max_severity": "LOW", "total_repeats": 0}
            activity[domain]["count"] += 1
            if r[1] and r[1] not in activity[domain]["assets"]:
                activity[domain]["assets"].append(r[1])
            activity[domain]["total_repeats"] += (r[2] or 1)
            # Track max severity
            sev_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            if sev_rank.get(r[3], 0) > sev_rank.get(activity[domain]["max_severity"], 0):
                activity[domain]["max_severity"] = r[3]
        return activity

    def _read_agent_health(self, cursor):
        """Notice which agents are active, silent, or erroring."""
        # Recent errors by agent (agent_logs uses 'source' not 'agent_name')
        cursor.execute("""
            SELECT source, COUNT(*) as error_count
            FROM agent_logs
            WHERE level = 'ERROR'
            AND timestamp > NOW() - INTERVAL '1 hour'
            GROUP BY source
            ORDER BY error_count DESC
        """)
        errors = {r[0]: r[1] for r in cursor.fetchall()}

        # Agent last activity
        cursor.execute("""
            SELECT source, MAX(timestamp) as last_active
            FROM agent_logs
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY source
        """)
        last_seen = {}
        for r in cursor.fetchall():
            agent = r[0]
            last_ts = r[1]
            if isinstance(last_ts, str):
                try:
                    last_ts = datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_ts = datetime.now()
            elif isinstance(last_ts, datetime):
                pass
            else:
                last_ts = datetime.now()

            hours_silent = (datetime.now() - last_ts).total_seconds() / 3600
            last_seen[agent] = {
                "hours_since_active": round(hours_silent, 1),
                "silent": hours_silent > 2,
                "errors_last_hour": errors.get(agent, 0)
            }

        return last_seen

    def _read_health_signals(self, cursor):
        """Read system-level health signals."""
        signals = {}

        # Check for recent circuit breaker activations (agent_logs uses 'message' not 'content')
        cursor.execute("""
            SELECT COUNT(*) FROM agent_logs
            WHERE (message LIKE '%circuit breaker%' OR message LIKE '%CIRCUIT_BREAKER%')
            AND timestamp > NOW() - INTERVAL '1 hour'
        """)
        row = cursor.fetchone()
        signals["circuit_breaker_activations"] = row[0] if row else 0

        # Check trade queue health
        cursor.execute("""
            SELECT status, COUNT(*) FROM trade_queue
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY status
        """)
        trade_status = {r[0]: r[1] for r in cursor.fetchall()}
        signals["trade_queue"] = trade_status

        # Check for stale directives
        cursor.execute("""
            SELECT COUNT(*) FROM lef_directives
            WHERE status = 'PENDING'
            AND created_at < NOW() - INTERVAL '1 hour'
        """)
        row = cursor.fetchone()
        signals["stale_directives"] = row[0] if row else 0

        return signals

    def _detect_patterns(self, consciousness, scars, agent_health, health_signals):
        """
        Detect recurring patterns across all data sources.

        A pattern is: something that keeps showing up.
        This method notices, it does not judge.
        """
        patterns = []
        now = datetime.now()
        cutoff = now - timedelta(hours=self._PATTERN_WINDOW_HOURS)

        # Pattern: Scar domain clustering
        for domain, info in scars.items():
            if info["total_repeats"] >= self._NOTICING_THRESHOLD:
                key = f"scar_cluster:{domain}"
                patterns.append({
                    "key": key,
                    "type": "recurring_failure",
                    "domain": domain,
                    "description": f"Failure type '{domain}' has repeated {info['total_repeats']} times across {info['count']} scars",
                    "severity": info["max_severity"],
                    "data": info
                })

        # Pattern: Agent silence
        silent_agents = [name for name, info in agent_health.items()
                        if info.get("silent", False)]
        if len(silent_agents) >= 2:
            patterns.append({
                "key": "agent_silence_cluster",
                "type": "communication_gap",
                "domain": "operational",
                "description": f"{len(silent_agents)} agents silent for >2h: {', '.join(silent_agents[:5])}",
                "severity": "MEDIUM",
                "data": {"agents": silent_agents}
            })

        # Pattern: Error concentration
        high_error_agents = [name for name, info in agent_health.items()
                           if info.get("errors_last_hour", 0) > 5]
        if high_error_agents:
            patterns.append({
                "key": f"error_concentration:{'_'.join(sorted(high_error_agents[:3]))}",
                "type": "error_cluster",
                "domain": "operational",
                "description": f"High error rate in {len(high_error_agents)} agents: {', '.join(high_error_agents[:5])}",
                "severity": "HIGH",
                "data": {"agents": {a: agent_health[a]["errors_last_hour"] for a in high_error_agents}}
            })

        # Pattern: Circuit breaker activations
        cb_count = health_signals.get("circuit_breaker_activations", 0)
        if cb_count > 0:
            patterns.append({
                "key": "circuit_breaker_active",
                "type": "system_stress",
                "domain": "operational",
                "description": f"Circuit breaker activated {cb_count} times in last hour",
                "severity": "HIGH" if cb_count > 3 else "MEDIUM",
                "data": {"count": cb_count}
            })

        # Pattern: Stale directives
        stale = health_signals.get("stale_directives", 0)
        if stale > 0:
            patterns.append({
                "key": "stale_directives",
                "type": "communication_gap",
                "domain": "governance",
                "description": f"{stale} directives pending for >1 hour",
                "severity": "MEDIUM",
                "data": {"count": stale}
            })

        # Pattern: Trade failures
        trade_q = health_signals.get("trade_queue", {})
        failed = trade_q.get("FAILED", 0)
        total = sum(trade_q.values()) if trade_q else 0
        if failed > 3 or (total > 0 and failed / total > 0.3):
            patterns.append({
                "key": "trade_failure_rate",
                "type": "recurring_failure",
                "domain": "wealth",
                "description": f"Trade failure rate elevated: {failed} failed of {total} total in 24h",
                "severity": "HIGH",
                "data": trade_q
            })

        # Phase 12: Detect purpose-domain patterns from consciousness_feed
        PURPOSE_CATEGORIES = {
            "existential_scotoma", "constitutional_alignment", "growth_journal",
            "dream_tension", "dream_alignment", "wake_intention",  # Phase 14
        }
        for entry in consciousness:
            cat = entry.get("category", "")
            if cat in PURPOSE_CATEGORIES and entry.get("count", 0) >= 1:
                key = f"purpose_signal:{cat}"
                patterns.append({
                    "key": key,
                    "type": "existential_observation",
                    "domain": "purpose",
                    "description": f"Existential signal: {entry.get('count', 0)} '{cat}' entries from {entry.get('agent', 'unknown')} in 24h",
                    "severity": "MEDIUM",
                    "data": {"category": cat, "agent": entry.get("agent"), "count": entry.get("count", 0)}
                })

        # Update pattern memory for temporal tracking
        for p in patterns:
            key = p["key"]
            if key in self._pattern_memory:
                self._pattern_memory[key]["count"] += 1
                self._pattern_memory[key]["last_seen"] = now.isoformat()
            else:
                self._pattern_memory[key] = {
                    "count": 1,
                    "first_seen": now.isoformat(),
                    "last_seen": now.isoformat(),
                    "domain": p.get("domain", "unknown")
                }

        # Clean old entries from pattern memory
        for key in list(self._pattern_memory.keys()):
            last = datetime.fromisoformat(self._pattern_memory[key]["last_seen"])
            if last < cutoff:
                del self._pattern_memory[key]

        return patterns

    def _write_awareness(self, cursor, patterns, scar_activity, agent_health, health_signals):
        """Write current awareness state to republic_awareness table."""
        try:
            cursor.execute("""
                INSERT INTO republic_awareness
                (active_patterns, scar_domain_activity, agent_health, republic_health_signals, pattern_count, cycle_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                json.dumps(patterns),
                json.dumps(scar_activity, default=str),
                json.dumps(agent_health, default=str),
                json.dumps(health_signals, default=str),
                len(patterns),
                self._cycle_number
            ))

            # Keep only last 1000 awareness snapshots (trim old ones)
            cursor.execute("""
                DELETE FROM republic_awareness
                WHERE id NOT IN (
                    SELECT id FROM republic_awareness ORDER BY id DESC LIMIT 1000
                )
            """)
        except Exception as e:
            logger.error(f"[BODY ONE] Failed to write awareness: {e}")

        # Phase 15: Surface significant patterns to consciousness_feed
        if patterns:
            try:
                significant = [p for p in patterns if p.get('severity', 'LOW') in ('MEDIUM', 'HIGH', 'CRITICAL')]
                if significant:
                    from db.db_helper import translate_sql
                    cursor.execute(translate_sql(
                        "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                        "VALUES (?, ?, 'republic_pattern', NOW())"
                    ), ('BodyOne', json.dumps({
                        'pattern_count': len(significant),
                        'patterns': [
                            {
                                'type': p.get('type', 'unknown'),
                                'key': p.get('key', '')[:100],
                                'description': str(p.get('description', ''))[:200],
                                'severity': p.get('severity', 'MEDIUM')
                            }
                            for p in significant[:5]
                        ]
                    })))
            except Exception as e:
                logger.debug(f"[BODY ONE] Failed to surface patterns to consciousness_feed: {e}")

    def get_current_awareness(self):
        """
        Public method: return the latest republic_awareness snapshot.
        Body Two and other systems call this.
        """
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT active_patterns, scar_domain_activity, agent_health,
                           republic_health_signals, pattern_count, cycle_number, timestamp
                    FROM republic_awareness
                    ORDER BY id DESC LIMIT 1
                """)
                row = c.fetchone()
                if not row:
                    return None
                return {
                    "active_patterns": json.loads(row[0]) if isinstance(row[0], str) else row[0],
                    "scar_domain_activity": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                    "agent_health": json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    "health_signals": json.loads(row[3]) if isinstance(row[3], str) else row[3],
                    "pattern_count": row[4],
                    "cycle_number": row[5],
                    "timestamp": row[6]
                }
        except Exception as e:
            logger.error(f"[BODY ONE] get_current_awareness failed: {e}")
            return None

    def get_patterns_above_threshold(self, threshold=None):
        """
        Return patterns from memory that have recurred enough to warrant Body Two's attention.
        """
        threshold = threshold or self._NOTICING_THRESHOLD
        surfaceable = []
        for key, mem in self._pattern_memory.items():
            if mem["count"] >= threshold:
                surfaceable.append({
                    "pattern_key": key,
                    "recurrence_count": mem["count"],
                    "domain": mem["domain"],
                    "first_seen": mem["first_seen"],
                    "last_seen": mem["last_seen"]
                })
        return sorted(surfaceable, key=lambda x: x["recurrence_count"], reverse=True)
