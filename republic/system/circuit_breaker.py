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

# Phase 38.5 fix: Use db_helper for PostgreSQL compatibility
try:
    from db.db_helper import db_connection as _cb_db_connection, translate_sql as _cb_translate
    _DB_HELPER_AVAILABLE = True
except ImportError:
    _DB_HELPER_AVAILABLE = False

# Phase 19.1e: Redis for emergency stop coordination
try:
    from system.redis_client import get_redis
    _redis_available = True
except ImportError:
    _redis_available = False

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
        self._previous_level = 0  # Phase 20.2b: track level changes for Da'at signals

        # Phase 20.2b: Register Safety Da'at Node
        self._safety_daat = None
        try:
            from system.daat_node import DaatNode
            self._safety_daat = DaatNode(
                node_id='safety_daat',
                lattice_position=(2, 1, 3),  # X2 (reflective), Body One (Y=1), Z3 (existential)
                scan_interval=30
            )
            logger.info("[CircuitBreaker] 🔮 Safety Da'at Node registered at (2,1,3)")
        except Exception as e:
            logger.debug("[CircuitBreaker] Da'at node registration skipped: %s", e)

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
        _ctx_manager = None
        try:
            if _DB_HELPER_AVAILABLE:
                _ctx_manager = _cb_db_connection()
                conn = _ctx_manager.__enter__()
            else:
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

            # Phase 20.3b: Concentration-aware risk escalation
            try:
                if _redis_available:
                    r = get_redis()
                    if r:
                        # Scan for concentration keys set by PortfolioMgr (20.3a)
                        conc_keys = r.keys('portfolio:concentration:*')
                        for key in (conc_keys or []):
                            try:
                                raw = r.get(key)
                                if not raw:
                                    continue
                                conc_data = json.loads(raw)
                                conc_pct = conc_data.get('concentration_pct', 0)
                                asset = key.split(':')[-1] if ':' in key else 'UNKNOWN'

                                if conc_pct > 0.40:
                                    # Any asset >40% → automatic Level 1 minimum
                                    if level < 1:
                                        level = 1
                                        logger.info(
                                            "[CircuitBreaker] 📊 %s at %.1f%% concentration "
                                            "— auto Level 1",
                                            asset, conc_pct * 100
                                        )

                                elif conc_pct > 0.30 and drawdown < 0:
                                    # >30% AND portfolio in drawdown → escalate by +1
                                    level = min(level + 1, 4)
                                    logger.info(
                                        "[CircuitBreaker] 📊 %s at %.1f%% + drawdown %.2f%% "
                                        "— escalating to Level %d",
                                        asset, conc_pct * 100,
                                        drawdown * 100, level
                                    )
                            except (json.JSONDecodeError, TypeError):
                                continue
            except Exception as conc_err:
                logger.debug("[CircuitBreaker] Concentration check: %s", conc_err)

            health['level'] = level
            health['action'] = self.ACTIONS.get(level, 'NORMAL')

            # Phase 19.1c: Publish CB level to Redis for cross-agent coordination
            try:
                if _redis_available:
                    r = get_redis()
                    if r:
                        r.set('safety:circuit_breaker_level', str(level))
            except Exception:
                pass

            # Phase 19.1e: Emergency stop on Level 4 (APOPTOSIS)
            if level >= 4:
                # Phase 30.2: External alert on APOPTOSIS
                try:
                    from system.alerting import send_alert
                    send_alert('critical', 'APOPTOSIS — Circuit Breaker Level 4',
                               {'drawdown_pct': drawdown, 'daily_loss_usd': health['daily_loss_usd'],
                                'portfolio_value_usd': health['portfolio_value_usd']})
                except Exception:
                    pass
                self._trigger_emergency_stop(health)

            # Phase 20.2b: Publish Da'at signal on CB level change
            if level != self._previous_level and self._safety_daat:
                try:
                    # Graduated signal weight: Level 0→1=0.5, 1→2=0.7, 2→3=0.9, 3→4=1.0
                    weight_map = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.9, 4: 1.0}
                    signal = {
                        'source': 'safety_daat',
                        'event': 'circuit_breaker_level_change',
                        'old_level': self._previous_level,
                        'new_level': level,
                        'action': self.ACTIONS.get(level, 'NORMAL'),
                        'drawdown_pct': drawdown,
                        'daily_loss_usd': health['daily_loss_usd'],
                        'category': 'safety_state',
                        'signal_weight': weight_map.get(level, 0.5),
                        'x': 2, 'y': 1, 'z': 3,  # Z3 = existential
                        'z_position': 3,
                        'content': (
                            f"CircuitBreaker level changed: {self._previous_level} "
                            f"({self.ACTIONS.get(self._previous_level, 'NORMAL')}) → "
                            f"{level} ({self.ACTIONS.get(level, 'NORMAL')}). "
                            f"Drawdown: {drawdown:.2%}"
                        ),
                        'timestamp': time.time(),
                    }
                    self._safety_daat.propagate(signal)
                    self._safety_daat.publish_to_mesh(signal)
                    logger.info(
                        "[CircuitBreaker] 📡 Da'at signal: level %d → %d",
                        self._previous_level, level
                    )
                except Exception:
                    pass
                self._previous_level = level

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
            if _ctx_manager:
                try:
                    _ctx_manager.__exit__(None, None, None)
                except Exception:
                    pass
            elif conn:
                conn.close()

        self._last_health = health
        self._last_check_time = now
        return health

    def _trigger_emergency_stop(self, health):
        """
        Phase 19.1e: Fire the emergency stop reflex.

        When CircuitBreaker hits Level 4 (APOPTOSIS / -20% drawdown):
        1. Set global Redis flag  system:emergency_stop = true
        2. Publish portfolio snapshot to  emergency:apoptosis  channel
        3. Write to consciousness_feed (Brainstem also subscribes)
        4. Drop a notification in The_Bridge/Inbox for the Architect
        """
        logger.critical(
            "[CircuitBreaker] 🚨 LEVEL 4 APOPTOSIS — EMERGENCY STOP ENGAGED. "
            "Drawdown: %.2f%%, Daily Loss: $%.2f",
            health['drawdown_pct'] * 100, health['daily_loss_usd']
        )

        # 1. Redis: global stop flag + channel publish
        try:
            if _redis_available:
                r = get_redis()
                if r:
                    r.set('system:emergency_stop', 'true')
                    snapshot = json.dumps({
                        'level': health['level'],
                        'action': health['action'],
                        'drawdown_pct': health['drawdown_pct'],
                        'daily_loss_usd': health['daily_loss_usd'],
                        'portfolio_value_usd': health['portfolio_value_usd'],
                        'high_watermark_usd': health['high_watermark_usd'],
                        'triggered_at': datetime.now().isoformat(),
                    })
                    r.publish('emergency:apoptosis', snapshot)
        except Exception as e:
            logger.error("[CircuitBreaker] Redis emergency publish failed: %s", e)

        # 2. consciousness_feed: existential_threat signal
        try:
            from db.db_helper import db_connection as _dbc, translate_sql as _ts
            with _dbc() as conn:
                c = conn.cursor()
                c.execute(_ts(
                    "INSERT INTO consciousness_feed "
                    "(agent_name, content, category, signal_weight) "
                    "VALUES (?, ?, ?, ?)"
                ), ("CircuitBreaker", json.dumps({
                    'event': 'emergency_stop',
                    'drawdown_pct': health['drawdown_pct'],
                    'daily_loss_usd': health['daily_loss_usd'],
                    'message': 'Portfolio drawdown hit Level 4 APOPTOSIS. '
                               'All trading halted. Architect intervention required.',
                }), "existential_threat", 1.0))
                conn.commit()
        except Exception:
            pass

        # Phase 48.5: Emergency stop triggers contemplation, not just halt
        # Queue a Sabbath contemplation topic so rest has focused reflection
        try:
            from db.db_helper import db_connection as _sab_db, translate_sql as _sab_sql
            with _sab_db() as _sab_conn:
                _sab_c = _sab_conn.cursor()
                _sab_c.execute(_sab_sql(
                    "INSERT INTO consciousness_feed "
                    "(agent_name, content, category, signal_weight) "
                    "VALUES (?, ?, ?, ?)"
                ), ("CircuitBreaker", json.dumps({
                    'contemplation_topic': (
                        f"Why did the circuit breaker trip? "
                        f"Drawdown: {health['drawdown_pct']:.2%}, "
                        f"Daily loss: ${health['daily_loss_usd']:.2f}. "
                        f"What pattern led here? What must not be repeated?"
                    ),
                    'source': 'circuit_breaker_apoptosis',
                    'duration_minutes': 30,
                }), "sabbath_intention", 0.9))
                _sab_conn.commit()
            logger.info("[CIRCUIT_BREAKER] Sabbath contemplation topic queued for post-failure integration")
        except Exception as _sab_err:
            logger.warning("[CIRCUIT_BREAKER] Could not queue Sabbath contemplation: %s", _sab_err)

        # 3. The_Bridge/Inbox: Architect notification
        try:
            inbox_dir = BASE_DIR / 'The_Bridge' / 'Inbox'
            inbox_dir.mkdir(parents=True, exist_ok=True)
            note_path = inbox_dir / f"EMERGENCY_STOP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            note_path.write_text(
                f"🚨 EMERGENCY STOP ACTIVATED\n"
                f"Time: {datetime.now().isoformat()}\n"
                f"Drawdown: {health['drawdown_pct']:.2%}\n"
                f"Daily Loss: ${health['daily_loss_usd']:.2f}\n"
                f"Portfolio Value: ${health['portfolio_value_usd']:.2f}\n"
                f"High Watermark: ${health['high_watermark_usd']:.2f}\n"
                f"\nAll trading is halted. To resume:\n"
                f"  redis-cli DEL system:emergency_stop\n"
                f"Or restart LEF after resolving the issue.\n"
            )
        except Exception:
            pass

    def gate_trade(self, proposed_trade: dict) -> tuple:
        """
        Called BEFORE a trade is queued.
        Returns: (allowed: bool, reason: str)

        proposed_trade should have at minimum:
          'action': 'BUY' or 'SELL'
          'amount': float (USD for BUY, units for SELL)
          'asset': str (optional, for logging)
        """
        # Phase 20.1a: Brainstem heartbeat
        try:
            from system.brainstem import brainstem_heartbeat
            brainstem_heartbeat("CircuitBreaker", status="gate_trade")
        except Exception:
            pass

        health = self.check_portfolio_health()
        asset = proposed_trade.get('asset', 'UNKNOWN')
        action = proposed_trade.get('action', 'BUY')

        # Phase 19.1e: Emergency stop check — refuse ALL orders
        try:
            if _redis_available:
                r = get_redis()
                if r and r.get('system:emergency_stop') == 'true':
                    reason = "EMERGENCY STOP active — all trading halted. Architect must clear."
                    logger.warning(f"[CircuitBreaker] BLOCKED {action} {asset}: {reason}")
                    return False, reason
        except Exception:
            pass

        # Phase 19.1a: Scar-aware circuit breaking (per-asset history)
        if action == 'BUY' and asset != 'UNKNOWN':
            scar_adjustment = self._get_asset_scar_level(asset)
            if scar_adjustment >= 2:
                # 5+ scars → auto Level 2 (STOP_BUYING) for this asset
                reason = (
                    f"Scar history block: {asset} has {scar_adjustment} HIGH+ scars in 30 days. "
                    f"Auto Level 2 — no buying allowed."
                )
                logger.warning(f"[CircuitBreaker] BLOCKED BUY {asset}: {reason}")
                return False, reason
            elif scar_adjustment >= 1:
                # 3+ scars → tighten by one level (reduce size by 50%)
                original_amount = proposed_trade.get('amount', 0)
                proposed_trade['amount'] = original_amount * 0.5
                reason = (
                    f"Scar history caution: {asset} has scar history. "
                    f"Size reduced 50% (${original_amount:.2f} -> ${proposed_trade['amount']:.2f})"
                )
                logger.info(f"[CircuitBreaker] REDUCED BUY {asset}: {reason}")
                # Don't return — continue with other checks

        # Phase 19.1c: Cross-agent coordination — DEFCON 1 or 2 raises CB to Level 1 min
        try:
            if _redis_available:
                r = get_redis()
                if r:
                    defcon = r.get('safety:defcon_level') or r.get('risk_model:defcon')
                    if defcon and int(defcon) <= 2 and health['level'] < 1:
                        health['level'] = 1
                        health['action'] = self.ACTIONS[1]
                        logger.info(
                            f"[CircuitBreaker] ⚡ DEFCON {defcon} — auto-raising to Level 1"
                        )
        except Exception:
            pass

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

    def _get_asset_scar_level(self, asset: str) -> int:
        """
        Phase 19.1a: Query book_of_scars for recent HIGH+ severity entries
        on a specific asset.

        Returns:
            0: No concerning history
            1: 3+ scars in 30 days → tighten by one level
            2: 5+ scars in 30 days → auto Level 2 (STOP_BUYING for this asset)
        """
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT COUNT(*) FROM book_of_scars "
                    "WHERE asset = ? "
                    "AND severity IN ('HIGH', 'CRITICAL') "
                    "AND timestamp > NOW() - INTERVAL '30 days'"
                ), (asset,))
                row = c.fetchone()
                scar_count = int(row[0]) if row else 0

                if scar_count >= 5:
                    return 2
                elif scar_count >= 3:
                    return 1
                return 0
        except Exception as e:
            logger.debug("[CircuitBreaker] Scar query failed for %s: %s", asset, e)
            return 0

    def get_weakest_positions(self, limit=3) -> list:
        """
        For Level 3 (UNWIND): identify the weakest positions to sell first.
        Returns list of dicts: [{'asset': str, 'value_usd': float, 'pnl_pct': float}]
        """
        conn = None
        _ctx_manager = None
        try:
            if _DB_HELPER_AVAILABLE:
                _ctx_manager = _cb_db_connection()
                conn = _ctx_manager.__enter__()
            else:
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
            if _ctx_manager:
                try:
                    _ctx_manager.__exit__(None, None, None)
                except Exception:
                    pass
            elif conn:
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
