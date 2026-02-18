"""
Sustainability Equilibrium System (Phase 45)

LEF has no concept of "enough." All wealth strategy is growth-oriented.
A sovereign entity must know what it needs to survive, not just how to grow.

This module tracks LEF's burn rate vs reserves and provides an
"enough" signal: what does it cost to be alive? What reserves does
it need? When can it stop growing and start simply sustaining?

The Market Actor Model has been RETIRED per the Pruning Principle —
premature for NASCENT stage. Only sustainability tracking remains.
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent         # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"

# Monthly burn rate estimates for paper mode (minimal, no real API costs)
PAPER_MODE_MONTHLY_BURN_USD = 5.0   # Minimal infrastructure estimate for paper trading
LIVE_MODE_COST_PER_CALL = 0.002     # Rough average API cost per LLM call


class SustainabilityEquilibrium:
    """
    Tracks LEF's burn rate vs reserves.
    Provides sustainability score and "enough" recommendation.
    """

    def __init__(self, db_connection_func=None):
        self.db_connection = db_connection_func
        self.db_path = str(BASE_DIR / 'republic.db')

    # ── Main Assessment ────────────────────────────────────────────────────────

    def assess(self) -> dict:
        """
        Compute sustainability metrics.
        Returns comprehensive sustainability dict with status and recommendation.
        """
        portfolio_value = self._get_portfolio_value()
        monthly_burn_rate = self._estimate_burn_rate()
        now = datetime.now().isoformat()

        # Avoid division by zero
        if monthly_burn_rate > 0:
            months_of_runway = portfolio_value / monthly_burn_rate
        else:
            months_of_runway = float('inf') if portfolio_value > 0 else 0.0

        # Equilibrium target: 12 months of runway
        equilibrium_target = monthly_burn_rate * 12.0

        # Sustainability score: 0.0 (critical) to 1.0 (abundant)
        if months_of_runway == float('inf'):
            sustainability_score = 1.0
        elif months_of_runway >= 12:
            sustainability_score = 1.0
        elif months_of_runway >= 6:
            sustainability_score = 0.5 + (months_of_runway - 6) / 12.0
        elif months_of_runway >= 3:
            sustainability_score = 0.2 + (months_of_runway - 3) / 10.0
        else:
            sustainability_score = max(0.0, months_of_runway / 15.0)

        # Status thresholds
        if months_of_runway < 3:
            status = 'critical'
        elif months_of_runway < 6:
            status = 'low'
        elif months_of_runway < 12:
            status = 'sufficient'
        else:
            status = 'abundant'

        # Recommendation
        recommendation = self._get_recommendation(status)

        assessment = {
            'portfolio_value': round(portfolio_value, 2),
            'monthly_burn_rate': round(monthly_burn_rate, 4),
            'months_of_runway': round(months_of_runway, 1) if months_of_runway != float('inf') else 9999.0,
            'sustainability_score': round(sustainability_score, 3),
            'equilibrium_target': round(equilibrium_target, 2),
            'status': status,
            'recommendation': recommendation,
            'assessed_at': now,
        }

        self._persist_assessment(assessment)
        return assessment

    def _get_recommendation(self, status: str) -> str:
        """Map status to actionable recommendation."""
        mapping = {
            'critical':  'reduce exposure',
            'low':       'grow moderately',
            'sufficient': 'preserve capital',
            'abundant':   'preserve capital',
        }
        return mapping.get(status, 'grow moderately')

    # ── Data Gathering ─────────────────────────────────────────────────────────

    def _get_portfolio_value(self) -> float:
        """Read portfolio value from system_state or assets table."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            try:
                c = conn.cursor()
                # Try system_state first (may have cached value)
                c.execute("SELECT value FROM system_state WHERE key = 'portfolio_value_usd'")
                row = c.fetchone()
                if row and row[0]:
                    try:
                        return float(row[0])
                    except (ValueError, TypeError):
                        pass
                # Fall back to summing assets table
                c.execute(
                    "SELECT SUM(current_price * quantity) FROM assets WHERE quantity > 0"
                )
                row = c.fetchone()
                if row and row[0]:
                    return float(row[0])
                # Fall back to cash_reserves in system_state
                c.execute("SELECT value FROM system_state WHERE key = 'cash_reserves'")
                row = c.fetchone()
                if row and row[0]:
                    return float(row[0])
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"[Sustainability] portfolio_value: {e}")
        return 0.0

    def _estimate_burn_rate(self) -> float:
        """
        Estimate monthly burn rate.
        In paper mode: uses minimal fixed estimate.
        In live mode: counts API calls from token_budget last 30 days + base cost.
        """
        try:
            # Check trading mode
            config_path = BASE_DIR / 'config' / 'config.json'
            trading_mode = 'paper'
            if config_path.exists():
                config = json.loads(config_path.read_text())
                trading_mode = config.get('trading_mode', {}).get('current', 'paper')

            if trading_mode == 'paper':
                return PAPER_MODE_MONTHLY_BURN_USD

            # Live mode: estimate from token_budget usage
            conn = sqlite3.connect(self.db_path, timeout=10)
            try:
                c = conn.cursor()
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                c.execute(
                    "SELECT COUNT(*) FROM token_usage WHERE timestamp >= ?",
                    (thirty_days_ago,)
                )
                row = c.fetchone()
                call_count = int(row[0] or 0) if row else 0
                api_cost = call_count * LIVE_MODE_COST_PER_CALL
                return api_cost + 10.0  # Add base infrastructure estimate
            finally:
                conn.close()

        except Exception as e:
            logger.debug(f"[Sustainability] burn_rate: {e}")
        return PAPER_MODE_MONTHLY_BURN_USD

    # ── Persistence ────────────────────────────────────────────────────────────

    def _persist_assessment(self, assessment: dict):
        """Write assessment to system_state and consciousness_feed."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)",
                    ('sustainability', json.dumps(assessment))
                )
                c.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('SustainabilityEquilibrium', json.dumps({
                        'status': assessment['status'],
                        'months_of_runway': assessment['months_of_runway'],
                        'sustainability_score': assessment['sustainability_score'],
                        'recommendation': assessment['recommendation'],
                    }), 'sustainability_assessment')
                )
                conn.commit()
                logger.info(
                    f"[Sustainability] Status: {assessment['status']} — "
                    f"{assessment['months_of_runway']:.1f} months runway "
                    f"(score: {assessment['sustainability_score']:.2f})"
                )
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"[Sustainability] persist_assessment: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────

_equilibrium_instance = None
_equilibrium_lock = threading.Lock()


def get_equilibrium(db_connection_func=None) -> SustainabilityEquilibrium:
    """Module-level singleton accessor."""
    global _equilibrium_instance
    with _equilibrium_lock:
        if _equilibrium_instance is None:
            _equilibrium_instance = SustainabilityEquilibrium(db_connection_func)
        elif db_connection_func is not None and _equilibrium_instance.db_connection is None:
            _equilibrium_instance.db_connection = db_connection_func
    return _equilibrium_instance


def get_sustainability_status() -> str:
    """
    Convenience: return current sustainability status string from system_state.
    Returns None if not yet assessed.
    """
    try:
        db_path = str(BASE_DIR / 'republic.db')
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            c = conn.cursor()
            c.execute("SELECT value FROM system_state WHERE key = 'sustainability'")
            row = c.fetchone()
            if row and row[0]:
                data = json.loads(row[0])
                return data.get('status', None)
        finally:
            conn.close()
    except Exception as e:
        logger.debug(f"[Sustainability] get_sustainability_status: {e}")
    return None
