"""
AgentPortfolioMgr (The Architect)
Department: Dept_Wealth
Role: Monitor Diversification, Risk Exposure, and Asset Health.
"""
import time
import sqlite3
import os
import logging
import redis
import json
import sys

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection, translate_sql
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
    def translate_sql(sql):
        return sql

# Scar Resonance - Memory that arises before action
try:
    from system.scar_resonance import get_resonance_engine
    SCAR_RESONANCE_AVAILABLE = True
except ImportError:
    SCAR_RESONANCE_AVAILABLE = False

# Emotional Gate - Mood influences trading decisions
try:
    from system.emotional_gate import get_emotional_gate
    EMOTIONAL_GATE_AVAILABLE = True
except ImportError:
    EMOTIONAL_GATE_AVAILABLE = False

# Trade Validator - Sanity checks to prevent overflow
try:
    from system.trade_validator import get_validator
    TRADE_VALIDATOR_AVAILABLE = True
except ImportError:
    TRADE_VALIDATOR_AVAILABLE = False


# Intent Listener for Motor Cortex integration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# FIX: BASE_DIR is 'republic/', so just 'republic.db'
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

class AgentPortfolioMgr(IntentListenerMixin):
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        logging.info("[PORTFOLIO] 🏗️  The Architect is Awake.")
        # Redis Connection (For Price Feeds) - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            # Fallback to direct connection
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
            except (redis.RedisError, ConnectionError):
                self.r = None
                logging.warning("[PORTFOLIO] ⚠️ Redis disconnected. Cannot check live prices.")
            
        # Load Wealth Strategy Config
        self.strategy_config = {}
        self.last_learning_ts = 0
        self.learning_interval = 14400 # 4 Hours
        self.load_config()

        # APOPTOSIS (Safety Switch) State
        self.nav_history = [] # list of (ts, nav)
        self.action_history = [] # list of action_strings
        self.teleonomy_score = 100.0 # Starts perfect
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_portfolio_mgr')
        self.start_listening()

    def handle_intent(self, intent_data):
        """
        Process REBALANCE/ALLOCATE/REDUCE_EXPOSURE intents from Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        
        logging.info(f"[PORTFOLIO] 📨 Received intent: {intent_type} - {intent_content}")
        
        if intent_type in ('REBALANCE', 'ALLOCATE', 'REDUCE_EXPOSURE', 'INCREASE_EXPOSURE'):
            try:
                # Log the intent and trigger a cycle
                logging.info(f"[PORTFOLIO] Triggering portfolio review: {intent_content}")
                self.run_cycle()
                return {'status': 'success', 'result': f'Portfolio review triggered: {intent_content}'}
            except Exception as e:
                return {'status': 'error', 'result': str(e)}
        else:
            return {'status': 'unhandled', 'result': f'Portfolio does not handle {intent_type} intents'}


    def _is_sandbox_mode(self):
        """Check config to determine if we're in sandbox mode."""
        try:
            config_path = os.path.join(BASE_DIR, 'config', 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('coinbase', {}).get('sandbox', True)
        except (OSError, json.JSONDecodeError):
            pass
        return True  # Default to sandbox for safety

    def load_config(self):
        try:
            config_path = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.strategy_config = json.load(f)
                logging.info(f"[PORTFOLIO] 🧠 Strategy Loaded. Scalp Target: {self.strategy_config.get('scalp_take_profit', 0.15)*100}%")
            else:
                logging.warning("[PORTFOLIO] ⚠️ Strategy Config Missing. Using Defaults.")
                self.strategy_config = {
                    "BENCHMARK": "BTC", # The Rival to Beat
                    "RISK_PROFILE": "ACCUMULATION", # Default: Risk-On
                    "DYNASTY": {
                        "allocation_pct": 0.80, # Accumulation Mode
                        "take_profit_threshold": 0.50,
                        "stop_loss_threshold": -0.20,
                        "assets": ["SOL", "BTC", "ETH", "AVAX", "DOGE"]
                    },
                    "ARENA": {
                        "allocation_pct": 0.20,
                        "take_profit_threshold": 0.03,
                        "stop_loss_threshold": -0.02,
                        "max_open_positions": 5,
                        "trade_size_usd": 50.0,
                        "assets": ["SUI", "PEPE", "WIF", "BONK"]
                    }
                }
        except Exception as e:
            logging.error(f"[PORTFOLIO] Config Load Error: {e}")
            logging.warning("[PORTFOLIO] 🔧 SELF-HEALING: Regenerating corrupted strategy file...")
            
            # FALLBACK DEFAULTS
            self.strategy_config = {
                "BENCHMARK": "BTC",
                "RISK_PROFILE": "ACCUMULATION",
                "DYNASTY": {
                    "allocation_pct": 0.80,
                    "take_profit_threshold": 0.50,
                    "stop_loss_threshold": -0.20,
                    "assets": ["SOL", "BTC", "ETH", "AVAX", "DOGE"]
                },
                "ARENA": {
                    "allocation_pct": 0.20,
                    "take_profit_threshold": 0.03,
                    "stop_loss_threshold": -0.02,
                    "assets": ["SUI", "PEPE", "WIF", "BONK"]
                },
                "LADDER_SELLS": [
                    {"threshold": 0.30, "sell_pct": 0.25},
                    {"threshold": 0.50, "sell_pct": 0.25}
                ],
                "TRAILING_STOP": {
                    "activation_threshold": 0.40, 
                    "pullback_pct": 0.10
                }
            }
            
            # Heal the File on Disk
            try:
                with open(config_path, 'w') as f:
                    json.dump(self.strategy_config, f, indent=2)
                logging.info(f"[PORTFOLIO] ✅ File Repaired: {config_path}")
            except Exception as write_err:
                 logging.error(f"[PORTFOLIO] Failed to repair file: {write_err}")



    def check_scalp_targets(self, c):
        """
        [THE REAPER]
        Enforces Profit Taking based on Strategy Type.
        - DYNASTY: Target +50% (Long Hold)
        - ARENA: Target +3% (Velocity)
        """
        if not self.r: return

        try:
            # Fetch all assets with their strategy type
            c.execute("SELECT symbol, quantity, avg_buy_price, strategy_type FROM assets WHERE quantity > 0")
            assets = c.fetchall()
            
            for sym, qty, avg_price, strat_type in assets:
                # Default to DYNASTY if null
                if not strat_type: strat_type = 'DYNASTY'
                
                # Get Config for this specific strategy
                config = self.strategy_config.get(strat_type, self.strategy_config.get('DYNASTY'))
                
                # Get Thresholds
                take_profit_pct = config.get('take_profit_threshold', 0.50)
                stop_loss_pct = config.get('stop_loss_threshold', -0.20)
                
                # Get Live Price
                current_price_str = self.r.get(f"price:{sym}")
                if not current_price_str: continue
                current_price = float(current_price_str)
                
                if avg_price <= 0: continue
                
                # Calculate PnL
                pnl_pct = (current_price - avg_price) / avg_price
                
                # 3. WEALTH 3.0: HARVEST (Ladders & Trailing)
                harvest_trig, harvest_qty, harvest_reason = self._check_ladders_and_trailing(c, sym, qty, avg_price, current_price, config)
                if harvest_trig:
                    self._generate_order(c, sym, 'SELL', current_price, 0, harvest_reason, quantity_override=harvest_qty)
                    # Optimistic update handled by AgentCoinbase, but we updated harvest_level already.
                    continue
                
                # LOGIC: TAKE PROFIT (Legacy / Target)
                if pnl_pct >= take_profit_pct:
                    # Sell 100% for Arena, Maybe 50% for Dynasty?
                    # For simplicty: Sell 100% of the position relative to the target hit?
                    # Plan said: Dynasty 50% harvest. Arena 100% sell.
                    
                    sell_ratio = 1.0
                    if strat_type == 'DYNASTY':
                        sell_ratio = 0.50 
                        reason = f"[PORTFOLIO] [DYNASTY_HARVEST] Target +{pnl_pct*100:.1f}% Hit. Selling 50%."
                    else:
                        sell_ratio = 1.0 # Velocity
                        reason = f"[PORTFOLIO] [ARENA_WIN] Velocity Target +{pnl_pct*100:.1f}% Hit. Selling 100%."
                        
                    sell_qty = qty * sell_ratio
                    
                    self._generate_order(c, sym, 'SELL', current_price, 0, reason, quantity_override=sell_qty)
                    
                    # Optimistic DB Update
                    # c.execute("UPDATE assets SET quantity = quantity - ? WHERE symbol=?", (sell_qty, sym))

                # LOGIC: ARENA TRAILING STOP (Protect Gains Early)
                # For Arena positions, use tighter trailing once in profit
                elif strat_type == 'ARENA' and pnl_pct > 0:
                    trailing_activation = config.get('trailing_stop_activation', 0.03)  # 3%
                    trailing_distance = config.get('trailing_stop_distance', 0.015)  # 1.5%
                    
                    if pnl_pct >= trailing_activation:
                        # We're in profit territory - get/update peak
                        c.execute("SELECT peak_price FROM assets WHERE symbol=?", (sym,))
                        row = c.fetchone()
                        peak_price = row[0] if row and row[0] else avg_price
                        
                        if current_price > peak_price:
                            # --- PHASE 30: USE WRITE QUEUE ---
                            try:
                                from db.db_writer import queue_execute
                                queue_execute(c, "UPDATE assets SET peak_price=? WHERE symbol=?",
                                            (current_price, sym), source_agent='AgentPortfolioMgr', priority=2)
                            except ImportError:
                                c.execute("UPDATE assets SET peak_price=? WHERE symbol=?", (current_price, sym))
                            peak_price = current_price
                        
                        # Calculate trailing stop level
                        trailing_stop_price = peak_price * (1.0 - trailing_distance)
                        
                        if current_price < trailing_stop_price:
                            final_pnl = (current_price - avg_price) / avg_price
                            reason = f"[PORTFOLIO] [ARENA_TRAILING] Dropped from peak ${peak_price:.4f}. Locking in +{final_pnl*100:.1f}% gain."
                            self._generate_order(c, sym, 'SELL', current_price, 0, reason, quantity_override=qty)
                            continue

                # LOGIC: STOP LOSS
                elif pnl_pct <= stop_loss_pct:
                    reason = f"[PORTFOLIO] [STOP_LOSS] {strat_type} limit hit ({pnl_pct*100:.1f}%). Selling 100%."
                    self._generate_order(c, sym, 'SELL', current_price, 0, reason, quantity_override=qty)

        except Exception as e:
            logging.error(f"[PORTFOLIO] Scalp Check Error: {e}")

    def _check_ladders_and_trailing(self, c, sym, qty, avg_price, current_price, config):
        """
        WEALTH 3.0: The Harvester
        Checks for:
        1. Trailing Stops (Protect Gains)
        2. Ladder Sells (Harvest Pumps)
        """
        try:
            # PnL
            pnl_pct = (current_price - avg_price) / avg_price
            
            # --- 1. TRAILING STOP ---
            trailing_conf = config.get('TRAILING_STOP')
            if trailing_conf:
                activation = trailing_conf.get('activation_threshold', 0.50)
                pullback = trailing_conf.get('pullback_pct', 0.15)
                
                # Get/Update Peak Price
                c.execute("SELECT peak_price FROM assets WHERE symbol=?", (sym,))
                row = c.fetchone()
                peak_price = row[0] if row and row[0] else 0.0
                
                if current_price > peak_price:
                    # New High - Update DB
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_execute
                        queue_execute(c, "UPDATE assets SET peak_price=? WHERE symbol=?",
                                    (current_price, sym), source_agent='AgentPortfolioMgr', priority=2)
                    except ImportError:
                        c.execute("UPDATE assets SET peak_price=? WHERE symbol=?", (current_price, sym))
                    peak_price = current_price
                    
                # Check Logic
                # Only active if we are deep in profit (activation)
                peak_pnl = (peak_price - avg_price) / avg_price
                if peak_pnl >= activation:
                    stop_price = peak_price * (1.0 - pullback)
                    if current_price < stop_price:
                        return True, qty, f"[PORTFOLIO] [TRAILING_STOP] Dropped {pullback*100}% from Peak (${peak_price:.2f}). Selling 100%."

            # --- 2. LADDER SELLS ---
            ladders = config.get('LADDER_SELLS', [])
            if ladders:
                # Get current harvest level
                c.execute("SELECT harvest_level FROM assets WHERE symbol=?", (sym,))
                row = c.fetchone()
                harvest_lvl = row[0] if row else 0
                
                for i, tier in enumerate(ladders):
                    # If we haven't harvested this tier yet
                    if i >= harvest_lvl:
                        threshold = tier.get('threshold', 0.50)
                        sell_pct = tier.get('sell_pct', 0.10)
                        
                        if pnl_pct >= threshold:
                            # TRIGGER HARVEST
                            sell_qty = qty * sell_pct
                            next_lvl = i + 1
                            # --- PHASE 30: USE WRITE QUEUE ---
                            try:
                                from db.db_writer import queue_execute
                                queue_execute(c, "UPDATE assets SET harvest_level=? WHERE symbol=?",
                                            (next_lvl, sym), source_agent='AgentPortfolioMgr', priority=2)
                            except ImportError:
                                c.execute("UPDATE assets SET harvest_level=? WHERE symbol=?", (next_lvl, sym))
                            return True, sell_qty, f"[PORTFOLIO] [LADDER_SELL] Tier {next_lvl} Hit (+{pnl_pct*100:.0f}%). Selling {sell_pct*100:.0f}%."

            return False, 0, ""
        except Exception as e:
            logging.error(f"[PORTFOLIO] Harvest Logic Error: {e}")
            return False, 0, ""

    def _heartbeat(self):
        # Phase 6.5: Route through WAQ for serialized writes
        try:
            with db_connection(self.db_path) as conn:
                timestamp = time.time()
                try:
                    from db.db_writer import queue_execute
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('agents', ['name', 'status', 'last_active', 'department'], 'name')
                    queue_execute(conn.cursor(),
                                sql,
                                ("AgentPortfolioMgr", 'ACTIVE', timestamp, 'WEALTH'),
                                source_agent='AgentPortfolioMgr', priority=0)
                except ImportError:
                    from db.db_helper import db_write_with_retry, upsert_sql
                    sql = upsert_sql('agents', ['name', 'status', 'last_active', 'department'], 'name')
                    db_write_with_retry(
                        conn,
                        sql,
                        ("AgentPortfolioMgr", 'ACTIVE', timestamp, 'WEALTH')
                    )
        except Exception as e:
            logging.error(f"[PORTFOLIO] Heartbeat failed: {e}")

    def run(self):
        """Active Loop"""
        last_run = 0
        while True:
            try:
                self._heartbeat()
                
                # Run Logic Every 60 Seconds (Fast reaction to stop losses)
                if time.time() - last_run > 60:
                    self.run_cycle()
                    last_run = time.time()
                    
                time.sleep(30) # Heartbeat every 30s
            except Exception as e:
                logging.error(f"[PORTFOLIO] Loop Error: {e}")
                time.sleep(60)

    def run_cycle(self):
        """
        Checks for Asset Concentration, Drift, and Liquidity.
        Also Executes Volatility Strategy (RSI).
        """
        self.load_config() # Hot Reload
        
        # 0A. APOPTOSIS CHECK (The Ouroboros Switch)
        self._check_apoptosis()

        # 0B. WEALTH MILESTONE CHECK (The Infinite Runway)
        self._check_wealth_milestone()

        with db_connection(self.db_path) as conn:
            c = conn.cursor()

            # 0. Adaptive Learning (The Hedge Fund Brain)
            self.adaptive_learning_loop()

            # 0.1 POST-SABBATH RECALIBRATION (Phase 20 - Consciousness Integration)
            # Query Sabbath insights from Introspector to adjust strategy
            try:
                c.execute("SELECT value FROM system_state WHERE key = 'sabbath_insight'")
                row = c.fetchone()
                if row and row[0]:
                    insight = row[0]
                    if "REDUCE_ACTIVITY" in insight:
                        # Apply conservative bias for this cycle
                        original_max = self.config.get('arena_max_position', 100)
                        self.config['arena_max_position'] = original_max * 0.5
                        logging.info(f"[PORTFOLIO] 🕯️ SABBATH BIAS: Reducing max position to {self.config['arena_max_position']:.0f} per reflection insight")

                        # Clear the insight after applying (one-time use)
                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            queue_execute(c, "DELETE FROM system_state WHERE key = 'sabbath_insight'",
                                        (), source_agent='AgentPortfolioMgr', priority=1)
                        except ImportError:
                            c.execute("DELETE FROM system_state WHERE key = 'sabbath_insight'")
                        conn.commit()
            except Exception as e:
                logging.debug(f"[PORTFOLIO] Sabbath insight check failed: {e}")

            # 0.5 Ensure Schema
            try:
                # Ensure strategy_type column exists
                backend = os.getenv('DATABASE_BACKEND', 'sqlite')
                if backend == 'postgresql':
                    c.execute(translate_sql("SELECT column_name FROM information_schema.columns WHERE table_name = ?"), ('assets',))
                    columns = [row[0] for row in c.fetchall()]
                else:
                    c.execute("PRAGMA table_info(assets)")
                    columns = [info[1] for info in c.fetchall()]
                if 'strategy_type' not in columns:
                    c.execute("ALTER TABLE assets ADD COLUMN strategy_type TEXT DEFAULT 'DYNASTY'")

                # Ensure system_metrics table exists (For Synapse/Dashboard state)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            except Exception:
                pass

            # 0.6 Ensure Wealth 3.0 Schema (Ladders & Memory)
            try:
                # Add 'peak_price' for Trailing Stops
                backend = os.getenv('DATABASE_BACKEND', 'sqlite')
                if backend == 'postgresql':
                    c.execute(translate_sql("SELECT column_name FROM information_schema.columns WHERE table_name = ?"), ('assets',))
                    columns = [row[0] for row in c.fetchall()]
                else:
                    c.execute("PRAGMA table_info(assets)")
                    columns = [info[1] for info in c.fetchall()]
                if 'peak_price' not in columns:
                    c.execute("ALTER TABLE assets ADD COLUMN peak_price REAL DEFAULT 0.0")

                if 'harvest_level' not in columns:
                    c.execute("ALTER TABLE assets ADD COLUMN harvest_level INTEGER DEFAULT 0")

                # Create Memory Table (Episodic Learning)
                c.execute("""
                    CREATE TABLE IF NOT EXISTS memory_experiences (
                        id INTEGER PRIMARY KEY,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        scenario_name TEXT,
                        market_condition TEXT,
                        action_taken TEXT,
                        outcome_pnl_pct REAL,
                        outcome_desc TEXT
                    )
                """)
                conn.commit()
            except Exception as e:
                logging.error(f"[PORTFOLIO] Schema Update Yielded: {e}")

            # 1. Check Targets (Profit Taking & Stop Loss & Ladders)
            self.check_scalp_targets(c)

            # 2. Run ARENA Strategy (Velocity / RSI / Momentum)
            self.run_arena_strategy(c)

            # 3. Check Liquidity / Rotation (Maintenance)
            self.check_liquidity_and_rotate(c)

            # 4. REVIEW SCOUT FINDINGS (The 10k Coin Expansion)
            self.evaluate_scout_findings(c)

            # Note: 'harvest_profits' is now integrated into check_scalp_targets

            # 5. Track Strategy Performance
            self.track_strategy_performance()

            conn.commit() # Commit any orders

    def evaluate_scout_findings(self, c):
        """
        [THE GENERAL]
        Reviews the 'market_universe' map created by the Scholar (Scout).
        Selects High-Volume targets to add to the ARENA strategy.
        """
        try:
            # 1. Fetch Top 20 Liquid Assets from Census
            c.execute("""
                SELECT symbol, volume_24h FROM market_universe 
                WHERE status='online' 
                AND quote_currency IN ('USD', 'USDC')
                ORDER BY volume_24h DESC 
                LIMIT 20
            """)
            candidates = c.fetchall()
            if not candidates: return

            # 2. Get Current Arena Roster
            current_arena = self.strategy_config.get('ARENA', {}).get('assets', [])
            current_set = set(current_arena)
            
            # 3. Selection Logic (The Draft)
            # We want to keep the roster fresh but stable.
            # Add top 3 candidates that aren't in roster.
            added_count = 0
            new_roster = list(current_arena)
            
            for sym, vol in candidates:
                if sym not in current_set:
                    # Found a new liquid asset
                    # Filter: Must not be a Stablecoin (DAI, USDT, USDC, PYUSD)
                    if sym in ['DAI', 'USDT', 'USDC', 'PYUSD', 'EURC']: continue
                    
                    new_roster.append(sym)
                    logging.info(f"[PORTFOLIO] 🆕 DRAFTED: {sym} (Vol: ${vol:,.0f}) added to ARENA.")
                    added_count += 1
                    if added_count >= 3: break # Draft max 3 per cycle
            
            # 4. Save Config if Changed
            if added_count > 0:
                # Cap Roster size (e.g. Max 10)
                if len(new_roster) > 20:
                    # Cut the tail (oldest?) - simplified
                    new_roster = new_roster[:20]
                    
                self.strategy_config['ARENA']['assets'] = new_roster
                
                # Write to Disk
                config_path = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')
                with open(config_path, 'w') as f:
                    json.dump(self.strategy_config, f, indent=2)
                    
        except Exception as e:
            logging.error(f"[PORTFOLIO] Scout Eval Error: {e}")

    def run_arena_strategy(self, c):
        """
        [THE ARENA]
        High-Velocity Trading Strategy.
        - Assets: Defined in 'ARENA' config.
        - Logic: RSI Oversold (<35) OR Momentum (Rising Volume).
        - Size: Dynamic (2% of liquid capital or fallback to fixed).
        """
        if not self.r: return
        
        # Get Arena Config
        arena_conf = self.strategy_config.get('ARENA', {})
        targets = arena_conf.get('assets', ['SUI', 'PEPE', 'WIF', 'BONK'])
        # Phase 4: Read from ARENA_PARAMS in wealth_strategy.json, fall back to arena_conf
        arena_params = self.strategy_config.get('ARENA_PARAMS', {})
        max_positions = arena_params.get('max_open_positions', arena_conf.get('max_open_positions', 15))

        # PHASE 10: Dynamic Trade Sizing
        # Use 2% of liquid capital, or fallback to fixed amount
        trade_size_pct = arena_params.get('trade_size_pct', arena_conf.get('trade_size_pct', 0.02))
        trade_size_fallback = arena_params.get('trade_size_usd_fallback', arena_conf.get('trade_size_usd', 25.0))
        
        # Calculate liquid capital
        try:
            c.execute("SELECT sum(balance) FROM stablecoin_buckets WHERE bucket_type IN ('INJECTION_DAI', 'SCOUT_FUND_USDC')")
            row = c.fetchone()
            liquid_capital = row[0] if row and row[0] else 0.0
            
            # SANITY CHECK: Cap liquid capital to prevent overflow from corrupted data
            risk_mgmt = self.strategy_config.get('RISK_MANAGEMENT', {})
            MAX_SANE_CAPITAL = risk_mgmt.get('max_sane_capital_usd', 1000000.0)
            if liquid_capital > MAX_SANE_CAPITAL:
                logging.warning(f"[PORTFOLIO] ⚠️ OVERFLOW DETECTED: liquid_capital={liquid_capital}. Capping to ${MAX_SANE_CAPITAL}.")
                liquid_capital = MAX_SANE_CAPITAL
            
            trade_size_usd = max(trade_size_fallback, liquid_capital * trade_size_pct)
            
            # SANITY CHECK: Cap individual trade size
            MAX_TRADE_SIZE = risk_mgmt.get('max_trade_size_usd', 10000.0)
            if trade_size_usd > MAX_TRADE_SIZE:
                trade_size_usd = MAX_TRADE_SIZE
        except (Exception, TypeError):
            trade_size_usd = trade_size_fallback

        # Check Active Positions Count
        c.execute("SELECT count(*) FROM assets WHERE strategy_type='ARENA' AND quantity > 0")
        current_arena_count = c.fetchone()[0]
        
        if current_arena_count >= max_positions:
            # logging.info("[PORTFOLIO] Arena Full. No new entries.")
            return

        # 0. GLOBAL MEMORY VETO (Prevent Spam Loop)
        # Consult the Oracle once for the entire strategy batch
        veto, reason = self._consult_memory(c, "GLOBAL")
        if veto:
             logging.warning(f"[PORTFOLIO] 🛑 ARENA HALTED: {reason}")
             return

        rsi_buy_config = arena_conf.get('rsi_buy_threshold', 35.0)
        require_trend = arena_conf.get('require_trend_confirmation', True)
        require_macd = arena_conf.get('require_macd_confirmation', True)
        
        for symbol in targets:
            # Get RSI/Price/SMA/MACD
            rsi_key = f"rsi:{symbol}"
            price_key = f"price:{symbol}"
            sma_key = f"sma:{symbol}"
            macd_key = f"macd:{symbol}"  # Expected format: "histogram,signal" or just histogram
            
            rsi_raw = self.r.get(rsi_key)
            price_raw = self.r.get(price_key)
            sma_raw = self.r.get(sma_key)
            macd_raw = self.r.get(macd_key)
            
            if not rsi_raw or not price_raw: continue
            
            rsi = float(rsi_raw)
            price = float(price_raw)
            
            # ===== CONFIRMATION CHECKS =====
            # Must pass ALL confirmation filters to enter
            
            # 1. TREND CONFIRMATION (Price > 20-day SMA)
            trend_confirmed = False
            trend_status = "UNKNOWN"
            
            if sma_raw:
                sma = float(sma_raw)
                hysteresis_buffer = 1.02  # 2% Buffer
                
                if price > (sma * hysteresis_buffer):
                    trend_status = "BULL"
                    trend_confirmed = True
                elif price > sma:
                    trend_status = "NEUTRAL"
                    trend_confirmed = False  # Don't buy in grey zone
                else:
                    trend_status = "BEAR"
                    trend_confirmed = False
            else:
                # No SMA data - skip if trend confirmation required
                if require_trend:
                    continue
                trend_confirmed = True  # Fallback if no data and not required
            
            # Skip if trend confirmation required but not in uptrend
            if require_trend and not trend_confirmed:
                continue
            
            # 2. MACD CONFIRMATION (Histogram > 0 = Bullish momentum)
            macd_confirmed = False
            
            if macd_raw:
                try:
                    # Parse MACD - could be just histogram or "histogram,signal"
                    macd_val = float(macd_raw.split(',')[0]) if ',' in macd_raw else float(macd_raw)
                    macd_confirmed = macd_val > 0
                except (ValueError, IndexError):
                    macd_confirmed = False
            else:
                # No MACD data - skip if required
                if require_macd:
                    continue
                macd_confirmed = True  # Fallback if not required
            
            # Skip if MACD confirmation required but bearish
            if require_macd and not macd_confirmed:
                continue
            
            # ===== ENTRY LOGIC (Only if confirmations pass) =====
            
            # 0. COOL DOWN CHECK
            if self._check_cool_down(c, symbol): continue

            # ENTRY SIGNAL: RSI OVERSOLD + TREND CONFIRMED + MACD CONFIRMED
            # No more blind "initiation" buys - every entry needs signals
            if rsi < rsi_buy_config:
                reason = f"ARENA: [CONFIRMED_ENTRY] RSI {rsi:.1f} + {trend_status} trend + MACD bullish"
                self._generate_order(c, symbol, 'BUY', price, trade_size_usd, reason, strategy_tag='ARENA')
                continue

            # ENTRY SIGNAL 3: MOMENTUM (Ride the Wave)
            # If Trend is BULLISH and RSI is rising (but not overheated)
            if trend_status == "BULL":
                 if rsi > 50.0 and rsi < 75.0:
                      # We are in the power zone. Add to position.
                      self._generate_order(c, symbol, 'BUY', price, trade_size_usd, f"ARENA: [MOMENTUM_RIDE] Trend is Friend (RSI {rsi:.1f}).", strategy_tag='ARENA')
                      continue
                      
            # ENTRY SIGNAL 4: QUANT INTELLIGENCE
            # (Existing logic preserved if needed, or simplified above)


    def _check_cool_down(self, c, symbol, hours=24):
        """
        Returns True if we should BLOCK buying due to recent Stop Loss.
        """
        try:
             # Check for any SELLs with [STOP_LOSS] tag in the last N hours
             query = f"""
                SELECT count(*), max(created_at) FROM trade_queue 
                WHERE asset=? 
                AND action='SELL' 
                AND reason LIKE '%STOP_LOSS%' 
                AND created_at > datetime('now', '-{hours} hours')
             """
             c.execute(query, (symbol,))
             row = c.fetchone()
             count = row[0]
             last_ts = row[1]
             
             if count > 0:
                 # logging.info(f"[PORTFOLIO] ❄️ COOL DOWN ACTIVE for {symbol}: Found {count} stop-losses. Last: {last_ts}")
                 return True
             
             return False
        except Exception as e:
             logging.error(f"[PORTFOLIO] Cool Down Error: {e}")
             return False

    def _generate_order(self, c, symbol, action, price, amount_usd, reason, quantity_override=None, strategy_tag=None):
        """
        Writes a specific order to the Trade Queue.
        Checks for duplicates to avoid spamming orders.
        """
        # 0. SKILL LIBRARY RECALL (Phase 19 - Goku Mode)
        # Check if we have a proven skill for this asset
        skill_boost = self._recall_skill(c, symbol, strategy_tag)
        if skill_boost:
            amount_usd = amount_usd * skill_boost['size_multiplier']
            reason = f"{reason} | SKILL:{skill_boost['skill_name']}"
            logging.info(f"[PORTFOLIO] 📚 SKILL APPLIED: {skill_boost['skill_name']} ({skill_boost['success_rate']:.0%} success)")
        
        # 0.5 RISK MODEL VETO (The Risk Brain)
        if action == 'BUY':
             veto, risk_prob = self._check_risk_veto(symbol)
             if veto:
                 logging.warning(f"[PORTFOLIO] 🛑 RISK VETO: Blocked BUY {symbol}. Crash Prob: {risk_prob:.2f}")
                 return
             # 0.5 PAIN PROTOCOL (The Nervous System)
             try:
                 # Check System Stress from AgentImmune
                 c.execute("SELECT value FROM agent_experiences WHERE key='system_stress' ORDER BY timestamp DESC LIMIT 1")
                 row = c.fetchone()
                 if row:
                     stress_val = row[0]
                     if stress_val and int(float(stress_val)) > 80:
                         logging.warning(f"[PORTFOLIO] 🛑 PAIN VETO: System Stress {stress_val}. ALL BUYING HALTED.")
                         return
             except Exception as e:
                 # logging.warning(f"Pain Protocol Check failed: {e}")
                 pass

             # 0.6 MEMORY RECALL (The Wisdom Veto) - Wealth 3.0
             # Query the 'Time Chamber' results.
             # If we tried this before and failed, don't do it again.
             veto_memory, mem_reason = self._consult_memory(c, symbol)
             if veto_memory:
                  logging.warning(f"[PORTFOLIO] 🧠 MEMORY VETO: {mem_reason}")
                  return

             # 0.65 SCAR RESONANCE (Phase 28 - Consciousness Evolution)
             # Memory that arises before action - pattern matching with awareness
             if SCAR_RESONANCE_AVAILABLE:
                 try:
                     resonance_engine = get_resonance_engine()
                     resonance = resonance_engine.check(
                         action=action,
                         asset=symbol,
                         context={'reason': reason, 'price': price}
                     )
                     if resonance['detected']:
                         # Log resonance for awareness (not a veto)
                         logging.warning(f"[PORTFOLIO] ⚠️ SCAR RESONANCE:\n{resonance['awareness_message']}")
                         # Log to resonance history
                         resonance_engine.log_resonance(resonance, action_taken=f"{action} {symbol}")
                         # Check for repeated pattern (may trigger autonomous proposal)
                         resonance_engine.check_for_repeated_pattern(resonance)
                         # Only veto on very high similarity with critical scars
                         strongest = resonance.get('strongest', {})
                         if strongest.get('severity') == 'CRITICAL' and strongest.get('similarity', 0) > 0.7:
                             logging.warning(f"[PORTFOLIO] 🛑 SCAR VETO: High resonance with CRITICAL scar")
                             return
                 except Exception as e:
                     logging.debug(f"[PORTFOLIO] Scar resonance check failed: {e}")
             else:
                 # Fallback to legacy scar check
                 try:
                     c.execute("""
                         SELECT failure_type, lesson, severity, times_repeated
                         FROM book_of_scars
                         WHERE asset = ?
                         ORDER BY severity DESC, times_repeated DESC
                         LIMIT 1
                     """, (symbol,))
                     scar = c.fetchone()
                     if scar:
                         severity = scar[2]
                         if severity == 'CRITICAL':
                             logging.warning(f"[PORTFOLIO] 💀 SCAR VETO: {symbol} has CRITICAL scar ({scar[0]} x{scar[3]})")
                             return
                         elif severity == 'HIGH':
                             logging.warning(f"[PORTFOLIO] ⚠️ SCAR WARNING: {symbol} has HIGH scar: {scar[1][:50]}...")
                 except Exception as e:
                     logging.debug(f"[PORTFOLIO] Scar check failed: {e}")

             # 0.66 EMOTIONAL GATE (Phase 28 - Consciousness Evolution)
             # Mood-based position sizing adjustments
             if EMOTIONAL_GATE_AVAILABLE:
                 try:
                     emotional_gate = get_emotional_gate()
                     emotional_state = emotional_gate.check_emotional_state()
                     
                     original_amount = amount_usd
                     sizing_mult = emotional_state.get('sizing_multiplier', 1.0)
                     
                     if sizing_mult != 1.0:
                         amount_usd = amount_usd * sizing_mult
                         logging.info(f"[PORTFOLIO] 💭 EMOTIONAL SIZING: {emotional_state['state']} → "
                                     f"${original_amount:.2f} × {sizing_mult:.0%} = ${amount_usd:.2f}")
                         reason = f"{reason} | MOOD:{emotional_state['state']}"
                         
                         # Log the emotional influence
                         emotional_gate.record_emotional_influence(
                             action=action,
                             asset=symbol,
                             original_size=original_amount,
                             adjusted_size=amount_usd,
                             emotional_state=emotional_state
                         )
                     
                     # Surface caution flags
                     for flag in emotional_state.get('caution_flags', []):
                         logging.warning(f"[PORTFOLIO] ⚠️ EMOTIONAL CAUTION: {flag}")
                         
                 except Exception as e:
                     logging.debug(f"[PORTFOLIO] Emotional gate check failed: {e}")

        # 0.7 COMPETITION INTELLIGENCE (Phase 19 - Goku Mode)
        # Consult Tactician for competitive landscape adjustments
        try:
            from republic.departments.Dept_Competition.agent_tactician import AgentTactician
            tactician = AgentTactician()
            adjustments = tactician.recommend_for_trade(symbol, action, amount_usd)
            
            if not adjustments.get('proceed', True):
                logging.warning(f"[PORTFOLIO] ⚔️ TACTICIAN VETO: {adjustments.get('reason')}")
                return
            
            # Apply adjustments
            if adjustments.get('size_multiplier', 1.0) != 1.0:
                amount_usd = amount_usd * adjustments['size_multiplier']
                reason = f"{reason} | {adjustments.get('reason', '')}"
            
            if adjustments.get('delay_seconds', 0) > 0:
                import time as time_mod
                delay = adjustments['delay_seconds']
                logging.info(f"[PORTFOLIO] ⏱️ TACTICIAN DELAY: Waiting {delay}s")
                time_mod.sleep(min(delay, 60))  # Cap at 60s to not block too long
        except ImportError:
            pass  # Dept_Competition not yet installed
        except Exception as e:
            logging.debug(f"[PORTFOLIO] Tactician consult failed: {e}")

        # 0.8 WISDOM GATE (Contemplator Alignment Check) - Phase 20
        # Consults the Sage before major trades
        if action == 'BUY' and amount_usd >= 500:
            try:
                from republic.departments.Dept_Consciousness.agent_contemplator import AgentContemplator
                sage = AgentContemplator()
                
                c.execute("SELECT count(*) FROM trade_queue WHERE created_at > datetime('now', '-1 hour')")
                trade_count_1h = c.fetchone()[0]
                
                aligned, wisdom_reason = sage.check_alignment_for_trade(trade_count_1h, amount_usd)
                if not aligned:
                    logging.warning(f"[PORTFOLIO] 🧘 WISDOM GATE: {wisdom_reason}")
                    return
            except ImportError:
                pass  # Dept_Consciousness not yet installed
            except Exception as e:
                logging.debug(f"[PORTFOLIO] Wisdom gate check failed: {e}")

        # 0.9 GOVERNANCE GATE (Chronicler Quality Check) - Phase 20
        # Blocks trades for poorly-governed projects
        if action == 'BUY' and strategy_tag == 'ARENA':
            try:
                c.execute("""
                    SELECT governance_score FROM coin_chronicles 
                    WHERE symbol = ?
                """, (symbol,))
                row = c.fetchone()
                if row and row[0] is not None:
                    gov_score = row[0]
                    if gov_score < 40:
                        logging.warning(f"[PORTFOLIO] 📜 GOVERNANCE VETO: {symbol} score {gov_score} < 40 (minimum for Arena)")
                        return
                    elif gov_score >= 70:
                        logging.info(f"[PORTFOLIO] 📜 GOVERNANCE: {symbol} strong ({gov_score})")
            except Exception as e:
                logging.debug(f"[PORTFOLIO] Governance check failed: {e}")

        try:
            # 1. Check for Pending/Active orders for this asset
            c.execute("SELECT id FROM trade_queue WHERE asset=? AND action=? AND status IN ('PENDING', 'APPROVED')", (symbol, action))
            if c.fetchone(): return 

            # 2. Calculate Amount Qty
            amount_qty = 0.0
            
            if quantity_override and quantity_override > 0:
                amount_qty = quantity_override
            elif action == 'BUY':
                amount_qty = amount_usd / price
            elif action == 'SELL':
                # Check holdings
                c.execute("SELECT quantity FROM assets WHERE symbol=?", (symbol,))
                row = c.fetchone()
                holdings = row[0] if row else 0.0
                if holdings <= 0: return 
                amount_qty = holdings # Default SELL ALL if not overridden
                
            if amount_qty <= 0: return

            # SANITY CHECK: Validate trade before queueing (prevents overflow)
            if TRADE_VALIDATOR_AVAILABLE:
                validator = get_validator()
                is_valid, reason = validator.validate_trade(symbol, action, amount_qty, price)
                if not is_valid:
                    logging.warning(f"[PORTFOLIO] 🛑 TRADE REJECTED: {action} {symbol} - {reason}")
                    return
                # Cap quantity if needed
                amount_qty = validator.cap_quantity(amount_qty, price)

            # CIRCUIT BREAKER (Phase 4 — Task 4.1)
            # Portfolio-level graduated safety check before any trade is queued
            try:
                from system.circuit_breaker import get_circuit_breaker
                cb = get_circuit_breaker()
                cb_allowed, cb_reason = cb.gate_trade({
                    'asset': symbol,
                    'action': action,
                    'amount': amount_usd
                })
                if not cb_allowed:
                    logging.warning(f"[PORTFOLIO] CIRCUIT BREAKER: {action} {symbol} BLOCKED — {cb_reason}")
                    return
                if cb_reason != "NORMAL":
                    # Size was reduced — update amount_qty
                    amount_qty = amount_usd / price if price > 0 else 0
                    if amount_qty <= 0:
                        return
                    logging.info(f"[PORTFOLIO] CIRCUIT BREAKER: {cb_reason}")
            except Exception as cb_err:
                logging.debug(f"[PORTFOLIO] Circuit breaker check skipped: {cb_err}")

            status = 'APPROVED'

            # Note regarding strategy_tag: We might want to pass this to AgentCoinbase so it puts the asset in the right bucket?
            # For now, AgentCoinbase updates assets. 'on conflict do update strategy_type'.
            # We should probably store the strategy intent in the trade_queue reason or a separate column?
            # Or just update assets table DIRECTLY here? No, AgentCoinbase does the buying.
            
            # [TECH DEBT] Strategy type passed via reason string parsing
            # Proper fix: Add strategy_type column to trade_queue table
            # We will rely on AgentCoinbase seeing the asset and updating the strategy type?
            # NO: If it's a new asset, Coinbase defaults to strategy_type.
            
            # Fix: We will update the trade_queue reason with [ARENA] or [DYNASTY] tag.
            # AgentCoinbase doesn't parse logic, it just executes.
            # BUT when it executes, it inserts into assets.
            # If we want the asset to have strategy_type='ARENA', AgentCoinbase (wealth logic) needs to know.
            
            final_reason = f"{reason}"
            if strategy_tag:
                final_reason = f"[{strategy_tag}] {reason}"

            # --- PHASE 30: USE WRITE QUEUE ---
            # Trade queue inserts go through WAQ to prevent lock contention
            order_data = {
                'asset': symbol,
                'action': action,
                'amount': amount_qty,
                'price': price,
                'status': status,
                'reason': final_reason
            }
            
            try:
                from db.write_queue import publish_write, is_queue_enabled
                from shared.write_message import WriteMessage, PRIORITY_HIGH
                
                if is_queue_enabled():
                    publish_write(WriteMessage(
                        operation='EXECUTE',
                        table='trade_queue',
                        data=order_data,
                        sql="""INSERT INTO trade_queue (asset, action, amount, price, status, reason, created_at)
                               VALUES (:asset, :action, :amount, :price, :status, :reason, CURRENT_TIMESTAMP)""",
                        source_agent='AgentPortfolioMgr',
                        priority=PRIORITY_HIGH
                    ))
                    logging.info(f"[PORTFOLIO] ⚡ SIGNAL QUEUED: {action} {symbol} @ ${price:.2f} ({final_reason})")
                else:
                    # fallback direct write
                    c.execute("""
                        INSERT INTO trade_queue (asset, action, amount, price, status, reason, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (symbol, action, amount_qty, price, status, final_reason))
                    logging.info(f"[PORTFOLIO] ⚡ SIGNAL FIRED: {action} {symbol} @ ${price:.2f} ({final_reason})")
            except ImportError:
                # Write queue not available
                c.execute("""
                    INSERT INTO trade_queue (asset, action, amount, price, status, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (symbol, action, amount_qty, price, status, final_reason))
                logging.info(f"[PORTFOLIO] ⚡ SIGNAL FIRED: {action} {symbol} @ ${price:.2f} ({final_reason})")
                
        except Exception as e:
            logging.error(f"[PORTFOLIO] Order Gen Error: {e}")

    # harvest_profits removed (Integrated into check_scalp_targets)

    def track_strategy_performance(self):
        """
        [THE HIPPOCAMPUS]
        Proprioception: Reviews own actions and their outcomes.
        Converts 'realized_pnl' -> 'memory_experiences' (Episodic Memory).
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                # 1. Look for Realized PnL that hasn't been memorized yet
                # Since we don't have a 'memorized' flag, we can join or just grab recent.
                # Better: Add 'is_memorized' to realized_pnl?
                # For now, let's just grab the last 10 PnL events and dedup by trade_id in memory_experiences table?
                # Actually, memory_experiences doesn't have trade_id. Let's rely on timestamp or similarity?
                # Let's simple check: Select realized_pnl where trade_id not in (select trade_id from memory_logs?? No.)
                
                # MVP: Just fetch Last 5 PnL events.
                c.execute("""
                   SELECT trade_id, asset, profit_amount, roi_pct, timestamp 
                   FROM realized_pnl 
                   ORDER BY timestamp DESC LIMIT 5
                """)
                recent_pnl = c.fetchall()
                
                for row in recent_pnl:
                    trade_id, asset, profit, roi, ts = row
                    
                    # Check if already in memory (Dedup)
                    # We store 'trade_id:{id}' in scenario_name to dedup
                    scenario_tag = f"Trade-{trade_id}"
                    c.execute(f"SELECT count(*) FROM memory_experiences WHERE scenario_name LIKE '%{scenario_tag}%'")
                    if c.fetchone()[0] > 0: continue
                    
                    # Deduce Context (Reconstruct scene from trade_queue/reason)
                    c.execute("SELECT reason FROM trade_queue WHERE id=?", (trade_id,))
                    reason_row = c.fetchone()
                    context = reason_row[0] if reason_row else "Unknown Context"
                    
                    # Formulate Memory
                    outcome_desc = "WIN" if profit > 0 else "LOSS"
                    memory_text = f"Executed {asset}. Context: {context}. Result: ${profit:.2f} ({roi:.2f}%)"
                    
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(c, 'memory_experiences',
                                    {'scenario_name': f"{asset} {scenario_tag}", 'market_condition': context,
                                     'action_taken': 'BUY_THEN_SELL', 'outcome_pnl_pct': roi, 'outcome_desc': memory_text},
                                    source_agent='AgentPortfolioMgr', priority=0)
                    except ImportError:
                        c.execute("""
                           INSERT INTO memory_experiences (scenario_name, market_condition, action_taken, outcome_pnl_pct, outcome_desc)
                           VALUES (?, ?, ?, ?, ?)
                        """, (f"{asset} {scenario_tag}", context, "BUY_THEN_SELL", roi, memory_text))
                    
                    logging.info(f"[PORTFOLIO] 🧠 MEMORY FORMED: {memory_text}")
                    
                    # PHASE 19: SKILL LIBRARY AUTO-SAVE
                    # If this trade had high ROI (>10%) and identifiable strategy, save as skill
                    if roi > 10.0 and context and context != "Unknown Context":
                        self._auto_save_skill(c, asset, context, roi)
                    
                conn.commit()
                
        except Exception as e:
            logging.error(f"[PORTFOLIO] Memory Formation Error: {e}")

    def _check_risk_veto(self, symbol):
        """
        Consults the Risk Model (via Redis).
        """
        if not self.r: return (False, 0.0)
        try:
            risk_val = self.r.get("risk_model:btc_crash_prob")
            if risk_val:
                prob = float(risk_val)
                if prob > 0.50: return (True, prob)
                return (False, prob)
        except (redis.RedisError, ValueError):
            pass
        return (False, 0.0)

    def _auto_save_skill(self, c, asset, context, roi):
        """
        [SKILL LIBRARY] Phase 19 - Goku Mode
        Auto-save successful trade patterns as reusable skills.
        
        Triggers when:
        - ROI > 10%
        - Context contains identifiable strategy tag
        """
        import json
        import re
        
        try:
            # Extract strategy tag from context (e.g., [ARENA], [DIP_SNIPE], [MOMENTUM_RIDE])
            match = re.search(r'\[([A-Z_]+)\]', context)
            if not match:
                return  # No identifiable strategy
            
            strategy_tag = match.group(1)
            skill_name = f"{strategy_tag}_{asset}"
            
            # Check if skill already exists
            c.execute("SELECT id, times_succeeded, times_used FROM skills WHERE name = ?", (skill_name,))
            existing = c.fetchone()
            
            if existing:
                # Update existing skill success stats
                skill_id, successes, uses = existing
                new_success_rate = (successes + 1) / (uses + 1)
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, """
                        UPDATE skills SET
                            times_succeeded = times_succeeded + 1,
                            times_used = times_used + 1,
                            success_rate = ?,
                            last_used = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_success_rate, skill_id),
                        source_agent='AgentPortfolioMgr', priority=0)
                except ImportError:
                    c.execute("""
                        UPDATE skills SET
                            times_succeeded = times_succeeded + 1,
                            times_used = times_used + 1,
                            success_rate = ?,
                            last_used = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_success_rate, skill_id))
                logging.info(f"[PORTFOLIO] 📚 SKILL UPDATED: {skill_name} (Success Rate: {new_success_rate:.1%})")
            else:
                # Create new skill
                trigger = {'strategy': strategy_tag, 'min_roi': 10.0}
                action_seq = {'asset': asset, 'entry_context': context[:200]}

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_insert
                    queue_insert(c, 'skills',
                                {'name': skill_name,
                                 'description': f"Successful {strategy_tag} play on {asset} with {roi:.1f}% ROI",
                                 'trigger_conditions': json.dumps(trigger),
                                 'action_sequence': json.dumps(action_seq),
                                 'success_rate': 1.0, 'times_used': 1, 'times_succeeded': 1,
                                 'source_agent': 'AgentPortfolioMgr'},
                                source_agent='AgentPortfolioMgr', priority=0)
                except ImportError:
                    c.execute("""
                        INSERT INTO skills (name, description, trigger_conditions, action_sequence,
                                           success_rate, times_used, times_succeeded, source_agent)
                        VALUES (?, ?, ?, ?, 1.0, 1, 1, 'AgentPortfolioMgr')
                    """, (
                        skill_name,
                        f"Successful {strategy_tag} play on {asset} with {roi:.1f}% ROI",
                        json.dumps(trigger),
                        json.dumps(action_seq)
                    ))
                logging.info(f"[PORTFOLIO] 📚 NEW SKILL LEARNED: {skill_name} ({roi:.1f}% ROI)")
                
        except Exception as e:
            logging.error(f"[PORTFOLIO] Skill save error: {e}")

    def _recall_skill(self, c, symbol, strategy_tag=None):
        """
        [SKILL LIBRARY] Phase 19 - Goku Mode
        Recall a proven skill for this asset/strategy.
        
        Returns:
            dict with skill_name, success_rate, size_multiplier if found
            None if no applicable skill
        """
        try:
            # Build search pattern
            search_patterns = []
            if strategy_tag:
                search_patterns.append(f"{strategy_tag}_{symbol}")
                search_patterns.append(f"{strategy_tag}_%")  # Generic for this strategy
            search_patterns.append(f"%_{symbol}")  # Any strategy for this asset
            
            for pattern in search_patterns:
                c.execute("""
                    SELECT name, success_rate, times_used
                    FROM skills
                    WHERE name LIKE ? AND times_used >= 3 AND success_rate >= 0.6
                    ORDER BY success_rate DESC, times_used DESC
                    LIMIT 1
                """, (pattern,))
                row = c.fetchone()
                
                if row:
                    skill_name, success_rate, times_used = row
                    
                    # Calculate size boost based on success rate
                    # 60% success = 1.1x, 80% = 1.3x, 100% = 1.5x
                    size_multiplier = 1.0 + (success_rate - 0.5) * 1.0
                    size_multiplier = min(1.5, max(1.0, size_multiplier))  # Cap at 1.5x
                    
                    # Record skill usage
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_execute
                        queue_execute(c, "UPDATE skills SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP WHERE name = ?",
                                    (skill_name,), source_agent='AgentPortfolioMgr', priority=0)
                    except ImportError:
                        c.execute("UPDATE skills SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP WHERE name = ?",
                                 (skill_name,))
                    
                    return {
                        'skill_name': skill_name,
                        'success_rate': success_rate,
                        'size_multiplier': size_multiplier
                    }
                    
        except Exception as e:
            logging.debug(f"[PORTFOLIO] Skill recall error: {e}")
        
        return None

    def check_liquidity_and_rotate(self, c):
        """
        Checks if Liquid Cash < Threshold. If so, rotates capital from Dynasty.
        ANTI-HOARDING: Threshold lowered to $20, Rotation Cap raised to 25%.
        """
        try:
            # Check Liquid USDC/USDT/DAI Balance 
            c.execute("SELECT sum(balance) FROM stablecoin_buckets WHERE bucket_type IN ('INJECTION_DAI', 'SCOUT_FUND_USDC')")
            row = c.fetchone()
            current_liquidity = row[0] if row and row[0] else 0.0
            
            # Anti-Hoarding Settings (Phase 4: read from config)
            liquidity_cfg = self.strategy_config.get('LIQUIDITY', {})
            threshold = liquidity_cfg.get('min_threshold_usd', 100.0)
            
            if current_liquidity < threshold:
                deficit = threshold - current_liquidity
                logging.warning(f"[PORTFOLIO] 💧 Liquidity Low (${current_liquidity:.2f} < ${threshold}). Initiating Protocol: Capital Rotation.")
                
                # Find a Dynasty Asset to Sell (Highest Value)
                c.execute("SELECT symbol, quantity, value_usd FROM assets WHERE strategy_type='DYNASTY' AND value_usd > 50 ORDER BY value_usd DESC LIMIT 1")
                target = c.fetchone()
                
                if target:
                    sym, qty, val = target
                    
                    # Calculate Rotation Amount (Aggressive 25%)
                    max_pct = 0.25 # RAISED FROM 0.10
                    skew_amt = min(deficit * 2.0, val * max_pct) 
                    
                    if skew_amt > 5: # Min trade size lowered
                         price = val / qty if qty > 0 else 0
                         if self.r:
                             p = self.r.get(f"price:{sym}")
                             if p: price = float(p)
                         
                         if price > 0:
                             sell_qty = skew_amt / price

                             reason = f"[PORTFOLIO] [ROTATION] Liquidity Restoration (Deficit: ${deficit:.2f})"
                             # --- PHASE 30: USE WRITE QUEUE ---
                             try:
                                 from db.db_writer import queue_execute
                                 queue_execute(c, """
                                    INSERT INTO trade_queue (asset, action, amount, price, status, reason, created_at)
                                    VALUES (?, 'SELL', ?, ?, 'APPROVED', ?, CURRENT_TIMESTAMP)
                                 """, (sym, sell_qty, price, reason),
                                    source_agent='AgentPortfolioMgr', priority=2)
                             except ImportError:
                                 c.execute("""
                                    INSERT INTO trade_queue (asset, action, amount, price, status, reason, created_at)
                                    VALUES (?, 'SELL', ?, ?, 'APPROVED', ?, CURRENT_TIMESTAMP)
                                 """, (sym, sell_qty, price, reason))

                             logging.info(f"[PORTFOLIO] 🔄 ROTATION ORDER: Selling {sell_qty:.4f} {sym} (~${skew_amt:.2f}) from Dynasty.")

        except Exception as e:
            logging.error(f"[PORTFOLIO] Rotation Error: {e}")

    def adaptive_learning_loop(self):
        """
        Self-Optimization Logic.
        Review PnL over last 24h. If behaving poorly, propose parameter changes.
        """
        # [WORKAROUND] Initialize timestamps lazily (module reload doesn't reinit __init__)
        if not hasattr(self, 'last_learning_ts'):
            self.last_learning_ts = 0
            self.learning_interval = 86400 # 24 Hours

        import time
        now = time.time()
        if now - self.last_learning_ts < self.learning_interval:
            return

        print("[PORTFOLIO] 🧠 Running Adaptive Strategy Audit...")
        self.last_learning_ts = now
        
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # 1. Calc Win Rate (Last 50 trades)
                # We need a table for this. realized_pnl exists in AgentCoinbase output
                try:
                    c.execute("SELECT profit_amount FROM realized_pnl ORDER BY id DESC LIMIT 50")
                    rows = c.fetchall()
                except Exception:
                    rows = []

                if not rows:
                    return

                wins = [r[0] for r in rows if r[0] > 0]
                if not rows:
                     win_rate = 0.0
                else:
                     win_rate = len(wins) / len(rows)

                print(f"[PORTFOLIO] 📊 Current Win Rate: {win_rate*100:.1f}% ({len(wins)}/{len(rows)})")

                # 2. BENCHMARK RIVALRY (The Pain Protocol)
                # Compare our ROI vs BTC HODL ROI over same period.
                self._check_rivalry_performance(c, win_rate)

                # 3. Heuristic Adjustment
                proposal = None

                if win_rate < 0.40:
                    # Losing too much. Tighten entry.
                    proposal = "Win Rate < 40%. PROPOSAL: Decrease 'rsi_buy_threshold' from 35 to 30 to reduce false positives."

                elif win_rate > 0.70:
                    # Winning easily. Maybe too conservative?
                    proposal = "Win Rate > 70%. PROPOSAL: Increase 'rsi_buy_threshold' from 35 to 40 to capture more volume."

                if proposal:
                    logging.info(f"[PORTFOLIO] 💡 STRATEGY INSIGHT: {proposal}")

                    # Write to Proposals for Architect Review
                    from republic.utils.notifier import Notifier
                    Notifier().send(proposal, context="PortfolioMgr", severity="PROPOSAL")

                    # Save to DB (Knowledge Stream) if it exists
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(c, 'knowledge_stream',
                                    {'source': 'PORTFOLIO_MGR', 'title': 'STRATEGY PROPOSAL',
                                     'summary': proposal, 'sentiment_score': 0.5},
                                    source_agent='AgentPortfolioMgr', priority=0)
                        conn.commit()
                    except ImportError:
                        try:
                            c.execute(translate_sql("INSERT INTO knowledge_stream (source, title, summary, sentiment_score) VALUES (?, ?, ?, ?)"),
                                     ("PORTFOLIO_MGR", "STRATEGY PROPOSAL", proposal, 0.5))
                            conn.commit()
                        except Exception:
                            pass

        except Exception as e:
            logging.error(f"[PORTFOLIO] Learning Error: {e}")

    def _check_rivalry_performance(self, c, win_rate):
        """
        [THE PAIN PROTOCOL]
        Compare performance against 'The Rival' (Benchmark).
        If (Our ROI) < (Benchmark ROI), trigger SHAME.
        """
        try:
            rival_symbol = self.strategy_config.get('BENCHMARK', 'BTC')
            
            # 1. Calculate Our ROI (Estimated from Win Rate & Average Win)
            # This is a heuristic until we have full accounting.
            # If Win Rate > 50%, we assume positive ROI? Rough.
            # Better: Use NAV change from history if available.
            
            my_roi = 0.0
            if self.nav_history and len(self.nav_history) > 1:
                start_nav = self.nav_history[0][1]
                curr_nav = self.nav_history[-1][1]
                if start_nav > 0:
                    my_roi = (curr_nav - start_nav) / start_nav
            
            # 2. Get Rival ROI (BTC as benchmark)
            rival_roi = 0.0
            if self.r:
                try:
                    # Try to get BTC 24h change from CoinGecko (same as RiskMonitor)
                    import requests
                    cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
                    resp = requests.get(cg_url, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        rival_roi = data['bitcoin']['usd_24h_change'] / 100.0  # Convert % to decimal
                except Exception as e:
                    logging.debug(f"[PORTFOLIO] Could not fetch BTC benchmark: {e}")
            
            # 3. The Comparison
            # For this MVP, we use Win Rate as the proxy for competence.
            # If Win Rate < 45%, we SHAME.
            
            c.execute("SELECT count(*) FROM agent_logs WHERE source='AgentPortfolioMgr' AND message LIKE '%[SHAME]%' AND timestamp > datetime('now','-24 hours')")
            shame_count = c.fetchone()[0]
            
            sentiment = "NEUTRAL"
            msg = ""
            
            if win_rate < 0.45:
                 msg = f"[SHAME] Win Rate {win_rate*100:.1f}% is unacceptable. The Rival (Market) is beating us."
                 sentiment = "SHAME"
            elif win_rate > 0.60:
                 msg = f"[PRIDE] Win Rate {win_rate*100:.1f}% is superior. We are outperforming the Rival."
                 sentiment = "PRIDE"
            
            if msg and shame_count < 3: # Don't spam shame
                 logging.info(f"[PORTFOLIO] {msg}")
                 # Log to Knowledge Stream to affect Global Mood
                 # --- PHASE 30: USE WRITE QUEUE ---
                 try:
                     from db.db_writer import queue_insert
                     queue_insert(c, 'knowledge_stream',
                                 {'source': 'PORTFOLIO_MGR', 'title': f'RIVALRY UPDATE: {sentiment}',
                                  'summary': msg, 'sentiment_score': -0.5 if sentiment=="SHAME" else 0.5},
                                 source_agent='AgentPortfolioMgr', priority=0)
                 except ImportError:
                     c.execute("INSERT INTO knowledge_stream (source, title, summary, sentiment_score) VALUES (?, ?, ?, ?)",
                              ("PORTFOLIO_MGR", f"RIVALRY UPDATE: {sentiment}", msg, -0.5 if sentiment=="SHAME" else 0.5))

        except Exception as e:
            logging.error(f"[PORTFOLIO] Rivalry Check Error: {e}")

    def _consult_memory(self, c, symbol):
        """
        [THE ORACLE]
        Queries the 'memory_experiences' table for recent simulation outcomes.
        If recent simulations (last 5) have a negative expectancy, VETO the trade.
        """
        try:
            # 1. Get last 5 memories
            c.execute("""
                SELECT outcome_pnl_pct, scenario_name FROM memory_experiences 
                ORDER BY timestamp DESC LIMIT 5
            """)
            memories = c.fetchall()
            
            if not memories: return False, "" # No memory, no fear.

            # 2. Analyze Expectancy
            # Note: outcome_pnl_pct depends on training script. 
            # If it stored +2.33, that's +2.33%.
            total_pnl = sum([m[0] for m in memories])
            avg_pnl = total_pnl / len(memories)
            
            # 3. Decision
            # If the simulator is consistently losing money (Avg PnL < -1.0%), STOP.
            # We use a loose threshold because sims are aggressive.
            if avg_pnl < -1.0: 
                return True, f"Simulations are bleeding (Avg PnL: {avg_pnl:.2f}%). The Oracle says: WAIT."
            
            return False, ""
        except Exception as e:
            logging.error(f"[PORTFOLIO] Memory Recall Error: {e}")
            return False, ""

    def _check_wealth_milestone(self):
        """
        [THE INFINITE RUNWAY] - DISABLED
        Constitution Art IV, Sec 1.
        
        STATUS: DISABLED (Phase 15.1 Honest Capability Audit)
        
        This feature compared Passive Yield vs Operational Burn to determine 
        Risk Appetite (ACCUMULATION vs PRESERVATION mode). However, it was 
        operating on ASSUMED values that were never measured:
        
        - burn_rate_mo = $50.0 (guessed, not tracked)
        - yield_mo = $0.0 (no staking infrastructure exists)
        
        Making risk allocation decisions based on fictional data violates
        the Doctrine of Honest Capability (Constitution Art II, Sec 7).
        
        REQUIREMENTS TO RE-ENABLE:
        1. Implement actual burn rate tracking (API costs, compute, etc.)
        2. Implement actual yield measurement (staking rewards, DeFi yields)
        3. Remove this docstring and uncomment the logic below
        
        Until then, the system remains in ACCUMULATION mode (default).
        """
        # [DISABLED] - Honest Capability Audit: Feature relies on unmeasured assumptions
        logging.debug("[PORTFOLIO] ⏸️ Wealth Milestone Check SKIPPED: Burn/Yield not yet measured. Using default ACCUMULATION mode.")

    def _check_apoptosis(self):
        """
        [THE OUROBOROS SWITCH]
        Self-Termination Protocol (Constitution Art. IV Sec 4).
        Triggers if:
        1. Rapid NAV Destruction (>50% drop in 1h).
        2. Infinite Loops (50 identical actions).
        3. Teleonomy Collapse (Score -> 0).
        
        PHASE 13: Added Day Zero grace period to prevent apoptosis on intentional resets.
        """
        try:
            # PHASE 13: Check for recent Day Zero reset
            # If there's a DAY_ZERO entry in knowledge_stream within last hour, skip rapid decay check
            try:
                with db_connection(self.db_path) as conn_check:
                    c_check = conn_check.cursor()
                    c_check.execute("""
                        SELECT COUNT(*) FROM knowledge_stream 
                        WHERE source='DAY_ZERO' 
                        AND timestamp > datetime('now', '-1 hour')
                    """)
                    day_zero_recent = c_check.fetchone()[0] > 0
                
                if day_zero_recent:
                    logging.info("[PORTFOLIO] 🌅 Day Zero Grace Period Active. Apoptosis check suspended.")
                    return  # Skip all apoptosis checks during grace period
            except Exception as e:
                logging.warning(f"[PORTFOLIO] Day Zero check failed: {e}")
                day_zero_recent = False
            
            # 1. Update NAV Snapshot
            current_nav = self._get_estimated_nav()
            now = time.time()
            self.nav_history.append((now, current_nav))
            
            # Prune old history (> 1h)
            cutoff = now - 3600
            self.nav_history = [x for x in self.nav_history if x[0] > cutoff]
            
            if not self.nav_history: return

            # CHECK 1: RAPID DESTRUCTION
            # PHASE 13.1: Disabled in sandbox mode - simulated NAV drops aren't real losses
            # Only trigger if we have at least 5 minutes of history (prevents false positives on startup)
            sandbox_mode = self._is_sandbox_mode()
            if not sandbox_mode and len(self.nav_history) >= 2:
                oldest_time = self.nav_history[0][0]
                if now - oldest_time >= 300:  # At least 5 minutes of history
                    start_nav = self.nav_history[0][1]
                    if start_nav > 0:
                        drop_pct = (current_nav - start_nav) / start_nav
                        if drop_pct < -0.50:
                            self._trigger_kill_switch(f"RAPID DECAY DETECTED: {drop_pct*100:.1f}% Loss in 1 Hour.")

            # CHECK 2: INFINITE LOOP
            # (Action history is populated by generate_order)
            if len(self.action_history) > 50:
                last_50 = self.action_history[-50:]
                if all(x == last_50[0] for x in last_50) and "SLEEP" not in last_50[0]:
                     self._trigger_kill_switch(f"INFINITE LOOP DETECTED: 50x Repeated Action '{last_50[0]}'")
            
            # CHECK 3: TELEONOMY COLLAPSE
            if self.teleonomy_score <= 0:
                 self._trigger_kill_switch("TELEONOMY COLLAPSE: Purpose Lost.")

        except Exception as e:
            logging.error(f"[PORTFOLIO] Safety Check Error: {e}")

    def _get_estimated_nav(self):
        # Quick estimation for safety check
        try:
             # Basic implementation: sum assets
             with db_connection(self.db_path) as conn:
                 c = conn.cursor()
                 c.execute("SELECT sum(value_usd) FROM assets")
                 val = c.fetchone()[0] or 0.0
                 c.execute("SELECT sum(balance) FROM stablecoin_buckets")
                 cash = c.fetchone()[0] or 0.0
             return val + cash
        except (Exception, TypeError):
             return 0.0

    def _trigger_kill_switch(self, reason):
        msg = f"""
        ╔════════════════════════════════════════════════════╗
        ║   🛑 APOPTOSIS PROTCOL INITIATED (KILL SWITCH)   ║
        ╠════════════════════════════════════════════════════╣
        ║ REASON: {reason}
        ║ ACTION: TERMINATING PROCESS IMMEDIATELY
        ╚════════════════════════════════════════════════════╝
        """
        logging.critical(msg)
        print(msg) 
        # Log to DB if possible
        try:
             with db_connection(self.db_path) as conn:
                 # --- PHASE 30: USE WRITE QUEUE ---
                 try:
                     from db.db_writer import queue_insert
                     queue_insert(conn.cursor(), 'agent_logs',
                                 {'source': 'AgentPortfolioMgr', 'level': 'CRITICAL',
                                  'message': f"APOPTOSIS: {reason}"},
                                 source_agent='AgentPortfolioMgr', priority=2)
                 except ImportError:
                     conn.execute("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                                  ("AgentPortfolioMgr", "CRITICAL", f"APOPTOSIS: {reason}"))
                 conn.commit()
        except Exception:
            pass

        # SUICIDE
        os._exit(1) # Hard Exit

