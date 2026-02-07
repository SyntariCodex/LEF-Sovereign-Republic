"""
CircuitBreaker — Portfolio-level safety system for LEF's metabolism.
Graduated responses to losses. Sits between strategy signals and trade execution.

Levels:
  0: NORMAL — all systems go
  1: REDUCE_SIZE — position sizes cut 50%
  2: STOP_BUYING — no new BUY orders allowed
  3: UNWIND — begin selling weakest positions
  4: APOPTOSIS — hand off to existing immune system

Phase 4 Active Tasks — Task 4.1
"""

import os
import json
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # republic/

logger = logging.getLogger("LEF.CircuitBreaker")


class CircuitBreaker:
    """
    Portfolio-level safety system. Graduated responses to losses.
    Sits between strategy signals and trade execution.
    """

    # Configurable thresholds (move to config/wealth_strategy.json later — Task 4.2)
    LEVEL_1_DRAWDOWN = -0.05   # -5%: Reduce position sizes by 50%
    LEVEL_2_DRAWDOWN = -0.10   # -10%: Stop all new BUY orders
    LEVEL_3_DRAWDOWN = -0.15   # -15%: Begin unwinding positions (sell weakest)
    LEVEL_4_DRAWDOWN = -0.20   # -20%: Apoptosis (existing behavior)

    MAX_DAILY_LOSS_USD = 50.0   # Hard stop: no more trades if daily loss exceeds this
    MAX_TRADES_PER_DAY = 20     # Hard cap on trade count

    ACTIONS = {
        0: 'NORMAL',
        1: 'REDUCE_SIZE',
        2: 'STOP_BUYING',
        3: 'UNWIND',
        4: 'APOPTOSIS'
    }

    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
        self._last_health = None
        self._last_check_time = 0
        self._cache_ttl = 30  # Cache health for 30 seconds to avoid DB hammering

        # Load thresholds from config (Phase 4 — Task 4.2)
        try:
            ws_path = BASE_DIR / 'config' / 'wealth_strategy.json'
            if ws_path.exists():
                with open(ws_path, 'r') as f:
                    cb_cfg = json.load(f).get('CIRCUIT_BREAKER', {})
                    self.LEVEL_1_DRAWDOWN = cb_cfg.get('level_1_drawdown', self.LEVEL_1_DRAWDOWN)
                    self.LEVEL_2_DRAWDOWN = cb_cfg.get('level_2_drawdown', self.LEVEL_2_DRAWDOWN)
                    self.LEVEL_3_DRAWDOWN = cb_cfg.get('level_3_drawdown', self.LEVEL_3_DRAWDOWN)
                    self.LEVEL_4_DRAWDOWN = cb_cfg.get('level_4_drawdown', self.LEVEL_4_DRAWDOWN)
                    self.MAX_DAILY_LOSS_USD = cb_cfg.get('max_daily_loss_usd', self.MAX_DAILY_LOSS_USD)
                    self.MAX_TRADES_PER_DAY = cb_cfg.get('max_trades_per_day', self.MAX_TRADES_PER_DAY)

            # Also check trading_mode for stricter limits (Phase 4 — Task 4.5)
            config_path = BASE_DIR / 'config' / 'config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                    mode_cfg = cfg.get('trading_mode', {})
                    current_mode = mode_cfg.get('current', 'paper')
                    mode_settings = mode_cfg.get('modes', {}).get(current_mode, {})
                    # Use stricter of circuit breaker vs trading mode limits
                    mode_daily_loss = mode_settings.get('max_daily_loss_usd')
                    mode_daily_trades = mode_settings.get('max_daily_trades')
                    if mode_daily_loss is not None:
                        self.MAX_DAILY_LOSS_USD = min(self.MAX_DAILY_LOSS_USD, mode_daily_loss)
                    if mode_daily_trades is not None:
                        self.MAX_TRADES_PER_DAY = min(self.MAX_TRADES_PER_DAY, mode_daily_trades)
        except Exception:
            pass

    def check_portfolio_health(self) -> dict:
        """
        Reads current portfolio state from DB.
        Returns: {
            'level': 0-4,
            'drawdown_pct': float,
            'daily_loss_usd': float,
            'trades_today': int,
            'action': 'NORMAL' | 'REDUCE_SIZE' | 'STOP_BUYING' | 'UNWIND' | 'APOPTOSIS',
            'portfolio_value_usd': float,
            'high_watermark_usd': float
        }
        """
        # Use cached result if recent
        now = time.time()
        if self._last_health and (now - self._last_check_time) < self._cache_ttl:
            return self._last_health

        health = {
            'level': 0,
            'drawdown_pct': 0.0,
            'daily_loss_usd': 0.0,
            'trades_today': 0,
            'action': 'NORMAL',
            'portfolio_value_usd': 0.0,
            'high_watermark_usd': 0.0
        }

        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            # 1. Calculate current portfolio value from assets table
            cursor.execute("""
                SELECT COALESCE(SUM(value_usd), 0) FROM assets
                WHERE value_usd > 0
            """)
            portfolio_value = cursor.fetchone()[0]
            health['portfolio_value_usd'] = portfolio_value

            # Add stablecoin bucket balances
            cursor.execute("""
                SELECT COALESCE(SUM(balance), 0) FROM stablecoin_buckets
            """)
            stablecoin_value = cursor.fetchone()[0]
            total_nav = portfolio_value + stablecoin_value

            # 2. Get high watermark from system_state (or compute it)
            cursor.execute("""
                SELECT value FROM system_state WHERE key = 'portfolio_high_watermark'
            """)
            row = cursor.fetchone()
            if row:
                high_watermark = float(row[0])
            else:
                high_watermark = total_nav

            # Update high watermark if current NAV is higher
            if total_nav > high_watermark:
                high_watermark = total_nav
                # Phase 6.5: Route through WAQ
                try:
                    from db.db_writer import queue_execute
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('system_state', ['key', 'value'], 'key')
                    queue_execute(
                        cursor,
                        sql,
                        ('portfolio_high_watermark', str(high_watermark)),
                        source_agent="CircuitBreaker",
                        priority=2  # CRITICAL — safety system
                    )
                except ImportError:
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('system_state', ['key', 'value'], 'key')
                    cursor.execute(sql, ('portfolio_high_watermark', str(high_watermark)))
                    conn.commit()

            health['high_watermark_usd'] = high_watermark

            # 3. Calculate drawdown from high watermark
            if high_watermark > 0:
                drawdown = (total_nav - high_watermark) / high_watermark
            else:
                drawdown = 0.0
            health['drawdown_pct'] = drawdown

            # 4. Calculate today's realized P&L
            today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
            cursor.execute("""
                SELECT COALESCE(SUM(profit_amount), 0) FROM realized_pnl
                WHERE timestamp > ?
            """, (today_start,))
            daily_pnl = cursor.fetchone()[0]
            health['daily_loss_usd'] = abs(daily_pnl) if daily_pnl < 0 else 0.0

            # 5. Count today's trades
            cursor.execute("""
                SELECT COUNT(*) FROM trade_queue
                WHERE created_at > ? AND status IN ('APPROVED', 'DONE')
            """, (today_start,))
            health['trades_today'] = cursor.fetchone()[0]

            # 6. Determine circuit breaker level
            level = 0
            if drawdown <= self.LEVEL_4_DRAWDOWN:
                level = 4
            elif drawdown <= self.LEVEL_3_DRAWDOWN:
                level = 3
            elif drawdown <= self.LEVEL_2_DRAWDOWN:
                level = 2
            elif drawdown <= self.LEVEL_1_DRAWDOWN:
                level = 1

            # Also check hard limits
            if health['daily_loss_usd'] >= self.MAX_DAILY_LOSS_USD:
                level = max(level, 2)  # At least STOP_BUYING
            if health['trades_today'] >= self.MAX_TRADES_PER_DAY:
                level = max(level, 2)  # At least STOP_BUYING

            health['level'] = level
            health['action'] = self.ACTIONS.get(level, 'NORMAL')

            # Log if circuit breaker is active
            if level > 0:
                logger.warning(
                    f"[CircuitBreaker] Level {level} ({health['action']}): "
                    f"drawdown={drawdown:.2%}, daily_loss=${health['daily_loss_usd']:.2f}, "
                    f"trades_today={health['trades_today']}"
                )

                # Write state to system_state for monitoring
                # Phase 6.5: Route through WAQ
                try:
                    from db.db_writer import queue_execute
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('system_state', ['key', 'value'], 'key')
                    queue_execute(
                        cursor,
                        sql,
                        ('circuit_breaker_level', str(level)),
                        source_agent="CircuitBreaker",
                        priority=2  # CRITICAL — safety system
                    )
                    queue_execute(
                        cursor,
                        sql,
                        ('circuit_breaker_action', health['action']),
                        source_agent="CircuitBreaker",
                        priority=2
                    )
                except ImportError:
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('system_state', ['key', 'value'], 'key')
                    cursor.execute(sql, ('circuit_breaker_level', str(level)))
                    cursor.execute(sql, ('circuit_breaker_action', health['action']))
                    conn.commit()

        except Exception as e:
            logger.error(f"[CircuitBreaker] Health check failed: {e}")
        finally:
            if conn:
                conn.close()

        self._last_health = health
        self._last_check_time = now
        return health

    def gate_trade(self, proposed_trade: dict) -> tuple:
        """
        Called BEFORE a trade is queued.
        Returns: (allowed: bool, reason: str)

        proposed_trade should have at minimum:
          'action': 'BUY' or 'SELL'
          'amount': float (USD for BUY, units for SELL)
          'asset': str (optional, for logging)
        """
        health = self.check_portfolio_health()
        asset = proposed_trade.get('asset', 'UNKNOWN')
        action = proposed_trade.get('action', 'BUY')

        # Hard stop: daily loss limit
        if health['daily_loss_usd'] >= self.MAX_DAILY_LOSS_USD:
            reason = (
                f"Daily loss limit reached (${health['daily_loss_usd']:.2f} >= "
                f"${self.MAX_DAILY_LOSS_USD:.2f})"
            )
            logger.warning(f"[CircuitBreaker] BLOCKED {action} {asset}: {reason}")
            return False, reason

        # Hard stop: daily trade count
        if health['trades_today'] >= self.MAX_TRADES_PER_DAY:
            reason = f"Daily trade limit reached ({health['trades_today']} >= {self.MAX_TRADES_PER_DAY})"
            logger.warning(f"[CircuitBreaker] BLOCKED {action} {asset}: {reason}")
            return False, reason

        # Level 3+: Only allow SELL orders (unwinding)
        if health['level'] >= 3 and action == 'BUY':
            reason = (
                f"Circuit breaker Level {health['level']} ({health['action']}): "
                f"No new buys. Drawdown: {health['drawdown_pct']:.2%}"
            )
            logger.warning(f"[CircuitBreaker] BLOCKED BUY {asset}: {reason}")
            return False, reason

        # Level 2: Stop all new BUY orders
        if health['level'] >= 2 and action == 'BUY':
            reason = (
                f"Circuit breaker Level {health['level']} ({health['action']}): "
                f"No new buys. Drawdown: {health['drawdown_pct']:.2%}"
            )
            logger.warning(f"[CircuitBreaker] BLOCKED BUY {asset}: {reason}")
            return False, reason

        # Level 1: Reduce position size by 50%
        if health['level'] >= 1 and action == 'BUY':
            original_amount = proposed_trade.get('amount', 0)
            proposed_trade['amount'] = original_amount * 0.5
            reason = (
                f"Circuit breaker Level {health['level']} ({health['action']}): "
                f"Size reduced 50% (${original_amount:.2f} -> ${proposed_trade['amount']:.2f}). "
                f"Drawdown: {health['drawdown_pct']:.2%}"
            )
            logger.info(f"[CircuitBreaker] REDUCED BUY {asset}: {reason}")
            return True, reason

        return True, "NORMAL"

    def get_weakest_positions(self, limit=3) -> list:
        """
        For Level 3 (UNWIND): identify the weakest positions to sell first.
        Returns list of dicts: [{'asset': str, 'value_usd': float, 'pnl_pct': float}]
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            # Find positions with worst unrealized P&L
            cursor.execute("""
                SELECT symbol, value_usd, avg_buy_price, quantity,
                       CASE WHEN avg_buy_price > 0 AND quantity > 0
                            THEN ((value_usd / quantity) - avg_buy_price) / avg_buy_price
                            ELSE 0
                       END as pnl_pct
                FROM assets
                WHERE value_usd > 0 AND quantity > 0
                ORDER BY pnl_pct ASC
                LIMIT ?
            """, (limit,))

            positions = []
            for row in cursor.fetchall():
                positions.append({
                    'asset': row[0],
                    'value_usd': row[1],
                    'pnl_pct': row[4]
                })

            return positions

        except Exception as e:
            logger.error(f"[CircuitBreaker] Weakest positions query failed: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_status_summary(self) -> str:
        """Human-readable circuit breaker status for logging/monitoring."""
        health = self.check_portfolio_health()
        return (
            f"Circuit Breaker: Level {health['level']} ({health['action']}) | "
            f"Drawdown: {health['drawdown_pct']:.2%} | "
            f"Daily Loss: ${health['daily_loss_usd']:.2f} | "
            f"Trades Today: {health['trades_today']} | "
            f"NAV: ${health['portfolio_value_usd']:.2f} | "
            f"HWM: ${health['high_watermark_usd']:.2f}"
        )


# Singleton
_circuit_breaker_instance = None


def get_circuit_breaker(db_path=None) -> CircuitBreaker:
    """Get the circuit breaker singleton."""
    global _circuit_breaker_instance
    if _circuit_breaker_instance is None:
        _circuit_breaker_instance = CircuitBreaker(db_path)
    return _circuit_breaker_instance
