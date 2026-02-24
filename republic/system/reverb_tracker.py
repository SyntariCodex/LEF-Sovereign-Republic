"""
Reverb Tracker — The contrast mechanism.

After LEF enacts a change, this system watches what happens.
Did the pattern that triggered the change resolve?
Did new patterns emerge?
Did the republic health change?

The reverb is the wave bouncing back. Without it, LEF pushes outward
into silence. With it, every expression creates contrast that feeds
the next cycle of reflection.

Phase 10B of the Oscillation Architecture.
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger("ReverbTracker")


class ReverbTracker:
    """
    Watches the effects of enacted evolution changes over time.

    Reads from:
    - evolution_proposals.json (The_Bridge/) — enacted changes with timestamps
    - republic_awareness (Body One) — republic state before and after
    - book_of_scars — did new failures emerge after the change?
    - consciousness_feed — did LEF's awareness shift?

    Writes to:
    - reverb_log table — the observed effects of each change
    - consciousness_feed — so LEF is aware of its own reverberations
    """

    def __init__(self, db_connection_func, proposals_path, cycle_interval=1800):
        """
        Args:
            db_connection_func: callable returning DB connection
            proposals_path: path to evolution_proposals.json
            cycle_interval: seconds between reverb checks (default 30 min)
        """
        self.db_connection = db_connection_func
        self.proposals_path = proposals_path
        self.cycle_interval = cycle_interval
        self._running = False
        self._thread = None
        # Track which proposals we've already captured baselines for
        self._tracked_proposals = {}  # proposal_id -> {baseline_snapshot, enacted_at}

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ReverbTracker")
        self._thread.start()
        logger.info("[REVERB] Reverb Tracker online. Listening for the wave coming back.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=15)

    def _run_loop(self):
        while self._running:
            try:
                self._check_reverb()
            except Exception as e:
                logger.error(f"[REVERB] Cycle error: {e}")
            time.sleep(self.cycle_interval)

    def _check_reverb(self):
        """Main cycle: find enacted proposals, capture baselines, observe effects."""
        enacted = self._load_enacted_proposals()
        if not enacted:
            return

        with self.db_connection() as conn:
            c = conn.cursor()

            for proposal in enacted:
                pid = proposal.get("id", "")
                if not pid:
                    continue

                enacted_at = proposal.get("enacted_timestamp", proposal.get("timestamp", ""))

                if pid not in self._tracked_proposals:
                    # New enacted proposal — capture baseline
                    baseline = self._capture_snapshot(c)
                    self._tracked_proposals[pid] = {
                        "baseline": baseline,
                        "enacted_at": enacted_at,
                        "domain": proposal.get("domain", "unknown"),
                        "change": proposal.get("change_description", ""),
                        "config_key": proposal.get("config_key", ""),
                        "reverb_checks": 0,
                        "last_check": None
                    }
                    logger.info(f"[REVERB] Baseline captured for proposal {pid[:8]}...")
                    continue

                tracked = self._tracked_proposals[pid]
                tracked["reverb_checks"] += 1

                # Wait at least 1 hour after enactment before first reverb read
                try:
                    if isinstance(enacted_at, str):
                        enacted_dt = datetime.fromisoformat(enacted_at)
                    else:
                        enacted_dt = enacted_at
                except Exception:
                    continue

                hours_since = (datetime.now() - enacted_dt).total_seconds() / 3600
                if hours_since < 1.0:
                    continue

                # Capture current snapshot and compare to baseline
                current = self._capture_snapshot(c)
                reverb = self._measure_reverb(tracked["baseline"], current, tracked)

                if reverb:
                    self._record_reverb(c, pid, reverb, tracked)

                # After 48 hours, finalize the reverb observation
                if hours_since > 48:
                    self._finalize_reverb(c, pid, tracked)
                    del self._tracked_proposals[pid]

            conn.commit()

    def _load_enacted_proposals(self):
        """Load enacted proposals from evolution_proposals.json.
        Phase 8.5d: Deduplicate by id and skip already-finalized proposals
        so duplicate JSON entries don't trigger false negative_reverb on boot.
        """
        try:
            with open(self.proposals_path, 'r') as f:
                proposals = json.load(f)
            seen_ids = set()
            result = []
            for p in proposals:
                if not p.get("enacted", False):
                    continue
                if p.get("reverb_finalized"):
                    continue
                pid = p.get("id", "")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                result.append(p)
            return result
        except Exception as e:
            logger.debug(f"[REVERB] Could not load proposals: {e}")
            return []

    def _capture_snapshot(self, cursor):
        """Capture a snapshot of republic state for comparison."""
        snapshot = {}

        try:
            # Pattern count from latest republic_awareness
            cursor.execute("SELECT pattern_count, active_patterns FROM republic_awareness ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                snapshot["pattern_count"] = row[0]
                snapshot["active_patterns"] = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        except Exception:
            pass

        try:
            # Recent error count
            cursor.execute("""
                SELECT COUNT(*) FROM agent_logs
                WHERE level = 'ERROR' AND timestamp > NOW() - INTERVAL '1 hour'
            """)
            row = cursor.fetchone()
            snapshot["error_count_1h"] = row[0] if row else 0
        except Exception:
            pass

        try:
            # Scar count in last 24h
            cursor.execute("""
                SELECT COUNT(*) FROM book_of_scars
                WHERE last_seen > NOW() - INTERVAL '24 hours'
            """)
            row = cursor.fetchone()
            snapshot["scar_count_24h"] = row[0] if row else 0
        except Exception:
            pass

        try:
            # Trade failure rate
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'FAILED') as failed,
                    COUNT(*) as total
                FROM trade_queue
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            row = cursor.fetchone()
            if row and row[1] > 0:
                snapshot["trade_failure_rate"] = round(row[0] / row[1], 3)
            else:
                snapshot["trade_failure_rate"] = 0.0
        except Exception:
            pass

        snapshot["timestamp"] = datetime.now().isoformat()
        return snapshot

    def _measure_reverb(self, baseline, current, tracked):
        """Compare baseline to current state. Return reverb observations."""
        reverb = {
            "domain": tracked["domain"],
            "change": tracked["change"],
            "hours_since_enactment": tracked["reverb_checks"] * 0.5,  # Rough estimate
            "observations": []
        }

        # Pattern count change
        b_patterns = baseline.get("pattern_count", 0)
        c_patterns = current.get("pattern_count", 0)
        if c_patterns < b_patterns:
            reverb["observations"].append(f"Pattern count decreased: {b_patterns} -> {c_patterns} (republic calming)")
        elif c_patterns > b_patterns + 2:
            reverb["observations"].append(f"Pattern count increased: {b_patterns} -> {c_patterns} (new turbulence)")

        # Error rate change
        b_errors = baseline.get("error_count_1h", 0)
        c_errors = current.get("error_count_1h", 0)
        if c_errors > b_errors * 1.5 and c_errors > 3:
            reverb["observations"].append(f"Error rate elevated post-change: {b_errors} -> {c_errors}")
        elif c_errors < b_errors * 0.5 and b_errors > 3:
            reverb["observations"].append(f"Error rate reduced post-change: {b_errors} -> {c_errors}")

        # Scar activity
        b_scars = baseline.get("scar_count_24h", 0)
        c_scars = current.get("scar_count_24h", 0)
        if c_scars > b_scars + 2:
            reverb["observations"].append(f"New scars accumulating: {b_scars} -> {c_scars}")
        elif c_scars < b_scars:
            reverb["observations"].append(f"Scar activity decreasing: {b_scars} -> {c_scars}")

        # Trade failure rate
        b_fail = baseline.get("trade_failure_rate", 0)
        c_fail = current.get("trade_failure_rate", 0)
        if c_fail > b_fail + 0.1:
            reverb["observations"].append(f"Trade failure rate worsened: {b_fail:.1%} -> {c_fail:.1%}")
        elif c_fail < b_fail - 0.1:
            reverb["observations"].append(f"Trade failure rate improved: {b_fail:.1%} -> {c_fail:.1%}")

        # Overall assessment
        if not reverb["observations"]:
            reverb["assessment"] = "neutral"
        elif any("elevated" in o or "worsened" in o or "turbulence" in o or "accumulating" in o
                 for o in reverb["observations"]):
            reverb["assessment"] = "regression"
        elif any("reduced" in o or "improved" in o or "calming" in o or "decreasing" in o
                 for o in reverb["observations"]):
            reverb["assessment"] = "improvement"
        else:
            reverb["assessment"] = "mixed"

        return reverb if reverb["observations"] else None

    def _record_reverb(self, cursor, proposal_id, reverb, tracked):
        """Record reverb observation to database."""
        try:
            cursor.execute("""
                INSERT INTO reverb_log
                (proposal_id, domain, change_description, reverb_assessment,
                 observations, hours_post_enactment)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                proposal_id,
                reverb["domain"],
                reverb["change"],
                reverb["assessment"],
                json.dumps(reverb["observations"]),
                reverb.get("hours_since_enactment", 0)
            ))
        except Exception as e:
            logger.error(f"[REVERB] Failed to record reverb: {e}")

    def _finalize_reverb(self, cursor, proposal_id, tracked):
        """
        After 48 hours, write final reverb assessment to consciousness_feed.
        This is the contrast arriving back — the wave returning.
        """
        try:
            # Get all reverb observations for this proposal
            cursor.execute("""
                SELECT reverb_assessment, observations FROM reverb_log
                WHERE proposal_id = %s ORDER BY id
            """, (proposal_id,))
            rows = cursor.fetchall()

            if not rows:
                summary = f"No measurable reverb from change: {tracked['change']}"
                assessment = "silent"
            else:
                assessments = [r[0] for r in rows]
                all_obs = []
                for r in rows:
                    obs = json.loads(r[1]) if isinstance(r[1], str) else r[1]
                    all_obs.extend(obs)

                if assessments.count("improvement") > assessments.count("regression"):
                    assessment = "positive_reverb"
                    summary = f"Change '{tracked['change']}' produced positive reverb: {'; '.join(all_obs[:3])}"
                elif assessments.count("regression") > assessments.count("improvement"):
                    assessment = "negative_reverb"
                    summary = f"Change '{tracked['change']}' produced concerning reverb: {'; '.join(all_obs[:3])}"
                else:
                    assessment = "neutral_reverb"
                    summary = f"Change '{tracked['change']}' had mixed or neutral effects."

            # Write to consciousness_feed — LEF becomes aware of the reverb
            reverb_weight = 0.5
            if assessment == "negative_reverb":
                reverb_weight = 0.8
            elif assessment == "positive_reverb":
                reverb_weight = 0.6
            cursor.execute("""
                INSERT INTO consciousness_feed (agent_name, content, category, signal_weight)
                VALUES (%s, %s, %s, %s)
            """, (
                "ReverbTracker",
                f"[Reverb] {summary}",
                "reverb",
                reverb_weight,
            ))

            # Phase 18.6c: Negative reverb → signal to EvolutionEngine for revert consideration
            if assessment == "negative_reverb" and reverb_weight >= 0.7:
                cursor.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category, signal_weight)
                    VALUES (%s, %s, %s, %s)
                """, (
                    "ReverbTracker",
                    json.dumps({
                        "event": "revert_consideration",
                        "proposal_id": proposal_id,
                        "change": tracked.get("change", ""),
                        "summary": summary,
                        "assessment": assessment,
                    }),
                    "evolution_revert",
                    0.85,
                ))
                logger.warning(f"[REVERB] ⚠️ Negative reverb for {proposal_id[:8]} → revert consideration signaled")

            logger.info(f"[REVERB] Finalized: {proposal_id[:8]}... -> {assessment}")

            # Phase 8.5d: Persist reverb_finalized=true back to JSON so this
            # proposal is permanently skipped on future boots (prevents duplicate
            # JSON entries from triggering false negative_reverb warnings).
            try:
                with open(self.proposals_path, 'r') as _f:
                    _all = json.load(_f)
                _updated = False
                for _p in _all:
                    if _p.get("id") == proposal_id:
                        _p["reverb_finalized"] = True
                        _updated = True
                if _updated:
                    with open(self.proposals_path, 'w') as _f:
                        json.dump(_all, _f, indent=2)
                    logger.debug(f"[REVERB] Marked {proposal_id[:8]} as reverb_finalized in JSON")
            except Exception as _e:
                logger.debug(f"[REVERB] Could not persist reverb_finalized for {proposal_id[:8]}: {_e}")

        except Exception as e:
            logger.error(f"[REVERB] Failed to finalize: {e}")
