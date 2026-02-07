"""
AgentSteward (The Keeper of the Dynasty)
Department: Dept_Wealth/Dynasty
Role: Slow energy management - infrastructure holdings, staking, governance participation.

Philosophy:
    "Fast energy burns quick. Slow energy sustains."
    
    AgentSteward manages the DYNASTY bucket - coins that represent long-term
    infrastructure bets. These are not traded for momentum; they are held,
    staked, and governed. The goal is symbiotic growth with the blockchain
    ecosystem, not extraction.

Responsibilities:
    1. Manage DYNASTY bucket holdings (long-term)
    2. Identify and execute staking opportunities
    3. Track governance proposals for held coins
    4. Monitor infrastructure coin health signals
    5. Signal to Treasury when rebalancing is needed
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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')

logging.basicConfig(level=logging.INFO)

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


class AgentSteward:
    """
    The Keeper of the Dynasty: Slow energy, infrastructure support.
    
    Unlike Arena trading (fast, extractive), Dynasty holdings are:
    - Long-term (months to years)
    - Staked when possible
    - Governed when supported
    - Held through volatility
    """
    
    # Staking configuration per coin (minimum amounts required for staking)
    STAKEABLE_COINS = {
        'ETH': {'method': 'native', 'min_amount': 0.01},
        'SOL': {'method': 'native', 'min_amount': 0.1},
        'AVAX': {'method': 'native', 'min_amount': 0.1},
        'ATOM': {'method': 'native', 'min_amount': 0.5},
        'DOT': {'method': 'native', 'min_amount': 1.0},
    }
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentSteward"
        logging.info(f"[STEWARD] 🏛️ The Keeper of the Dynasty is Online.")
        
        # Register with matrix
        register_agent(self.name, "WEALTH/DYNASTY", self.db_path)
        
        # Redis for signals - Use shared singleton
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
    
    def _get_db_connection(self):
        """DEPRECATED: Use `with db_connection(self.db_path) as conn:` instead."""
        import warnings
        warnings.warn("_get_db_connection is deprecated, use db_connection context manager", DeprecationWarning)
        return sqlite3.connect(self.db_path, timeout=60.0)
    
    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        return {}
    
    # =========================================================================
    # DYNASTY HOLDINGS MANAGEMENT
    # =========================================================================
    
    def get_dynasty_holdings(self):
        """
        Retrieve current DYNASTY bucket holdings from assets table.
        """
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            
            c.execute("""
                SELECT symbol, quantity, avg_buy_price, value_usd
                FROM assets 
                WHERE strategy_type = 'DYNASTY' AND quantity > 0
                ORDER BY value_usd DESC
            """)
            holdings = c.fetchall()
            conn.close()
            
            logging.info(f"[STEWARD] 👑 Dynasty Holdings: {len(holdings)} positions")
            return holdings
            
        except Exception as e:
            logging.error(f"[STEWARD] Holdings query error: {e}")
            return []
    
    def assess_dynasty_health(self):
        """
        Evaluate the health of Dynasty holdings.
        Uses signals from AgentChronicler (maturity stage, governance health).
        """
        holdings = self.get_dynasty_holdings()
        if not holdings:
            return {'status': 'EMPTY', 'holdings': []}
        
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            
            health_report = []
            for symbol, qty, avg_price, value in holdings:
                # Check for maturity stage from chronicler data
                c.execute("""
                    SELECT maturity_stage, governance_score, last_updated
                    FROM coin_chronicles
                    WHERE symbol = ?
                """, (symbol,))
                chronicle = c.fetchone()
                
                if chronicle:
                    stage, gov_score, updated = chronicle
                    health = {
                        'symbol': symbol,
                        'value_usd': value,
                        'maturity': stage,
                        'governance_score': gov_score,
                        'status': 'HEALTHY' if gov_score and gov_score > 50 else 'WATCH'
                    }
                else:
                    health = {
                        'symbol': symbol,
                        'value_usd': value,
                        'maturity': 'UNKNOWN',
                        'governance_score': None,
                        'status': 'NEEDS_ANALYSIS'
                    }
                
                health_report.append(health)
            
            conn.close()
            
            # Log summary
            healthy = sum(1 for h in health_report if h['status'] == 'HEALTHY')
            logging.info(f"[STEWARD] 📊 Dynasty Health: {healthy}/{len(health_report)} healthy")
            
            return {'status': 'ACTIVE', 'holdings': health_report}
            
        except Exception as e:
            logging.error(f"[STEWARD] Health assessment error: {e}")
            return {'status': 'ERROR', 'holdings': []}
    
    # =========================================================================
    # STAKING OPPORTUNITIES
    # =========================================================================
    
    def identify_staking_opportunities(self):
        """
        Check if any Dynasty holdings can be staked.
        """
        holdings = self.get_dynasty_holdings()
        opportunities = []
        
        for symbol, qty, avg_price, value in holdings:
            if symbol in self.STAKEABLE_COINS:
                config = self.STAKEABLE_COINS[symbol]
                if qty >= config['min_amount']:
                    opportunities.append({
                        'symbol': symbol,
                        'quantity': qty,
                        'method': config['method'],
                        'status': 'ELIGIBLE'
                    })
                    logging.info(f"[STEWARD] 🥩 Staking opportunity: {symbol} ({qty})")
        
        return opportunities
    
    def propose_staking(self, symbol, quantity):
        """
        Propose a staking action directly to Treasury for approval.
        Bypasses Congress - Treasury handles staking decisions.
        """
        try:
            proposal = {
                'type': 'STAKING_REQUEST',
                'symbol': symbol,
                'quantity': quantity,
                'proposed_by': self.name,
                'timestamp': datetime.now().isoformat(),
                'status': 'PENDING_TREASURY'
            }
            
            # Write to trade_signals table for Treasury consumption
            conn = self._get_db_connection()
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS trade_signals 
                         (source TEXT, target TEXT, signal_type TEXT, token TEXT, timestamp REAL)''')
            # --- PHASE 30: USE WRITE QUEUE ---
            try:
                from db.db_writer import queue_execute
                queue_execute(c, "INSERT INTO trade_signals VALUES (?, ?, ?, ?, ?)",
                            (self.name, "TREASURY", "STAKING_REQUEST", symbol, time.time()),
                            source_agent='AgentSteward', priority=1)
            except ImportError:
                c.execute("INSERT INTO trade_signals VALUES (?, ?, ?, ?, ?)",
                          (self.name, "TREASURY", "STAKING_REQUEST", symbol, time.time()))
            conn.commit()
            conn.close()
            
            logging.info(f"[STEWARD] 📜 Staking request sent to Treasury: {symbol}")
            
            # Notify via Redis (Treasury listens to events)
            if self.redis:
                self.redis.publish('events', json.dumps({
                    'type': 'STAKING_REQUEST',
                    'source': self.name,
                    'symbol': symbol,
                    'quantity': quantity,
                    'requires': 'TREASURY_APPROVAL'
                }))
            
            return True
            
        except Exception as e:
            logging.error(f"[STEWARD] Staking request error: {e}")
            return False
    
    # =========================================================================
    # GOVERNANCE TRACKING (Future)
    # =========================================================================
    
    def monitor_governance_proposals(self):
        """
        Track governance proposals for coins we hold using Snapshot.org API.
        Snapshot.org is the standard for off-chain governance (ETH ecosystem).
        """
        holdings = self.get_dynasty_holdings()
        if not holdings:
            return []
        
        # Known Snapshot spaces for major coins
        snapshot_spaces = {
            'ETH': None,  # ETH itself doesn't use Snapshot
            'UNI': 'uniswap.eth',
            'AAVE': 'aave.eth',
            'ENS': 'ens.eth',
            'GTC': 'gitcoindao.eth',
            'OP': 'opcollective.eth',
            'ARB': 'arbitrumfoundation.eth',
        }
        
        proposals = []
        
        try:
            import requests
            
            for symbol, qty, avg_price, value in holdings:
                if symbol not in snapshot_spaces or not snapshot_spaces[symbol]:
                    continue
                
                space = snapshot_spaces[symbol]
                
                # Query Snapshot GraphQL API
                query = """
                query {
                    proposals(
                        first: 5,
                        skip: 0,
                        where: { space: "%s", state: "active" },
                        orderBy: "created",
                        orderDirection: desc
                    ) {
                        id
                        title
                        state
                        end
                    }
                }
                """ % space
                
                try:
                    response = requests.post(
                        'https://hub.snapshot.org/graphql',
                        json={'query': query},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        space_proposals = data.get('data', {}).get('proposals', [])
                        
                        for prop in space_proposals:
                            proposals.append({
                                'symbol': symbol,
                                'space': space,
                                'title': prop.get('title', 'Unknown'),
                                'state': prop.get('state', 'unknown'),
                                'end': prop.get('end'),
                                'id': prop.get('id')
                            })
                            logging.info(f"[STEWARD] 🗳️ Active proposal for {symbol}: {prop.get('title', 'Unknown')[:50]}")
                            
                except requests.RequestException as e:
                    logging.debug(f"[STEWARD] Snapshot API error for {space}: {e}")
                    continue
            
            if proposals:
                # Store in database for tracking
                conn = self._get_db_connection()
                c = conn.cursor()
                c.execute("""CREATE TABLE IF NOT EXISTS governance_proposals 
                             (id TEXT PRIMARY KEY, symbol TEXT, space TEXT, title TEXT, 
                              state TEXT, end_time INTEGER, discovered_at REAL)""")
                for prop in proposals:
                    try:
                        # --- PHASE 30: USE WRITE QUEUE ---
                        try:
                            from db.db_writer import queue_execute
                            from db.db_helper import upsert_sql
                            columns = ['id', 'symbol', 'space', 'title', 'state', 'end_time', 'discovered_at']
                            sql = upsert_sql('governance_proposals', columns, 'id')
                            queue_execute(c, sql,
                                        (prop['id'], prop['symbol'], prop['space'],
                                         prop['title'], prop['state'], prop.get('end'), time.time()),
                                        source_agent='AgentSteward', priority=0)
                        except ImportError:
                            from db.db_helper import upsert_sql
                            columns = ['id', 'symbol', 'space', 'title', 'state', 'end_time', 'discovered_at']
                            sql = upsert_sql('governance_proposals', columns, 'id')
                            c.execute(sql,
                                      (prop['id'], prop['symbol'], prop['space'],
                                       prop['title'], prop['state'], prop.get('end'), time.time()))
                    except sqlite3.IntegrityError:
                        pass
                conn.commit()
                conn.close()
            
            return proposals
            
        except ImportError:
            logging.debug("[STEWARD] 🗳️ Governance monitoring requires 'requests' library")
            return []
        except Exception as e:
            logging.error(f"[STEWARD] Governance monitoring error: {e}")
            return []
    
    # =========================================================================
    # REBALANCING SIGNALS
    # =========================================================================
    
    def check_rebalance_needed(self):
        """
        Check if Dynasty portfolio needs rebalancing.
        Signals Treasury if action needed.
        """
        config = self._load_config()
        dynasty_config = config.get('DYNASTY', {})
        target_allocation = dynasty_config.get('allocation_pct', 0.6)
        
        try:
            conn = self._get_db_connection()
            c = conn.cursor()
            
            # Get total portfolio value
            c.execute("SELECT SUM(value_usd) FROM assets WHERE quantity > 0")
            total = c.fetchone()[0] or 0
            
            # Get dynasty value
            c.execute("SELECT SUM(value_usd) FROM assets WHERE strategy_type='DYNASTY' AND quantity > 0")
            dynasty_value = c.fetchone()[0] or 0
            
            conn.close()
            
            if total == 0:
                return False
            
            current_allocation = dynasty_value / total
            drift = abs(current_allocation - target_allocation)
            
            # If drift > 10%, signal rebalance
            if drift > 0.10:
                logging.info(f"[STEWARD] ⚖️ Rebalance needed: {current_allocation:.1%} vs target {target_allocation:.1%}")
                
                if self.redis:
                    self.redis.publish('events', json.dumps({
                        'type': 'REBALANCE_NEEDED',
                        'source': self.name,
                        'current_pct': current_allocation,
                        'target_pct': target_allocation,
                        'drift': drift
                    }))
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[STEWARD] Rebalance check error: {e}")
            return False
    
    # =========================================================================
    # MAIN CYCLE
    # =========================================================================
    
    def run_cycle(self):
        """
        Dynasty management cycle (runs every 30 minutes).
        
        Focus:
        1. Assess Dynasty health
        2. Identify staking opportunities
        3. Monitor governance
        4. Check rebalancing needs
        """
        logging.info("[STEWARD] 🏛️ Dynasty Stewardship Cycle Starting...")
        
        while True:
            try:
                # 1. Assess health
                health = self.assess_dynasty_health()
                
                # 2. Check staking opportunities
                opportunities = self.identify_staking_opportunities()
                
                # 3. Monitor governance (placeholder)
                self.monitor_governance_proposals()
                
                # 4. Check rebalancing
                self.check_rebalance_needed()
                
                time.sleep(1800)  # 30 minute cycle
                
            except Exception as e:
                logging.error(f"[STEWARD] Cycle error: {e}")
                time.sleep(300)


def run_steward_loop(db_path=None):
    """Entry point for main.py"""
    agent = AgentSteward(db_path)
    agent.run_cycle()


if __name__ == "__main__":
    agent = AgentSteward()
    agent.run_cycle()
