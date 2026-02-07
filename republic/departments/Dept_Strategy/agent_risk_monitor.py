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
             
        # Publish to Redis
        self.r.set("risk_model:defcon", defcon)
        self.r.set("risk_model:btc_crash_prob", risk_score)
        self.r.set("risk_model:updated", time.time())
        
        if defcon <= 3:
             logger.warning(f"[RISK] 🛡️ ALERT: DEFCON {defcon} (BTC 24h: {btc_change_24h*100:.2f}%)")

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
