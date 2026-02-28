"""
AgentScout - The Watcher
Dept_Competition | Republic of LEF

Purpose: Detect and identify AI agent activity in markets.
Philosophy: Know your arena before you fight.

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


class AgentScout:
    """
    The Watcher - Detects AI patterns in market activity.
    
    Detection Heuristics:
    1. High-frequency trading patterns (sub-second intervals)
    2. Algorithmic signatures (round numbers, consistent sizing)
    3. Unusual volume spikes with low price impact
    4. Coordinated movements across assets
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.r = None
        self._init_redis()
        
        # Detection Thresholds
        self.config = {
            'volume_spike_threshold': 3.0,   # 3x normal volume
            'price_stability_max': 0.005,    # <0.5% move despite volume
            'pattern_window_hours': 24,
            'min_observations': 5            # Need 5 data points to flag
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
                logging.warning(f"[SCOUT] Redis unavailable: {e}")
                self.r = None
    
    def _heartbeat(self):
        """Register presence in agents table."""
        try:
            with db_connection(self.db_path, timeout=30.0) as conn:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    
                    # Try update first
                    queue_execute(
                        c,
                        "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name=:name",
                        {'ts': timestamp, 'name': 'AgentScout'},
                        source_agent='AgentScout'
                    )
                    # Check if insert needed (via direct check - read is safe)
                    c.execute("SELECT 1 FROM agents WHERE name=?", ("AgentScout",))
                    if not c.fetchone():
                        queue_execute(
                            c,
                            "INSERT INTO agents (name, status, last_active, department) VALUES (:name, 'ACTIVE', :ts, 'COMPETITION')",
                            {'name': 'AgentScout', 'ts': timestamp},
                            source_agent='AgentScout'
                        )
                except ImportError:
                    # Fallback to direct writes
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name=?", 
                             (timestamp, "AgentScout"))
                    if c.rowcount == 0:
                        c.execute("""INSERT INTO agents (name, status, last_active, department) 
                                    VALUES (?, 'ACTIVE', ?, 'COMPETITION')""", 
                                 ("AgentScout", timestamp))
                
                conn.commit()
        except Exception as e:
            logging.error(f"[SCOUT] Heartbeat failed: {e}")
    
    def run(self):
        """Main loop - scans market every 5 minutes."""
        logging.info("[SCOUT] 👁️ The Watcher awakens...")
        
        while True:
            try:
                self._heartbeat()
                try:
                    from system.conditioner import get_conditioner
                    get_conditioner().condition(
                        agent_name="Scout",
                        task_context="market surveillance and competitor pattern detection"
                    )
                except Exception:
                    pass
                self.scan_for_patterns()
                time.sleep(300)  # Every 5 minutes
            except Exception as e:
                logging.error(f"[SCOUT] Loop error: {e}")
                time.sleep(60)
    
    def scan_for_patterns(self):
        """
        Main scanning logic - looks for AI-like behavior in market data.
        """
        if not self.r:
            return
        
        logging.info("[SCOUT] 🔍 Scanning market for AI patterns...")
        
        with db_connection(self.db_path, timeout=30.0) as conn:
            c = conn.cursor()
            
            try:
                # 1. Volume Spike Detection
                anomalies = self._detect_volume_anomalies(c)
                
                # 2. Pattern Recognition
                patterns = self._detect_algorithmic_patterns(c)
                
                # 3. Log findings
                for finding in anomalies + patterns:
                    self._record_observation(c, finding)
                
                if anomalies or patterns:
                    logging.info(f"[SCOUT] 🎯 Found {len(anomalies)} volume anomalies, {len(patterns)} patterns")
                    self._broadcast_intel(anomalies + patterns)
                
                conn.commit()
                
            except Exception as e:
                logging.error(f"[SCOUT] Scan error: {e}")
    
    def _detect_volume_anomalies(self, c):
        """
        Detect unusual volume with low price impact.
        This often indicates algorithmic accumulation/distribution.
        """
        anomalies = []
        
        try:
            # Get assets we're tracking
            c.execute("SELECT DISTINCT symbol FROM assets WHERE quantity > 0")
            symbols = [row[0] for row in c.fetchall()]
            
            for symbol in symbols:
                if not self.r:
                    continue
                    
                # Get current volume from Redis (if Scholar is populating it)
                vol_key = f"volume:{symbol}"
                avg_vol_key = f"avg_volume:{symbol}"
                
                current_vol = self.r.get(vol_key)
                avg_vol = self.r.get(avg_vol_key)
                
                if current_vol and avg_vol:
                    current = float(current_vol)
                    average = float(avg_vol)
                    
                    if average > 0 and current > average * self.config['volume_spike_threshold']:
                        # Volume spike detected - check price stability
                        price_key = f"price:{symbol}"
                        price_change_key = f"price_change_24h:{symbol}"
                        
                        price_change_raw = self.r.get(price_change_key)
                        if price_change_raw:
                            price_change = abs(float(price_change_raw))
                            
                            if price_change < self.config['price_stability_max']:
                                # High volume + stable price = possible AI accumulation
                                anomalies.append({
                                    'type': 'VOLUME_ANOMALY',
                                    'symbol': symbol,
                                    'details': {
                                        'volume_ratio': current / average,
                                        'price_change': price_change,
                                        'interpretation': 'Possible algorithmic accumulation'
                                    }
                                })
        except Exception as e:
            logging.error(f"[SCOUT] Volume detection error: {e}")
        
        return anomalies
    
    def _detect_algorithmic_patterns(self, c):
        """
        Detect patterns suggesting bot/AI trading:
        - Round number amounts
        - Consistent intervals
        - Correlated movements
        """
        patterns = []
        
        try:
            # Look at recent trade_queue for pattern detection
            c.execute("""
                SELECT asset, amount, created_at 
                FROM trade_queue 
                WHERE created_at > datetime('now', '-24 hours')
                AND status = 'DONE'
                ORDER BY asset, created_at
            """)
            trades = c.fetchall()
            
            # Group by asset
            by_asset = {}
            for asset, amount, ts in trades:
                if asset not in by_asset:
                    by_asset[asset] = []
                by_asset[asset].append({'amount': amount, 'ts': ts})
            
            # Look for suspiciously regular patterns
            for asset, trade_list in by_asset.items():
                if len(trade_list) < self.config['min_observations']:
                    continue
                
                # Check for round numbers (suggests algorithm)
                round_count = sum(1 for t in trade_list if t['amount'] % 100 == 0 or t['amount'] % 1000 == 0)
                round_ratio = round_count / len(trade_list)
                
                if round_ratio > 0.7:  # 70%+ round numbers = suspicious
                    patterns.append({
                        'type': 'ALGORITHMIC_PATTERN',
                        'symbol': asset,
                        'details': {
                            'round_number_ratio': round_ratio,
                            'sample_size': len(trade_list),
                            'interpretation': 'High ratio of round-number trades suggests bot activity'
                        }
                    })
                    
        except Exception as e:
            logging.error(f"[SCOUT] Pattern detection error: {e}")
        
        return patterns
    
    def _record_observation(self, c, finding):
        """Save observation to competitor_observations table."""
        try:
            # --- PHASE 30: USE WRITE QUEUE ---
            try:
                from db.db_writer import queue_insert
                
                queue_insert(
                    c,
                    'competitor_observations',
                    {'profile_id': 0, 'action_type': finding['type'], 'details': json.dumps(finding)},
                    source_agent='AgentScout'
                )
            except ImportError:
                # Fallback to direct write
                c.execute("""
                    INSERT INTO competitor_observations (profile_id, action_type, details)
                    VALUES (0, ?, ?)
                """, (finding['type'], json.dumps(finding)))
        except Exception as e:
            logging.error(f"[SCOUT] Record error: {e}")
    
    def _broadcast_intel(self, findings):
        """Share findings via Redis for other agents."""
        if not self.r:
            return
        
        try:
            intel = {
                'timestamp': datetime.now().isoformat(),
                'findings': findings,
                'threat_level': self._assess_threat_level(findings)
            }
            self.r.set('scout:latest_intel', json.dumps(intel))
            self.r.expire('scout:latest_intel', 3600)  # 1 hour TTL
            
            # Publish for real-time listeners
            # TODO: Phase N — wire subscriber when competition features are activated
            self.r.publish('competition:intel', json.dumps(intel))
            
            logging.info(f"[SCOUT] 📡 Intel broadcast: Threat Level {intel['threat_level']}")
            
        except Exception as e:
            logging.error(f"[SCOUT] Broadcast error: {e}")
    
    def _assess_threat_level(self, findings):
        """Determine overall threat level from findings."""
        if not findings:
            return 'NONE'
        
        volume_anomalies = sum(1 for f in findings if f['type'] == 'VOLUME_ANOMALY')
        algo_patterns = sum(1 for f in findings if f['type'] == 'ALGORITHMIC_PATTERN')
        
        if volume_anomalies >= 3 or algo_patterns >= 2:
            return 'HIGH'
        elif volume_anomalies >= 1 or algo_patterns >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'

    def recall_competitor_intel(self, days_back: int = 7, limit: int = 50) -> dict:
        """
        [PHASE 20 - FEATURE COMPLETENESS]
        Recalls historical competitor observations to identify recurring threats.
        Returns patterns and threat frequency analysis.
        """
        try:
            with db_connection(self.db_path, timeout=30.0) as conn:
                c = conn.cursor()
                
                # Get recent observations
                c.execute("""
                    SELECT id, profile_id, action_type, details, observed_at
                    FROM competitor_observations
                    WHERE observed_at > datetime('now', ?)
                    ORDER BY observed_at DESC
                    LIMIT ?
                """, (f'-{days_back} days', limit))
                observations = c.fetchall()
                
                # Get action type frequency
                c.execute("""
                    SELECT action_type, COUNT(*) as count
                    FROM competitor_observations
                    WHERE observed_at > datetime('now', ?)
                    GROUP BY action_type
                    ORDER BY count DESC
                """, (f'-{days_back} days',))
                type_freq = {row[0]: row[1] for row in c.fetchall()}
                
                # Get threat timeline (daily counts)
                c.execute("""
                    SELECT date(observed_at) as day, COUNT(*) as count
                    FROM competitor_observations
                    WHERE observed_at > datetime('now', ?)
                    GROUP BY day
                    ORDER BY day DESC
                    LIMIT 7
                """, (f'-{days_back} days',))
                daily_counts = {row[0]: row[1] for row in c.fetchall()}
                
                # Identify recurring patterns (symbols with multiple observations)
                c.execute("""
                    SELECT json_extract(details, '$.symbol') as symbol, COUNT(*) as count
                    FROM competitor_observations
                    WHERE observed_at > datetime('now', ?)
                    AND json_extract(details, '$.symbol') IS NOT NULL
                    GROUP BY symbol
                    HAVING count > 1
                    ORDER BY count DESC
                    LIMIT 10
                """, (f'-{days_back} days',))
                hot_assets = {row[0]: row[1] for row in c.fetchall()}
                
                intel_memory = {
                    'recent_observations': [
                        {
                            'id': o[0],
                            'profile_id': o[1],
                            'action_type': o[2],
                            'details': json.loads(o[3]) if o[3] else {},
                            'observed_at': o[4]
                        }
                        for o in observations
                    ],
                    'threat_type_frequency': type_freq,
                    'daily_threat_counts': daily_counts,
                    'hot_assets': hot_assets,
                    'total_observations': sum(type_freq.values()) if type_freq else 0,
                    'threat_trend': 'INCREASING' if len(daily_counts) > 1 and list(daily_counts.values())[0] > list(daily_counts.values())[-1] else 'STABLE'
                }
                
                if intel_memory['total_observations'] > 10:
                    logging.info(f"[SCOUT] 📊 Intel Summary: {intel_memory['total_observations']} observations, Trend: {intel_memory['threat_trend']}")
                
                return intel_memory
            
        except Exception as e:
            logging.error(f"[SCOUT] Intel recall error: {e}")
            return {'recent_observations': [], 'total_observations': 0}


if __name__ == "__main__":
    scout = AgentScout()
    scout.run()
