"""
Coinbase Agent (The "Mouth")
Executes trades on Coinbase Advanced Trade API.
Never decides Why - only executes approved orders.

Based on: The Fulcrum Protocol White Paper
The Hand (Execution) is separate from the Eye (Information) and Brain (Decision).
"""

import sqlite3
import ccxt
import time
import os
import json
import math
import random
import redis
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path
import pandas as pd
import sys
import logging
import os

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


# Add parent directories to path to allow imports if running as script
try:
    # Add 'republic' package directory (.../republic)
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
    # Add project root (.../LEF Ai) to allow 'from republic...' imports
    # File: republic/departments/Dept_Wealth/agent_coinbase.py -> 4 levels up to get to LEF Ai
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    # Intent Listener for Motor Cortex integration
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object  # Fallback if import fails
    pass

class SafeLogger:
    """
    Biological Safety: The Membrane must speak clearly without choking.
    Bypasses standard logging module locks that cause deadlocks in threaded execution.
    Uses connection pool to prevent file descriptor exhaustion.
    """
    db_path = None # Set by Agent on Init
    _pool = None   # Connection pool reference

    @staticmethod
    def _get_pool():
        if SafeLogger._pool is None:
            try:
                from db.db_pool import get_pool
                SafeLogger._pool = get_pool()
            except ImportError:
                SafeLogger._pool = None
        return SafeLogger._pool

    @staticmethod
    def _write(level, msg):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        # Format similar to standard logging: TIMESTAMP - LEVEL - MSG
        output = f"{timestamp} - [MOUTH] {level}: {msg}\n"
        sys.stdout.write(output)
        sys.stdout.flush()

        # Database Logging (Proprioception) - uses pool
        if SafeLogger.db_path:
            try:
                with db_connection(SafeLogger.db_path) as conn:
                    # Parse source: Usually [MOUTH] or [SYNAPSE] if logged from there
                    source = "AgentCoinbase"
                    if "[SYNAPSE]" in msg: source = "Synapse"

                    conn.execute(
                        translate_sql("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)"),
                        (source, level, msg)
                    )
                    conn.commit()
            except Exception:
                pass # Fail silently to avoid breaking execution loop

    @staticmethod
    def info(msg):
        SafeLogger._write("INFO", msg)
        
    @staticmethod
    def warning(msg):
        SafeLogger._write("WARNING", msg)
        
    @staticmethod
    def error(msg):
        SafeLogger._write("ERROR", msg)

# Redirect standard logging to prevent accidental usage
logging.info = SafeLogger.info
logging.warning = SafeLogger.warning
logging.error = SafeLogger.error

# --- IMPORTS ---
try:
    import pandas_ta as ta
except ImportError:
    ta = None
    SafeLogger.warning("pandas_ta not found. Technical Analysis disabled.")

try:
    from republic.knowledge.asset_fundamentals import ASSET_LIBRARY
except ImportError:
    # Fallback if path setup fails
    SafeLogger.warning("Could not import ASSET_LIBRARY. Auto-Discovery disabled.")
    ASSET_LIBRARY = {}

try:
    from republic.utils.notifier import Notifier
except ImportError:
    try:
        # If running from inside republic/
        from utils.notifier import Notifier
    except ImportError:
        class Notifier:
            def send(self, *args, **kwargs): pass



class CoinbaseAgent(IntentListenerMixin):
    """
    The "Mouth" - Executes trades, but never decides Why.
    Sovereignty preserved via Human Gate (only executes APPROVED orders).
    Receives BUY/SELL/TRADE intents from Motor Cortex.
    """
    
    def __init__(self, config_path: str = None, db_path: str = None):
        if db_path is None:
             # Robust Path: Go up to 'republic' directory
             # __file__ = republic/departments/Dept_Wealth/agent_coinbase.py
             # 1. Dept_Wealth, 2. departments, 3. republic
             REPUBLIC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             self.db_path = os.getenv('DB_PATH', os.path.join(REPUBLIC_DIR, 'republic.db'))
        else:
             self.db_path = db_path
        
        # Connect SafeLogger to DB
        SafeLogger.db_path = self.db_path
        if config_path is None:
             # Default to relative path from this file: ../../../config/config.json
             config_path = str(Path(__file__).parent.parent.parent / 'config' / 'config.json')
        
        SafeLogger.info(f"DEBUG: Init Start. Config: {config_path}")
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        SafeLogger.info("DEBUG: Config Loaded.")
        
        # Coinbase API rate limiting (10,000 requests/hour per API key)
        self.api_call_count = 0
        self.api_call_times = []  # Track API call timestamps
        coinbase_cfg = self.config.get('coinbase', {})
        self.max_requests_per_hour = coinbase_cfg.get('rate_limit_per_hour', 9000)

        # Silence Protocol (Error Streak Tracker)
        self.error_streak = 0
        self.max_error_streak = coinbase_cfg.get('max_error_streak', 5)



        
        # Redis connection (The Eyes) - Use shared singleton
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_config = self.config.get('redis', {})
        try:
            from system.redis_client import get_redis
            SafeLogger.info(f"DEBUG: Using shared Redis singleton...")
            self.r = get_redis()
            if self.r:
                SafeLogger.info("DEBUG: Redis Pinged.")
        except ImportError:
            try:
                SafeLogger.info(f"DEBUG: Connecting to Redis at {redis_host}...")
                self.r = redis.Redis(
                    host=redis_host,
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0)
                )
                self.r.ping() # Check connection
                SafeLogger.info("DEBUG: Redis Pinged.")
            except Exception as e:
                SafeLogger.warning(f"Warning: Redis connection failed: {e}")
                self.r = None
        
        # Coinbase API configuration
        coinbase_config = self.config.get('coinbase', {})
        api_key = coinbase_config.get('api_key', '')
        api_secret = coinbase_config.get('api_secret', '')
        
        # Resolve ENV placeholders
        if api_key.startswith('ENV:'):
            env_key = api_key.split('ENV:')[1]
            api_key = os.environ.get(env_key, '')
            
        if api_secret.startswith('ENV:'):
            env_key = api_secret.split('ENV:')[1]
            api_secret = os.environ.get(env_key, '')

        # Try loading separate coinbase.json (Direct Download from Portal)
        coinbase_json_path = str(Path(__file__).parent.parent.parent / 'config' / 'coinbase.json')
        if os.path.exists(coinbase_json_path):
             try:
                 with open(coinbase_json_path, 'r') as f:
                     cb_data = json.load(f)
                     # Coinbase JSON format usually has 'name' and 'privateKey'
                     if 'name' in cb_data and 'privateKey' in cb_data:
                         api_key = cb_data['name']
                         api_secret = cb_data['privateKey']
                         print("Found separate coinbase.json key file. Using it.")
             except Exception as e:
                 print(f"Error reading coinbase.json: {e}")

        sandbox = coinbase_config.get('sandbox', True)
        
        # Connect to Coinbase Advanced Trade
        SafeLogger.info("DEBUG: Connecting to Exchange...")
        if api_key and api_secret and api_key != 'YOUR_CB_API_KEY':
            try:
                self.exchange = ccxt.coinbaseadvanced({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                })
                # Verify credentials (optional)
                # self.exchange.fetch_balance() 
                SafeLogger.info("Connected to Coinbase API (Advanced Trade).")
            except Exception as e:
                SafeLogger.error(f"Connection Error: {e}")
                self.exchange = None

        else:
            self.exchange = None
            print("[MOUTH] Warning: Coinbase API keys not configured.")

        # TRADING MODE (Phase 4 — Task 4.5)
        # Graduated transition: paper -> micro_live -> scaled_live
        trading_mode_cfg = self.config.get('trading_mode', {})
        self.trading_mode = trading_mode_cfg.get('current', 'paper')
        mode_settings = trading_mode_cfg.get('modes', {}).get(self.trading_mode, {})

        # Derive sandbox from trading mode (overrides coinbase.sandbox if set)
        sandbox = mode_settings.get('sandbox', sandbox)

        # Apply mode-specific limits
        self.mode_max_trade_size = mode_settings.get('max_trade_size_usd', 100000)
        self.mode_max_daily_trades = mode_settings.get('max_daily_trades', 100)
        self.mode_max_daily_loss = mode_settings.get('max_daily_loss_usd', 1000)

        # Sandbox Logic
        if sandbox:
            SafeLogger.info(f"Trading Mode: {self.trading_mode.upper()} (sandbox=true)")
            self.simulation_mode = True
            SafeLogger.info("[PAPER TRADE] SIMULATION MODE ACTIVE")

            # If we didn't connect (e.g. keys invalid), we fall back to full mock
            if not self.exchange:
                SafeLogger.info("Note: Offline Mode. Using Mock Data for prices.")
        else:
            self.simulation_mode = False
            if self.exchange:
                SafeLogger.info(f"Trading Mode: {self.trading_mode.upper()} (LIVE). Max trade: ${self.mode_max_trade_size}, Max daily trades: {self.mode_max_daily_trades}")
            else:
                SafeLogger.warning("Execution Disabled (No Exchange).")

        self.synapse = None
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_coinbase')
        self.start_listening()

    def handle_intent(self, intent_data):
        """
        Process BUY/SELL/TRADE intents from Motor Cortex.
        IMPORTANT: This queues trades for approval, does NOT auto-execute.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        
        SafeLogger.info(f"📨 Received intent: {intent_type} - {intent_content}")
        
        if intent_type in ('BUY', 'SELL', 'TRADE'):
            try:
                # Parse intent content for asset and amount
                # Expected format: "BUY 100 USD of BTC" or "SELL 0.5 ETH"
                parts = intent_content.split()
                
                # Default values - require human review
                asset = parts[-1] if parts else 'UNKNOWN'
                action = intent_type if intent_type != 'TRADE' else 'BUY'
                amount = 100.0  # Default amount, human should review
                
                # Queue trade for approval (Human Gate preserved)
                with db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO trade_queue (asset, action, amount, status, reason, created_at)
                        VALUES (?, ?, ?, 'PENDING', ?, datetime('now'))
                    """, (asset, action, amount, f"[MOTOR_CORTEX] {intent_content}"))
                    conn.commit()
                    trade_id = c.lastrowid
                
                SafeLogger.info(f"📝 Trade queued (ID: {trade_id}): {action} {asset} - awaiting approval")
                return {'status': 'queued', 'result': f'Trade {trade_id} queued for approval'}
                
            except Exception as e:
                SafeLogger.error(f"Intent handling error: {e}")
                return {'status': 'error', 'result': str(e)}
        else:
            return {'status': 'unhandled', 'result': f'Coinbase does not handle {intent_type} intents'}

    
    def _check_rate_limit(self):
        """Check and enforce Coinbase rate limits (10,000 requests/hour)"""
        current_time = time.time()
        
        # Remove API calls older than 1 hour
        self.api_call_times = [t for t in self.api_call_times if current_time - t < 3600]
        
        # If we're approaching the limit, wait
        if len(self.api_call_times) >= self.max_requests_per_hour:
            oldest_call = min(self.api_call_times)
            wait_time = 3600 - (current_time - oldest_call) + 1  # +1 second buffer
            if wait_time > 0:
                SafeLogger.info(f"Rate limit approaching, waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                # Clean up again after sleep
                self.api_call_times = [t for t in self.api_call_times if current_time - t < 3600]
        
        # Track this API call
        self.api_call_times.append(time.time())
        self.api_call_count += 1
    

    def get_balance(self, symbol: str = 'USDC') -> float:
        """
        Checks available balance.
        If Simulation Mode + Exchange Connected -> Returns REAL balance (Read-Only).
        If Simulation Mode + Offline -> Returns MOCK balance.
        """
        # 1. Try Real Data (Read-Only)
        if self.exchange:
            try:
                self._check_rate_limit()
                balance = self.exchange.fetch_balance()
                if symbol in balance:
                    free_balance = balance[symbol].get('free', 0.0)
                    # SafeLogger.info(f"Real Available {symbol}: {free_balance}")
                    # If real balance is 0 and we are in simulation, maybe offer mock funds?
                    if free_balance == 0 and self.simulation_mode:
                        SafeLogger.info(f"[PAPER] Real balance is 0. Using Mock $100k for testing.")
                        return 100000.0 if symbol == 'USDC' else 0.0
                    return free_balance
                return 0.0
            except Exception as e:
                print(f"[MOUTH] Warning: Could not fetch real balance: {e}")
                # Fall through to mock

        # 2. Fallback to Mock Data (DB Buckets)
        if self.simulation_mode:
            # Check 'stablecoin_buckets' table for simulated funds
            try:
                with db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    
                    # Logic: If simulation needs USDC/Buying Power, use 'INJECTION_DAI' + 'SNW_LLC_USDC'
                    if symbol == 'USDC' or symbol == 'DAI':
                         c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type IN ('INJECTION_DAI', 'SNW_LLC_USDC')")
                         rows = c.fetchall()
                         total_buying_power = sum(row[0] for row in rows)
                         SafeLogger.info(f"[PAPER] Connected to Virtual Buckets. Buying Power: ${total_buying_power:.2f}")
                         return total_buying_power
            except Exception as e:
                print(f"[MOUTH] Error reading virtual buckets: {e}")
                
            print(f"[MOUTH] [PAPER] No virtual bucket found for {symbol}. Returning 0.")
            return 0.0

        return 0.0
    

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetches current market price.
        [OPTIMIZATION] Checks Redis first (populated by Gladiator) before API call.
        If Simulation Mode + Exchange Connected -> Returns REAL Price.
        """
        # 0. Stablecoin shortcut
        if symbol.upper() in ['USDC', 'USDT', 'DAI', 'PYUSD', 'GYEN']:
            return 1.0
        
        # 1. Try Redis FIRST (Gladiator already populates this)
        if self.r:
            try:
                cached_price = self.r.get(f"price:{symbol}")
                if cached_price:
                    price = float(cached_price)
                    # Only use cache if it's recent (Gladiator updates every 30s)
                    # We can't check staleness without TTL, but Gladiator is reliable
                    return price
            except (redis.RedisError, ValueError):
                pass  # Fall through to API
        
        # 2. Try Real Data (API call if Redis miss)
        if self.exchange:
            try:
                self._check_rate_limit()
                market_symbol = f"{symbol}/USD"
                ticker = self.exchange.fetch_ticker(market_symbol)
                price = ticker.get('last', None)
                
                if price:
                    # Broadcast to Redis for Master Agent ("The Brain")
                    if self.r:
                        self.r.set(f"price:{symbol}", price)
                        # Optional: Publish to channel if needed
                        # self.r.publish('price_updates', json.dumps({'symbol': symbol, 'price': price}))
                    
                    # SILENCE: Reduced terminal noise as requested by User
                    # print(f"[MOUTH] Real Price for {symbol}: ${price}")
                    return float(price)
            except Exception as e:
                # SILENCE PROTOCOL: Check for persistent auth/network errors
                err_str = str(e).lower()
                if '401' in err_str or 'unauthorized' in err_str:
                     SafeLogger.error(f"🛑 CRITICAL AUTH ERROR: {e}. Keys likely invalid.")
                     SafeLogger.warning("🔌 SILENCE PROTOCOL: Disabling Exchange Connection IMMEDIATELY to prevent error storm.")
                     self.exchange = None
                     self.simulation_mode = True # Force Paper Mode
                     return None
                
                # Connection/Network Errors (Don't count as Auth failures, but do count as glitches)
                if 'connection' in err_str or 'timeout' in err_str:
                    logger.warning(f"[MOUTH] Network Glitch ({symbol}): {e}")
                    # Don't increment streak too aggressively for network blips
                    time.sleep(1) 
                    return None

                print(f"[MOUTH] Warning: Could not fetch real price: {e}")
                self.error_streak += 1
                if self.error_streak >= self.max_error_streak:
                    SafeLogger.warning("🔌 SILENCE PROTOCOL: Disabling Exchange Connection (Too many errors). Switching to Offline Mode.")
                    self.exchange = None
                    self.simulation_mode = True # Force Paper Mode
                # Fall through to mock


        # 2. Fallback to Mock Data
        if self.simulation_mode:
            price = None
            # S-CLASS UPGRADE: Deterministic Mock Universe (Parity with Master)
            # This ensures the Brain and Hand agree on reality.
            # Load mock prices from config file (Phase 4 — Task 4.2)
            mock_universe = {'USDC': 1.00, 'USDT': 1.00, 'DAI': 1.00}
            try:
                mock_prices_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'mock_prices.json')
                if os.path.exists(mock_prices_path):
                    with open(mock_prices_path, 'r') as _mp:
                        mock_universe.update(json.load(_mp))
            except Exception:
                pass
            # Add sine wave for SOL volatility simulation
            if 'SOL' in mock_universe:
                mock_universe['SOL'] = mock_universe['SOL'] + (math.sin(time.time()) * 10)
            
            # 1. Stablecoins
            if symbol.upper() in ['USDC', 'USDT', 'DAI']: 
                price = 1.00
            
            # 2. Known Assets
            elif symbol.upper() in mock_universe:
                base = mock_universe[symbol.upper()]
                # Minor noise to simulate live market (0.2%)
                drift = random.uniform(-0.002, 0.002) * base 
                price = round(base + drift, 6) # Precision matter for PEPE
            
            # 3. Fallback for Unknowns (Seed based)
            else:
                seed = sum(ord(c) for c in symbol) 
                base_price = (seed * 1.5) % 1000 
                price = base_price
                
            if price:
                if self.r:
                     self.r.set(f"price:{symbol}", price)
                return price
            
        return None
            
        return None
    
    def execute_trade(self, symbol: str, action: str, amount: float, price: Optional[float] = None, trade_id: int = None) -> Optional[Dict]:
        """
        Places a Limit Order (safer than Market Order - prevents slippage).
        
        Coinbase Compliance:
        - Uses LIMIT orders only (not market orders - prevents slippage)
        - Spot trading only (no futures/derivatives)
        - Respects rate limits (10,000 requests/hour)
        - Only executes APPROVED trades (Human Gate)
        
        This is the 'Voice' speaking to the world.
        """
        if not self.exchange and not self.simulation_mode:
            SafeLogger.warning("Cannot execute: Exchange not configured.")
            return None
        
        # SIMULATION MODE
        if self.simulation_mode:
            start_time = time.time()
            # Check rate limit before calculation (simulate real latency)
            # self._check_rate_limit() 
            ordered_price = price or 0.0 # prevent UnboundLocalError 
            
            # Format symbol
            market_symbol = f"{symbol}/USD"
            
            # Fetch Price if missing (Critical for conversion)
            if price is None:
                price = self.get_current_price(symbol)
                if price is None:
                     SafeLogger.info(f"[SIM] Cannot execute: Price fetch failed for {symbol}")
                     return None
            
            # NUCLEUS-MEMBRANE TRANSLATION (SIMULATION):
            if action == 'BUY':
                 # Convert USD Amount -> Token Units
                 executed_amount = amount / price
                 SafeLogger.info(f"[SIM] 🗣️ TRANSLATION: Nucleus Intent ${amount:.2f} -> Membrane Action {executed_amount:.6f} {symbol}")
            else:
                 executed_amount = amount 

            # Simulate Latency & Slippage
            time.sleep(random.uniform(0.05, 0.2)) # 50-200ms
            
            # Simulate Slippage (volatile assets slip more)
            volatility_factor = 0.005 if symbol in ['PEPE', 'SOL'] else 0.001
            executed_price = price * (1 + random.uniform(-volatility_factor, volatility_factor))
            
            slippage_pct = (executed_price - ordered_price) / ordered_price
            latency_ms = int((time.time() - start_time) * 1000)
            
            SafeLogger.info(f"[SIMULATION] EXECUTING TRADE: {action} {executed_amount:.6f} {symbol} @ {executed_price:.4f} (Slip: {slippage_pct*100:.2f}%)")
            
            # PROPRIOCEPTION: Log to execution_logs
            try:
                if trade_id:
                    with db_connection(self.db_path) as conn:
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO execution_logs 
                            (trade_id, asset, side, ordered_price, executed_price, slippage_pct, fee_usd, latency_ms, raw_response)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (trade_id, symbol, action, ordered_price, executed_price, slippage_pct, 0.0, latency_ms, '{"simulation": true}'))
                        conn.commit()
            except Exception as e_log:
                SafeLogger.warning(f"Failed to log execution metrics: {e_log}")
            
            return {
                'id': f'sim_order_{int(time.time())}',
                'status': 'open',
                'filled': 0.0,
                'amount': executed_amount, 
                'price': executed_price
            }
        
        # REAL MODE
        self._check_rate_limit()
        
        try:
            # Format symbol for Coinbase Advanced Trade
            market_symbol = f"{symbol}/USD"
            
            # If price not provided, fetch current price
            if price is None:
                price = self.get_current_price(symbol)
                if price is None:
                    SafeLogger.warning(f"Cannot execute: Could not fetch price for {symbol}")
                    return None
            
            ordered_price = price
            
            if action == 'BUY':
                # Limit buy order: Buy at or below current price
                limit_price = price * 0.999  # 0.1% below market
                
                # NUCLEUS-MEMBRANE TRANSLATION:
                quantity_units = amount / limit_price
                quantity_units = round(quantity_units, 6)
                
                SafeLogger.info(f"🗣️ TRANSLATION: Nucleus Intent ${amount:.2f} -> Membrane Action {quantity_units:.6f} {symbol}")
                
                order = self.exchange.create_limit_buy_order(
                    market_symbol, 
                    quantity_units, 
                    limit_price
                )
                SafeLogger.info(f"ORDER PLACED: BUY {amount} {symbol} @ ${limit_price:.2f} (Limit Order)")
                
            elif action == 'SELL':
                limit_price = price * 1.001  # 0.1% above market
                
                order = self.exchange.create_limit_sell_order(
                    market_symbol,
                    amount,
                    limit_price
                )
                SafeLogger.info(f"ORDER PLACED: SELL {amount} {symbol} @ ${limit_price:.2f} (Limit Order)")
                
            else:
                SafeLogger.error(f"Invalid action: {action}")
                return None
            
            # REAL MODE PROPRIOCEPTION
            latency_ms = int((time.time() - start_time) * 1000)
            try:
                if trade_id:
                    with db_connection(self.db_path) as conn:
                        c = conn.cursor()
                        # Limit orders don't have executed_price yet. Use limit_price as placeholder.
                        c.execute("""
                            INSERT INTO execution_logs 
                            (trade_id, asset, side, ordered_price, executed_price, slippage_pct, fee_usd, latency_ms, raw_response)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (trade_id, symbol, action, ordered_price, limit_price, 0.0, 0.0, latency_ms, str(order)))
                        conn.commit()
            except Exception as e_log:
                SafeLogger.warning(f"Failed to log real execution metrics: {e_log}")

            return order
            
        except Exception as e:
            err_str = str(e).lower()
            if '401' in err_str or 'unauthorized' in err_str:
                 SafeLogger.error(f"🛑 CRITICAL AUTH ERROR during Trade: {e}.")
                 self.exchange = None
                 self.simulation_mode = True
            
            SafeLogger.error(f"Error executing trade: {e}")
            return None
    
    def process_queue(self):
        """
        The 'Larynx Reflex':
        Checks the trade_queue database for orders that have been 'APPROVED' by the Human.
        
        CRITICAL: Only executes orders with status='APPROVED'.
        This is the Human Gate - sovereignty preserved.
        """
        print("[MOUTH] ENTRY: process_queue") # CRITICAL DEBUG
        # OPTIMIZATION: Auto-Approve if Configured (Zero-Delay Mode)
        try:
             auto_delay = self.config.get('thresholds', {}).get('auto_execute_delay_minutes', 5)
             if auto_delay == 0:
                 self._auto_approve_pending()
        except Exception as logger_err:
             print(f"[MOUTH] Error in auto-approval check: {logger_err}")

        print(f"[MOUTH] TRACE: Connecting to DB: {self.db_path}")
        sys.stdout.flush()
        _cm = db_connection(self.db_path)
        conn = _cm.__enter__()
        c = conn.cursor()

        # DEBUG: Loud Print
        print(f"[MOUTH] Checking Queue... (DB: {self.db_path})")
        c.execute("""
            SELECT id, asset, action, amount, price, created_at, schema_version
            FROM trade_queue 
            WHERE status = 'APPROVED'
            AND (schema_version IS NULL OR schema_version = 'v1_spot')
            ORDER BY created_at ASC
        """)
        
        orders = c.fetchall()
        if len(orders) > 0:
             print(f"[MOUTH] DEBUG: Found {len(orders)} APPROVED orders.")
        
        if not orders:
            # No approved orders
            _cm.__exit__(None, None, None)
            return
        
        print(f"[MOUTH] Found {len(orders)} approved order(s) to execute.")
        
        for order in orders:
            # Unpack with version check availability
            if len(order) == 7:
                 order_id, asset, action, amount, price, created_at, schema_version = order
            else:
                 # Fallback for old schema if query mismatch (should not happen with * explicit select)
                 order_id, asset, action, amount, price, created_at = order[:6]
                 schema_version = 'v1_spot'
            
            # RESILIENCE: Check for Stale Orders (Blackout Protection)
            # If order is > 5 minutes old, it might be from before the internet went out.
            # Parse created_at
            try:
                # Assuming format YYYY-MM-DD HH:MM:SS
                order_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                stale_cutoff_sec = self.config.get('coinbase', {}).get('stale_order_minutes', 5) * 60
                if (datetime.now() - order_time).total_seconds() > stale_cutoff_sec:
                     print(f"[MOUTH] STALE ORDER DETECTED: {order_id} is > {stale_cutoff_sec//60} mins old. Expiring for safety.")
                     c.execute(translate_sql("UPDATE trade_queue SET status = 'EXPIRED (STALE)' WHERE id = ?"), (order_id,))
                     conn.commit()
                     continue
            except Exception as e:
                print(f"[MOUTH] Warning: Could not verify order age: {e}")

            SafeLogger.info(f"Processing Order ID: {order_id} - {action} {amount} {asset}")

            # TRADING MODE GATE (Phase 4 — Task 4.5)
            # Enforce mode-specific limits
            notional = amount * (price if price else 1.0) if action == 'SELL' else amount
            if notional > self.mode_max_trade_size:
                print(f"[MOUTH] MODE LIMIT: {self.trading_mode} max trade ${self.mode_max_trade_size}. Order ${notional:.2f} rejected.")
                c.execute(translate_sql("UPDATE trade_queue SET status = 'VETOED', reason = ? WHERE id = ?"),
                          (f"Exceeds {self.trading_mode} mode limit (${self.mode_max_trade_size})", order_id))
                conn.commit()
                continue

            try:
                # 1. Check if we have sufficient balance and Identify Fund Source
                is_scout_trade = False
                c.execute(translate_sql("SELECT reason FROM trade_queue WHERE id=?"), (order_id,))
                row_reason = c.fetchone()
                if row_reason and row_reason[0] and '[SCOUT]' in row_reason[0]:
                    is_scout_trade = True
                    SafeLogger.info(f"🦅 Scout Fund Trade Detected: {asset}")

                if action == 'BUY':
                    # For BUY, check USDC balance
                    
                    # PAPER MODE OVERRIDE: Use Virtual Buckets, ignore Real Wallet
                    if self.simulation_mode:
                        # PAPER TRADING: Check specific bucket
                        bucket_target = 'SCOUT_FUND_USDC' if is_scout_trade else 'INJECTION_DAI'
                        c.execute(translate_sql("SELECT balance FROM stablecoin_buckets WHERE bucket_type = ?"), (bucket_target,))
                        rows = c.fetchall()
                        balance = sum([row[0] for row in rows])
                        logging.debug(f"[PAPER] Checking Virtual Balance ({bucket_target}): ${balance:.2f}")
                    else:
                        balance = self.get_balance('USDC')
                        logging.debug(f"[LIVE] Checking Real USDC Balance: ${balance:.2f}")

                    if not price or price <= 0:
                        SafeLogger.info(f"🔄 Price missing/zero. Fetching live price for {asset}...")
                        price = self.get_current_price(asset)

                    if not price or price <= 0:
                        SafeLogger.warning(f"🛑 Safety: Aborting Trade. Invalid Price: {price}")
                        c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED (INVALID PRICE)' WHERE id = ?"), (order_id,))
                        conn.commit()
                        continue

                    if self.simulation_mode:
                        # SIMULATION/PAPER: Treasury sends Amount in USD for BUYs
                        required = amount
                    else:
                         # LIVE: Amount might be units? No, let's standardize.
                         # Protocol: BUY = Amount is USD. SELL = Amount is Units.
                         required = amount
                    
                    if balance < required:
                        SafeLogger.warning(f"Insufficient Buying Power. Required: ${required:.2f}, Available: ${balance:.2f}")
                        c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED' WHERE id = ?"), (order_id,))
                        conn.commit()
                        continue

                elif action == 'SELL':
                    # For SELL, check asset balance
                    
                    # PAPER MODE OVERRIDE: Check local DB 'assets' table, ignore Real Wallet
                    if self.simulation_mode:
                        c.execute(translate_sql("SELECT quantity FROM assets WHERE symbol=?"), (asset,))
                        row = c.fetchone()
                        balance = row[0] if row else 0.0
                        SafeLogger.info(f"[PAPER] Checking Virtual {asset} Balance: {balance}")
                    else:
                        balance = self.get_balance(asset)
                        SafeLogger.info(f"[LIVE] Checking Real {asset} Balance: {balance}")

                    if balance < amount:
                        SafeLogger.warning(f"Insufficient {asset} balance. Required: {amount}, Available: {balance}")
                        c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED' WHERE id = ?"), (order_id,))
                        conn.commit()
                        continue
                
                # 1.5 MEV PROTECTION (Anti-Frontrunning)
                try:
                    from republic.system.mev_protection import get_mev_protection
                    mev = get_mev_protection()
                    mev_rec = mev.get_execution_recommendation(asset, amount, price)
                    
                    # Apply random delay to prevent pattern detection
                    if mev_rec['delay'] > 0:
                        time.sleep(mev_rec['delay'])
                    
                    # Check if blocked by slippage guard
                    if not mev_rec['proceed']:
                        SafeLogger.warning(f"[MEV] 🛡️ Trade blocked: {mev_rec['notes']}")
                        c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED (MEV_BLOCKED)' WHERE id = ?"), (order_id,))
                        conn.commit()
                        continue
                    
                    # Warn on whale activity
                    if mev_rec['whale_warning']:
                        SafeLogger.warning(f"[MEV] 🐋 Whale activity on {asset} - proceeding with caution")
                except Exception as e_mev:
                    pass  # Don't block trading for MEV check failures
                
                # 2. Execute trade
                order_result = self.execute_trade(asset, action, amount, price, trade_id=order_id)
                
                if order_result:
                    # 3. Mark as 'DONE' - PHASE 30: Use Write Queue
                    try:
                        from db.db_writer import queue_execute
                        queue_execute(
                            c,
                            translate_sql("UPDATE trade_queue SET status = 'DONE', executed_at = CURRENT_TIMESTAMP WHERE id = ?"),
                            (order_id,),
                            source_agent='AgentCoinbase'
                        )
                    except ImportError:
                        c.execute(translate_sql("""
                            UPDATE trade_queue
                            SET status = 'DONE', executed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """), (order_id,))
                    
                    # 3.5 LAM-STYLE ACTION LOGGING (Training Data)
                    try:
                        from republic.system.action_logger import get_action_logger
                        c.execute(translate_sql("SELECT reason FROM trade_queue WHERE id=?"), (order_id,))
                        reason_row = c.fetchone()
                        intent = reason_row[0] if reason_row else f"{action} {asset}"

                        get_action_logger(self.db_path).log_simple(
                            agent_name="AgentCoinbase",
                            intent=intent,
                            action_type="TRADE",
                            outcome="SUCCESS",
                            action_details={"asset": asset, "action": action, "amount": amount, "price": price},
                            outcome_details=f"Order {order_id} executed @ ${price:.2f}",
                            reward_signal=1.0
                        )
                    except Exception as e_log:
                        pass  # Don't block trading for logging failures
                    
                    # 4. Wealth Management Logic (The Mind)
                    try:
                        if action == 'BUY':
                            # Update Avg Buy Price
                            # Calculate weighted average
                            c.execute(translate_sql("SELECT quantity, avg_buy_price FROM assets WHERE symbol=?"), (asset,))
                            row = c.fetchone()
                            current_qty = row[0] if row else 0.0
                            current_avg = row[1] if row else 0.0
                            
                            # New weighted avg
                            # New weighted avg
                            # FIX: For BUY, 'amount' is USD (Intent). 'new_units' must be calculated.
                            executed_qty = amount / price
                            new_qty = current_qty + executed_qty
                            total_cost = (current_qty * current_avg) + (amount) # Cost is USD input
                            new_avg = total_cost / new_qty if new_qty > 0 else 0.0
                            
                            # FEE LOGIC (The Taxman)
                            # 1. Try to get Real Fee from Exchange Report
                            real_fee = 0.0
                            if order_result and 'fee' in order_result and order_result['fee']:
                                try:
                                    real_fee = float(order_result['fee']['cost'])
                                    SafeLogger.info(f"🧾 VERIFIED FEE: ${real_fee:.2f} (Source: Exchange)")
                                except (ValueError, KeyError, TypeError):
                                    pass
                            
                            # 2. Fallback to Simulation (0.6%) if no real fee found
                            
                            # 2. Fallback to Simulation (0.6%) if no real fee found
                            if real_fee == 0.0:
                                fee_rate = self.config.get('coinbase', {}).get('estimated_fee_pct', 0.006)
                                # If BUY, amount is USD, so fee is base on amount
                                # If SELL, amount is Units, so fee is amount * price
                                basis = amount if action == 'BUY' else (amount * price)
                                real_fee = basis * fee_rate
                                SafeLogger.info(f"🧾 SIMULATED FEE: ${real_fee:.2f} (Source: 0.6% Estimate)")
                            
                            if action == 'BUY':
                                trade_cost_raw = amount # Input is USD
                                # Qty update was wrong above
                            else:
                                trade_cost_raw = amount * price
                                
                            total_cost_with_fee = trade_cost_raw + real_fee
                            
                            if action == 'BUY' and total_cost_with_fee > 0:
                                 # Effective price per UNIT
                                 # We need executed_qty
                                 executed_qty = amount / price
                                 effective_price = total_cost_with_fee / executed_qty
                            else:
                                 effective_price = price
                            
                            # Dynamic Wallet Assignment Logic (Reason Parsing)
                            target_wallet_id = 1 # Default to Dynasty
                            strategy_type = 'DYNASTY' # Default
                            
                            # Parse trade reason for tags
                            try:
                                c.execute(translate_sql("SELECT reason FROM trade_queue WHERE id=?"), (order_id,))
                                reason_row = c.fetchone()
                                if reason_row and reason_row[0]:
                                    reason_str = reason_row[0]
                                    
                                    # Wallet ID
                                    import re
                                    match = re.search(r'\[W(\d+)\]', reason_str)
                                    if match:
                                        target_wallet_id = int(match.group(1))
                                        print(f"[MOUTH] 🎯 Dynamic Wallet Identified: ID {target_wallet_id}")
                                        
                                    # Strategy Type (Phase 101)
                                    if '[SCALP]' in reason_str:
                                        strategy_type = 'SCALP'
                                        print(f"[MOUTH] ⚡ Strategy Identified: SCALP (Quick Gains Mode)")
                                    elif '[ARENA]' in reason_str:
                                        strategy_type = 'ARENA'
                                        print(f"[MOUTH] ⚔️ Strategy Identified: ARENA (Velocity Mode)")
                                    elif '[DYNASTY]' in reason_str:
                                        strategy_type = 'DYNASTY'
                                        print(f"[MOUTH] 🏛️ Strategy Identified: DYNASTY (Long Hold)")

                            except Exception as e:
                                print(f"[MOUTH] Warning parsing tags: {e}")

                            # Upsert asset
                            # We update strategy_type if it's a new buy.
                            c.execute(translate_sql("""
                                INSERT INTO assets (symbol, quantity, avg_buy_price, current_wallet_id, strategy_type)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(symbol) DO UPDATE SET
                                    quantity = quantity + ?,
                                    avg_buy_price = ?,
                                    current_wallet_id = ?,
                                    strategy_type = ?
                            """), (asset, executed_qty, effective_price, target_wallet_id, strategy_type,
                                  executed_qty, effective_price, target_wallet_id, strategy_type))
                            print(f"[MOUTH] Updated {asset} (Strategy: {strategy_type}) Cost Basis to ${effective_price:.2f}")
                            
                            # FUNDING DEDUCTION (The Checkbook)
                            try:
                                bucket_source = 'SCOUT_FUND_USDC' if is_scout_trade else 'INJECTION_DAI'
                                total_deduction = total_cost_with_fee
                                
                                c.execute(translate_sql("UPDATE stablecoin_buckets SET balance = balance - ? WHERE bucket_type = ?"), (total_deduction, bucket_source))
                                print(f"[MOUTH] 📉 Deducted ${total_deduction:.2f} from {bucket_source} Bucket.")
                            except Exception as e_fund:
                                print(f"[MOUTH] ⚠️ Funding Deduction Error: {e_fund}")


                        elif action == 'SELL':
                            # Calculate Realized Profit
                            c.execute(translate_sql("SELECT avg_buy_price FROM assets WHERE symbol=?"), (asset,))
                            row = c.fetchone()
                            avg_buy_price = row[0] if row else 0.0
                            
                            if avg_buy_price > 0:
                                raw_revenue = amount * price
                                
                                # FEE LOGIC (The Taxman)
                                real_fee = 0.0
                                if order_result and 'fee' in order_result and order_result['fee']:
                                    try:
                                        real_fee = float(order_result['fee']['cost'])
                                        print(f"[MOUTH] 🧾 VERIFIED FEE: ${real_fee:.2f} (Source: Exchange)")
                                    except (ValueError, KeyError, TypeError):
                                        pass
                                
                                if real_fee == 0.0:
                                     sell_fee_pct = self.config.get('coinbase', {}).get('estimated_fee_pct', 0.006)
                                     real_fee = raw_revenue * sell_fee_pct
                                     print(f"[MOUTH] SIMULATED FEE: ${real_fee:.2f} (Source: {sell_fee_pct*100:.1f}% Estimate)")

                                net_revenue = raw_revenue - real_fee
                                
                                cost_basis = amount * avg_buy_price
                                profit = net_revenue - cost_basis
                                
                                print(f"[MOUTH] Trade Result: Net Revenue=${net_revenue:.2f} (Fees: ${real_fee:.2f}), Cost=${cost_basis:.2f}, Net Profit=${profit:.2f}")
                                
                                if profit > 0:
                                    # Allocate to SNW (The Legacy)
                                    snw_split = self.config.get('coinbase', {}).get('profit_snw_split_pct', 0.50)
                                    snw_share = profit * snw_split
                                    retained_share = profit - snw_share
                                    
                                    c.execute(translate_sql("""
                                        UPDATE stablecoin_buckets
                                        SET balance = balance + ?
                                        WHERE bucket_type = 'SNW_LLC_USDC'
                                    """), (snw_share,))

                                    # Log it
                                    c.execute(translate_sql("""
                                        INSERT INTO profit_allocation (trade_id, profit_amount, bucket_type)
                                        VALUES (?, ?, 'SNW_LLC_USDC')
                                    """), (order_id, snw_share))
                                    print(f"[MOUTH] 💰 Allocated ${snw_share:.2f} to SNW/LLC Stablecoin Bucket")
                                    
                                    # RECYCLE: Return Principal + Retained Profit to Trading Pool (INJECTION_DAI)
                                    recycle_amount = cost_basis + retained_share
                                else:
                                    # Loss Case: Return whatever revenue we salvaged
                                    recycle_amount = net_revenue
                                
                                # Executed Recycle
                                c.execute(translate_sql("""
                                    UPDATE stablecoin_buckets
                                    SET balance = balance + ?
                                    WHERE bucket_type = 'INJECTION_DAI'
                                """), (recycle_amount,))
                                print(f"[MOUTH] 🔄 Recycled ${recycle_amount:.2f} back to INJECTION_DAI (Principal + Retained).")
                                
                                # LOG PnL (For Agent Reflex)
                                try:
                                    roi_calc = ((net_revenue - cost_basis) / cost_basis) * 100.0 if cost_basis > 0 else 0.0
                                    c.execute(translate_sql("""
                                        INSERT INTO realized_pnl (trade_id, asset, profit_amount, roi_pct)
                                        VALUES (?, ?, ?, ?)
                                    """), (order_id, asset, profit, roi_calc))
                                except Exception as e_pnl:
                                    print(f"[MOUTH] Warn: Failed to log realized_pnl: {e_pnl}")
                            
                            # Decrease quantity
                            c.execute(translate_sql("UPDATE assets SET quantity = max(0, quantity - ?) WHERE symbol=?"), (amount, asset))
                            
                        # COMMIT SUCCESSFUL TRANSACTION
                        conn.commit()
                        logging.info(f"[MOUTH] Order {order_id} executed successfully.")

                        # NOTIFIER HOOK
                        if Notifier:
                            try:
                                Notifier().send(
                                    f"**ORDER EXECUTED**\nAction: {action} {asset}\nAmount: {amount}\nPrice: ${price:.4f}\nStatus: **SUCCESS**",
                                    context="COINBASE (Mouth)",
                                    severity="SUCCESS",
                                    color=0x2ecc71 if action=='BUY' else 0xe74c3c
                                )
                            except Exception:
                                pass

                    except Exception as e:
                        conn.rollback() # CRITICAL: Undo partial changes (Free Lunch Prevention)
                        print(f"[MOUTH] Error in Wealth Logic (Rolled Back): {e}")
                        # Mark as failed in separate transaction so we don't lose the record
                        # We need a fresh cursor/commit for the failure status if we rolled back
                        pass 

                else:
                    # Execution failed
                    c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED' WHERE id = ?"), (order_id,))
                    conn.commit()
                    print(f"[MOUTH] Order {order_id} execution failed.")
                    
            except Exception as e:
                print(f"[MOUTH] ERROR executing order {order_id}: {e}")
                c.execute(translate_sql("UPDATE trade_queue SET status = 'FAILED' WHERE id = ?"), (order_id,))
                conn.commit()

        _cm.__exit__(None, None, None)

    def _auto_approve_pending(self):
        """
        Helper: Automatically approves PENDING orders if delay is 0.
        Simulates 'Instant Human Approval' or 'Fully Autonomous Mode'.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                # Check for PENDING
                c.execute("SELECT count(*) FROM trade_queue WHERE status='PENDING'")
                pending_count = c.fetchone()[0]
                
                if pending_count > 0:
                    SafeLogger.info(f"Auto-Approving {pending_count} PENDING orders (Zero-Delay Mode)...")
                    c.execute("UPDATE trade_queue SET status='APPROVED' WHERE status='PENDING'")
                    conn.commit()
        except Exception as e:
            SafeLogger.error(f"Error auto-approving: {e}")

    def scan_new_listings(self):
        """
        The 'Scout':
        Periodically scans Coinbase for new tradeable assets that LEF doesn't know about yet.
        """
        SafeLogger.info("🔭 Scanning for new Coinbase listings...")
        
        known_assets = set(ASSET_LIBRARY.keys())
        
        # Check DB for assets we've already discovered/stored
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT symbol FROM assets")
                db_assets = [r[0] for r in c.fetchall()]
                known_assets.update(db_assets)
        except Exception as e:
            SafeLogger.warning(f"Warning: Could not fetch known assets from DB: {e}")

        discovered = []
        
        if self.exchange:
            try:
                # REAL MODE
                markets = self.exchange.load_markets()
                for symbol in markets:
                    # Symbol format in CCXT is usually 'BTC/USD'
                    if '/USD' in symbol:
                        base_asset = symbol.split('/')[0]
                        if base_asset not in known_assets:
                             discovered.append(base_asset)
            except Exception as e:
                SafeLogger.error(f"Error scanning listings: {e}")
                
        elif self.simulation_mode:
            # SIMULATION MOCK
            # Randomly "discover" a new coin occasionally
            if random.random() < 0.05: # 5% chance per scan
                mock_new_coins = ['SUI', 'APT', 'SEI', 'TIA', 'BLUR']
                candidate = random.choice(mock_new_coins)
                if candidate not in known_assets:
                    discovered.append(candidate)

        # Process Discoveries
        if discovered:
            SafeLogger.info(f"🚨 NEW LISTINGS: Found {len(discovered)} new tradeable assets.")
            
            # Batch Insert (Auto-Catalog)
            try:
                with db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    
                    new_count = 0
                    for new_coin in discovered:
                        # Check if exists (Redundant if we trust known_assets logic, but safer)
                        c.execute(translate_sql("SELECT  1 FROM assets WHERE symbol = ?"), (new_coin,))
                        if not c.fetchone():
                            # Insert as 'DISCOVERY'
                            # quantity=0, value_usd=0, strategy_type='DISCOVERY'
                            # We need to ensure table has strategy_type, else default.
                            try:
                               c.execute("""
                                    INSERT INTO assets (symbol, quantity, value_usd, strategy_type)
                                    VALUES (?, 0, 0, 'DISCOVERY')
                               """, (new_coin,))
                               new_count += 1
                            except Exception:
                               # Fallback if strategy_type column missing
                               c.execute("""
                                    INSERT INTO assets (symbol, quantity, value_usd)
                                    VALUES (?, 0, 0)
                               """, (new_coin,))
                               new_count += 1
                    
                    conn.commit()
                    SafeLogger.info(f"✅ Auto-Cataloged {new_count} new assets into DB.")
                
            except Exception as e:
                SafeLogger.error(f"Failed to auto-catalog discoveries: {e}")
                
        else:
             # Quiet Log (Debug only really)
             pass

    def get_technicals(self, symbol: str):
        """
        Fetches Candles (OHLCV) and calculates RSI/MACD using pandas-ta.
        Publishes to Redis: 'rsi:{symbol}'
        """
        if not self.exchange:
            # MOCK TECHNICALS (For Simulation)
            if self.simulation_mode and self.r:
                # Generate Random RSI
                import random
                mock_rsi = random.uniform(25.0, 75.0) # Full range to trigger trades
                self.r.set(f"rsi:{symbol}", mock_rsi)
                # print(f"[MOUTH] [MOCK] 📊 TA Update {symbol}: RSI={mock_rsi:.2f}")
            return # Cannot do Real TA without real data (or mock generator)
            
        try:
             # Coinbase Advanced Trade format
             market_symbol = f"{symbol}/USD"
             
             # Fetch 100 hours of 1h candles
             candles = self.exchange.fetch_ohlcv(market_symbol, timeframe='1h', limit=100)
             
             if not candles:
                 return
                 
             # Convert to DataFrame
             df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
             
             # --- PANDAS-TA ENABLED ---
             df.ta.rsi(length=14, append=True)
             # df.ta.macd(append=True)
             latest = df.iloc[-1]
             rsi = latest['RSI_14']
             # rsi = 50.0 # Mock RSI neutral
             # -----------------------------------------------------
             
             # Publish to Redis
             if self.r:
                 self.r.set(f"rsi:{symbol}", float(rsi))
                 # SafeLogger.info(f"📊 TA Update {symbol}: RSI={rsi:.2f}")
                 
        except Exception as e:
            SafeLogger.warning(f"TA Error {symbol}: {e}")
            pass

    def update_portfolio_valuations(self):
        """
        Mark-to-Market: Updates value_usd for all held assets.
        Also checks for Auto-Harvest opportunities (Profit Taking).
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    c.execute("SELECT symbol, quantity, avg_buy_price FROM assets WHERE quantity > 0")
                    rows = c.fetchall()
                    
                    for row in rows:
                        symbol, qty, avg_buy = row
                        
                        # Get current price (Real or Mock)
                        current_price = self.get_current_price(symbol)
                        
                        if current_price and current_price > 0:
                            current_value = qty * current_price
                            
                            # Update DB
                            c.execute(translate_sql("UPDATE assets SET value_usd = ?, last_updated=CURRENT_TIMESTAMP WHERE symbol=?"), (current_value, symbol))
                            
                            # Calculate ROI
                            if avg_buy > 0:
                                roi_pct = ((current_price - avg_buy) / avg_buy) * 100.0
                                
                                # Publish ROI to Redis for Master to see
                                if self.r:
                                    self.r.set(f"roi:{symbol}", roi_pct)

                    conn.commit()
                    return  # Success, exit the retry loop
                    
            except Exception as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                SafeLogger.error(f"Error updating valuations: {e}")
                break

            
    def _sync_wallet_state(self):
        """
        Syncs the local DB 'assets' and 'stablecoin_buckets' with the REAL Coinbase Balance.
        Run this periodically to ensure truth.
        """
        if self.simulation_mode or not self.exchange:
            return

        SafeLogger.info("🔄 Syncing Wallet with Coinbase...")
        try:
            balance = self.exchange.fetch_balance()
            total = balance.get('total', {})
            
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                for symbol, qty in total.items():
                    if qty <= 0: continue
                    
                    # 1. Handle STABLECOINS (USDC, DAI, USDT) -> Buckets
                    if symbol == 'USDC':
                        # We treat USDC as the 'SNW_LLC_USDC' master bucket logic for now.
                        # Or 'INJECTION_DAI' if we are trading. 
                        # Let's put it in SNW_LLC_USDC as the Catch-All for now.
                        c.execute(translate_sql("UPDATE stablecoin_buckets SET balance=?, last_updated=CURRENT_TIMESTAMP WHERE bucket_type='SNW_LLC_USDC'"), (qty,))

                    elif symbol == 'DAI':
                         c.execute(translate_sql("UPDATE stablecoin_buckets SET balance=?, last_updated=CURRENT_TIMESTAMP WHERE bucket_type='INJECTION_DAI'"), (qty,))
                         
                    # 2. Handle ASSETS (Crypto) -> Assets Table
                    else:
                        # Upsert. 
                        # Note: We don't know the avg_buy_price if it's external, so we leave it or set to current price?
                        # Better to ignore avg_buy_price update if it exists, only update quantity.
                        
                        # Check if exists
                        c.execute(translate_sql("SELECT quantity FROM assets WHERE symbol=?"), (symbol,))
                        row = c.fetchone()

                        if row:
                            # Update Quantity
                            c.execute(translate_sql("UPDATE assets SET quantity=?, last_updated=CURRENT_TIMESTAMP WHERE symbol=?"), (qty, symbol))
                        else:
                            # Insert New Found Asset
                            SafeLogger.info(f"🔭 FOUND NEW ASSET: {qty} {symbol}")
                            # Fetch price for value calculation
                            price = self.get_current_price(symbol) or 0.0
                            c.execute(translate_sql("INSERT INTO assets (symbol, quantity, avg_buy_price, current_wallet_id, value_usd) VALUES (?, ?, ?, ?, ?)"),
                                      (symbol, qty, price, 1, qty*price))
                
                conn.commit()
            # SafeLogger.info("🔄 Wallet Sync Complete.")
            
        except Exception as e:
            SafeLogger.error(f"Error syncing wallet: {e}")

    def run_main_loop(self):
         """
         Main Loop Wrapper
         """
         SafeLogger.info("Coinbase Agent started.")
         SafeLogger.info(f"DEBUG: Using Database Path: {self.db_path}")
         
         # Startup check
         if os.path.exists(self.db_path):
            try:
                with db_connection(self.db_path) as conn:
                    cursor_debug = conn.cursor()
                    
                    # Check tables (backend-aware)
                    import os as _os
                    _backend = _os.getenv('DATABASE_BACKEND', 'sqlite')
                    if _backend == 'postgresql':
                        cursor_debug.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                    else:
                        cursor_debug.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor_debug.fetchall()
                    SafeLogger.info(f"DEBUG: Tables found: {[t[0] for t in tables]}")
                    
                    # Create realized_pnl if missing
                    cursor_debug.execute("""
                        CREATE TABLE IF NOT EXISTS realized_pnl (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            trade_id TEXT,
                            asset TEXT,
                            profit_amount REAL,
                            roi_pct REAL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
            except Exception as e:
                SafeLogger.error(f"DEBUG: Error reading/creating tables: {e}")
         else:
             SafeLogger.error(f"DEBUG: Database file DOES NOT EXIST at {self.db_path}")
     
         SafeLogger.info("Checking for approved orders every 1 second (High Frequency)...")
         SafeLogger.info("Press Ctrl+C to stop.")
         
         check_interval = 1 
         
         # Initial Sync
         self._sync_wallet_state()
         
         # PHASE 34 FIX: Use while loop instead of recursion to prevent file descriptor exhaustion
         consecutive_errors = 0
         max_consecutive_errors = 10
         
         while True:
             try:
                 # 1. Process Orders
                 self.process_queue()
                 
                 # 1.5 Sync Wallet (Keep DB Truthful)
                 self._sync_wallet_state()
                 
                 # 2. Update Valuations (Mark to Market)
                 self.update_portfolio_valuations()

                 # 3. Publish Prices (The Eyes) -> THROTTLED
                 tracked_assets = [
                     'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'DOT',
                     'POL', 'UNI', 'LTC', 'SHIB', 'PEPE', 'NEAR', 'ATOM', 'XLM', 'ALGO', 'FIL',
                     'HBAR', 'ICP', 'VET', 'QNT', 'AAVE', 'MKR', 'SNX', 'CRV'
                 ]
                 
                 run_technicals = (int(time.time()) % 60) < 30
                 
                 for asset in tracked_assets:
                     try:
                         time.sleep(0.2)
                         price = self.get_current_price(asset) 
                         if run_technicals:
                             self.get_technicals(asset)
                     except Exception as e:
                          pass
                          
                 # 4. Scout for New Listings (Once per Hour)
                 if (int(time.time()) % 3600) < 5: 
                     self.scan_new_listings()
                     
                 # Reset error counter on success
                 consecutive_errors = 0
                 
                 time.sleep(15)
                 
             except KeyboardInterrupt:
                 print("[MOUTH] Shutting down...")
                 break
             except Exception as e:
                 consecutive_errors += 1
                 print(f"[MOUTH] Fatal error in Main Loop ({consecutive_errors}/{max_consecutive_errors}): {e}")
                 SafeLogger.error(f"[MOUTH] Error in loop: {e}. Sleeping 60s...")
                 
                 # CRITICAL: If too many consecutive errors, exit instead of consuming resources
                 if consecutive_errors >= max_consecutive_errors:
                     SafeLogger.error(f"[MOUTH] CRITICAL: {max_consecutive_errors} consecutive errors. Exiting to prevent resource exhaustion.")
                     break
                     
                 time.sleep(60)

def run_coinbase_agent(db_path=None):
    with open("/tmp/debug_coinbase_wrapper.txt", "w") as f:
        f.write(f"WRAPPER CALLED at {time.time()}\n")
    logging.info(f"[MOUTH] DEBUG: WRAPPER CALLED with db_path={db_path}")
    agent = CoinbaseAgent(db_path=db_path)
    
    if not agent.exchange and not getattr(agent, 'simulation_mode', False):
         print("[MOUTH] Cannot start: Exchange not configured and NOT in Sandbox.")
         return
         
    agent.run_main_loop()

if __name__ == "__main__":
    # Test run
    agent = CoinbaseAgent()
    
    if agent.exchange:
        # Test balance check
        balance = agent.get_balance('USDC')
        print(f"Test balance: {balance}")
        
        # Test price fetch
        price = agent.get_current_price('BTC')
        print(f"Test price: {price}")
    else:
        print("Test skipped: Exchange not configured.")
    
    # Test queue processing (will only execute if orders are APPROVED)
    print("\n[MOUTH] Testing queue processing...")
    agent.process_queue()
