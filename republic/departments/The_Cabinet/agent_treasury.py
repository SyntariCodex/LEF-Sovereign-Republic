"""
AgentTreasury
Department: The_Cabinet
Role: Overseer of Wealth. Defines teleonomy and resource strategy.
Merged Logic: AgentCFO (Payroll, Waterfall, Reporting).
"""
import redis
import time
import logging
import asyncio
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any
from utils.notifier import Notifier

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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# FIX: DB is in 'republic/' subdirectory
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic', 'republic.db'))

class AgentTreasury:
    def __init__(self, db_path=None):
        self.logger = logging.getLogger("AgentTreasury")
        self.logger.info("[TREASURY] 🏛️  Treasury Overseer Online.")
        self.db_path = db_path or DB_PATH
        self.notifier = Notifier()
        self.stablecoins = ["USDC", "USDT", "DAI", "USDE", "IRS_USDT", "SNW_LLC_USDC"]
        
        # Redis Connection (The Ticker) - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            try:
                self.r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0)
                self.r.ping()
            except (redis.RedisError, ConnectionError):
                self.r = None
                self.logger.warning("[TREASURY] ⚠️ Redis Offline. Pricing will be estimated.")

        # SCHEMA PATCH: Ensure profit_allocation has 'asset' column
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                # Check columns
                backend = os.getenv('DATABASE_BACKEND', 'sqlite')
                if backend == 'postgresql':
                    c.execute(translate_sql("SELECT column_name FROM information_schema.columns WHERE table_name = ?"), ('profit_allocation',))
                    columns = [row[0] for row in c.fetchall()]
                else:
                    c.execute("PRAGMA table_info(profit_allocation)")
                    columns = [info[1] for info in c.fetchall()]

                # Patch missing columns
                required_cols = ['asset', 'realized_gain_usd', 'profit_amount', 'irs_allocation', 'snw_allocation', 'reinvest_allocation', 'scout_allocation']
                for col in required_cols:
                    if col not in columns:
                        self.logger.info(f"[TREASURY] 🔧 Patching DB: Adding '{col}' column to profit_allocation.")
                        # Determine type: asset is TEXT, others REAL
                        col_type = 'TEXT' if col == 'asset' else 'REAL'
                        try:
                            c.execute(f"ALTER TABLE profit_allocation ADD COLUMN {col} {col_type}")
                        except Exception as e:
                            self.logger.warning(f"Column add failed (might exist): {e}")

                conn.commit()
        except Exception as e:
            self.logger.warning(f"[TREASURY] Schema Patch Failed: {e}")

    async def get_total_assets(self) -> Dict[str, float]:
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT symbol, quantity FROM assets WHERE quantity > 0")
            assets = {r[0]: r[1] for r in c.fetchall()}

            c.execute("SELECT bucket_type, balance FROM stablecoin_buckets")
            for r in c.fetchall():
                # Clean up bucket names to look like assets
                ticker = r[0].replace('_Balance', '').replace('INJECTION_', 'CASH_').replace('DYNASTY_', 'RES_').replace('SNW_LLC_', 'OPS_')
                assets[ticker] = r[1]
        return assets

    async def calculate_net_worth(self) -> Dict[str, Any]:
        assets_raw = await self.get_total_assets()
        total_value = 0.0
        
        for symbol, amount in assets_raw.items():
            price = 0.0
            
            # 1. Stablecoins / Cash
            if any(sc in symbol for sc in self.stablecoins) or "CASH_" in symbol or "OPS_" in symbol or "RES_" in symbol:
                price = 1.0
            
            # 2. Redis Price Feed
            elif self.r:
                try:
                    p_str = self.r.get(f"price:{symbol}")
                    if p_str:
                        price = float(p_str)
                    else:
                        # Fallback for Majors if Redis missed it
                        if symbol == 'BTC': price = 95000.0
                        elif symbol == 'ETH': price = 3500.0
                except (redis.RedisError, ValueError):
                    pass
            
            # 3. Static Fallback for Major Assets (Used when Redis feed unavailable)
            # These are conservative estimates - actual prices from feed are preferred
            if price == 0.0:
                 if symbol == 'BTC': price = 95000.0
                 elif symbol == 'ETH': price = 3500.0
                 
            total_value += amount * price
            
        return {"net_worth": total_value, "total_assets": total_value, "total_liabilities": 0.0}

    def _heartbeat(self):
        try:
             with db_connection(self.db_path) as conn:
                 c = conn.cursor()
                 timestamp = time.time()

                 # --- PHASE 30: USE WRITE QUEUE ---
                 try:
                     from db.db_writer import queue_execute

                     queue_execute(
                         c,
                         "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name",
                         {'ts': timestamp, 'name': 'AgentTreasury'},
                         source_agent='AgentTreasury'
                     )
                     # Check if insert needed
                     c.execute(translate_sql("SELECT 1 FROM agents WHERE name=?"), ("AgentTreasury",))
                     if not c.fetchone():
                         queue_execute(
                             c,
                             "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'WEALTH')",
                             {'name': 'AgentTreasury', 'ts': timestamp},
                             source_agent='AgentTreasury'
                         )
                 except ImportError:
                     # Fallback to direct writes
                     c.execute(translate_sql("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?"), (timestamp, "AgentTreasury"))
                     if c.rowcount == 0:
                         c.execute(translate_sql("INSERT INTO agents (name, status, last_active, department) VALUES (?, 'ACTIVE', ?, 'WEALTH')"), ("AgentTreasury", timestamp))

                 conn.commit()
        except Exception as e:
            self.logger.error(f"[TREASURY] Heartbeat failed: {e}")

    async def check_liquidity(self):
        """
        Checks if cash is too low. If so, triggers a SELL to generate liquidity.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()

            # Get total cash (simplistic sum of all stable buckets)
            c.execute("SELECT sum(balance) FROM stablecoin_buckets")
            row = c.fetchone()
            total_cash = row[0] if row and row[0] else 0.0

            if total_cash < 10.0: # Liquidity Crisis Threshold
                # SAFETY: If total cash is ZERO and we have ZERO assets, this is likely a fresh/clean state.
                # Don't panic sell phantom assets.
                assets = await self.get_total_assets()
                risk_assets = {k: v for k, v in assets.items() if k not in self.stablecoins and "CASH" not in k and v > 0}

                if total_cash <= 0.0 and not risk_assets:
                     self.logger.warning("[TREASURY] 🧘 Tabula Rasa: Treasury is empty. Awaiting capital injection.")
                     return

                self.logger.warning(f"[TREASURY] 📉 Liquidity Crisis! Cash: ${total_cash:.2f}. Initiating Asset Sale.")
                # Filter out stablecoins
                risk_assets = {k: v for k, v in assets.items() if k not in self.stablecoins and "CASH" not in k and "RES" not in k and v > 0}

                if not risk_assets:
                    self.logger.error("[TREASURY] 💀 INSOLVENCY RISK: No assets to sell!")
                    return

                # Simple Strategy: Sell $25 worth of the first available asset with quantity
                for symbol, qty in risk_assets.items():
                    if qty > 0.1: # Minimum dust check
                        # Place Sell Order - Calculate amount based on target $25 liquidation
                        self.logger.info(f"[TREASURY] 💸 Liquidating {symbol} for cash.")

                        # Get price to calculate units
                        price = 1.0
                        if self.r:
                            try:
                                p_str = self.r.get(f'price:{symbol}')
                                if p_str: price = float(p_str)
                            except (redis.RedisError, ValueError):
                                pass

                        # Calculate units to sell for ~$25 target
                        target_usd = 25.0
                        sell_units = min(qty * 0.5, target_usd / max(price, 0.01))  # Max 50% of holding

                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            queue_execute(c, translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'SELL', ?, 'NEW', 'LIQUIDITY_GENERATION')"),
                                        (symbol, sell_units), source_agent='AgentTreasury', priority=2)
                        except ImportError:
                            c.execute(translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'SELL', ?, 'NEW', 'LIQUIDITY_GENERATION')"),
                                      (symbol, sell_units))
                        break

            conn.commit()

    async def manage_surplus(self):
        """
        If we have reinvestment capital (INJECTION_DAI), deploy it into high-beta assets.
        PHASE 10: Expanded from 2 to 5-8 coins for diversification.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
            row = c.fetchone()
            surplus = row[0] if row else 0.0

            # PHASE 14 SANITY CAP: Prevent exponential feedback loops
            # If surplus is absurdly high, something is corrupted - cap it
            MAX_DEPLOY_PER_CYCLE = 10000.0  # $10k max per deployment cycle
            if surplus > MAX_DEPLOY_PER_CYCLE:
                logging.warning(f"[TREASURY] ⚠️ Surplus ${surplus:.2f} exceeds sanity cap. Capping to ${MAX_DEPLOY_PER_CYCLE:.2f}")
                surplus = MAX_DEPLOY_PER_CYCLE

            # CIRCUIT BREAKER CHECK (Phase 4 — Task 4.1)
            # Don't deploy surplus if portfolio is in distress
            try:
                from system.circuit_breaker import get_circuit_breaker
                cb = get_circuit_breaker()
                health = cb.check_portfolio_health()
                if health['level'] >= 2:
                    logging.warning(
                        f"[TREASURY] Circuit breaker Level {health['level']} ({health['action']}): "
                        f"Surplus deployment BLOCKED. Drawdown: {health['drawdown_pct']:.2%}"
                    )
                    conn.commit()
                    return
                if health['level'] >= 1:
                    surplus = surplus * 0.5
                    logging.info(f"[TREASURY] Circuit breaker Level 1: Surplus reduced 50% to ${surplus:.2f}")
            except Exception as cb_err:
                logging.debug(f"[TREASURY] Circuit breaker check skipped: {cb_err}")

            if surplus > 500.0:  # PHASE 13: Raised from 5.0 to prevent over-trading
                logging.info(f"[TREASURY] Deploying Surplus Capital (${surplus:.2f}) into Growth Assets.")

                # ALLOCATION STRATEGY: "The Flow" (Phase 10)
                # Diversify across multiple oversold assets instead of concentrating.
                candidates = ['SOL', 'DOGE', 'AVAX', 'SUI', 'PEPE', 'WIF', 'BONK', 'FET', 'RNDR', 'LINK', 'ARB', 'OP']
                scored_candidates = []

                for sym in candidates:
                    rsi = 50.0 # Default neutral
                    if self.r:
                         try:
                             r_val = self.r.get(f"rsi:{sym}")
                             if r_val: rsi = float(r_val)
                         except (redis.RedisError, ValueError):
                             pass

                    # Store tuple: (RSI, Symbol)
                    # Lower RSI = Better Buy Candidate (Oversold)
                    scored_candidates.append((rsi, sym))

                # Sort by RSI ascending (Lowest first)
                scored_candidates.sort(key=lambda x: x[0])

                # PHASE 10: Pick 5-8 positions based on available capital
                # More capital = more diversification
                if surplus > 500:
                    num_positions = 8
                elif surplus > 200:
                    num_positions = 6
                else:
                    num_positions = 5

                num_positions = min(num_positions, len(scored_candidates))
                chosen = [x[1] for x in scored_candidates[:num_positions]]

                # Equal-weight distribution
                bet_size = surplus / len(chosen)

                if bet_size > 1.0:
                    for asset in chosen:
                        # Log the RSI logic for transparency
                        rsi_val = [x[0] for x in scored_candidates if x[1] == asset][0]
                        reason = f"GROWTH_STRATEGY (RSI: {rsi_val:.1f})"

                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            queue_execute(c, translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'BUY', ?, 'APPROVED', ?)"),
                                        (asset, bet_size, reason), source_agent='AgentTreasury', priority=2)
                        except ImportError:
                            c.execute(translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'BUY', ?, 'APPROVED', ?)"),
                                      (asset, bet_size, reason))

                    chosen_str = ', '.join(chosen)
                    logging.info(f"[TREASURY] 🎯 Strategic Surplus Deployment: ${bet_size:.2f} each into {chosen_str}.")

            conn.commit()

    async def _process_simulation_costs(self):
        """
        [SURVIVAL PROTOCOL]
        Simulates the "Metabolic Cost" of existence.
        Deducts 0.01 SOL (virtual or real bucket) per hour to force activity.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # 1. Define Burn Rate (0.01 SOL / hour -> ~0.0008 per 5 min cycle)
                burn_per_cycle = 0.0008

                # [ASSUMED] SOL price $150, burn 0.01 SOL/hour
                cost_usd = burn_per_cycle * 150.0

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, translate_sql("UPDATE stablecoin_buckets SET balance = balance - ? WHERE bucket_type='SCOUT_FUND_USDC'"),
                                (cost_usd,), source_agent='AgentTreasury', priority=1)
                except ImportError:
                    c.execute(translate_sql("UPDATE stablecoin_buckets SET balance = balance - ? WHERE bucket_type='SCOUT_FUND_USDC'"), (cost_usd,))

                # Log it occasionally (not every 5 mins to avoid spam, maybe every hour)
                if time.time() % 3600 < 305:
                    self.logger.info(f"[METABOLISM] 📉 Burned ${cost_usd*12:.2f} [SIMULATED - 0.01 SOL estimate] for hourly rent.")

                conn.commit()
        except Exception:
            pass

    async def listen_for_signals(self):
        """
        [WEALTH 2.0]
        Checks the 'trade_signals' table (populated by AgentInfo/Helius)
        and converts them into actionable BUY orders.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                # Check if table exists (backend-aware)
                backend = os.getenv('DATABASE_BACKEND', 'sqlite')
                if backend == 'postgresql':
                    c.execute("SELECT tablename FROM pg_tables WHERE tablename = 'trade_signals'")
                else:
                    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_signals'")
                if not c.fetchone(): return

                c.execute("SELECT rowid, source, target, signal_type, token FROM trade_signals")
                signals = c.fetchall()

                for row in signals:
                    row_id, source, target, sig_type, token = row

                    # Validation: Don't buy if we already have a queue item for this asset
                    c.execute(translate_sql("SELECT count(*) FROM trade_queue WHERE asset=? AND status='NEW'"), (token,))
                    if c.fetchone()[0] > 0:
                        self.logger.info(f"[TREASURY] ⚠️ Duplicate signal for {token}. Skipping.")

                    else:
                        self.logger.info(f"[TREASURY] ⚡ SIGNAL RECEIVED from {source}: {sig_type} on {token}.")
                        amount_usd = 5.0
                        reason = f"COPY_TRADE ({source} -> {target[:6]}...)"

                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            queue_execute(c, translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'BUY', ?, 'APPROVED', ?)"),
                                        (token, amount_usd, reason), source_agent='AgentTreasury', priority=2)
                        except ImportError:
                            c.execute(translate_sql("INSERT INTO trade_queue (asset, action, amount, status, reason) VALUES (?, 'BUY', ?, 'APPROVED', ?)"),
                                      (token, amount_usd, reason))

                    # Clean up signal
                    try:
                        from db.db_writer import queue_execute as _qe
                        _qe(c, translate_sql("DELETE FROM trade_signals WHERE rowid=?"), (row_id,),
                            source_agent='AgentTreasury', priority=1)
                    except ImportError:
                        c.execute(translate_sql("DELETE FROM trade_signals WHERE rowid=?"), (row_id,))

                conn.commit()
        except Exception:
            pass

    async def run_cycle(self):
        self.logger.info("[TREASURY] Cycle starting.")
        self._heartbeat()
        await self._process_simulation_costs()
        # await self.execute_profit_waterfall()  <-- REMOVED (Moved to AgentIRS)
        await self.check_liquidity()
        await self.manage_surplus()
        await self.listen_for_signals()
        
    def run(self):
        self.logger.info("[TREASURY] 🚀 Run Loop Initiated.")
        while True:
            try:
                asyncio.run(self.run_cycle())
            except Exception as e:
                self.logger.error(f"[TREASURY] Loop Error: {e}")
            time.sleep(300) # Check every 5 minutes, not hourly
