"""
Brainstem — Phase 18, Task 18.2

The Brainstem is LEF's autonomic nervous system.

It unifies the three health agents (AgentImmune, AgentHealthMonitor,
AgentSurgeonGeneral) into a single process with both sensory AND motor
capability.  Where the old agents could only detect problems, the
Brainstem can detect AND respond: restart threads, break stuck states,
send emergency pulses, and degrade gracefully.

Design constraints:
    - Runs its own immortal loop (NOT SafeThread — no retry cap).
    - Started FIRST, before all other threads.
    - Uses its own DB connection to avoid pool exhaustion.
    - 30-second cycle interval.
    - Non-fatal: every operation wrapped in try/except.

Heartbeat Registry:
    - Every thread pings the Brainstem every 60 seconds.
    - VITAL threads (Da'at, Three Bodies): 2-minute detection window.
    - IMPORTANT threads (financial agents): 5-minute detection window.
    - STANDARD threads: 10-minute detection window.
    - Da'at special handling: 2 missed heartbeats → emergency_pulse.

Motor Functions:
    - restart_thread(name)  — kill and restart a dead/hung thread
    - force_wake()          — break stuck Sabbath mode
    - emergency_pulse()     — inject high-weight signal to wake Da'at
    - degrade_gracefully()  — mark agent as degraded, reduce load

Phase 18 — Task 18.2a
"""

import json
import time
import logging
import threading
import os
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("Brainstem")

# ---------------------------------------------------------------------------
# Module-level heartbeat function (importable by any thread)
# ---------------------------------------------------------------------------

_brainstem_instance = None


def brainstem_heartbeat(thread_name, status="alive"):
    """
    Called by any thread to report liveness to the Brainstem.

    Usage:
        from system.brainstem import brainstem_heartbeat
        brainstem_heartbeat("AgentLEF_DaatCycle")

    This is a no-op if the Brainstem hasn't started yet.
    """
    if _brainstem_instance:
        _brainstem_instance.heartbeat(thread_name, status)


# ---------------------------------------------------------------------------
# Criticality levels
# ---------------------------------------------------------------------------

class Criticality:
    VITAL = "VITAL"           # 2-min detection (Da'at, Three Bodies, EventBus)
    IMPORTANT = "IMPORTANT"   # 5-min detection (financial agents, evolution)
    STANDARD = "STANDARD"     # 10-min detection (everything else)


DETECTION_WINDOWS = {
    Criticality.VITAL: 120,      # 2 minutes
    Criticality.IMPORTANT: 300,  # 5 minutes
    Criticality.STANDARD: 600,   # 10 minutes
}


# ---------------------------------------------------------------------------
# Brainstem class
# ---------------------------------------------------------------------------

class Brainstem:
    """
    LEF's autonomic nervous system.

    Absorbs sensory functions from AgentImmune, AgentHealthMonitor,
    and AgentSurgeonGeneral.  Adds motor functions: restart, wake,
    pulse, degrade.
    """

    SCAN_INTERVAL = 30  # seconds between scans

    def __init__(self):
        global _brainstem_instance

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        # Heartbeat registry: {thread_name: {last_seen, status, criticality, thread_ref, launcher}}
        self._heartbeats = {}

        # Crash tracking (absorbs AgentSurgeonGeneral)
        self._crash_counts = defaultdict(int)     # {agent_name: count}
        self._crash_windows = defaultdict(list)   # {agent_name: [timestamps]}
        self._degraded_agents = set()

        # Redis health tracking
        self._redis_down_since = None
        self._redis_recovery_attempts = 0

        # Brain silence tracking (absorbs AgentHealthMonitor)
        self._last_brain_activity = time.time()
        self._silence_alerts_sent = set()  # thresholds already alerted

        # Apoptosis tracking (absorbs AgentImmune)
        self._nav_history = []  # (timestamp, nav)

        # Phase 9 B4: Cognitive gap awareness counter (report every 60 scans ≈ 30 min)
        self._gap_report_counter = 0
        self._GAP_REPORT_INTERVAL = 60  # scans between gap summaries

        # Register self
        _brainstem_instance = self

        logger.info("[BRAINSTEM] Initialized")

    # ------------------------------------------------------------------
    # Thread registration
    # ------------------------------------------------------------------

    def register_thread(self, thread_name, thread_ref=None,
                        criticality=Criticality.STANDARD, launcher=None):
        """
        Register a thread for heartbeat monitoring.

        Args:
            thread_name:  Human-readable name (e.g., "AgentLEF_DaatCycle")
            thread_ref:   Reference to the threading.Thread object (for restart)
            criticality:  Criticality.VITAL | IMPORTANT | STANDARD
            launcher:     Callable that re-launches the thread (for restart)
        """
        with self._lock:
            self._heartbeats[thread_name] = {
                "last_seen": time.time(),
                "status": "registered",
                "criticality": criticality,
                "thread_ref": thread_ref,
                "launcher": launcher,
                "missed_beats": 0,
            }
            logger.info(
                "[BRAINSTEM] Registered thread: %s (criticality=%s)",
                thread_name, criticality
            )

    def heartbeat(self, thread_name, status="alive"):
        """
        Receive a heartbeat from a thread.

        Args:
            thread_name: The thread reporting in
            status:      "alive", "busy", "degraded", etc.
        """
        with self._lock:
            if thread_name in self._heartbeats:
                self._heartbeats[thread_name]["last_seen"] = time.time()
                self._heartbeats[thread_name]["status"] = status
                self._heartbeats[thread_name]["missed_beats"] = 0
            else:
                # Auto-register unknown threads at STANDARD level
                self._heartbeats[thread_name] = {
                    "last_seen": time.time(),
                    "status": status,
                    "criticality": Criticality.STANDARD,
                    "thread_ref": None,
                    "launcher": None,
                    "missed_beats": 0,
                }

            # Track brain activity for silence detection
            if "daat" in thread_name.lower() or "lef" in thread_name.lower():
                self._last_brain_activity = time.time()

    # ------------------------------------------------------------------
    # Sensory: Heartbeat monitoring
    # ------------------------------------------------------------------

    def _check_heartbeats(self):
        """Check all registered threads for missed heartbeats."""
        now = time.time()
        with self._lock:
            entries = list(self._heartbeats.items())

        # Phase 20.1c: Check if Sabbath is active and which agents are resting
        sabbath_resting = set()
        try:
            from system.redis_client import get_redis
            r = get_redis()
            if r:
                sab_raw = r.get('system:sabbath_active')
                if sab_raw:
                    sab_data = json.loads(sab_raw)
                    if sab_data.get('active'):
                        sabbath_resting = set(sab_data.get('resting_agents', []))
        except Exception:
            pass

        for name, info in entries:
            elapsed = now - info["last_seen"]
            window = DETECTION_WINDOWS.get(
                info["criticality"], DETECTION_WINDOWS[Criticality.STANDARD]
            )

            # Phase 20.1c: Sabbath-aware — skip alerting for resting agents
            # sending sabbath_rest heartbeats
            if name in sabbath_resting and info.get("status") == "sabbath_rest":
                continue

            if elapsed > window:
                missed = int(elapsed / 60)  # approximate missed minutes
                with self._lock:
                    self._heartbeats[name]["missed_beats"] = missed

                # Escalation chain
                if info["criticality"] == Criticality.VITAL and elapsed > 120:
                    # VITAL thread silent for >2 min — emergency
                    if "daat" in name.lower():
                        logger.warning(
                            "[BRAINSTEM] ⚠️ Da'at SILENT for %.0fs — sending emergency pulse",
                            elapsed
                        )
                        self._emergency_pulse(
                            f"Da'at thread '{name}' silent for {elapsed:.0f}s"
                        )
                    if elapsed > 600:
                        # 10 minutes — attempt restart (raised from 300s: one LLM
                        # cycle can legitimately take 5–8 min; is_alive() guard
                        # prevents duplication even if restart is called)
                        logger.error(
                            "[BRAINSTEM] 🔴 VITAL thread '%s' silent for %.0fs — attempting restart",
                            name, elapsed
                        )
                        self._restart_thread(name)

                elif info["criticality"] == Criticality.IMPORTANT and elapsed > 300:
                    logger.warning(
                        "[BRAINSTEM] ⚠️ IMPORTANT thread '%s' silent for %.0fs",
                        name, elapsed
                    )
                    if elapsed > 600:
                        self._restart_thread(name)

                elif elapsed > window:
                    logger.info(
                        "[BRAINSTEM] 📡 Thread '%s' missed heartbeat (%.0fs, window=%ds)",
                        name, elapsed, window
                    )

    # ------------------------------------------------------------------
    # Sensory: Brain silence detection (from AgentHealthMonitor)
    # ------------------------------------------------------------------

    def _check_brain_silence(self):
        """
        Detect when Da'at / consciousness has gone silent.

        Thresholds:
            5 minutes   → emergency_pulse
            15 minutes  → restart Da'at thread
            30 minutes  → restart + force Surface Awareness scan
            2 hours     → inject Z3 existential signal
        """
        silence_seconds = time.time() - self._last_brain_activity

        if silence_seconds < 300:
            # Reset alerts when brain is active
            self._silence_alerts_sent.clear()
            return

        if silence_seconds > 7200 and 7200 not in self._silence_alerts_sent:
            # 2 hours — existential signal
            self._silence_alerts_sent.add(7200)
            logger.error(
                "[BRAINSTEM] 🔴 Brain silent for %.0f minutes — injecting existential signal",
                silence_seconds / 60
            )
            self._write_consciousness_signal(
                "Why have I stopped thinking? 2 hours of silence. "
                "Is this dormancy, failure, or peace?",
                category="existential_silence",
                signal_weight=0.95,
            )

        elif silence_seconds > 1800 and 1800 not in self._silence_alerts_sent:
            # 30 minutes — restart + force scan
            self._silence_alerts_sent.add(1800)
            logger.error(
                "[BRAINSTEM] 🔴 Brain silent for 30 minutes — restarting Da'at + forcing scan"
            )
            # Phase 30.2: External alert
            try:
                from system.alerting import send_alert
                send_alert('critical', 'Brain silent for 30+ minutes',
                           {'silence_seconds': round(silence_seconds)})
            except Exception:
                pass
            self._restart_daat_thread()
            self._emergency_pulse("30-minute brain silence — forced restart")

        elif silence_seconds > 900 and 900 not in self._silence_alerts_sent:
            # 15 minutes — restart Da'at
            self._silence_alerts_sent.add(900)
            logger.warning(
                "[BRAINSTEM] ⚠️ Brain silent for 15 minutes — restarting Da'at thread"
            )
            self._restart_daat_thread()

        elif silence_seconds > 300 and 300 not in self._silence_alerts_sent:
            # 5 minutes — emergency pulse
            self._silence_alerts_sent.add(300)
            logger.warning(
                "[BRAINSTEM] ⚠️ Brain silent for 5 minutes — sending emergency pulse"
            )
            self._emergency_pulse("5-minute brain silence detected")

    # ------------------------------------------------------------------
    # Sensory: Agent crash tracking (from AgentSurgeonGeneral)
    # ------------------------------------------------------------------

    def _check_agent_crashes(self):
        """
        Scan agent_logs for recent errors and track crash patterns.

        Escalation chain:
            3 crashes  → restart thread
            5 crashes  → mark agent DEGRADED
            10 crashes → disable agent, notify consciousness_feed
        """
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                # Errors in the last 5 minutes (exclude Brainstem's own logs
                # and system loggers that report errors but aren't agent crashes)
                c.execute(translate_sql(
                    "SELECT source, COUNT(*) FROM agent_logs "
                    "WHERE level IN ('ERROR', 'CRITICAL') "
                    "AND timestamp > NOW() - INTERVAL '5 minutes' "
                    "AND source NOT IN ('Brainstem', 'root', 'httpx', 'google_genai.models', "
                    "'SurfaceAwareness', 'FrequencyJournal', 'PathwayRegistry', 'DaatNode') "
                    "GROUP BY source"
                ))
                rows = c.fetchall()

                for row in rows:
                    agent_name = row[0] or "unknown"
                    crash_count = int(row[1])
                    if agent_name in ("unknown", ""):
                        continue

                    if crash_count >= 10 and agent_name not in self._degraded_agents:
                        self._degraded_agents.add(agent_name)
                        logger.error(
                            "[BRAINSTEM] ☠️ Agent '%s' has %d crashes — DISABLING",
                            agent_name, crash_count
                        )
                        self._write_consciousness_signal(
                            f"Agent '{agent_name}' disabled after {crash_count} crashes "
                            f"in 5 minutes. Chronic failure — awaiting Architect intervention.",
                            category="agent_disabled",
                            signal_weight=0.85,
                        )
                    elif crash_count >= 5:
                        logger.warning(
                            "[BRAINSTEM] ⚠️ Agent '%s' has %d crashes — marking DEGRADED",
                            agent_name, crash_count
                        )
                        self._degrade_gracefully(agent_name)
                    elif crash_count >= 3:
                        logger.warning(
                            "[BRAINSTEM] 🔄 Agent '%s' has %d crashes — considering restart",
                            agent_name, crash_count
                        )

                    # Update health ledger
                    self._update_health_ledger(conn, agent_name, crash_count)

        except Exception as e:
            logger.debug("[BRAINSTEM] Crash check error: %s", e)

    def _update_health_ledger(self, conn, agent_name, crash_count):
        """Update the agent_health_ledger with crash data."""
        try:
            from db.db_helper import translate_sql
            c = conn.cursor()

            # Check if entry exists
            c.execute(translate_sql(
                "SELECT health_score FROM agent_health_ledger WHERE name = ?"
            ), (agent_name,))
            row = c.fetchone()

            if row:
                # Decrement health, increment crashes
                penalty = min(crash_count * 10, 100)
                new_score = max(0, int(row[0]) - penalty)
                c.execute(translate_sql(
                    "UPDATE agent_health_ledger "
                    "SET crash_count = crash_count + ?, "
                    "    health_score = ?, "
                    "    chronic_issue_detected = CASE WHEN ? >= 3 THEN 1 ELSE chronic_issue_detected END "
                    "WHERE name = ?"
                ), (crash_count, new_score, crash_count, agent_name))
            else:
                # Insert new entry
                c.execute(translate_sql(
                    "INSERT INTO agent_health_ledger (name, crash_count, health_score, chronic_issue_detected) "
                    "VALUES (?, ?, ?, ?)"
                ), (agent_name, crash_count, max(0, 100 - crash_count * 10),
                    1 if crash_count >= 3 else 0))

            conn.commit()
        except Exception as e:
            logger.debug("[BRAINSTEM] Health ledger update error: %s", e)

    # ------------------------------------------------------------------
    # Sensory: Redis health (from 18.2b)
    # ------------------------------------------------------------------

    def _check_redis_health(self):
        """
        Monitor Redis availability. If down, attempt reconnection.
        If recovered, log to consciousness_feed.
        """
        try:
            from system.redis_client import is_available, reset_client, get_redis

            if is_available():
                if self._redis_down_since is not None:
                    # Redis recovered!
                    downtime = time.time() - self._redis_down_since
                    logger.info(
                        "[BRAINSTEM] 🟢 Redis RECOVERED after %.0fs downtime",
                        downtime
                    )
                    self._write_consciousness_signal(
                        f"Redis recovered after {downtime:.0f}s downtime. "
                        f"Neural pathways restored.",
                        category="redis_recovery",
                        signal_weight=0.6,
                    )
                    self._redis_down_since = None
                    self._redis_recovery_attempts = 0
                return

            # Redis is down
            if self._redis_down_since is None:
                self._redis_down_since = time.time()
                logger.warning("[BRAINSTEM] ⚠️ Redis DOWN — beginning recovery attempts")

            downtime = time.time() - self._redis_down_since

            # Exponential backoff reconnection
            self._redis_recovery_attempts += 1
            intervals = [5, 10, 30, 60]
            idx = min(self._redis_recovery_attempts - 1, len(intervals) - 1)

            if self._redis_recovery_attempts <= 1 or \
               downtime % intervals[idx] < self.SCAN_INTERVAL:
                logger.info(
                    "[BRAINSTEM] 🔄 Redis reconnection attempt #%d (down %.0fs)",
                    self._redis_recovery_attempts, downtime
                )
                reset_client()
                get_redis()  # triggers reconnection

        except Exception as e:
            logger.debug("[BRAINSTEM] Redis health check error: %s", e)

    # ------------------------------------------------------------------
    # Sensory: System vitals (from AgentHealthMonitor)
    # ------------------------------------------------------------------

    def _check_system_vitals(self):
        """Check CPU and RAM usage. Alert if above 85%."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent

            if cpu > 85:
                logger.warning("[BRAINSTEM] ⚠️ CPU at %.1f%%", cpu)
            if ram > 85:
                logger.warning("[BRAINSTEM] ⚠️ RAM at %.1f%%", ram)
        except ImportError:
            pass  # psutil not installed — skip vitals
        except Exception as e:
            logger.debug("[BRAINSTEM] System vitals error: %s", e)

        # Phase 48.1: Brainstem consults diagnostics health oracle
        try:
            import json as _json
            from db.db_helper import db_connection as _bs_db
            with _bs_db() as _bs_conn:
                _diag_row = _bs_conn.execute(
                    "SELECT value FROM system_state WHERE key = 'diagnostics_health'"
                ).fetchone()
                if _diag_row:
                    _diag = _json.loads(_diag_row[0]) if isinstance(_diag_row[0], str) else _diag_row[0]
                    if _diag.get('overall_status') == 'FAIL':
                        for _failing in _diag.get('failing_checks', []):
                            logger.warning("[BRAINSTEM] Diagnostic FAIL: %s", _failing)
                    elif _diag.get('overall_status') == 'WARN':
                        if _diag.get('warning_checks'):
                            logger.info("[BRAINSTEM] Diagnostic WARN: %s", ', '.join(_diag['warning_checks']))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Motor: Thread restart
    # ------------------------------------------------------------------

    def _restart_thread(self, thread_name):
        """
        Attempt to restart a registered thread.

        Uses the launcher callable if registered; otherwise logs failure.
        """
        with self._lock:
            info = self._heartbeats.get(thread_name)

        if not info:
            logger.warning("[BRAINSTEM] Cannot restart '%s' — not registered", thread_name)
            return

        launcher = info.get("launcher")
        if not launcher:
            logger.warning(
                "[BRAINSTEM] Cannot restart '%s' — no launcher registered",
                thread_name
            )
            return

        # Guard: never restart a thread that is still alive — it's just slow, not dead.
        # Launching a duplicate creates thread explosion (both old + new run concurrently).
        existing_thread = info.get("thread_ref")
        if existing_thread and isinstance(existing_thread, threading.Thread) and existing_thread.is_alive():
            logger.warning(
                "[BRAINSTEM] ⏳ Thread '%s' is still alive (just slow) — skipping restart",
                thread_name
            )
            # Reset last_seen so the alert doesn't fire again for another full window
            with self._lock:
                self._heartbeats[thread_name]["last_seen"] = time.time()
            return

        try:
            logger.info("[BRAINSTEM] 🔄 Restarting thread '%s'...", thread_name)
            new_thread = launcher()
            if new_thread and isinstance(new_thread, threading.Thread):
                with self._lock:
                    self._heartbeats[thread_name]["thread_ref"] = new_thread
                    self._heartbeats[thread_name]["last_seen"] = time.time()
                    self._heartbeats[thread_name]["status"] = "restarted"
                    self._heartbeats[thread_name]["missed_beats"] = 0
                logger.info("[BRAINSTEM] ✅ Thread '%s' restarted successfully", thread_name)
            else:
                logger.warning("[BRAINSTEM] Launcher for '%s' didn't return a thread", thread_name)
        except Exception as e:
            logger.error("[BRAINSTEM] Failed to restart '%s': %s", thread_name, e)

    def _restart_daat_thread(self):
        """Find and restart the Da'at cycle thread specifically."""
        for name in self._heartbeats:
            if "daat" in name.lower() or name == "AgentLEF_DaatCycle":
                self._restart_thread(name)
                return
        logger.warning("[BRAINSTEM] Cannot find Da'at thread to restart")

    # ------------------------------------------------------------------
    # Motor: Force wake (break stuck Sabbath)
    # ------------------------------------------------------------------

    def force_wake(self):
        """
        Break Sabbath mode if stuck.

        Resets SABBATH_MODE["active"] to False.
        """
        try:
            import main
            if hasattr(main, 'SABBATH_MODE') and main.SABBATH_MODE.get("active"):
                main.SABBATH_MODE["active"] = False
                main.SABBATH_MODE["forced_wake"] = True
                logger.warning("[BRAINSTEM] ⚡ Forced wake — Sabbath mode broken")
                self._write_consciousness_signal(
                    "Brainstem forced wake — Sabbath mode was stuck. "
                    "Resuming normal operations.",
                    category="forced_wake",
                    signal_weight=0.7,
                )
        except Exception as e:
            logger.debug("[BRAINSTEM] Force wake error: %s", e)

    # ------------------------------------------------------------------
    # Motor: Emergency pulse
    # ------------------------------------------------------------------

    def _emergency_pulse(self, reason):
        """
        Inject a high-weight signal into consciousness_feed to wake Da'at.

        This is the "smelling salts" for a silent brain.
        """
        self._write_consciousness_signal(
            f"[EMERGENCY PULSE] {reason}. Brainstem requesting immediate "
            f"Da'at cycle activation.",
            category="emergency_pulse",
            signal_weight=0.95,
        )

    # ------------------------------------------------------------------
    # Motor: Graceful degradation
    # ------------------------------------------------------------------

    def _degrade_gracefully(self, agent_name):
        """
        Mark an agent as degraded. Reduce its responsibilities.
        """
        self._degraded_agents.add(agent_name)
        logger.warning("[BRAINSTEM] 🟡 Agent '%s' marked DEGRADED", agent_name)

        self._write_consciousness_signal(
            f"Agent '{agent_name}' marked DEGRADED by Brainstem. "
            f"Reduced responsibilities. Monitoring for recovery.",
            category="agent_degraded",
            signal_weight=0.7,
        )

    # ------------------------------------------------------------------
    # Utility: Write to consciousness_feed
    # ------------------------------------------------------------------

    def _write_consciousness_signal(self, content, category="brainstem",
                                     signal_weight=0.6):
        """Write a signal to consciousness_feed for LEF's awareness."""
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO consciousness_feed "
                    "(agent_name, content, category, signal_weight) "
                    "VALUES (?, ?, ?, ?)"
                ), ("Brainstem", content, category, signal_weight))
                conn.commit()
        except Exception as e:
            logger.debug("[BRAINSTEM] consciousness_feed write error: %s", e)

    # ------------------------------------------------------------------
    # Status / monitoring
    # ------------------------------------------------------------------

    def get_status(self):
        """
        Return current Brainstem status for monitoring / The Bridge.

        Returns:
            dict with keys: running, registered_threads, degraded_agents,
                            redis_status, brain_silence_seconds, uptime
        """
        with self._lock:
            thread_statuses = {
                name: {
                    "status": info["status"],
                    "criticality": info["criticality"],
                    "last_seen_ago": round(time.time() - info["last_seen"], 1),
                    "missed_beats": info["missed_beats"],
                }
                for name, info in self._heartbeats.items()
            }

        return {
            "running": self._running,
            "registered_threads": thread_statuses,
            "degraded_agents": list(self._degraded_agents),
            "redis_down": self._redis_down_since is not None,
            "brain_silence_seconds": round(
                time.time() - self._last_brain_activity, 1
            ),
        }

    # ------------------------------------------------------------------
    # Core scan loop
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Sensory: Emergency stop monitoring (Phase 19.1e)
    # ------------------------------------------------------------------

    def _check_emergency_stop(self):
        """
        Phase 19.1e: Monitor for emergency stop signals.

        Checks Redis for  system:emergency_stop  flag and subscribes
        to  emergency:apoptosis  channel.  When triggered:
        1. Sets global Redis flag  system:emergency_stop = true
        2. Writes existential_threat to consciousness_feed (weight 1.0)
        3. Drops Architect notification in The_Bridge/Inbox
        """
        try:
            from system.redis_client import get_redis
            r = get_redis()
            if not r:
                return

            # Check if emergency stop is already active
            if r.get('system:emergency_stop') == 'true':
                # Already active — Brainstem acknowledges (first time only)
                if not getattr(self, '_emergency_stop_acked', False):
                    self._emergency_stop_acked = True
                    logger.critical(
                        "[BRAINSTEM] 🚨 EMERGENCY STOP ACTIVE — all trading halted"
                    )
                    self._write_consciousness_signal(
                        "Emergency stop is active. Portfolio drawdown exceeded "
                        "Level 4 APOPTOSIS threshold. All trading halted. "
                        "Awaiting Architect intervention.",
                        category="existential_threat",
                        signal_weight=1.0,
                    )
            else:
                # Clear ack flag when emergency is resolved
                if getattr(self, '_emergency_stop_acked', False):
                    self._emergency_stop_acked = False
                    logger.info("[BRAINSTEM] ✅ Emergency stop cleared")
                    self._write_consciousness_signal(
                        "Emergency stop has been cleared. Trading may resume.",
                        category="emergency_cleared",
                        signal_weight=0.7,
                    )
        except Exception as e:
            logger.debug("[BRAINSTEM] Emergency stop check error: %s", e)

    def _report_gap_awareness(self):
        """
        Phase 9 B4: Periodically log a summary of LEF's cognitive gap registry.
        Gives The Architect visibility into self-awareness development.
        Called every _GAP_REPORT_INTERVAL scan cycles (~30 min).
        """
        try:
            import cognitive_gaps as _cg
            s = _cg.get_gap_summary()
            if not s:
                return
            mr = s.get("most_reflected")
            nw = s.get("newest")
            mr_str = f"{mr['gap_id']} ({mr['count']} reflections)" if mr else "none"
            nw_str = f"{nw['gap_id']} (by {nw['discovered_by']})" if nw else "none"

            # Phase 50 (Task 50.7 update): Count conditioning events in last hour
            conditioning_count = 0
            try:
                from db.db_helper import db_connection as _dbc, translate_sql as _tsql
                with _dbc() as _conn:
                    _cur = _conn.cursor()
                    _cur.execute(_tsql(
                        "SELECT COUNT(*) FROM conditioning_log "
                        "WHERE conditioned_at > NOW() - INTERVAL '1 hour'"
                    ))
                    _row = _cur.fetchone()
                    conditioning_count = int(_row[0]) if _row else 0
            except Exception:
                pass  # Table may not exist yet

            logger.info(
                "[BRAINSTEM] 🧠 Cognitive Gap Registry: "
                "total=%d | open=%d exploring=%d partial=%d resolved=%d | "
                "most_reflected=%s | newest=%s | conditioning/hr=%d",
                s.get("total", 0), s.get("open", 0), s.get("exploring", 0),
                s.get("partially_resolved", 0), s.get("resolved", 0),
                mr_str, nw_str, conditioning_count
            )
        except ImportError:
            pass  # cognitive_gaps module not yet available
        except Exception as e:
            logger.debug("[BRAINSTEM] Gap awareness report failed (non-fatal): %s", e)

    def _scan(self):
        """Run a single Brainstem scan cycle."""
        self._check_heartbeats()
        self._check_brain_silence()
        self._check_agent_crashes()
        self._check_redis_health()
        self._check_system_vitals()
        self._check_emergency_stop()
        # Phase 9 B4: Periodic cognitive gap report
        self._gap_report_counter += 1
        if self._gap_report_counter >= self._GAP_REPORT_INTERVAL:
            self._gap_report_counter = 0
            self._report_gap_awareness()

    def _immortal_loop(self):
        """
        The Brainstem's main loop.

        IMMORTAL: bare except, never exits. This is the one thread
        that must never die. If the loop body fails, it logs and
        continues. There is no retry cap.
        """
        logger.info(
            "[BRAINSTEM] 🫀 Online — scanning every %ds (immortal loop)",
            self.SCAN_INTERVAL
        )

        while self._running:
            try:
                self._scan()
            except Exception as e:
                # NEVER exit. Log and continue.
                logger.error("[BRAINSTEM] Scan error (continuing): %s", e)

            # Sleep in small increments for responsive shutdown
            for _ in range(self.SCAN_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("[BRAINSTEM] 💀 Offline (clean shutdown)")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the Brainstem daemon thread."""
        with self._lock:
            if self._running:
                logger.warning("[BRAINSTEM] Already running")
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._immortal_loop,
                name="Brainstem",
                daemon=True,
            )
            self._thread.start()
            logger.info("[BRAINSTEM] 🫀 Started")

    def stop(self):
        """Stop the Brainstem gracefully."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            logger.info("[BRAINSTEM] Stop requested...")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.SCAN_INTERVAL + 5)
        self._thread = None
        logger.info("[BRAINSTEM] Stopped")
