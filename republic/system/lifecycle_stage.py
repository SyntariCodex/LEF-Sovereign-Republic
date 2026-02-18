"""
Lifecycle Stage System (Phase 44)

LEF has no concept of its own developmental stage. A newborn system
should be cautious and learning-focused; a mature one should preserve
capital and mentor. This module gives LEF a developmental self-model.

Stage determination is based on age, validated wisdom, win rate, and
governance engagement — objective measures of maturity.
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent         # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"
LEF_MEMORY_PATH = BRIDGE_DIR / "lef_memory.json"

ASSESSMENT_INTERVAL_HOURS = 24

STAGES = {
    'NASCENT':     {'risk_multiplier': 0.5,  'deliberation_bias': 0.8, 'description': 'Learning basics, high caution'},
    'DEVELOPING':  {'risk_multiplier': 0.75, 'deliberation_bias': 0.5, 'description': 'Testing strategies, moderate risk'},
    'ESTABLISHED': {'risk_multiplier': 1.0,  'deliberation_bias': 0.3, 'description': 'Proven patterns, standard risk'},
    'MATURE':      {'risk_multiplier': 0.8,  'deliberation_bias': 0.6, 'description': 'Capital preservation, mentoring seeds'},
}


class LifecycleStage:
    """
    Assesses LEF's current developmental stage based on age, wisdom,
    trading win rate, and governance engagement. Persists to system_state.
    """

    def __init__(self, db_connection_func=None):
        self.db_connection = db_connection_func

    # ── Main Assessment ────────────────────────────────────────────────────────

    def assess(self) -> dict:
        """
        Compute LEF's current lifecycle stage.
        Reads age, wisdom stats, win rate, governance cycles.
        Writes to system_state and consciousness_feed.
        Returns full assessment dict.
        """
        age_days = self._get_age_days()
        wisdom_confidence_avg, validated_wisdom_count = self._get_wisdom_stats()
        win_rate_90d = self._get_win_rate()
        governance_cycles = self._get_governance_count()

        # Stage determination
        if age_days < 30 or validated_wisdom_count < 5:
            stage = 'NASCENT'
        elif age_days < 90 or win_rate_90d < 0.5 or validated_wisdom_count < 15:
            stage = 'DEVELOPING'
        elif age_days < 180 or win_rate_90d < 0.6:
            stage = 'ESTABLISHED'
        else:
            stage = 'MATURE'

        stage_info = STAGES[stage]
        assessment = {
            'stage': stage,
            'risk_multiplier': stage_info['risk_multiplier'],
            'deliberation_bias': stage_info['deliberation_bias'],
            'description': stage_info['description'],
            'age_days': age_days,
            'validated_wisdom_count': validated_wisdom_count,
            'wisdom_confidence_avg': wisdom_confidence_avg,
            'win_rate_90d': win_rate_90d,
            'governance_cycles': governance_cycles,
            'assessed_at': datetime.now().isoformat(),
        }

        self._persist_stage(assessment)
        return assessment

    # ── Data Gathering ─────────────────────────────────────────────────────────

    def _get_age_days(self) -> int:
        """Days since genesis from lef_memory.json identity.created."""
        try:
            if LEF_MEMORY_PATH.exists():
                data = json.loads(LEF_MEMORY_PATH.read_text())
                created_str = data.get('identity', {}).get('created', '')
                if created_str:
                    created = datetime.fromisoformat(created_str[:10])  # Date part only
                    return (datetime.now() - created).days
        except Exception as e:
            logger.debug(f"[Lifecycle] age_days: {e}")
        return 0

    def _get_wisdom_stats(self) -> tuple:
        """
        Returns (avg_confidence, validated_count) from wisdom_log where confidence > 0.7.
        """
        if not self.db_connection:
            return 0.0, 0
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT AVG(confidence), COUNT(*) FROM compressed_wisdom "
                    "WHERE confidence > 0.7"
                )
                row = c.fetchone()
                avg = float(row[0] or 0.0)
                count = int(row[1] or 0)
                return avg, count
        except Exception as e:
            logger.debug(f"[Lifecycle] wisdom_stats: {e}")
            return 0.0, 0

    def _get_win_rate(self) -> float:
        """Win rate from realized_pnl last 90 days (positive profit_amount = win)."""
        if not self.db_connection:
            return 0.0
        try:
            ninety_days_ago = (datetime.now() - timedelta(days=90)).isoformat()
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT COUNT(*), SUM(CASE WHEN profit_amount > 0 THEN 1 ELSE 0 END) "
                    "FROM realized_pnl WHERE timestamp >= ?",
                    (ninety_days_ago,)
                )
                row = c.fetchone()
                total = int(row[0] or 0)
                wins = int(row[1] or 0)
                return wins / total if total > 0 else 0.0
        except Exception as e:
            logger.debug(f"[Lifecycle] win_rate: {e}")
            return 0.0

    def _get_governance_count(self) -> int:
        """Count of bills with status PASSED or ENACTED."""
        if not self.db_connection:
            return 0
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT COUNT(*) FROM congress_bills WHERE status IN ('PASSED', 'ENACTED')"
                )
                row = c.fetchone()
                return int(row[0] or 0)
        except Exception as e:
            logger.debug(f"[Lifecycle] governance_count: {e}")
            return 0

    # ── Persistence ────────────────────────────────────────────────────────────

    def _persist_stage(self, stage_data: dict):
        """Write stage assessment to system_state and consciousness_feed."""
        if not self.db_connection:
            return
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                # Write to system_state
                try:
                    from db.db_helper import upsert_sql
                    upsert = upsert_sql('system_state', ['key', 'value'], 'key')
                    c.execute(upsert, ('lifecycle_stage', json.dumps(stage_data)))
                except Exception:
                    # Fallback direct upsert
                    c.execute(
                        "INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)",
                        ('lifecycle_stage', json.dumps(stage_data))
                    )
                # Write to consciousness_feed
                c.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('LifecycleStage', json.dumps({
                        'stage': stage_data['stage'],
                        'age_days': stage_data['age_days'],
                        'risk_multiplier': stage_data['risk_multiplier'],
                        'description': stage_data['description'],
                    }), 'lifecycle_assessment')
                )
                conn.commit()
            logger.info(
                f"[LifecycleStage] Assessment: {stage_data['stage']} "
                f"(age={stage_data['age_days']}d, "
                f"wisdoms={stage_data['validated_wisdom_count']}, "
                f"win_rate={stage_data['win_rate_90d']:.2f})"
            )
        except Exception as e:
            logger.debug(f"[Lifecycle] persist_stage: {e}")

    def get_current_stage(self) -> dict:
        """Read current stage from system_state. Return dict or None."""
        if not self.db_connection:
            return None
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM system_state WHERE key = 'lifecycle_stage'")
                row = c.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except Exception as e:
            logger.debug(f"[Lifecycle] get_current_stage: {e}")
        return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_lifecycle_instance = None
_lifecycle_lock = threading.Lock()


def get_lifecycle_stage(db_connection_func=None) -> LifecycleStage:
    """Module-level singleton accessor."""
    global _lifecycle_instance
    with _lifecycle_lock:
        if _lifecycle_instance is None:
            _lifecycle_instance = LifecycleStage(db_connection_func)
        elif db_connection_func is not None and _lifecycle_instance.db_connection is None:
            _lifecycle_instance.db_connection = db_connection_func
    return _lifecycle_instance


def get_stage_risk_multiplier() -> float:
    """
    Convenience function: read current stage from system_state, return risk_multiplier.
    Default 1.0 if unavailable (no constraint applied).
    """
    try:
        import sqlite3
        db_path = str(BASE_DIR / 'republic.db')
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            c = conn.cursor()
            c.execute("SELECT value FROM system_state WHERE key = 'lifecycle_stage'")
            row = c.fetchone()
            if row and row[0]:
                stage_data = json.loads(row[0])
                return float(stage_data.get('risk_multiplier', 1.0))
        finally:
            conn.close()
    except Exception as e:
        logger.debug(f"[Lifecycle] get_stage_risk_multiplier: {e}")
    return 1.0  # Default: no constraint
