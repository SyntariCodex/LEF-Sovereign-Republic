"""
Biological Systems Module
Department: Dept_Health
Role: Centralizes biological metaphors - circadian rhythms, metabolism, energy budgets.

Biological Patterns:
    - Circadian Rhythms: Time-of-day activity modulation
    - Metabolism: Resource consumption tracking (API calls, compute, storage)
    - Energy Budget: Rate limiting as "available energy"
    - Homeostasis: System stability metrics

This module is queried by the Router to adjust agent activity.
"""

import sqlite3
import os
import time
import json
import logging
import redis
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

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


class BiologicalSystems:
    """
    Centralized biological systems for LEF.
    
    Circadian States:
        DAWN (5am-9am): Waking up, low activity, prepare for day
        DAY (9am-5pm): Peak activity, trading hours
        DUSK (5pm-9pm): Winding down, reflection
        NIGHT (9pm-5am): Minimal activity, maintenance only
        SABBATH: Special state, deep reflection
    
    Metabolic Rates:
        BASE: 0.0001 ETH/hour equivalent (simulated)
        ACTIVE: Scales with agent activity count
        PEAK: During high-volatility or crisis
    """
    
    CIRCADIAN_STATES = {
        'DAWN': {'hours': (5, 9), 'activity_multiplier': 0.5, 'priority': ['BACKGROUND', 'CONSCIOUSNESS']},
        'DAY': {'hours': (9, 17), 'activity_multiplier': 1.0, 'priority': ['MARKET_HOURS', 'COMPETITION']},
        'DUSK': {'hours': (17, 21), 'activity_multiplier': 0.7, 'priority': ['CONSCIOUSNESS', 'BACKGROUND']},
        'NIGHT': {'hours': (21, 24), 'activity_multiplier': 0.3, 'priority': ['ALWAYS_ON']},
        'NIGHT_LATE': {'hours': (0, 5), 'activity_multiplier': 0.2, 'priority': ['ALWAYS_ON']},
    }
    
    # Metabolic cost in simulated USD per hour
    METABOLIC_COSTS = {
        'base_rate': 0.12,       # $0.12/hour base (like server costs)
        'per_agent': 0.01,       # $0.01/hour per active agent
        'api_call': 0.0001,      # $0.0001 per API call
        'llm_call': 0.002,       # $0.002 per LLM call (Gemini Flash)
        'trade_execution': 0.01, # $0.01 per trade executed
    }
    
    _initialized_once = False  # Class-level flag to log startup only once

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        if not BiologicalSystems._initialized_once:
            logging.info("[BIO] 🧬 Biological Systems Online")
            BiologicalSystems._initialized_once = True
        
        # Redis for state - Use shared singleton
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
        
        self._ensure_tables()
    
    def _get_db_connection(self):
        """DEPRECATED: Use `with db_connection(self.db_path) as conn:` instead."""
        import warnings
        warnings.warn("_get_db_connection is deprecated, use db_connection context manager", DeprecationWarning)
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_tables(self):
        """Create metabolism tracking tables."""
        conn = self._get_db_connection()
        c = conn.cursor()
        
        # Metabolic log
        c.execute("""
            CREATE TABLE IF NOT EXISTS metabolism_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                cost_usd REAL,
                source TEXT,
                details TEXT
            )
        """)
        
        # Energy budget
        c.execute("""
            CREATE TABLE IF NOT EXISTS energy_budget (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                daily_budget_usd REAL DEFAULT 10.0,
                spent_usd REAL DEFAULT 0.0,
                api_calls INTEGER DEFAULT 0,
                llm_calls INTEGER DEFAULT 0,
                trades_executed INTEGER DEFAULT 0,
                active_agent_hours REAL DEFAULT 0.0
            )
        """)
        
        # Circadian log
        c.execute("""
            CREATE TABLE IF NOT EXISTS circadian_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                state TEXT,
                activity_multiplier REAL,
                active_agents INTEGER,
                reason TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_circadian_state(self):
        """
        Determine current circadian state based on local time.
        Also checks for Sabbath mode.
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        # Phase 14: Check sleep state first (overrides circadian)
        try:
            c.execute("SELECT value FROM system_state WHERE key='sleep_state'")
            row = c.fetchone()
            if row and row[0] in ('SLEEPING', 'DROWSY', 'WAKING'):
                sleep_state = row[0]
                conn.close()
                return {
                    'state': sleep_state,
                    'activity_multiplier': 0.0 if sleep_state == 'SLEEPING' else 0.2,
                    'priority': [] if sleep_state == 'SLEEPING' else ['ALWAYS_ON'],
                    'reason': f'Sleep cycle: {sleep_state}'
                }
        except Exception:
            pass

        # Check Sabbath
        c.execute("SELECT value FROM system_state WHERE key='sabbath_active'")
        row = c.fetchone()
        if row and row[0] == '1':
            conn.close()
            return {
                'state': 'SABBATH',
                'activity_multiplier': 0.1,
                'priority': ['CONSCIOUSNESS'],
                'reason': 'Sabbath rest period active'
            }
        
        conn.close()
        
        # Get current hour
        now = datetime.now()
        hour = now.hour
        
        # Determine state
        for state_name, config in self.CIRCADIAN_STATES.items():
            start, end = config['hours']
            if start <= hour < end:
                return {
                    'state': state_name,
                    'activity_multiplier': config['activity_multiplier'],
                    'priority': config['priority'],
                    'reason': f'Local time {now.strftime("%H:%M")} falls in {state_name} period'
                }
        
        # Fallback (shouldn't reach here)
        return {
            'state': 'DAY',
            'activity_multiplier': 1.0,
            'priority': ['MARKET_HOURS'],
            'reason': 'Default state'
        }
    
    def record_metabolic_cost(self, category, cost_usd, source, details=None):
        """
        Track metabolic expenditure.
        Categories: base, api_call, llm_call, trade, agent_time
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        # Log the cost
        c.execute("""
            INSERT INTO metabolism_log (category, cost_usd, source, details)
            VALUES (?, ?, ?, ?)
        """, (category, cost_usd, source, details))
        
        # Update daily budget
        today = datetime.now().strftime('%Y-%m-%d')

        # Ensure today's budget exists
        from db.db_helper import ignore_insert_sql
        sql = ignore_insert_sql('energy_budget', ['date'], 'date')
        c.execute(sql, (today,))
        
        # Update spent amount
        c.execute("UPDATE energy_budget SET spent_usd = spent_usd + ? WHERE date = ?", (cost_usd, today))
        
        # Update category counters
        if category == 'api_call':
            c.execute("UPDATE energy_budget SET api_calls = api_calls + 1 WHERE date = ?", (today,))
        elif category == 'llm_call':
            c.execute("UPDATE energy_budget SET llm_calls = llm_calls + 1 WHERE date = ?", (today,))
        elif category == 'trade':
            c.execute("UPDATE energy_budget SET trades_executed = trades_executed + 1 WHERE date = ?", (today,))
        
        conn.commit()
        conn.close()
    
    def get_energy_remaining(self):
        """
        Check remaining energy budget for today.
        Returns (remaining_usd, percentage_remaining)
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT daily_budget_usd, spent_usd FROM energy_budget WHERE date = ?", (today,))
        row = c.fetchone()
        
        conn.close()
        
        if not row:
            return 10.0, 100.0  # Full budget if no record
        
        budget = row[0]
        spent = row[1]
        remaining = max(0, budget - spent)
        percentage = (remaining / budget) * 100 if budget > 0 else 0
        
        return remaining, percentage
    
    def should_conserve_energy(self):
        """
        Returns True if system should reduce activity to conserve energy.
        Triggers when less than 20% of daily budget remains.
        """
        remaining, percentage = self.get_energy_remaining()
        return percentage < 20
    
    def get_metabolic_summary(self):
        """
        Get today's metabolic activity summary.
        """
        conn = self._get_db_connection()
        c = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("""
            SELECT daily_budget_usd, spent_usd, api_calls, llm_calls, trades_executed
            FROM energy_budget WHERE date = ?
        """, (today,))
        row = c.fetchone()
        
        conn.close()
        
        if not row:
            return {
                'date': today,
                'budget': 10.0,
                'spent': 0.0,
                'remaining': 10.0,
                'api_calls': 0,
                'llm_calls': 0,
                'trades': 0
            }
        
        return {
            'date': today,
            'budget': row[0],
            'spent': row[1],
            'remaining': max(0, row[0] - row[1]),
            'api_calls': row[2],
            'llm_calls': row[3],
            'trades': row[4]
        }
    
    def log_circadian_transition(self, new_state, active_agents, reason):
        """Log when circadian state changes."""
        conn = self._get_db_connection()
        c = conn.cursor()
        
        state_info = self.CIRCADIAN_STATES.get(new_state, {})
        multiplier = state_info.get('activity_multiplier', 1.0)
        
        c.execute("""
            INSERT INTO circadian_log (state, activity_multiplier, active_agents, reason)
            VALUES (?, ?, ?, ?)
        """, (new_state, multiplier, active_agents, reason))
        
        conn.commit()
        conn.close()
    
    def broadcast_biological_state(self):
        """Push current biological state to Redis for other agents."""
        if not self.redis:
            return
        
        circadian = self.get_circadian_state()
        remaining, pct = self.get_energy_remaining()
        conserve = self.should_conserve_energy()
        
        state = {
            'circadian_state': circadian['state'],
            'activity_multiplier': circadian['activity_multiplier'],
            'priority_categories': circadian['priority'],
            'energy_remaining_usd': remaining,
            'energy_percentage': pct,
            'conserve_mode': conserve,
            'timestamp': datetime.now().isoformat()
        }
        
        self.redis.set('biological_state', json.dumps(state))
        return state


# Utility functions for other agents
def get_activity_multiplier():
    """Quick check for agents to scale their activity."""
    try:
        bio = BiologicalSystems()
        state = bio.get_circadian_state()
        
        # Also check energy conservation
        if bio.should_conserve_energy():
            return state['activity_multiplier'] * 0.5  # Further reduce if low energy
        
        return state['activity_multiplier']
    except Exception:
        return 1.0  # Default to full activity


def record_api_call(source):
    """Track an API call in metabolism."""
    try:
        bio = BiologicalSystems()
        bio.record_metabolic_cost('api_call', bio.METABOLIC_COSTS['api_call'], source)
    except Exception:
        pass


def record_llm_call(source):
    """Track an LLM call in metabolism."""
    try:
        bio = BiologicalSystems()
        bio.record_metabolic_cost('llm_call', bio.METABOLIC_COSTS['llm_call'], source)
    except Exception:
        pass


def record_trade(source):
    """Track a trade execution in metabolism."""
    try:
        bio = BiologicalSystems()
        bio.record_metabolic_cost('trade', bio.METABOLIC_COSTS['trade_execution'], source)
    except Exception:
        pass


if __name__ == "__main__":
    bio = BiologicalSystems()
    
    print("\n🧬 BIOLOGICAL SYSTEMS STATUS\n")
    
    # Circadian
    circadian = bio.get_circadian_state()
    print(f"Circadian State: {circadian['state']}")
    print(f"Activity Multiplier: {circadian['activity_multiplier']}")
    print(f"Priority Categories: {circadian['priority']}")
    print(f"Reason: {circadian['reason']}")
    
    # Energy
    remaining, pct = bio.get_energy_remaining()
    print(f"\nEnergy Remaining: ${remaining:.2f} ({pct:.1f}%)")
    print(f"Conservation Mode: {bio.should_conserve_energy()}")
    
    # Summary
    summary = bio.get_metabolic_summary()
    print(f"\nToday's Metabolism:")
    print(f"  Budget: ${summary['budget']:.2f}")
    print(f"  Spent: ${summary['spent']:.2f}")
    print(f"  API Calls: {summary['api_calls']}")
    print(f"  LLM Calls: {summary['llm_calls']}")
    print(f"  Trades: {summary['trades']}")
