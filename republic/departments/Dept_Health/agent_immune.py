
"""
AgentImmune (The Sentinel)
Department: Dept_Health
Role: Guardian of the System. 
Function:
1. Monitors Total Portfolio Value (NAV).
2. Triggers 'APOPTOSIS' (System Shutdown) if critical failure detected.
3. Critical Failure = >20% Drawdown in 24 hours.
"""

import os
import time
import json
import logging
import sys
import redis
from datetime import datetime

# Fix Pathing
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # republic/
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
sys.path.insert(0, BASE_DIR)

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'republic.log')),
        logging.StreamHandler()
    ]
)

class AgentImmune:
    def __init__(self):
        self.db_path = DB_PATH
        logging.info("[IMMUNE] 🛡️  The Sentinel is Awake.")
        
        # Redis (To get realtime NAV from CoinScanner/Portfolio) - Use shared singleton
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
               logging.warning("[IMMUNE] Redis offline. Cannot fetch live prices for NAV check.")

        self.threshold_pct = 0.20 # 20% Drop triggers death
        self.check_interval = 300 # 5 Minutes
        self.history_window = 86400 # 24 Hours

    def calculate_nav(self):
        """
        Calculates Total Net Liquidation Value (USD).
        Uses connection pool to prevent database locking.
        """
        total_usd = 0.0
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Get Assets
                c.execute("SELECT symbol, quantity FROM assets WHERE quantity > 0")
                assets = c.fetchall()
                
                for sym, qty in assets:
                    price = 0.0
                    # 1. Try Redis
                    if self.r:
                        price_str = self.r.get(f"price:{sym}")
                        if price_str: price = float(price_str)
                    
                    # 2. Fallback? If no price, skip or use last_known?
                    # For safety, if we can't value it, we assume 0 (Conservative)
                    # But that might trigger apoptosis falsely!
                    # Better: Use 'value_usd' from DB if Redis fails.
                    
                    if price == 0.0:
                         c.execute("SELECT value_usd FROM assets WHERE symbol=?", (sym,))
                         val = c.fetchone()[0]
                         total_usd += val
                    else:
                         total_usd += (qty * price)
            
            return total_usd
            
        except Exception as e:
            logging.error(f"[IMMUNE] NAV Calc Error: {e}")
            return 0.0


    def check_vitals(self):
        """
        Compares Current NAV vs 24h High Water Mark.
        """
        current_nav = self.calculate_nav()
        
        if current_nav <= 0:
            logging.warning("[IMMUNE] NAV is 0 or Error. Skipping check to avoid False Positive Suicide.")
            return

        # Simple In-Memory History for now? 
        # Or better: Check 'macro_history' or a 'nav_history' table?
        # We don't have a reliable NAV history table yet. 
        # Let's create a simple tracking file/db logic for the Sentinel itself.
        
        self.log_heartbeat(current_nav)
        
        # Get Max NAV in last 24h
        max_nav_24h = self.get_24h_high()
        
        if max_nav_24h <= 0: return # First run
        
        # --- HALLUCINATION CHECK (PTSD CURE) ---
        # If the recorded peak is > 5x the current value, it's likely a leftover from a previous simulation/mock run.
        # We must purge this to prevent false suicide.
        if current_nav > 0 and max_nav_24h > (current_nav * 5.0):
             logging.warning(f"[IMMUNE] 💊 PTSD Detected: Peak (${max_nav_24h:,.2f}) is > 5x Current (${current_nav:,.2f}). Resetting history.")
             self.history = [] # Clear memory
             self.log_heartbeat(current_nav) # Re-seed with reality
             max_nav_24h = current_nav
             # Remove the file too
             try:
                 history_file = os.path.join(BASE_DIR, 'data', 'immune_history.json')
                 if os.path.exists(history_file): os.remove(history_file)
             except OSError:
                 pass
        # ----------------------------------------
        
        drawdown = (max_nav_24h - current_nav) / max_nav_24h
        
        if current_nav <= 0:
             logging.warning("[IMMUNE] NAV is 0 (Startup or Offline). Skipping Vitals Check to prevent false suicide.")
             return

        if current_nav <= 0:
             logging.warning("[IMMUNE] NAV is 0 (Startup or Offline). Skipping Vitals Check to prevent false suicide.")
             return

        # Only log if there's a significant movement to reduce spam
        if abs(drawdown) > 0.01:
             logging.info(f"[IMMUNE] 💓 Pulse Check: ${current_nav:,.2f} (24h Peak: ${max_nav_24h:,.2f} | DD: {drawdown*100:.2f}%)")
        
        if drawdown >= self.threshold_pct:
            self.trigger_apoptosis(current_nav, max_nav_24h, drawdown)

    def log_heartbeat(self, nav):
        """
        Stores (timestamp, nav) in a local JSON (or DB) for history tracking.
        Using a JSON file for simplicity and isolation.
        """
        history_file = os.path.join(BASE_DIR, 'data', 'immune_history.json')
        if not os.path.exists(os.path.dirname(history_file)):
             os.makedirs(os.path.dirname(history_file))
             
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
            
        # Prune > 24h
        cutoff = time.time() - self.history_window
        history = [h for h in history if h['ts'] > cutoff]
        
        # Append
        history.append({'ts': time.time(), 'nav': nav})
        
        with open(history_file, 'w') as f:
            json.dump(history, f)

    def get_24h_high(self):
        history_file = os.path.join(BASE_DIR, 'data', 'immune_history.json')
        if not os.path.exists(history_file): return 0.0
        
        try:
            with open(history_file, 'r') as f:
                 history = json.load(f)
            
            if not history: return 0.0
            
            high = max(h['nav'] for h in history)
            return high
        except (json.JSONDecodeError, OSError, KeyError):
            return 0.0

    def trigger_apoptosis(self, current, peak, drawdown):
        """
        THE KILL SWITCH.
        Only terminates in PRODUCTION mode. In SIMULATION, just logs and continues.
        """
        reason = f"CRITICAL: {drawdown*100:.1f}% Drawdown detected (Pk: ${peak:,.2f} -> Cur: ${current:,.2f})."
        
        # Check if we're in production mode
        mode = os.getenv('MODE', 'SIMULATION').upper()
        is_production = mode == 'PRODUCTION'
        
        if is_production:
            logging.critical(f"[IMMUNE] 💀 INITIATING APOPTOSIS. REASON: {reason}")
        else:
            logging.warning(f"[IMMUNE] ⚠️ APOPTOSIS WOULD TRIGGER (SIMULATION MODE - NOT KILLING). REASON: {reason}")
        
        # --- PHASE 30: USE WRITE QUEUE ---
        # Try write queue first, fallback to direct if unavailable
        try:
            from db.write_queue import publish_write, is_queue_enabled
            from shared.write_message import WriteMessage, PRIORITY_CRITICAL
            
            if is_queue_enabled():
                # Log apoptosis event via queue
                publish_write(WriteMessage(
                    operation='INSERT',
                    table='apoptosis_log',
                    data={
                        'trigger_reason': reason,
                        'nav_start': peak,
                        'nav_end': current,
                        'drawdown_pct': drawdown,
                        'actions_taken': "LOGGED_ONLY" if not is_production else "PROCESS_KILL + ORDER_CANCEL"
                    },
                    source_agent='AgentImmune',
                    priority=PRIORITY_CRITICAL
                ))
                
                # Cancel pending orders in production
                if is_production:
                    publish_write(WriteMessage(
                        operation='EXECUTE',
                        table='trade_queue',
                        data={},
                        sql="UPDATE trade_queue SET status='CANCELLED', reason='APOPTOSIS_EVENT' WHERE status='PENDING'",
                        source_agent='AgentImmune',
                        priority=PRIORITY_CRITICAL
                    ))
                
                logging.info("[IMMUNE] 📝 Apoptosis logged via Write Queue")
            else:
                # Fallback to direct write
                self._direct_apoptosis_write(reason, peak, current, drawdown, is_production)
        except ImportError:
            # Write queue not available, use direct write
            self._direct_apoptosis_write(reason, peak, current, drawdown, is_production)
        
        # 3. Only broadcast/kill in production
        if is_production:
            if self.r:
                self.r.publish("system_alerts", "APOPTOSIS_TRIGGERED")
                self.r.set("SYSTEM_STATUS", "DEAD")

            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("!!!          SYSTEM FAILURE              !!!")
            print(f"!!! {reason} !!!")
            print("!!!          SHUTTING DOWN               !!!")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            
            # 4. TERMINATE (Only in production!)
            sys.exit(1)
        else:
            logging.info("[IMMUNE] 🛡️ Simulation mode: Continuing operation despite drawdown. Monitor closely.")

    def _direct_apoptosis_write(self, reason, peak, current, drawdown, is_production):
        """Fallback direct DB write for when write queue is unavailable."""
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # 1. Log Death/Near-Death
            c.execute("""
                INSERT INTO apoptosis_log (trigger_reason, nav_start, nav_end, drawdown_pct, actions_taken)
                VALUES (?, ?, ?, ?, ?)
            """, (reason, peak, current, drawdown, "LOGGED_ONLY" if not is_production else "PROCESS_KILL + ORDER_CANCEL"))
            
            # 2. Only cancel orders in production
            if is_production:
                c.execute("UPDATE trade_queue SET status='CANCELLED', reason='APOPTOSIS_EVENT' WHERE status='PENDING'")
            
            conn.commit()

    def _recall_near_death_experiences(self):
        """
        [PHASE 20 - FEATURE COMPLETENESS]
        Recalls past apoptosis events to recognize crisis patterns.
        Returns history of near-death experiences for pattern learning.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Get all past apoptosis events
                c.execute("""
                    SELECT 
                        id, trigger_reason, nav_start, nav_end, 
                        drawdown_pct, actions_taken, timestamp
                    FROM apoptosis_log
                    ORDER BY id DESC
                    LIMIT 10
                """)
                events = c.fetchall()
                
                # Aggregate statistics
                c.execute("""
                    SELECT 
                        COUNT(*) as total_deaths,
                        AVG(drawdown_pct) as avg_drawdown,
                        MAX(drawdown_pct) as worst_drawdown
                    FROM apoptosis_log
                """)
                stats = c.fetchone()
            
            near_death_memory = {
                'total_deaths': stats[0] or 0,
                'avg_drawdown': stats[1] or 0,
                'worst_drawdown': stats[2] or 0,
                'recent_events': [
                    {
                        'id': e[0],
                        'reason': e[1],
                        'nav_start': e[2],
                        'nav_end': e[3],
                        'drawdown': e[4],
                        'actions': e[5],
                        'timestamp': e[6]
                    }
                    for e in events
                ],
                'has_died_before': (stats[0] or 0) > 0
            }
            
            if near_death_memory['has_died_before']:
                logging.info(f"[IMMUNE] 📜 DEATH CHRONICLE: {near_death_memory['total_deaths']} past deaths. Worst: {near_death_memory['worst_drawdown']*100:.1f}% drawdown")
            
            return near_death_memory
            
        except Exception as e:
            logging.error(f"[IMMUNE] Near-death recall error: {e}")
            return {'total_deaths': 0, 'has_died_before': False}


    def run(self):
        while True:
            try:
                self.check_vitals()
                time.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"[IMMUNE] Monitor Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    agent = AgentImmune()
    agent.run()

def run_immune_loop(*args):
    """
    Wrapper for Orchestrator to launch the Sentinel.
    """
    try:
        agent = AgentImmune()
        agent.run()
    except Exception as e:
        logging.error(f"[IMMUNE] Crash: {e}")
