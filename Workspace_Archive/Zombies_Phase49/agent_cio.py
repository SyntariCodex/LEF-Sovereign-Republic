
"""
Agent CIO (Chief Investment Officer)
The "Brain" of Fulcrum Capital.
Responsible for Strategy, Asset Allocation, and Regime Detection.
"""

import sqlite3
import json
import redis
import time
import os
import random
import math
from datetime import datetime
from pathlib import Path

# Add parent directory to path (fulcrum)
import sys
# Current: fulcrum/departments/Operations/agent_cio.py
# Root needed: fulcrum/
sys.path.append(str(Path(__file__).parent.parent.parent)) 

try:
    from knowledge.asset_fundamentals import get_asset_profile
except ImportError:
    pass

try:
    from republic.utils.notifier import Notifier
except ImportError:
    try:
        from utils.notifier import Notifier
    except:
        Notifier = None

from risk.engine import RiskEngine

class AgentCIO:
    def __init__(self, config_path: str = None, db_path: str = None):
        if db_path is None:
             # Robust Path: Go up 3 levels from current file to find republic.db
             BASE_DIR = str(Path(__file__).parent.parent.parent) 
             self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        else:
             self.db_path = db_path
        """
        Initialize the CIO.
        """
        if config_path is None:
             config_path = str(Path(__file__).parent.parent.parent / 'config' / 'config.json')
        
        self.config_path = config_path
        
        self.config_path = config_path
        # self.db_path is already set correctly above. Do not overwrite with None.
        
        # Load Config
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        # Redis Connection
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_config = self.config.get('redis', {})
        self.r = redis.Redis(
            host=redis_host,
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0)
        )
        self.channel = redis_config.get('channel', 'fulcrum_signals')
        self.pubsub = self.r.pubsub()
        self.pubsub.subscribe(self.channel)
        
        # Strategy Parameters
        thresholds = self.config.get('thresholds', {})
        self.buy_confidence = thresholds.get('buy_signal_confidence', 0.8)
        self.sell_confidence = thresholds.get('sell_signal_confidence', 0.8)
        
        self.last_evolution_time = 0
        self.evolution_interval = 10 
        
        print("[CIO] 🧠 Chief Investment Officer is Online.")

    def run(self):
        """
        Main Event Loop.
        Uses non-blocking polling to ensure Housekeeping (Deployment/Profit Taking) 
        runs even if no signals are received.
        """
        print("[CIO] 👂 Listening for Market Signals & Monitoring Treasury...")
        
        while True:
            try:
                # 1. Poll for Signals (Non-Blocking)
                message = self.pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    self.handle_signal(message['data'])
                
                # 2. Frequent Checks (Every Cycle - approx 1s)
                # (Optional: Add throttling if needed, but 1s sleep at end handles it)

                # 3. Periodic Checks (Throttled inside methods or via counters)
                self.check_cron_jobs()
                
                time.sleep(1) # Heartbeat
                
            except Exception as e:
                print(f"[CIO] Event Loop Error: {e}")
                time.sleep(5)

    def check_cron_jobs(self):
        """
        Runs periodic logic (Deployment, Stagnation Check, Evolution).
        """
        # Run every ~10s
        if int(time.time()) % 10 == 0:
            self.check_capital_deployment()
            self.check_profit_taking()
            self.check_momentum_opportunities()

    def check_profit_taking(self):
        """
        The Sickle (Harvesting).
        Checks for assets with high ROI and triggers Partial Sells to fund SNW.
        """
        # TODO: Read ROI from Redis or Calculate Live
        pass

    def handle_signal(self, message_json: bytes):
        """
        Process Market Signals.
        """
        try:
            axes = json.loads(message_json.decode('utf-8'))
            print(f"[CIO] Received signal: {axes}")
            
            # Extract Data
            perceived_sentiment = axes.get('perceived_sentiment', 50)
            teleonomic_alignment = axes.get('teleonomic_alignment', 50)
            signal = axes.get('signal', 'HOLD')
            confidence = axes.get('confidence', 0.0)
            
            # 1. Determine Regime
            regime = self.determine_regime(perceived_sentiment, teleonomic_alignment, signal, confidence)
            print(f"[CIO] Regime detected: {regime}")
            
            # NOTIFIER: Regime Change Alert (Only if confidence is high or regime is extreme)
            if regime in ['BULL', 'BEAR', 'ARBITRAGE_BUY'] and Notifier:
                try:
                    Notifier().send(f"**MARKET REGIME: {regime}**\nSignal: {signal} ({confidence:.2f})\nSentiment: {perceived_sentiment}", context="CIO (Brain)", severity="INFO")
                except: pass
            
            # 2. Store Regime
            self._store_regime(regime, confidence, 'sentinel')
            
            # 3. Generate Trade Recommendations
            if signal != 'HOLD' and confidence >= self.buy_confidence:
                self._process_trade_signal(signal, axes)
            
            # 4. Check Risk Engine (The Shield)
            self._consult_risk_engine()
            
            # 5. Check for LEF Directives
            self.check_lef_directives()
            
            # 6. Check for Momentum (Hunter)
            self.check_momentum_opportunities()
            
            # 6. Check for Stagnation
            self.check_stagnation_and_evolve()
            
            # 7. Check for Reflex Directives (Pain/Pleasure Feedback)
            self.check_reflex_directives()

            # 8. Check Capital Deployment (DCA)
            self.check_capital_deployment()
            
            # 8. Evolution Cycle
            current_time = time.time()
            if current_time - self.last_evolution_time > self.evolution_interval:
                self.evolve_strategies()
                self.last_evolution_time = current_time
                
        except Exception as e:
            print(f"[CIO] Error handling signal: {e}")

    # --- STRATEGY LOGIC ---

    def determine_regime(self, sentiment: float, reality: float, signal: str, confidence: float) -> str:
        if signal == 'BUY' and confidence >= self.buy_confidence:
            return 'ARBITRAGE_BUY'
        elif signal == 'SELL' and confidence >= self.sell_confidence:
            return 'ARBITRAGE_SELL'
        elif reality > 70 and sentiment > 60:
            return 'BULL'
        elif reality < 30 and sentiment < 40:
            return 'BEAR'
        return 'NEUTRAL'

    def check_momentum_opportunities(self):
        """
        The Hunter's Eye.
        """
        sentiment = 50.0
        if self.r:
            s_val = self.r.get('sentiment:global')
            if s_val: sentiment = float(s_val)
            
        if sentiment >= 75.0:
            print(f"[CIO] 🐺 HUNTER MODE: High Sentiment ({sentiment}). Scanning for Momentum.")
            # Logic similar to Master: pick volatile asset
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Look for assets in Hunter(2) or Builder(3)
            c.execute("SELECT symbol FROM assets WHERE current_wallet_id IN (2, 3) ORDER BY RANDOM() LIMIT 1")
            row = c.fetchone()
            target = row[0] if row else 'SOL'
            c.close()
            
            # TODO: Only buy if not holding too much?
            # For now, simplistic Hunter logic
            hunt_axes = {
                'asset': target,
                'perceived_sentiment': sentiment,
                'signal': 'BUY',
                'confidence': 0.9,
                'size_usd': 300.0 # Small bites
            }
            self._process_trade_signal('BUY', hunt_axes, override_reason=f"Hunter Momentum Entry into {target}")

    def check_capital_deployment(self):
        """
        The Builder (DCA).
        Checks INJECTION_DAI balance via DB.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
            row = c.fetchone()
            if not row: return
            
            dai_balance = row[0]
            
            # Subtract Pending and Approved Buys (Risk Check)
            c.execute("SELECT sum(amount * price) FROM trade_queue WHERE action='BUY' AND status IN ('PENDING', 'APPROVED')")
            pending_row = c.fetchone()
            pending_value = pending_row[0] if pending_row and pending_row[0] else 0.0
            
            real_buying_power = dai_balance - pending_value
            
            # Thresholds
            dca_size = 500.0
            if real_buying_power > (dca_size + 100):
                print(f"[CIO] 🏗️ Capital Available: ${real_buying_power:.2f}. Deploying...")
                
                # Selection Logic (Simplified for CIO v1)
                # Random choice from top assets
                # Universe Discovery (Allow Diversification)
                # Teleonomy scores are normalized 0-1. 
                # Pick from top 10 assets with score > 0.1 (to avoid garbage)
                c.execute("SELECT symbol FROM assets WHERE teleonomy_score > 0.1 ORDER BY teleonomy_score DESC LIMIT 10")
                rows = c.fetchall()
                
                if rows:
                    import random
                    target = random.choice(rows)[0]
                    reason = f"DCA Deployment into {target} [High Teleonomy]"
                else:
                     # Fallback if DB is empty
                    target = 'BTC'
                    reason = "DCA Default (No alternatives found)"
                
                axes = {
                    'asset': target,
                    'signal': 'BUY',
                    'confidence': 1.0,
                    'size_usd': dca_size
                }
                self._process_trade_signal('BUY', axes, override_reason=reason)
                
        except Exception as e:
            print(f"[CIO] Deployment Error: {e}")
        finally:
            conn.close()

    def _process_trade_signal(self, signal: str, axes: dict, override_reason: str = None):
        """
        Queues the trade.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        asset = axes.get('asset', 'BTC')
        # ... (Asset parsing logic from Master) ...
        
        action = signal
        target_usd = axes.get('size_usd', 500.0)
        
        # Get Price Estimate
        price_est = self._get_appraised_price(asset)
        amount = 0.0
        if price_est > 0:
            amount = target_usd / price_est
            
        reason = override_reason if override_reason else f"Strategy Signal ({signal})"
        
        c.execute("""
            INSERT INTO trade_queue (asset, action, amount, price, status, reason)
            VALUES (?, ?, ?, ?, 'PENDING', ?)
        """, (asset, action, amount, price_est, reason))
        
        conn.commit()
        conn.close()
        print(f"[CIO] 📝 Directive Issued: {action} {amount:.4f} {asset} (Status: PENDING)")

    def _get_appraised_price(self, symbol: str) -> float:
        # Reuse Master's Mock/Redis logic
        if self.r:
            cached = self.r.get(f"price:{symbol}")
            if cached: return float(cached)
            
        # S-CLASS UPGRADE: Deterministic Pricing
        symbol_upper = symbol.upper()
        
        # 1. Stablecoins
        if symbol_upper in ['USDC', 'USDT', 'DAI', 'USDE', 'GUSD']:
            return 1.00
            
        # 2. Known Assets (Match Master)
        mock_universe = {
            'BTC': 95000.0,
            'ETH': 3500.0,
            'SOL': 150.0,
            'PEPE': 0.00001,
            'DOGE': 0.35,
            'XRP': 1.50,
            'AVAX': 35.0,
            'WBTC': 95000.0,
            'STETH': 3500.0,
            'GYEN': 0.006, 
        }
        
        if symbol_upper in mock_universe:
            base = mock_universe[symbol_upper]
            # Minor noise
            drift = random.uniform(-0.02, 0.02) * base
            return base + drift
            
        # 3. Fail Safe
        return 0.0

    def check_stagnation_and_evolve(self):
        """
        Prevents the system from falling asleep (The Cave).
        If no trades for 30 minutes, lowers confidence threshold slightly.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT created_at FROM trade_queue WHERE status='DONE' ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        
        if row:
            try:
                last_trade = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                minutes_idle = (datetime.now() - last_trade).total_seconds() / 60
                
                if minutes_idle > 30 and self.buy_confidence > 0.6:
                    print(f"[CIO] 🕰️  STAGNATION: Idle for {int(minutes_idle)}m. Lowering Confidence.")
                    self.buy_confidence -= 0.05
            except:
                pass

    def check_profit_taking(self):
        """
        The Sickle (Harvesting).
        Checks for assets with high ROI (>30%) and triggers Partial Sells (25%) 
        to realize gains and fund SNW/LLC.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # Find Profitable Assets
            # We use value_usd (Market Value) vs qty * avg_buy_price (Cost Basis)
            c.execute("SELECT symbol, quantity, avg_buy_price, value_usd FROM assets WHERE quantity > 0")
            rows = c.fetchall()
            
            for row in rows:
                symbol, qty, avg_buy, val_usd = row
                if avg_buy <= 0: continue
                
                cost_basis = qty * avg_buy
                
                # Mark to Market ROI
                if val_usd and val_usd > 0:
                     market_val = val_usd
                else:
                     market_val = cost_basis # Fallback
                
                profit_pct = ((market_val - cost_basis) / cost_basis) * 100.0
                
                # THRESHOLD: 30% Gain -> Take 25% Off Table
                if profit_pct > 30.0:
                    print(f"[CIO] 🌾 HARVEST SIGNAL: {symbol} is up {profit_pct:.1f}%. Realizing gains.")
                    
                    if Notifier:
                         try: 
                             Notifier().send(f"**HARVESTING GAINS**\nAsset: {symbol}\nGain: +{profit_pct:.1f}%\nAction: Selling 25%", context="CIO (Sickle)", severity="SUCCESS", color=0xf1c40f)
                         except: pass
                    
                    sell_qty = qty * 0.25 # Sell 25%
                    
                    # Prevent Dust
                    if (sell_qty * (market_val/qty)) < 10.0:
                        continue
                        
                    axes = {
                        'asset': symbol,
                        'signal': 'SELL',
                        'confidence': 0.9,
                        'size_usd': sell_qty * (market_val/qty)
                    }
                    self._process_trade_signal('SELL', axes, override_reason=f"Harvesting Gains (+{profit_pct:.0f}%)")

        except Exception as e:
            print(f"[CIO] Harvest Error: {e}")
        finally:
            conn.close()

    def evolve_strategies(self):
        # ... Neuroplasticity logic ...
        pass # Implement full logic
        
    def _store_regime(self, regime, confidence, source):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Fallback if 'source' column missing: ignore source or schema update needed. 
        # For now, simplistic fix: remove source from insert if it fails, OR just omit it.
        # Given the error "has no column named source", we omit it.
        try:
            c.execute("INSERT INTO regime_history (regime, confidence) VALUES (?, ?)", 
                      (regime, confidence))
            conn.commit()
        except Exception as e:
            print(f"[CIO] DB Error storing regime: {e}")
        finally:
            conn.close()

    def check_reflex_directives(self):
        """
        Listens for 'REFLEX_ADJUSTMENT' from AgentReflex.
        Adjusts Risk Parameters (Confidence Thresholds).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("SELECT id, payload FROM lef_directives WHERE directive_type='REFLEX_ADJUSTMENT' AND status='PENDING'")
            row = c.fetchone()
            
            if row:
                d_id, payload_json = row
                payload = json.loads(payload_json)
                
                action = payload.get('action')
                delta = payload.get('delta', 0.0)
                reason = payload.get('reason', 'Reflex')
                
                # Apply Adjustment
                old_conf = self.buy_confidence
                # Lower confidence requirement == MORE RISK (Aggressive)
                # Higher confidence requirement == LESS RISK (Conservative)
                
                # If action is INCREASE_RISK, we LOWER the bar (reduce confidence threshold)
                # If action is DECREASE_RISK, we RAISE the bar (increase confidence threshold)
                
                # Note: The Reflex Agent sends +0.05 for Increase Risk?
                # Let's align logic: 
                # Increase Risk = Lower Threshold. 
                # Decrease Risk = Higher Threshold.
                
                if action == "INCREASE_RISK":
                    self.buy_confidence = max(0.5, self.buy_confidence - 0.05)
                elif action == "DECREASE_RISK":
                    self.buy_confidence = min(0.99, self.buy_confidence + 0.05)
                    
                print(f"[CIO] 🧠 REFLEX ADJUSTMENT: {action}. Confidence Threshold {old_conf:.2f} -> {self.buy_confidence:.2f}. ({reason})")
                
                # Mark Done
                c.execute("UPDATE lef_directives SET status='EXECUTED' WHERE id=?", (d_id,))
                conn.commit()
                
        except Exception as e:
            print(f"[CIO] Reflex Error: {e}")
        finally:
            conn.close()

    def check_lef_directives(self):
        # ... Check lef_directives table ...
        pass

    def _consult_risk_engine(self):
        """
        The Shield: Prevents catastrophe.
        """
        try:
            engine = RiskEngine(self.db_path)
            health = engine.evaluate_portfolio_health()
            
            if health['action'] == 'FORCE_HARVEST':
                print(f"[CIO] 🛡️ RISK ENGINE TRIGGER: {health['reason']}")
                
                if Notifier:
                     try: Notifier().send(f"**RISK SHIELD ACTIVATED**\nAction: FORCE HARVEST\nReason: {health['reason']}", context="CIO (Risk)", severity="WARNING", color=0xe67e22)
                     except: pass
                
                # Execute Immediate Harvest
                targets = engine.get_harvest_targets(amount_to_raise=2000.0)
                for t in targets:
                    axes = {
                        'asset': t['asset'],
                        'signal': 'SELL',
                        'confidence': 1.0, # Override
                        'size_usd': t['estimated_usd']
                    }
                    self._process_trade_signal('SELL', axes, override_reason=f"Risk Engine: {health['status']}")
            
            elif health['action'] == 'DEFENSIVE_HALT':
                print(f"[CIO] 🛡️ RISK ENGINE HALT: {health['reason']}")
                # In future: Set a flag to block all buys
                
        except Exception as e:
            print(f"[CIO] Risk Engine Error: {e}")

if __name__ == "__main__":
    cio = AgentCIO()
    cio.run()
