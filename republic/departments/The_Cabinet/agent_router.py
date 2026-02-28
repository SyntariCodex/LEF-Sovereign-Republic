"""
AgentRouter (The Hypothalamus)
Department: The_Cabinet
Role: Mixture-of-Experts routing - predicts which agents need to activate based on context.

Inspired by: Arcee Trinity (MoE with 1B active of 6B params)
LEF Integration: LEF already has 30+ agents, but all run independently.
This router predicts which agents are NEEDED and signals them to wake/sleep.

Architecture:
    Context Signals → AgentRouter → Activation Predictions → Sleep/Wake Commands

Context Signals:
    - Market state (bull/bear/volatile/stable)
    - Time of day (market hours, off-hours, Sabbath)
    - Recent events (trades executed, errors, vetoes)
    - System stress level
    - User activity (bridge messages)
"""

import sqlite3
import os
import time
import json
import logging
import redis
from datetime import datetime
from contextlib import contextmanager

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Phase 6.75: Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        import os
        backend = os.getenv('DATABASE_BACKEND', 'sqlite').lower()
        if backend == 'sqlite':
            conn = sqlite3.connect(db_path or DB_PATH, timeout=timeout)
            if os.getenv('DATABASE_BACKEND', 'sqlite') != 'postgresql':
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=120000")
            conn.row_factory = sqlite3.Row
        else:
            # PostgreSQL fallback (would need psycopg2)
            raise ImportError("PostgreSQL not supported in fallback mode")
        try:
            yield conn
        finally:
            conn.close()

logging.basicConfig(level=logging.INFO)


class AgentRouter:
    """
    The Hypothalamus: Routes attention to relevant agents.
    
    Agent Categories:
        ALWAYS_ON: Core agents that never sleep (LEF, Treasury, Immune)
        MARKET_HOURS: Agents active during trading (PortfolioMgr, Coinbase, Gladiator)
        ON_DEMAND: Agents activated by specific triggers (Scholar, Civics)
        BACKGROUND: Low-priority agents for maintenance (Chronicler, PostMortem)
    """
    
    # Agent activation profiles
    AGENT_PROFILES = {
        # ALWAYS_ON - Never sleep
        'AgentLEF': {'category': 'ALWAYS_ON', 'min_interval': 60},
        'AgentTreasury': {'category': 'ALWAYS_ON', 'min_interval': 60},
        'AgentImmune': {'category': 'ALWAYS_ON', 'min_interval': 60},
        
        # MARKET_HOURS - Active during trading windows
        'AgentPortfolioMgr': {'category': 'MARKET_HOURS', 'min_interval': 60},
        'AgentCoinbase': {'category': 'MARKET_HOURS', 'min_interval': 30},
        'AgentGladiator': {'category': 'MARKET_HOURS', 'min_interval': 30},
        'AgentCoinMgr': {'category': 'MARKET_HOURS', 'min_interval': 300},
        
        # COMPETITION - Active when market is volatile or competitors detected
        'AgentScout': {'category': 'COMPETITION', 'min_interval': 300},
        'AgentTactician': {'category': 'COMPETITION', 'min_interval': 600},
        
        # CONSCIOUSNESS - Active during reflection periods
        'AgentPhilosopher': {'category': 'CONSCIOUSNESS', 'min_interval': 300},
        'AgentContemplator': {'category': 'CONSCIOUSNESS', 'min_interval': 3600},
        'AgentIntrospector': {'category': 'CONSCIOUSNESS', 'min_interval': 3600},
        
        # BACKGROUND - Low priority, maintenance
        'AgentScholar': {'category': 'BACKGROUND', 'min_interval': 3600},
        'AgentChronicler': {'category': 'BACKGROUND', 'min_interval': 7200},
        'AgentCivics': {'category': 'BACKGROUND', 'min_interval': 3600},
        'AgentPostMortem': {'category': 'BACKGROUND', 'min_interval': 300},
        'AgentSteward': {'category': 'BACKGROUND', 'min_interval': 1800},
    }
    
    # Context → Category activation map
    CONTEXT_ACTIVATIONS = {
        'MARKET_VOLATILE': ['MARKET_HOURS', 'COMPETITION'],
        'MARKET_STABLE': ['MARKET_HOURS'],
        'MARKET_CLOSED': ['BACKGROUND', 'CONSCIOUSNESS'],
        'SABBATH': ['CONSCIOUSNESS'],
        'HIGH_STRESS': ['ALWAYS_ON'],  # Reduce to essentials
        'USER_ACTIVE': ['ALWAYS_ON', 'MARKET_HOURS', 'CONSCIOUSNESS'],
        'NORMAL': ['ALWAYS_ON', 'MARKET_HOURS', 'BACKGROUND'],
    }
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentRouter"
        logging.info(f"[ROUTER] 🧠 The Hypothalamus is Online.")
        
        # Redis for commands - Use shared singleton
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
                logging.warning("[ROUTER] Redis unavailable.")
        
        # Activation state
        self.agent_states = {}  # agent_name -> {'active': bool, 'last_wake': timestamp}
        self._last_context = None  # Track previous context to suppress duplicate broadcasts
        self._last_wake_set = None  # Track previous wake set
        self._suppress_count = 0  # Count suppressed duplicate broadcasts
        self._pending_context = None  # Hysteresis: new context must persist 2 cycles
        self._pending_wake_set = None
        self._pending_count = 0  # How many cycles the pending context has been seen
        self._ensure_tables()
    
    def _heartbeat(self):
        """Register heartbeat for dashboard visibility."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                timestamp = time.time()

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute

                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name",
                                 {'ts': timestamp, 'name': self.name}, source_agent='AgentRouter')
                    c.execute("SELECT 1 FROM agents WHERE name=?", (self.name,))
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'CABINET')",
                                     {'name': self.name, 'ts': timestamp}, source_agent='AgentRouter')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?", (timestamp, self.name))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active, department) VALUES (?, 'ACTIVE', ?, 'CABINET')",
                                 (self.name, timestamp))

                conn.commit()
        except sqlite3.Error:
            pass

    def _ensure_tables(self):
        """Create routing_decisions table for audit trail."""
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS routing_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    context TEXT,
                    active_categories TEXT,
                    agents_woken TEXT,
                    agents_sleeping TEXT,
                    reason TEXT
                )
            """)
            conn.commit()
    
    def _get_current_context(self):
        """
        Analyze current state and return context signal.
        Returns one of: MARKET_VOLATILE, MARKET_STABLE, SABBATH, HIGH_STRESS, USER_ACTIVE, NORMAL
        Phase 6.75: Migrated to context manager for proper connection lifecycle.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()

            context = 'NORMAL'
            reasons = []

            # 1. Check Sabbath state
            c.execute("SELECT value FROM system_state WHERE key='sabbath_active'")
            row = c.fetchone()
            if row and row[0] == '1':
                return 'SABBATH', ['Sabbath mode active']

            # 2. Check system stress (graceful if table doesn't exist yet)
            try:
                c.execute("SELECT value FROM agent_experiences WHERE key='system_stress' ORDER BY timestamp DESC LIMIT 1")
                row = c.fetchone()
                if row and row[0]:
                    try:
                        stress = int(float(row[0]))
                        if stress > 80:
                            return 'HIGH_STRESS', [f'System stress: {stress}%']
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                logging.debug(f"[ROUTER] agent_experiences table not ready: {e}")

            # 3. Check recent user activity (bridge messages in last 5 min)
            try:
                c.execute("""
                    SELECT count(*) FROM inbox
                    WHERE sender='USER' AND timestamp > datetime('now', '-5 minutes')
                """)
                row = c.fetchone()
                if row and row[0] > 0:
                    context = 'USER_ACTIVE'
                    reasons.append(f'{row[0]} recent user messages')
            except Exception as e:
                logging.debug(f"[ROUTER] inbox table not ready: {e}")

        # 4. Check market volatility (via Redis) — outside DB connection
        if self.redis:
            try:
                rsi_keys = self.redis.keys('rsi:*')
                extreme_count = 0
                for key in rsi_keys[:10]:
                    val = self.redis.get(key)
                    if val:
                        rsi = float(val)
                        if rsi < 30 or rsi > 70:
                            extreme_count += 1

                if extreme_count >= 4:  # Phase 12.H6: Raised from 3 to 4 to prevent borderline oscillation
                    context = 'MARKET_VOLATILE'
                    reasons.append(f'{extreme_count} assets with extreme RSI')
            except (redis.RedisError, ValueError):
                pass

        return context, reasons
    
    def _get_agents_to_activate(self, context):
        """Given context, return list of agents that should be active."""
        active_categories = self.CONTEXT_ACTIVATIONS.get(context, ['ALWAYS_ON'])
        
        agents_to_wake = []
        for agent_name, profile in self.AGENT_PROFILES.items():
            if profile['category'] in active_categories:
                agents_to_wake.append(agent_name)
        
        return agents_to_wake, active_categories
    
    def _broadcast_activation(self, agents_to_wake, agents_to_sleep, reason):
        """
        Broadcast activation/deactivation signals via Redis.
        Agents listen on 'router_commands' channel.
        """
        if not self.redis:
            return
        
        command = {
            'type': 'ROUTING_UPDATE',
            'source': self.name,
            'timestamp': datetime.now().isoformat(),
            'wake': agents_to_wake,
            'sleep': agents_to_sleep,
            'reason': reason
        }
        
        self.redis.publish('router_commands', json.dumps(command))
        
        # Also set individual agent states
        for agent in agents_to_wake:
            self.redis.set(f"agent_state:{agent}", "ACTIVE")
        for agent in agents_to_sleep:
            self.redis.set(f"agent_state:{agent}", "SLEEPING")
        
        logging.info(f"[ROUTER] 📡 Broadcast: Wake {len(agents_to_wake)}, Sleep {len(agents_to_sleep)}")
    
    def _log_decision(self, context, active_categories, agents_woken, agents_sleeping, reason):
        """Log routing decision for audit trail."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO routing_decisions
                    (context, active_categories, agents_woken, agents_sleeping, reason)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    context,
                    json.dumps(active_categories),
                    json.dumps(agents_woken),
                    json.dumps(agents_sleeping),
                    reason
                ))
                conn.commit()
        except Exception as e:
            logging.debug(f"[ROUTER] Failed to log decision: {e}")
    
    def route(self):
        """
        Main routing logic. Analyzes context and broadcasts activation signals.
        Now integrates with BiologicalSystems for circadian modulation.
        """
        # 0. Get biological state (circadian + energy)
        try:
            from departments.Dept_Health.biological_systems import BiologicalSystems
            bio = BiologicalSystems(self.db_path)
            circadian = bio.get_circadian_state()
            bio.broadcast_biological_state()
            
            # Override context based on circadian if more restrictive
            circadian_context = None
            if circadian['state'] == 'SLEEPING':
                circadian_context = 'HIGH_STRESS'  # Reduces to ALWAYS_ON agents only
            elif circadian['state'] in ('DROWSY', 'WAKING'):
                circadian_context = 'MARKET_CLOSED'  # Wind down/ramp up
            elif circadian['state'] == 'SABBATH':
                circadian_context = 'SABBATH'
            elif circadian['state'] in ['NIGHT', 'NIGHT_LATE'] and circadian['activity_multiplier'] < 0.3:
                circadian_context = 'MARKET_CLOSED'
            
            # Check energy conservation
            if bio.should_conserve_energy():
                circadian_context = 'HIGH_STRESS'  # Use minimal agents
                logging.warning("[ROUTER] ⚡ LOW ENERGY: Entering conservation mode")
        except Exception as e:
            logging.debug(f"[ROUTER] BiologicalSystems unavailable: {e}")
            circadian_context = None
        
        # 1. Get current context
        context, reasons = self._get_current_context()
        
        # Apply circadian override if more restrictive
        if circadian_context:
            context = circadian_context
            reasons.append(f"Circadian override: {circadian_context}")
        
        reason_str = "; ".join(reasons) if reasons else "Normal operation"
        
        # 2. Determine which agents should be active
        agents_to_wake, active_categories = self._get_agents_to_activate(context)
        
        # 3. Determine which agents should sleep
        all_agents = set(self.AGENT_PROFILES.keys())
        agents_to_sleep = list(all_agents - set(agents_to_wake))
        
        # 4. Suppress duplicate broadcasts + hysteresis to prevent oscillation
        # A new context must persist for 2 consecutive cycles before we broadcast the change.
        # This prevents NORMAL ↔ MARKET_VOLATILE flip-flopping when RSI is borderline.
        wake_set = frozenset(agents_to_wake)

        if context == self._last_context and wake_set == self._last_wake_set:
            # Same as last broadcast — suppress
            self._suppress_count += 1
            self._pending_context = None  # Reset any pending change
            self._pending_count = 0
            if self._suppress_count % 10 == 0:
                logging.info(f"[ROUTER] 🎯 Context: {context} | Active: {len(agents_to_wake)} agents | Stable ({self._suppress_count} cycles)")
            return {
                'context': context,
                'active_agents': agents_to_wake,
                'sleeping_agents': agents_to_sleep,
                'reason': reason_str
            }

        # Context differs from last broadcast — apply hysteresis
        if context == self._pending_context and wake_set == self._pending_wake_set:
            self._pending_count += 1
        else:
            # New pending context — start counting
            self._pending_context = context
            self._pending_wake_set = wake_set
            self._pending_count = 1

        if self._pending_count < 2:
            # Not yet stable — don't broadcast, keep old context active
            logging.debug(f"[ROUTER] Pending context: {context} (seen {self._pending_count}/2, waiting for stability)")
            return {
                'context': self._last_context or context,
                'active_agents': agents_to_wake,
                'sleeping_agents': agents_to_sleep,
                'reason': reason_str
            }

        # Context persisted for 2+ cycles — commit the change
        if self._suppress_count > 0:
            logging.info(f"[ROUTER] Context shifted after {self._suppress_count} stable cycles")
        self._last_context = context
        self._last_wake_set = wake_set
        self._suppress_count = 0
        self._pending_context = None
        self._pending_count = 0

        self._broadcast_activation(agents_to_wake, agents_to_sleep, reason_str)

        # 5. Log decision
        self._log_decision(context, active_categories, agents_to_wake, agents_to_sleep, reason_str)

        logging.info(f"[ROUTER] 🎯 Context CHANGED: {context} | Active: {len(agents_to_wake)} agents | Reason: {reason_str}")
        
        return {
            'context': context,
            'active_agents': agents_to_wake,
            'sleeping_agents': agents_to_sleep,
            'reason': reason_str
        }
    
    def get_agent_state(self, agent_name):
        """
        Check if an agent should be active.
        Called by agents to determine if they should run their cycle.
        """
        if not self.redis:
            return True  # Default to active if no Redis
        
        state = self.redis.get(f"agent_state:{agent_name}")
        if state == "SLEEPING":
            return False
        return True
    
    def run_cycle(self):
        """
        Main loop. Re-evaluates routing every 60 seconds.
        Phase 12.H6: Reduced from 30s to 60s to lower pool pressure.
        Duplicate broadcasts suppressed in route() — only logs/broadcasts on context change.
        """
        logging.info("[ROUTER] 🧠 Starting routing cycle...")
        backoff = 60

        while True:
            try:
                self._heartbeat()
                self.route()
                time.sleep(60)  # Re-evaluate every 60 seconds
                backoff = 60  # Reset backoff on success

            except Exception as e:
                logging.error(f"[ROUTER] Cycle error: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)  # Exponential backoff, cap at 5 min


def run_router_loop(db_path=None):
    """Entry point for main.py thread"""
    agent = AgentRouter(db_path)
    agent.run_cycle()


# Utility for agents to check their state
def should_agent_run(agent_name):
    """
    Quick check for agents to call at start of their loop.
    Returns True if agent should run, False if it should sleep.
    """
    try:
        from system.redis_client import get_redis
        r = get_redis()
        if r:
            state = r.get(f"agent_state:{agent_name}")
            return state != "SLEEPING"
        return True
    except ImportError:
        try:
            r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=6379, db=0, decode_responses=True)
            state = r.get(f"agent_state:{agent_name}")
            return state != "SLEEPING"
        except (redis.RedisError, ConnectionError):
            return True  # Default to active


if __name__ == "__main__":
    router = AgentRouter()
    result = router.route()
    print(f"\nContext: {result['context']}")
    print(f"\nActive ({len(result['active_agents'])}):")
    for agent in result['active_agents']:
        print(f"  ✓ {agent}")
    print(f"\nSleeping ({len(result['sleeping_agents'])}):")
    for agent in result['sleeping_agents']:
        print(f"  💤 {agent}")
