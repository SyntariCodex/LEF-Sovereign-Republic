"""
AgentRiskMonitor
Department: Dept_Strategy
Role: The Shield. 
- Audits pending orders.
- Monitors Global Volatility (DEFCON).
"""
import time
import logging
import sqlite3
import os
import sys
import json
import requests

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


# Log to main republic log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentRiskMonitor")

# Intent Listener for Motor Cortex integration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object

class AgentRiskMonitor(IntentListenerMixin):
    def __init__(self, db_path=None):
        super().__init__()
        if db_path is None:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        else:
            self.db_path = db_path
            
        # Redis - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
            if self.r:
                logger.info("[RISK] 🟢 Redis Connected.")
        except ImportError:
            try:
                import redis
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
                logger.info("[RISK] 🟢 Redis Connected.")
            except (redis.RedisError, ConnectionError):
                self.r = None
                logger.warning("[RISK] ⚠️ Redis Disconnected.")
            
        logger.info("[RISK] Risk Monitor Online.")

        # Load wealth strategy config (Phase 4 — Task 4.2)
        self.risk_config = {}
        try:
            config_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            ws_path = os.path.join(config_base, 'config', 'wealth_strategy.json')
            if os.path.exists(ws_path):
                with open(ws_path, 'r') as f:
                    ws = json.load(f)
                    self.risk_config = ws.get('RISK_MONITOR', {})
        except Exception:
            pass

        # Phase 20.2b: Previous DEFCON tracking for Da'at signal change detection
        self._previous_defcon = 5

        # Phase 20.2b: Reference Safety Da'at Node (created by CircuitBreaker)
        self._safety_daat = None
        try:
            from system.daat_node import DaatNode
            # Try to get the existing safety_daat node (registered by CircuitBreaker)
            self._safety_daat = DaatNode.get_node('safety_daat')
            if not self._safety_daat:
                # If CB hasn't registered yet, create it here (first-come registration)
                self._safety_daat = DaatNode(
                    node_id='safety_daat',
                    lattice_position=(2, 1, 3),
                    scan_interval=30
                )
            logger.info("[RISK] 🔮 Safety Da'at Node linked.")
        except Exception:
            pass

        # Motor Cortex Integration
        self.setup_intent_listener('agent_risk_monitor')
        self.start_listening()

    def handle_intent(self, intent_data):
        """
        Process ASSESS_RISK intents from Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        intent_id = intent_data.get('intent_id')
        
        logger.info(f"[RISK] 🛡️ Received intent: {intent_type} - {intent_content[:100]}")
        
        if intent_type == 'ASSESS_RISK':
            # Run risk assessment
            btc_change = self.fetch_global_pulse()
            defcon = 5
            if self.r:
                d = self.r.get("risk_model:defcon")
                if d: defcon = int(d)
            
            assessment = {
                'defcon': defcon,
                'btc_24h_change': btc_change,
                'risk_level': 'HIGH' if defcon <= 2 else 'MEDIUM' if defcon <= 3 else 'LOW'
            }
            
            self.send_feedback(intent_id, 'COMPLETE', 
                f"Risk Assessment: DEFCON {defcon}, BTC 24h: {btc_change*100:.2f}%", 
                assessment)
            
            return {'status': 'success', 'assessment': assessment}
        
        return {'status': 'unknown_intent', 'type': intent_type}

    def fetch_global_pulse(self):
        """
        The Eye of the Shield.
        Fetches BTC Price Change from Public API (Unauthenticated).
        Source: Coinbase Public API (Spot Price)
        """
        try:
            # 1. Get Spot Price
            url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
            r = requests.get(url, timeout=5)
            data = r.json()
            price = float(data['data']['amount'])
            
            # 2. Compare to Redis stored price (if available) or internal tracking
            # Ideally we want 24h change. 
            try:
                cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
                r_cg = requests.get(cg_url, timeout=5)
                if r_cg.status_code == 200:
                    cg_data = r_cg.json()
                    btc_change_24h = cg_data['bitcoin']['usd_24h_change'] / 100.0 # Convert to float
                    return btc_change_24h
            except Exception as e:
                # Fallback to Coinbase Public Spot if CoinGecko fails (Simulating change via drift if needed, or just return 0)
                # For now, just return 0 to stay safe (DEFCON 5)
                logger.warning(f"[RISK] ⚠️ CoinGecko API Fail: {e}")
                
            return 0.0 # Neural State
            
        except Exception as e:
            logger.warning(f"[RISK] ⚠️ Could not fetch External Pulse: {e}")
            return 0.0
            
            btc_change_24h = cg_data['bitcoin']['usd_24h_change'] / 100.0 # Convert to float (e.g. -5.0 -> -0.05)
            
            return btc_change_24h
            
        except Exception as e:
            logger.warning(f"[RISK] ⚠️ Could not fetch External Pulse: {e}")
            return 0.0

    def update_defcon_level(self):
        """
        Calculates DEFCON Level (1-5).
        5 = Peace (Low Volatility)
        1 = Nuclear War (Usage Market Crash)
        """
        if not self.r: return

        # 1. Fetch External Price Volatility (Independent Verification)
        btc_change_24h = self.fetch_global_pulse()
        
        # 2. Fetch Internal Panic (Veto Count)
        veto_count = self._get_recent_vetoes()
        
        # 3. Determine Level
        defcon = 5
        risk_score = 0.1
        
        # LOGIC:
        # DEFCON 1: > 10% Drop
        # DEFCON 2: > 5% Drop
        # DEFCON 3: > 2% Drop
        
        # Phase 4: DEFCON thresholds from config
        d1_drop = self.risk_config.get('defcon_1_btc_drop_pct', -0.10)
        d2_drop = self.risk_config.get('defcon_2_btc_drop_pct', -0.05)
        d2_veto = self.risk_config.get('defcon_2_veto_threshold', 5)
        d3_drop = self.risk_config.get('defcon_3_btc_drop_pct', -0.02)
        d3_veto = self.risk_config.get('defcon_3_veto_threshold', 2)

        if btc_change_24h < d1_drop:
            defcon = 1
            risk_score = 0.95
        elif btc_change_24h < d2_drop or veto_count > d2_veto:
            defcon = 2
            risk_score = 0.80
        elif btc_change_24h < d3_drop or veto_count > d3_veto:
            defcon = 3
            risk_score = 0.50
        elif btc_change_24h < 0.00:
             defcon = 4
             risk_score = 0.30
             
        # Phase 19.1b: Boost DEFCON based on chronic scar patterns
        try:
            chronic_count = self._count_chronic_scar_patterns()
            if chronic_count > 0:
                defcon_boost = min(chronic_count, 3)  # Max boost of 3 levels
                old_defcon = defcon
                defcon = max(defcon - defcon_boost, 2)  # Can't go below DEFCON 2 from scars alone
                if defcon < old_defcon:
                    logger.warning(
                        f"[RISK] 🗡️ Scar patterns boosted DEFCON: {old_defcon} → {defcon} "
                        f"({chronic_count} chronic pattern(s))"
                    )
        except Exception:
            pass

        # Phase 19.1c: Cross-agent safety — floor DEFCON at 3 if CircuitBreaker is Level 2+
        try:
            cb_level = self.r.get('safety:circuit_breaker_level')
            if cb_level and int(cb_level) >= 2:
                if defcon > 3:
                    logger.info(f"[RISK] ⚡ CB Level {cb_level} — setting DEFCON floor to 3")
                    defcon = 3
        except Exception:
            pass

        # Publish to Redis
        self.r.set("risk_model:defcon", defcon)
        self.r.set("risk_model:btc_crash_prob", risk_score)
        self.r.set("risk_model:updated", time.time())
        # Phase 19.1c: Publish DEFCON to shared safety key for CB to read
        self.r.set("safety:defcon_level", defcon)

        # Phase 20.2b: Publish Da'at signal on DEFCON change
        if defcon != self._previous_defcon and self._safety_daat:
            try:
                shift = abs(defcon - self._previous_defcon)
                # Graduated weight: shift by 1 = 0.5, shift by 2+ = 0.8, DEFCON 1 = 1.0
                if defcon == 1:
                    weight = 1.0
                elif shift >= 2:
                    weight = 0.8
                else:
                    weight = 0.5

                signal = {
                    'source': 'safety_daat',
                    'event': 'defcon_change',
                    'old_defcon': self._previous_defcon,
                    'new_defcon': defcon,
                    'shift': shift,
                    'direction': 'escalated' if defcon < self._previous_defcon else 'de-escalated',
                    'btc_24h_change': btc_change_24h,
                    'risk_score': risk_score,
                    'category': 'safety_state',
                    'signal_weight': weight,
                    'x': 2, 'y': 1, 'z': 3,  # Z3 = existential
                    'z_position': 3,
                    'content': (
                        f"DEFCON changed: {self._previous_defcon} → {defcon} "
                        f"({'escalated' if defcon < self._previous_defcon else 'de-escalated'}). "
                        f"BTC 24h: {btc_change_24h*100:.2f}%"
                    ),
                    'timestamp': time.time(),
                }
                self._safety_daat.propagate(signal)
                self._safety_daat.publish_to_mesh(signal)
                logger.info(f"[RISK] 📡 Da'at signal: DEFCON {self._previous_defcon} → {defcon}")
            except Exception:
                pass
            self._previous_defcon = defcon

        if defcon <= 3:
             logger.warning(f"[RISK] 🛡️ ALERT: DEFCON {defcon} (BTC 24h: {btc_change_24h*100:.2f}%)")

    def _count_chronic_scar_patterns(self):
        """
        Phase 19.1b: Query book_of_scars for chronic failure patterns.

        Returns the number of distinct (failure_type, asset) combinations
        with 3+ HIGH/CRITICAL scars in the last 7 days.
        """
        try:
            from db.db_helper import db_connection as _dbc, translate_sql as _ts
            with _dbc() as conn:
                c = conn.cursor()
                c.execute(_ts(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT failure_type, asset FROM book_of_scars "
                    "  WHERE severity IN ('HIGH', 'CRITICAL') "
                    "  AND timestamp > NOW() - INTERVAL '7 days' "
                    "  GROUP BY failure_type, asset "
                    "  HAVING COUNT(*) >= 3"
                    ") AS chronic_patterns"
                ))
                row = c.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            logger.debug(f"[RISK] Scar pattern query failed: {e}")
            return 0

    def _get_recent_vetoes(self):
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT count(*) FROM trade_queue WHERE status='VETOED' AND created_at > datetime('now', '-1 hour')")
                count = c.fetchone()[0]
            return count
        except sqlite3.Error:
            return 0

    def run(self):
        """
        Main Loop
        """
        while True:
            try:
                # Phase 20.1a: Brainstem heartbeat
                try:
                    from system.brainstem import brainstem_heartbeat
                    brainstem_heartbeat("AgentRiskMonitor", status="monitoring")
                except Exception:
                    pass

                self.audit_queue()
                self.update_defcon_level()
            except Exception as e:
                logger.error(f"[RISK] Audit Error: {e}")
            
            time.sleep(self.risk_config.get('audit_poll_interval_seconds', 10))

    def audit_queue(self):
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Select PENDING orders
            c.execute("SELECT id, asset, action, amount, price FROM trade_queue WHERE status='PENDING'")
            rows = c.fetchall()
            
            # Get Current DEFCON
            defcon = 5
            if self.r:
                d = self.r.get("risk_model:defcon")
                if d: defcon = int(d)
            
            for row in rows:
                order_id, asset, action, amount, price = row
                
                notional_value = amount * (price if price else 0)
                
                veto_reason = None
                
                # RULE 1: DEFCON 1/2 = NO BUYING
                if defcon <= 2 and action == 'BUY':
                    veto_reason = f"DEFCON {defcon} Active (Market Crash Protocol). ALL BUYS HALTED."

                # RULE 2: MAX ORDER SIZE (Phase 4: from config)
                max_order_size = self.risk_config.get('max_order_size_usd', 10000)
                if notional_value > max_order_size:
                    veto_reason = f"Exceeds Max Order Size (${max_order_size:,.0f}). Value: ${notional_value:.2f}"

                # RULE 3: BLACKLIST (Phase 4: from config)
                risk_assets = self.risk_config.get('blacklisted_assets', ['LUNA', 'FTT', 'UST'])
                if asset in risk_assets:
                    veto_reason = f"Asset {asset} is on High Risk Blacklist."
                
                if veto_reason:
                    self.veto_order(c, order_id, veto_reason)
                    conn.commit()

    def veto_order(self, cursor, order_id, reason):
        logger.warning(f"[RISK] 🛡️ VETOING Order #{order_id}: {reason}")
        # --- PHASE 30: USE WRITE QUEUE ---
        try:
            from db.db_writer import queue_execute
            queue_execute(cursor, "UPDATE trade_queue SET status='VETOED', reason=? WHERE id=?",
                        (f"[RISK] {reason}", order_id),
                        source_agent='AgentRiskMonitor', priority=2)
        except ImportError:
            cursor.execute("UPDATE trade_queue SET status='VETOED', reason=? WHERE id=?",
                           (f"[RISK] {reason}", order_id))
