
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger("LEF.RiskEngine")


class RiskEngine:
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            # Default path resolution
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'republic.db')
        
        self._pool = None
            
        # Risk Constants
        self.STARTING_CAPITAL = 10000.0
        self.PROFIT_TARGET_THRESHOLD = 15000.0 # Start harvesting above $15k
        self.MAX_DRAWDOWN_THRESHOLD = 8000.0   # Stop trading below $8k

        # Phase 37: Model loading for trade evaluation (TLS-09/TLS-10)
        self._model = None
        self._model_version = None
        self._model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'risk_v1'
        )

    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool

    def _get_conn(self):
        """Get a connection from the pool or fallback to direct connect."""
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=30.0), pool
        else:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=30.0), None

    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()
        
    def evaluate_portfolio_health(self):
        """
        Global Health Check.
        Returns: status (str), reason (str), action_items (list)
        """
        total_value = self._calculate_total_equity()
        
        status = "HEALTHY"
        action = "NONE"
        reason = f"Equity: ${total_value:,.2f}"
        
        # 1. Check for Massive Gains (Force Harvest)
        if total_value > self.PROFIT_TARGET_THRESHOLD:
            surplus = total_value - self.STARTING_CAPITAL
            status = "EUPHORIA"
            action = "FORCE_HARVEST"
            reason = f"Portfolio ATH (${total_value:,.2f}). Surplus: ${surplus:,.2f}. Harvest time."
            
        # 2. Check for Critical Drawdown
        elif total_value < self.MAX_DRAWDOWN_THRESHOLD:
            status = "CRITICAL"
            action = "DEFENSIVE_HALT"
            reason = f"Portfolio Drawdown Reached (${total_value:,.2f}). Halting Buys."
            
        return {
            "status": status,
            "action": action,
            "reason": reason,
            "equity": total_value
        }
        
    def _calculate_total_equity(self):
        """
        Calculates realistic liquidation value of portfolio.
        """
        conn, pool = self._get_conn()
        try:
            c = conn.cursor()
            
            # 1. Cash
            try:
                c.execute("SELECT sum(balance) FROM stablecoin_buckets")
                row = c.fetchone()
                if row is None or row[0] is None:
                    logging.error("[RiskEngine] Treasury rows missing — no stablecoin buckets found")
                    cash = 0.0  # Fail-closed: no trading if no treasury
                else:
                    cash = float(row[0])
            except Exception as e:
                logging.error(f"[RiskEngine] Cash query failed (assuming $0): {e}")
                cash = 0.0  # Fail-closed: no trading if cash unknown
                
            # 2. Assets (using value_usd which is updated by Sentinel/Master)
            c.execute("SELECT sum(value_usd) FROM assets WHERE quantity > 0")
            row = c.fetchone()
            assets_val = row[0] if row and row[0] else 0.0
            
            return cash + assets_val
        finally:
            self._release_conn(conn, pool)

    def get_harvest_targets(self, amount_to_raise=1000.0):
        """
        Identifies assets to sell to raise 'amount_to_raise'.
        Strategy: Sell biggest bags first (rebalancing).
        """
        conn, pool = self._get_conn()
        try:
            c = conn.cursor()
            
            c.execute("SELECT symbol, quantity, value_usd FROM assets WHERE quantity > 0 ORDER BY value_usd DESC")
            holdings = c.fetchall()
            
            targets = []
            raised_so_far = 0.0
            
            for symbol, qty, val_usd in holdings:
                if raised_so_far >= amount_to_raise:
                    break
                    
                # Don't sell everything, just trim
                # Max trim per asset = 30% of position size
                trim_usd = val_usd * 0.30 
                
                # Or if we need less than that, take what we need
                needed = amount_to_raise - raised_so_far
                sell_usd = min(trim_usd, needed)
                
                # Calculate quantity
                if val_usd > 0:
                    sell_qty = qty * (sell_usd / val_usd)
                    targets.append({
                        "asset": symbol,
                        "action": "SELL",
                        "amount": sell_qty, # This is quantity, not USD
                        "estimated_usd": sell_usd,
                        "reason": "Risk Engine Harvest"
                    })
                    raised_so_far += sell_usd
                    
            return targets
        finally:
            self._release_conn(conn, pool)

    # =========================================================================
    # Phase 37: Trade Evaluation Gate (TLS-09)
    # =========================================================================

    def evaluate_trade(self, trade: dict) -> dict:
        """
        Phase 37: Evaluate a trade before execution.
        Called by trade executor. Returns approval or BLOCKED status.

        Args:
            trade: dict with 'symbol', 'side' (BUY/SELL), 'quantity', 'price_usd'

        Returns:
            {'approved': bool, 'reason': str, 'risk_level': str}
        """
        symbol = trade.get('symbol', 'UNKNOWN')
        side = trade.get('side', 'BUY')
        price_usd = trade.get('price_usd', 0)

        # 1. Check portfolio health first
        health = self.evaluate_portfolio_health()
        if health['action'] == 'DEFENSIVE_HALT' and side == 'BUY':
            return {
                'approved': False,
                'reason': f"Portfolio in CRITICAL drawdown ({health['reason']}). All buys halted.",
                'risk_level': 'CRITICAL'
            }

        # 2. Single-trade size limit (max 10% of equity)
        equity = health.get('equity', 0)
        if equity > 0 and price_usd > equity * 0.10:
            return {
                'approved': False,
                'reason': f"Trade size ${price_usd:.2f} exceeds 10% of equity ${equity:.2f}.",
                'risk_level': 'HIGH'
            }

        # 3. Model-based risk check (if model loaded)
        if self._model is not None:
            try:
                prediction = self._predict_risk(trade)
                if prediction and prediction.get('risk_crash', 0) > 0.7:
                    return {
                        'approved': False,
                        'reason': f"Model predicts {prediction['risk_crash']:.0%} crash probability for {symbol}.",
                        'risk_level': 'HIGH'
                    }
            except Exception as e:
                logger.warning(f"[RiskEngine] Model prediction failed: {e}")

        return {
            'approved': True,
            'reason': f"Trade approved. Portfolio {health['status']}.",
            'risk_level': 'LOW'
        }

    def _predict_risk(self, trade: dict) -> dict:
        """Use loaded model to predict crash risk. Returns None if no model."""
        if self._model is None:
            return None
        try:
            # Model expects features: Close, volatility_24h, drawdown_24h, vol_shock
            import pandas as pd
            features = pd.DataFrame([{
                'Close': trade.get('price_usd', 0),
                'volatility_24h': trade.get('volatility', 0.02),
                'drawdown_24h': trade.get('drawdown', 0),
                'vol_shock': trade.get('vol_shock', 1.0),
            }])
            prediction = self._model.predict_proba(features)
            # prediction is a DataFrame with probability of each class
            crash_prob = float(prediction.iloc[0].get(1, 0))
            return {'risk_crash': crash_prob}
        except Exception as e:
            logger.warning(f"[RiskEngine] Prediction error: {e}")
            return None

    # =========================================================================
    # Phase 37: Model Loading & Hot-Reload (TLS-10)
    # =========================================================================

    def load_model(self):
        """Load the trained risk model from disk."""
        if not os.path.exists(self._model_path):
            logger.info("[RiskEngine] No risk model found — operating without ML predictions")
            return False
        try:
            from autogluon.tabular import TabularPredictor
            self._model = TabularPredictor.load(self._model_path)
            self._model_version = datetime.now().isoformat()
            logger.info(f"[RiskEngine] Risk model loaded from {self._model_path}")
            return True
        except ImportError:
            logger.warning("[RiskEngine] AutoGluon not installed — model predictions disabled")
            return False
        except Exception as e:
            logger.error(f"[RiskEngine] Model load failed: {e}")
            return False

    def watch_for_model_updates(self):
        """
        Phase 37: Subscribe to Redis for model update notifications (TLS-10).
        When train_risk_model publishes a new version, reload the model.
        """
        try:
            import redis
            import threading

            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.ping()

            def _watcher():
                pubsub = r.pubsub()
                pubsub.subscribe('risk_model_updated')
                logger.info("[RiskEngine] Watching for model updates on Redis")
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        logger.info(f"[RiskEngine] Model update signal received: {message['data']}")
                        self.load_model()

            thread = threading.Thread(target=_watcher, daemon=True, name="RiskEngine-ModelWatcher")
            thread.start()
        except Exception as e:
            logger.warning(f"[RiskEngine] Cannot watch for model updates: {e}")


if __name__ == "__main__":
    engine = RiskEngine()
    health = engine.evaluate_portfolio_health()
    print(json.dumps(health, indent=2))

    if health['action'] == "FORCE_HARVEST":
        print("\n[SUGGESTED TRADES]")
        from pprint import pprint
        pprint(engine.get_harvest_targets(amount_to_raise=2000))

