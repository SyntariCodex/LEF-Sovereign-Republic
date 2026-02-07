"""
AgentCoinMgr (The Tactician)
Department: Dept_Wealth
Role: Classifies coins from market_universe into strategy buckets (DYNASTY/ARENA/SCOUT).

Pipeline:
    AgentScholar (populates market_universe)
        ↓
    AgentCoinMgr (classification)
        ↓
    wealth_strategy.json (assets lists)
        ↓
    AgentPortfolioMgr (execution)

Classification Criteria:
    DYNASTY: Top by market cap, low volatility, proven track record
    ARENA: High beta, RSI extremes, trending
    SCOUT: New listings, small cap, experimental
"""

import sqlite3
import os
import time
import json
import logging
import redis
from datetime import datetime

try:
    from utils.agent_registry import register_agent, heartbeat
except ImportError:
    register_agent = lambda *a, **k: None
    heartbeat = lambda *a, **k: None

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')

# Logging
logging.basicConfig(level=logging.INFO)

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


class AgentCoinMgr:
    """
    The Tactician: Classifies coins into strategy buckets.
    Reads: market_universe table (populated by AgentScholar)
    Writes: wealth_strategy.json (assets lists only, preserves other settings)
    """
    
    # Classification thresholds
    DYNASTY_MIN_MARKET_CAP = 10_000_000_000  # $10B
    DYNASTY_MAX_VOLATILITY = 0.05  # 5% daily
    DYNASTY_MIN_AGE_DAYS = 365  # 1 year
    
    ARENA_MIN_BETA = 1.2
    ARENA_MAX_POSITIONS = 20
    
    SCOUT_MAX_MARKET_CAP = 500_000_000  # $500M
    SCOUT_MAX_AGE_DAYS = 90  # 3 months
    SCOUT_MAX_POSITIONS = 5
    
    # Core assets that should always be in DYNASTY
    CORE_DYNASTY = ["BTC", "ETH"]
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentCoinMgr"
        logging.info(f"[COIN_MGR] 🎯 The Tactician is Online.")
        
        # Register with matrix
        register_agent(self.name, "WEALTH", self.db_path)
        
        # Redis for caching - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.redis = get_redis()
        except ImportError:
            try:
                self.redis = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), 
                                          port=6379, db=0, decode_responses=True)
                self.redis.ping()
            except (redis.RedisError, ConnectionError):
                self.redis = None
                logging.warning("[COIN_MGR] Redis unavailable, running without cache.")
    
    def _get_db_connection(self):
        """DEPRECATED: Use with db_connection(self.db_path) instead.
        Note: Returns a raw connection for backward compat. Caller must close."""
        import warnings
        warnings.warn("_get_db_connection is deprecated, use db_connection context manager", DeprecationWarning)
        from db.db_helper import get_connection, release_connection
        conn, pool = get_connection(self.db_path, timeout=60.0)
        # Store pool ref so close() can release properly
        conn._pool_ref = pool
        conn._release = lambda: release_connection(conn, pool)
        try:
            conn.row_factory = sqlite3.Row
        except Exception:
            pass  # PostgreSQL doesn't support row_factory
        return conn
    
    def _heartbeat(self):
        """Register heartbeat in agents table for dashboard visibility."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                import time
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name", 
                                 {'ts': timestamp, 'name': self.name}, source_agent='AgentCoinMgr')
                    c.execute("SELECT 1 FROM agents WHERE name=?", (self.name,))
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'WEALTH')",
                                     {'name': self.name, 'ts': timestamp}, source_agent='AgentCoinMgr')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?", (timestamp, self.name))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active, department) VALUES (?, 'ACTIVE', ?, 'WEALTH')", 
                                 (self.name, timestamp))
                
                conn.commit()
        except Exception:
            pass
    
    def _load_current_config(self):
        """Load current wealth_strategy.json"""
        if not os.path.exists(CONFIG_PATH):
            return {}
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    
    def _save_config(self, config):
        """Save updated wealth_strategy.json"""
        config['LAST_UPDATED_BY'] = self.name
        config['UPDATE_TIMESTAMP'] = datetime.now().isoformat()
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logging.info(f"[COIN_MGR] 📝 Updated wealth_strategy.json")
    
    def get_market_universe(self):
        """
        Fetch all coins from market_universe table.
        Expects columns: symbol, market_cap, volume_24h, volatility, first_seen, sector
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()

            # Check if table exists (backend-aware)
            backend = os.getenv('DATABASE_BACKEND', 'sqlite')
            if backend == 'postgresql':
                c.execute("SELECT tablename FROM pg_tables WHERE tablename = 'market_universe'")
            else:
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_universe'")
            if not c.fetchone():
                logging.warning("[COIN_MGR] market_universe table not found. Creating skeleton.")
                c.execute("""
                    CREATE TABLE IF NOT EXISTS market_universe (
                        symbol TEXT PRIMARY KEY,
                        name TEXT,
                        market_cap REAL DEFAULT 0,
                        volume_24h REAL DEFAULT 0,
                        volatility REAL DEFAULT 0.1,
                        beta REAL DEFAULT 1.0,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sector TEXT DEFAULT 'UNKNOWN',
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                return []

            c.execute("""
                SELECT symbol, name, market_cap, volume_24h, volatility, beta, first_seen, sector
                FROM market_universe
                WHERE market_cap > 0
                ORDER BY market_cap DESC
            """)
            coins = c.fetchall()
            return coins
    
    def classify_dynasty(self, coins):
        """
        Select DYNASTY assets: Blue chips for long-term hold.
        Criteria: High market cap, low volatility, established
        """
        dynasty = list(self.CORE_DYNASTY)  # Always include BTC, ETH
        
        for coin in coins:
            symbol = coin['symbol']
            if symbol in dynasty:
                continue
                
            market_cap = coin['market_cap'] or 0
            volatility = coin['volatility'] or 0.1
            first_seen = coin['first_seen']
            
            # Check age
            try:
                if first_seen:
                    first_date = datetime.fromisoformat(str(first_seen).replace('Z', ''))
                    age_days = (datetime.now() - first_date).days
                else:
                    age_days = 0
            except (ValueError, TypeError, AttributeError):
                age_days = 0
            
            # Dynasty criteria
            if (market_cap >= self.DYNASTY_MIN_MARKET_CAP and 
                volatility <= self.DYNASTY_MAX_VOLATILITY and
                age_days >= self.DYNASTY_MIN_AGE_DAYS):
                dynasty.append(symbol)
        
        # Limit to top 5 by market cap
        # Re-sort by market cap
        cap_map = {c['symbol']: c['market_cap'] or 0 for c in coins}
        dynasty_sorted = sorted(dynasty, key=lambda x: cap_map.get(x, 0), reverse=True)
        
        return dynasty_sorted[:5]
    
    def _get_contested_assets(self):
        """
        [INTEGRATION] Query Scout's competitor observations.
        Returns assets with HIGH threat level (heavily contested by bots).
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT DISTINCT asset FROM competitor_observations
                    WHERE threat_level = 'HIGH'
                    AND timestamp > datetime('now', '-24 hours')
                """)
                rows = c.fetchall()
                contested = [row[0] for row in rows]
                if contested:
                    logging.info(f"[COIN_MGR] ⚔️ Scout Intel: Avoiding {len(contested)} contested assets: {contested}")
                return contested
        except Exception as e:
            logging.warning(f"[COIN_MGR] Could not query Scout intel: {e}")
            return []

    def classify_arena(self, coins, dynasty_assets):
        """
        Select ARENA assets: High-beta for active trading.
        Criteria: Higher volatility, momentum potential
        [INTEGRATION] Now queries Scout intel to avoid contested assets.
        """
        arena = []
        
        # Get contested assets from Scout
        contested_assets = self._get_contested_assets()
        
        for coin in coins:
            symbol = coin['symbol']
            
            # Skip if already in Dynasty
            if symbol in dynasty_assets:
                continue
            
            # [INTEGRATION] Skip if heavily contested (Scout intel)
            if symbol in contested_assets:
                logging.info(f"[COIN_MGR] ⚠️ Skipping {symbol} (contested by bots)")
                continue
            
            beta = coin['beta'] or 1.0
            market_cap = coin['market_cap'] or 0
            volume = coin['volume_24h'] or 0
            
            # Arena criteria: Good volume, reasonable market cap, higher beta
            if (beta >= self.ARENA_MIN_BETA and
                market_cap >= 100_000_000 and  # At least $100M
                volume >= 10_000_000):  # At least $10M daily volume
                arena.append(symbol)
        
        return arena[:self.ARENA_MAX_POSITIONS]
    
    def classify_scout(self, coins, dynasty_assets, arena_assets):
        """
        Select SCOUT assets: New discoveries for exploration.
        Criteria: New, small cap, experimental
        """
        scout = []
        existing = set(dynasty_assets + arena_assets)
        
        for coin in coins:
            symbol = coin['symbol']
            
            if symbol in existing:
                continue
            
            market_cap = coin['market_cap'] or 0
            first_seen = coin['first_seen']
            
            # Check age
            try:
                if first_seen:
                    first_date = datetime.fromisoformat(str(first_seen).replace('Z', ''))
                    age_days = (datetime.now() - first_date).days
                else:
                    age_days = 999
            except (ValueError, TypeError, AttributeError):
                age_days = 999
            
            # Scout criteria: New and small
            if (market_cap <= self.SCOUT_MAX_MARKET_CAP and
                market_cap >= 10_000_000 and  # At least $10M (not dust)
                age_days <= self.SCOUT_MAX_AGE_DAYS):
                scout.append(symbol)
        
        return scout[:self.SCOUT_MAX_POSITIONS]
    
    def classify_universe(self):
        """
        Main classification method. Runs the full pipeline:
        1. Read market_universe
        2. Classify into buckets
        3. Update wealth_strategy.json
        """
        logging.info("[COIN_MGR] 🔄 Starting universe classification...")
        
        # 1. Get coins
        coins = self.get_market_universe()
        if not coins:
            logging.warning("[COIN_MGR] No coins in market_universe. Skipping classification.")
            return False
        
        logging.info(f"[COIN_MGR] 📊 Analyzing {len(coins)} coins from market_universe")
        
        # 2. Classify
        dynasty = self.classify_dynasty(coins)
        arena = self.classify_arena(coins, dynasty)
        scout = self.classify_scout(coins, dynasty, arena)
        
        logging.info(f"[COIN_MGR] 👑 DYNASTY: {dynasty}")
        logging.info(f"[COIN_MGR] ⚔️ ARENA: {arena}")
        logging.info(f"[COIN_MGR] 🔭 SCOUT: {scout}")
        
        # 3. Update config
        config = self._load_current_config()
        
        # Preserve existing structure, only update assets lists
        if 'DYNASTY' not in config:
            config['DYNASTY'] = {}
        if 'ARENA' not in config:
            config['ARENA'] = {}
        if 'SCOUT' not in config:
            config['SCOUT'] = {}
        
        config['DYNASTY']['assets'] = dynasty
        config['ARENA']['assets'] = arena
        config['SCOUT']['assets'] = scout
        config['UPDATE_REASON'] = f"Universe reclassification: {len(coins)} coins analyzed"
        
        self._save_config(config)
        
        # 4. Publish event
        if self.redis:
            self.redis.publish('events', json.dumps({
                'type': 'BUCKETS_UPDATED',
                'source': self.name,
                'dynasty_count': len(dynasty),
                'arena_count': len(arena),
                'scout_count': len(scout),
                'timestamp': datetime.now().isoformat()
            }))
        
        return True
    
    def run_cycle(self):
        """
        Main loop. Runs classification periodically.
        - Full classification: Every 4 hours
        - Quick ARENA refresh: Every hour
        """
        logging.info("[COIN_MGR] 🎯 Starting classification cycle...")
        last_full_run = 0
        
        while True:
            try:
                self._heartbeat()  # Dashboard visibility
                current_time = time.time()
                
                # Full classification every 4 hours
                if current_time - last_full_run >= 14400:  # 4 hours
                    self.classify_universe()
                    last_full_run = current_time
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"[COIN_MGR] Cycle error: {e}")
                time.sleep(60)


def run_coin_mgr_loop(db_path=None):
    """Entry point for main.py thread"""
    agent = AgentCoinMgr(db_path)
    agent.run_cycle()


if __name__ == "__main__":
    agent = AgentCoinMgr()
    agent.classify_universe()
