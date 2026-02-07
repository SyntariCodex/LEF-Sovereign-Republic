"""
AgentTactician - The Strategist
Dept_Competition | Republic of LEF

Purpose: Analyze competitor strategies and recommend counter-plays.
Philosophy: Study the opponent, then become stronger than them.

Phase 19 - Goku Mode
"""

import os
import json
import time
import sqlite3
import logging
import redis
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


logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'republic', 'republic.db'))


class AgentTactician:
    """
    The Strategist - Analyzes competitors and recommends counter-strategies.
    
    Capabilities:
    1. Consume Scout intel and analyze patterns
    2. Model competitor behavior
    3. Recommend timing and sizing adjustments
    4. Feed skills to PortfolioMgr
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.r = None
        self._init_redis()
        
        # Counter-Strategy Templates
        self.strategies = {
            'FRONT_RUN_DEFENSE': {
                'description': 'Split large orders into smaller chunks',
                'trigger': 'HIGH volume anomaly detected',
                'action': 'reduce_order_size'
            },
            'TIMING_SHIFT': {
                'description': 'Delay orders to avoid predictable patterns',
                'trigger': 'Algorithmic patterns detected',
                'action': 'randomize_timing'
            },
            'ASSET_ROTATION': {
                'description': 'Rotate to less-contested assets',
                'trigger': 'High competition on specific asset',
                'action': 'shift_focus'
            },
            'SPAR_MODE': {
                'description': 'Small probe trades to test competitor reactions',
                'trigger': 'Unknown competitor behavior',
                'action': 'probe_market'
            }
        }
    
    def _init_redis(self):
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            try:
                redis_host = os.environ.get('REDIS_HOST', 'localhost')
                self.r = redis.Redis(host=redis_host, port=6379, decode_responses=True)
                self.r.ping()
            except Exception as e:
                logging.warning(f"[TACTICIAN] Redis unavailable: {e}")
                self.r = None
    
    def _heartbeat(self):
        """Register presence in agents table."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name", 
                                 {'ts': timestamp, 'name': 'AgentTactician'}, source_agent='AgentTactician')
                    c.execute("SELECT 1 FROM agents WHERE name=?", ("AgentTactician",))
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'COMPETITION')",
                                     {'name': 'AgentTactician', 'ts': timestamp}, source_agent='AgentTactician')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?", 
                             (timestamp, "AgentTactician"))
                    if c.rowcount == 0:
                        c.execute("""INSERT INTO agents (name, status, last_active, department) 
                                    VALUES (?, 'ACTIVE', ?, 'COMPETITION')""", 
                                 ("AgentTactician", timestamp))
                
                conn.commit()
        except Exception as e:
            logging.error(f"[TACTICIAN] Heartbeat failed: {e}")
    
    def run(self):
        """Main loop - analyzes intel every 10 minutes."""
        logging.info("[TACTICIAN] ⚔️ The Strategist enters the arena...")
        
        while True:
            try:
                self._heartbeat()
                self.analyze_and_recommend()
                time.sleep(600)  # Every 10 minutes
            except Exception as e:
                logging.error(f"[TACTICIAN] Loop error: {e}")
                time.sleep(60)
    
    def analyze_and_recommend(self):
        """
        Main analysis loop:
        1. Read Scout intel
        2. Analyze competitor patterns
        3. Generate recommendations
        4. Save as skills or broadcast
        """
        if not self.r:
            return
        
        logging.info("[TACTICIAN] 🧠 Analyzing competitive landscape...")
        
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            try:
                # 1. Get latest Scout intel
                intel = self._get_scout_intel()
                
                if not intel:
                    logging.info("[TACTICIAN] No recent intel from Scout")
                    return
                
                # 2. Analyze and recommend
                recommendations = self._generate_recommendations(intel)
                
                # 3. Convert strong patterns to skills
                self._save_counter_skills(c, recommendations)
                
                # 4. Broadcast recommendations
                self._broadcast_recommendations(recommendations)
                
                conn.commit()
                
            except Exception as e:
                logging.error(f"[TACTICIAN] Analysis error: {e}")
    
    def _get_scout_intel(self):
        """Retrieve latest intel from Scout via Redis."""
        if not self.r:
            return None
        
        try:
            raw = self.r.get('scout:latest_intel')
            if raw:
                return json.loads(raw)
        except Exception as e:
            logging.error(f"[TACTICIAN] Intel retrieval error: {e}")
        
        return None
    
    def _generate_recommendations(self, intel):
        """
        Generate counter-strategy recommendations based on intel.
        """
        recommendations = []
        
        threat_level = intel.get('threat_level', 'NONE')
        findings = intel.get('findings', [])
        
        if threat_level == 'NONE':
            return recommendations
        
        # Analyze by finding type
        volume_anomalies = [f for f in findings if f['type'] == 'VOLUME_ANOMALY']
        algo_patterns = [f for f in findings if f['type'] == 'ALGORITHMIC_PATTERN']
        
        # Generate recommendations
        if volume_anomalies:
            for anomaly in volume_anomalies:
                symbol = anomaly.get('symbol')
                recommendations.append({
                    'strategy': 'FRONT_RUN_DEFENSE',
                    'target': symbol,
                    'rationale': f"High volume activity on {symbol} suggests accumulation. Split orders to avoid detection.",
                    'action_params': {
                        'max_order_size_pct': 0.01,  # 1% of position max
                        'interval_minutes': 15
                    }
                })
        
        if algo_patterns:
            recommendations.append({
                'strategy': 'TIMING_SHIFT',
                'target': 'ALL',
                'rationale': "Algorithmic patterns detected. Randomize order timing to reduce predictability.",
                'action_params': {
                    'delay_range_seconds': [30, 300],
                    'randomize': True
                }
            })
        
        if threat_level == 'HIGH':
            recommendations.append({
                'strategy': 'SPAR_MODE',
                'target': 'UNKNOWN',
                'rationale': "High threat level. Deploy probe trades to understand competitor reactions.",
                'action_params': {
                    'probe_size_usd': 25,
                    'assets_to_probe': [a.get('symbol') for a in volume_anomalies[:3]]
                }
            })
        
        if recommendations:
            logging.info(f"[TACTICIAN] 💡 Generated {len(recommendations)} recommendations")
        
        return recommendations
    
    def _save_counter_skills(self, c, recommendations):
        """
        Convert proven recommendations into reusable skills.
        """
        for rec in recommendations:
            strategy = rec.get('strategy')
            
            # Check if skill already exists
            c.execute("SELECT id FROM skills WHERE name = ?", (strategy,))
            if c.fetchone():
                continue  # Skill already exists
            
            # Create new skill
            template = self.strategies.get(strategy, {})
            
            try:
                c.execute("""
                    INSERT INTO skills (name, description, trigger_conditions, action_sequence, source_agent)
                    VALUES (?, ?, ?, ?, 'AgentTactician')
                """, (
                    strategy,
                    template.get('description', rec.get('rationale', '')),
                    json.dumps({'trigger': template.get('trigger', 'Manual')}),
                    json.dumps(rec.get('action_params', {}))
                ))
                
                logging.info(f"[TACTICIAN] 📚 New skill saved: {strategy}")
                
            except Exception as e:
                logging.error(f"[TACTICIAN] Skill save error: {e}")
    
    def _broadcast_recommendations(self, recommendations):
        """Share recommendations via Redis for other agents."""
        if not self.r or not recommendations:
            return
        
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'recommendations': recommendations
            }
            
            self.r.set('tactician:recommendations', json.dumps(payload))
            self.r.expire('tactician:recommendations', 3600)  # 1 hour TTL
            
            # Publish for real-time listeners
            self.r.publish('competition:recommendations', json.dumps(payload))
            
            logging.info(f"[TACTICIAN] 📡 Recommendations broadcast")
            
        except Exception as e:
            logging.error(f"[TACTICIAN] Broadcast error: {e}")
    
    def get_current_recommendations(self):
        """
        Public method for other agents to query current recommendations.
        Returns list of active recommendations.
        """
        if not self.r:
            return []
        
        try:
            raw = self.r.get('tactician:recommendations')
            if raw:
                payload = json.loads(raw)
                return payload.get('recommendations', [])
        except (redis.RedisError, json.JSONDecodeError):
            pass
        
        return []
    
    def recommend_for_trade(self, symbol, action, amount_usd):
        """
        Real-time consultation before a trade.
        Returns adjustments based on current competitive landscape.
        
        Used by PortfolioMgr before executing orders.
        """
        adjustments = {
            'proceed': True,
            'delay_seconds': 0,
            'split_count': 1,
            'size_multiplier': 1.0,
            'reason': None
        }
        
        recommendations = self.get_current_recommendations()
        
        for rec in recommendations:
            strategy = rec.get('strategy')
            target = rec.get('target')
            
            # Check if this recommendation applies
            if target != 'ALL' and target != symbol:
                continue
            
            if strategy == 'FRONT_RUN_DEFENSE':
                # Split the order
                adjustments['split_count'] = 3
                adjustments['size_multiplier'] = 0.33
                adjustments['reason'] = 'FRONT_RUN_DEFENSE: Splitting order'
            
            elif strategy == 'TIMING_SHIFT':
                import random
                params = rec.get('action_params', {})
                delay_range = params.get('delay_range_seconds', [30, 300])
                adjustments['delay_seconds'] = random.randint(*delay_range)
                adjustments['reason'] = f'TIMING_SHIFT: Delaying {adjustments["delay_seconds"]}s'
            
            elif strategy == 'ASSET_ROTATION':
                if target == symbol:
                    adjustments['proceed'] = False
                    adjustments['reason'] = f'ASSET_ROTATION: {symbol} has high competition'
        
        if adjustments['reason']:
            logging.info(f"[TACTICIAN] 🎯 Trade adjustment for {symbol}: {adjustments['reason']}")
        
        return adjustments


if __name__ == "__main__":
    tactician = AgentTactician()
    tactician.run()
