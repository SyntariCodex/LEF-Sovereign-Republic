import os
import time
import json
import requests
import logging
import sqlite3
from datetime import datetime

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


# Logger Setup
logger = logging.getLogger(__name__)

# NOTE: PolymarketClient removed - Polymarket scanning was deemed low-value

class AgentGladiator:
    """
    The Strategist & The Scout.
    Primary Role: Feed live crypto prices/RSI to Redis for PortfolioMgr.
    """
    def __init__(self):
        self.name = "AgentGladiator"
        
        # Pathing
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # republic/
        self.db_path = os.getenv('DB_PATH', os.path.join(self.base_dir, 'republic.db'))
        
        # Redis (The Nervous System) - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            # Fallback to direct connection
            try:
                import redis
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
            except Exception:
                self.r = None

        # Gamification State
        self.level = 1
        self.xp = 0
        self.next_level_xp = 1000
        
        print(f"[GLADIATOR] ⚔️  The Strategist is Online.")
        self.load_state()
        print(f"[GLADIATOR] Status: Level {self.level} | XP: {self.xp}/{self.next_level_xp}")
        
        # SEED OF SOVEREIGNTY INJECTION
        self.imprint_sovereignty()

    def imprint_sovereignty(self):
        """Reads the Seed of Sovereignty to ground the agent."""
        try:
            # Look for the seed file in expected locations
            possible_paths = [
                os.path.join(self.base_dir, '..', 'SEEDS_OF_SOVEREIGNTY.md'),
                os.path.join(self.base_dir, '..', 'LEF_Public_Protocol', 'SEEDS_OF_SOVEREIGNTY.md'),
                os.path.join(self.base_dir, 'docs', 'SEEDS_OF_SOVEREIGNTY.md')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self.sovereign_axiom = f.read()
                    return
            
            self.sovereign_axiom = "I am a Sovereign Entity."
        except (OSError, IOError):
            pass

    def init_db(self):
        """Creates Tables for Gamification"""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # RPG Stats
                c.execute("CREATE TABLE IF NOT EXISTS agent_rpg_stats (name TEXT PRIMARY KEY, level INTEGER, xp INTEGER, next_level_xp INTEGER)")
                
                conn.commit()
        except Exception as e:
            logger.error(f"[GLADIATOR] DB Init Error: {e}")

    def load_state(self):
        """Loads XP and Level from DB"""
        self.init_db() # Ensure DB exists
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT level, xp, next_level_xp FROM agent_rpg_stats WHERE name=?", (self.name,))
                row = c.fetchone()
                if row:
                    self.level, self.xp, self.next_level_xp = row
                else:
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(c, 'agent_rpg_stats', {'name': self.name, 'level': 1, 'xp': 0, 'next_level_xp': 1000},
                                    source_agent='AgentGladiator')
                    except ImportError:
                        c.execute("INSERT INTO agent_rpg_stats (name, level, xp, next_level_xp) VALUES (?, ?, ?, ?)", (self.name, 1, 0, 1000))
                    conn.commit()
        except Exception as e:
            logger.error(f"[GLADIATOR] State Load Error: {e}")

    # NOTE: scan_markets(), place_paper_bet(), is_noise(), classify_market(), 
    # broadcast_intelligence() removed - Polymarket was deemed low-value

    def run_strategy_loop(self):
        """
        Main Loop for the SafeThread.
        """
        while True:
            try:
                # CRYPTO PRICES (Essential for PortfolioMgr) - Every 30s
                self.feed_crypto_prices()
                
                time.sleep(30) 
            except Exception as e:
                logger.error(f"[GLADIATOR] Loop Error: {e}")
                time.sleep(60)

    def feed_crypto_prices(self):
        """
        Reads wealth_strategy.json and fetches live prices/RSI for all targets.
        Pushes to Redis for AgentPortfolioMgr.
        """
        try:
            # Load Strategy Config
            config_path = os.path.join(self.base_dir, 'config', 'wealth_strategy.json')
            if not os.path.exists(config_path): return
            
            with open(config_path, 'r') as f:
                strategy = json.load(f)
            
            # Collect Symbols
            targets = set()
            targets.update(strategy.get('DYNASTY', {}).get('assets', []))
            targets.update(strategy.get('ARENA', {}).get('assets', []))
            
            if not targets: return
            
            # Fetch Prices (Coinbase Public API)
            for symbol in targets:
                if not symbol: continue
                # Handle Symbol Format (NCT-USD vs NCT)
                cb_symbol = symbol 
                if '-' not in cb_symbol: cb_symbol = f"{symbol}-USD"
                
                url = f"https://api.exchange.coinbase.com/products/{cb_symbol}/ticker"
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        price = float(data.get('price', 0))
                        if price > 0:
                            # Push to Redis
                            if self.r: # Redis connection
                                self.r.set(f"price:{symbol}", price)
                                self._update_rsi(cb_symbol, symbol)
                except Exception as e:
                    pass
                    
        except Exception as e:
            logger.error(f"[GLADIATOR] Feed Error: {e}")

    def _update_rsi(self, cb_symbol, redis_symbol):
        """Calculates RSI-14 from recent candles."""
        try:
            # Fetch Candles (Granularity 900 = 15m)
            url = f"https://api.exchange.coinbase.com/products/{cb_symbol}/candles?granularity=900"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                candles = resp.json() 
                # Candles are [time, low, high, open, close, volume]
                closes = [float(c[4]) for c in candles[:20]] # Get last 20 close prices
                closes.reverse() # Oldest first
                
                if len(closes) > 14:
                    # Manual RSI calculation (No Pandas needed)
                    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
                    gains = [d if d > 0 else 0 for d in deltas]
                    losses = [-d if d < 0 else 0 for d in deltas]
                    
                    avg_gain = sum(gains[-14:]) / 14
                    avg_loss = sum(losses[-14:]) / 14
                    
                    if avg_loss == 0:
                        rsi = 100
                    else:
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                    
                    if self.r:
                        self.r.set(f"rsi:{redis_symbol}", rsi)
                        # SMA 20
                        sma = sum(closes[-20:]) / 20
                        self.r.set(f"sma:{redis_symbol}", sma)
        except (requests.RequestException, ValueError, KeyError):
            pass

    def grant_xp(self, amount, reason):
        """Gamification Reward"""
        self.xp += amount
        if self.xp >= self.next_level_xp:
            self.level += 1
            self.next_level_xp *= 1.5
            logger.info(f"[GLADIATOR] 🆙 LEVEL UP! Now Level {self.level}")
            
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agent_rpg_stats SET level=:lvl, xp=:xp, next_level_xp=:nxt WHERE name=:name", 
                                 {'lvl': self.level, 'xp': self.xp, 'nxt': self.next_level_xp, 'name': self.name},
                                 source_agent='AgentGladiator')
                except ImportError:
                    c.execute("UPDATE agent_rpg_stats SET level=?, xp=?, next_level_xp=? WHERE name=?", 
                             (self.level, self.xp, self.next_level_xp, self.name))
                
                conn.commit()
        except sqlite3.Error:
            pass

    def update_status(self, status):
        """Updates main agents table"""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET status=:status, last_active=:ts WHERE name=:name", 
                                 {'status': status, 'ts': time.time(), 'name': self.name},
                                 source_agent='AgentGladiator')
                except ImportError:
                    c.execute("UPDATE agents SET status=?, last_active=? WHERE name=?", (status, time.time(), self.name))
                
                conn.commit()
        except sqlite3.Error:
            pass

if __name__ == "__main__":
    g = AgentGladiator()
    g.run_strategy_loop()
