"""
Observation Loop

Monitors system health after self-modifications.
If metrics degrade beyond threshold, triggers automatic rollback.

The observation loop follows the SELF_EVOLUTION_MANUAL.md pattern:
- Threshold changes (Pattern A): 24 hours observation
- Behavior additions (Pattern B): 48 hours observation
- Structural changes (Pattern C): 1 week observation

Usage:
    from system.observation_loop import ObservationLoop
    
    loop = ObservationLoop()
    loop.start_observation(
        bill_id="BILL-2026-001",
        snapshot_id="abc123...",
        pattern="A",
        metrics=["error_count", "agent_health"]
    )
"""

import os
import json
import sqlite3
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("LEF.ObservationLoop")

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = str(BASE_DIR / "republic" / "republic.db")
OBSERVATIONS_FILE = BASE_DIR / "republic" / "system" / "active_observations.json"

# Observation durations by pattern
OBSERVATION_HOURS = {
    "A": 24,   # Threshold changes
    "B": 48,   # Behavior additions
    "C": 168,  # Structural changes (1 week)
}

# Degradation threshold for auto-rollback
DEGRADATION_THRESHOLD = 0.20  # 20% worse triggers rollback


class ObservationLoop:
    """
    Monitors system health after LEF self-modifications.
    
    Tracks metrics before and after changes, and triggers
    automatic rollback if degradation exceeds threshold.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.observations: Dict = {}
        self._load_observations()
        
    def _load_observations(self):
        """Load active observations from file."""
        try:
            if OBSERVATIONS_FILE.exists():
                with open(OBSERVATIONS_FILE, "r") as f:
                    self.observations = json.load(f)
                logger.info(f"[OBS] Loaded {len(self.observations)} active observations")
        except Exception as e:
            logger.error(f"[OBS] Failed to load observations: {e}")
            self.observations = {}
    
    def _save_observations(self):
        """Persist observations to file."""
        try:
            OBSERVATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OBSERVATIONS_FILE, "w") as f:
                json.dump(self.observations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[OBS] Failed to save observations: {e}")
    
    def start_observation(
        self,
        bill_id: str,
        snapshot_id: str,
        pattern: str = "A",
        metrics: List[str] = None,
        config_key: str = ""
    ) -> bool:
        """
        Start observing system health after a change.

        Args:
            bill_id: The bill that triggered the change
            snapshot_id: Git commit to rollback to if needed
            pattern: 'A' (threshold), 'B' (behavior), or 'C' (structural)
            metrics: List of metrics to monitor (defaults to all)
            config_key: Phase 46.5 — what config key was changed (for rollback learning)

        Returns:
            True if observation started
        """
        if metrics is None:
            metrics = ["error_count", "agent_health", "uptime"]

        duration_hours = OBSERVATION_HOURS.get(pattern, 24)

        # Capture baseline metrics
        baseline = self._capture_metrics(metrics)

        observation = {
            "bill_id": bill_id,
            "snapshot_id": snapshot_id,
            "pattern": pattern,
            "started_at": datetime.now().isoformat(),
            "ends_at": (datetime.now() + timedelta(hours=duration_hours)).isoformat(),
            "duration_hours": duration_hours,
            "baseline": baseline,
            "current": baseline,
            "status": "ACTIVE",
            "checks": 0,
            "max_degradation": 0.0,
            "config_key": config_key  # Phase 46.5: track what was changed
        }

        self.observations[bill_id] = observation
        self._save_observations()
        
        logger.info(
            f"[OBS] 🔍 Started observation for {bill_id} "
            f"(Pattern {pattern}, {duration_hours}h)"
        )
        
        return True
    
    def check_observations(self) -> List[dict]:
        """
        Check all active observations for degradation.
        
        Returns:
            List of observations that need attention
        """
        alerts = []
        now = datetime.now()
        
        for bill_id, obs in list(self.observations.items()):
            if obs["status"] != "ACTIVE":
                continue
                
            ends_at = datetime.fromisoformat(obs["ends_at"])
            
            # Check if observation period ended
            if now >= ends_at:
                obs["status"] = "COMPLETED"
                logger.info(f"[OBS] ✅ Observation completed for {bill_id}")
                self._save_observations()
                continue
            
            # Capture current metrics
            metrics = list(obs["baseline"].keys())
            current = self._capture_metrics(metrics)
            obs["current"] = current
            obs["checks"] += 1
            
            # Calculate degradation
            degradation = self._calculate_degradation(obs["baseline"], current)
            obs["max_degradation"] = max(obs["max_degradation"], degradation)
            
            if degradation > DEGRADATION_THRESHOLD:
                logger.warning(
                    f"[OBS] ⚠️ DEGRADATION DETECTED for {bill_id}: "
                    f"{degradation:.1%} (threshold: {DEGRADATION_THRESHOLD:.0%})"
                )
                alerts.append({
                    "bill_id": bill_id,
                    "degradation": degradation,
                    "snapshot_id": obs["snapshot_id"],
                    "action": "ROLLBACK_RECOMMENDED"
                })
                obs["status"] = "DEGRADED"
            
            self._save_observations()
            
        return alerts
    
    def trigger_rollback(self, bill_id: str) -> bool:
        """
        Trigger rollback for a specific bill.
        
        Args:
            bill_id: The bill to rollback
            
        Returns:
            True if rollback successful
        """
        obs = self.observations.get(bill_id)
        if not obs:
            logger.error(f"[OBS] No observation found for {bill_id}")
            return False
            
        snapshot_id = obs.get("snapshot_id")
        if not snapshot_id:
            logger.error(f"[OBS] No snapshot ID for {bill_id}")
            return False
        
        # Import here to avoid circular imports
        from system.git_safety import GitSafety
        
        git = GitSafety()
        if git.rollback_to_snapshot(snapshot_id):
            obs["status"] = "ROLLED_BACK"
            obs["rolled_back_at"] = datetime.now().isoformat()
            self._save_observations()
            
            logger.warning(f"[OBS] 🔙 ROLLBACK executed for {bill_id}")
            return True
            
        return False
    
    def get_rolled_back_changes(self, lookback_days: int = 30) -> list:
        """
        Phase 46.2: Return list of changes that were rolled back due to degradation.
        Used by EvolutionEngine to avoid re-proposing failed changes.
        """
        rolled_back = []
        for bill_id, obs in self.observations.items():
            if obs.get('status') == 'ROLLED_BACK':
                rolled_back.append({
                    'bill_id': bill_id,
                    'config_key': obs.get('config_key', ''),
                    'rolled_back_at': obs.get('rolled_back_at', ''),
                    'max_degradation': obs.get('max_degradation', 0),
                    'pattern': obs.get('pattern', '')
                })
        return rolled_back

    def _capture_metrics(self, metrics: List[str]) -> Dict:
        """Capture current values for specified metrics."""
        result = {}
        
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                c = conn.cursor()
                
                for metric in metrics:
                    if metric == "error_count":
                        # Count recent errors (last hour)
                        c.execute("""
                            SELECT COUNT(*) FROM lef_scars 
                            WHERE timestamp > datetime('now', '-1 hour')
                        """)
                        row = c.fetchone()
                        result["error_count"] = row[0] if row else 0
                        
                    elif metric == "agent_health":
                        # Average agent health score
                        c.execute("""
                            SELECT AVG(health_score) FROM agent_health_ledger
                            WHERE timestamp > datetime('now', '-1 hour')
                        """)
                        row = c.fetchone()
                        result["agent_health"] = row[0] if row and row[0] else 100
                        
                    elif metric == "uptime":
                        # Just record current time (for trend analysis)
                        result["uptime"] = datetime.now().isoformat()
                        
        except Exception as e:
            logger.error(f"[OBS] Failed to capture metrics: {e}")
            
        return result
    
    def _calculate_degradation(self, baseline: Dict, current: Dict) -> float:
        """
        Calculate overall degradation percentage.
        
        Returns:
            Degradation as a float (0.0 = no change, 0.2 = 20% worse)
        """
        degradation_sum = 0.0
        count = 0
        
        # Error count: higher is worse
        if "error_count" in baseline and "error_count" in current:
            base_errors = baseline["error_count"] or 1
            curr_errors = current["error_count"] or 0
            if curr_errors > base_errors:
                degradation_sum += (curr_errors - base_errors) / max(base_errors, 10)
            count += 1
        
        # Agent health: lower is worse
        if "agent_health" in baseline and "agent_health" in current:
            base_health = baseline["agent_health"] or 100
            curr_health = current["agent_health"] or 100
            if curr_health < base_health:
                degradation_sum += (base_health - curr_health) / 100
            count += 1
        
        return degradation_sum / max(count, 1)
    
    def get_active_observations(self) -> List[dict]:
        """Get all active observations."""
        return [
            {**obs, "bill_id": bid}
            for bid, obs in self.observations.items()
            if obs["status"] == "ACTIVE"
        ]
    
    def get_observation_status(self, bill_id: str) -> Optional[dict]:
        """Get status of a specific observation."""
        return self.observations.get(bill_id)


def run_observation_check():
    """One-shot check of all observations (for cron/scheduler)."""
    loop = ObservationLoop()
    alerts = loop.check_observations()
    
    for alert in alerts:
        if alert["action"] == "ROLLBACK_RECOMMENDED":
            logger.warning(f"[OBS] Rollback recommended for {alert['bill_id']}")
            # Phase 18.6a: Auto-rollback when degradation > 20% (lowered from 50%)
            if alert["degradation"] > DEGRADATION_THRESHOLD:
                logger.warning(f"[OBS] Auto-rollback triggered for {alert['bill_id']} ({alert['degradation']:.1%})")
                loop.trigger_rollback(alert["bill_id"])
                # Write to consciousness_feed for awareness
                try:
                    from db.db_helper import db_connection as _db, translate_sql as _ts
                    import json as _json
                    with _db() as _conn:
                        _c = _conn.cursor()
                        _c.execute(_ts(
                            "INSERT INTO consciousness_feed "
                            "(agent_name, content, category, signal_weight) "
                            "VALUES (?, ?, ?, ?)"
                        ), (
                            "ObservationLoop",
                            _json.dumps({
                                "event": "auto_rollback",
                                "bill_id": alert["bill_id"],
                                "degradation": alert["degradation"],
                            }),
                            "system_integrity",
                            0.85,
                        ))
                        _conn.commit()
                except Exception:
                    pass
                
    return alerts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    loop = ObservationLoop()
    print(f"Active observations: {len(loop.get_active_observations())}")
    
    alerts = loop.check_observations()
    if alerts:
        print(f"⚠️ {len(alerts)} alerts detected")
        for a in alerts:
            print(f"  - {a['bill_id']}: {a['degradation']:.1%} degradation")
    else:
        print("✅ All systems nominal")
