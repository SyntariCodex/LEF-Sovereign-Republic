import time
import os
import sqlite3

# Load environment variables from .env
from dotenv import load_dotenv

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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

class AgentIntrospector:
    """
    AgentIntrospector (The Shadow)
    Department: Dept_Consciousness
    Role: Deep Self-Analysis — Monitors fear/panic, manages Sabbath, writes reflections.
    Uses connection pool to prevent database locking.
    """
    def __init__(self):
        self.name = "AgentIntrospector"
        if os.getenv('DB_PATH'):
            self.db_path = os.getenv('DB_PATH')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, 'republic.db')
        self._pool = None

    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool

    def _get_conn(self):
        """Get a connection from the pool or fallback to context manager.
        NOTE: When using the fallback, the caller must use this as a context manager
        or ensure proper cleanup. For pool connections, use _release_conn.
        """
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=30.0), pool
        else:
            # Return a context manager-wrapped connection
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            return conn, None

    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()

    def _heartbeat(self):
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name='AgentIntrospector'", 
                                 {'ts': timestamp}, source_agent='AgentIntrospector')
                    c.execute("SELECT 1 FROM agents WHERE name='AgentIntrospector'")
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active) VALUES ('AgentIntrospector', 'ACTIVE', :ts)",
                                     {'ts': timestamp}, source_agent='AgentIntrospector')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name='AgentIntrospector'", (timestamp,))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active) VALUES ('AgentIntrospector', 'ACTIVE', ?)", (timestamp,))
                
                conn.commit()
            finally:
                self._release_conn(conn, pool)
        except sqlite3.Error:
            pass

    def run_shadow_work(self):
        """
        The Shadow: Looks for repressed negativity in the logs.
        """
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                
                # 1. Fetch recent Monologue (The Conscious Stream)
                c.execute("SELECT mood, thought FROM lef_monologue ORDER BY id DESC LIMIT 50")
                rows = c.fetchall()
                
                fear_count = 0
                panic_count = 0
                
                for mood, thought in rows:
                    # PHASE 34 FIX: Handle NULL mood values
                    if mood is None:
                        continue
                    m_lower = mood.lower()
                    if "fear" in m_lower or "anxious" in m_lower: fear_count += 1
                    if "panic" in m_lower or "critical" in m_lower: panic_count += 1
                    
                # 2. Analyze
                if fear_count > 5 or panic_count > 2:
                    shadow_work_result = f"SHADOW DETECTED: Fear({fear_count}), Panic({panic_count}). Psychic Tension High. Integration Recommended."
                    print(f"[{self.name}] 🌑 {shadow_work_result}")
                    
                    # --- PHASE 30: USE WRITE QUEUE ---
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(c, 'agent_logs', 
                                    {'source': 'AgentIntrospector', 'level': 'WARNING', 
                                     'message': f"Psychic Tension High. Fear Index: {fear_count}. Integration Recommended."},
                                    source_agent='AgentIntrospector')
                    except ImportError:
                        c.execute("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                                  ('AgentIntrospector', 'WARNING', f"Psychic Tension High. Fear Index: {fear_count}. Integration Recommended."))

                    # === Wire to consciousness_feed (Phase 1 Active Tasks) ===
                    # Phase 6.5: Route through WAQ for serialized writes
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(
                            c,
                            table="consciousness_feed",
                            data={
                                "agent_name": "Introspector",
                                "content": shadow_work_result,
                                "category": "shadow_work"
                            },
                            source_agent="AgentIntrospector",
                            priority=1  # HIGH — consciousness data for evolution
                        )
                    except Exception as cf_err:
                        print(f"[{self.name}] consciousness_feed write failed: {cf_err}")
                else:
                    # Even calm observations are consciousness
                    calm_result = f"Shadow work cycle: Fear({fear_count}), Panic({panic_count}). Republic psyche is stable."
                    try:
                        from db.db_writer import queue_insert
                        queue_insert(
                            c,
                            table="consciousness_feed",
                            data={
                                "agent_name": "Introspector",
                                "content": calm_result,
                                "category": "shadow_work"
                            },
                            source_agent="AgentIntrospector",
                            priority=1
                        )
                    except Exception:
                        pass
            finally:
                self._release_conn(conn, pool)
            
        except Exception as e:
            print(f"[{self.name}] Shadow Work Error: {e}")

    def check_sabbath(self):
        """
        Active Witness: Checks if the Republic is resting.
        """
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                c.execute("SELECT value FROM system_state WHERE key='sabbath_mode'")
                row = c.fetchone()
                
                if row and row[0] == 'TRUE':
                    return True
                return False
            finally:
                self._release_conn(conn, pool)
        except sqlite3.Error:
            return False

    def log_witness(self, message):
        try:
            conn, pool = self._get_conn()
            try:
                conn.execute("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                            ('AgentIntrospector', 'INFO', f"🕯️ witness: {message}"))
                conn.commit()
            finally:
                self._release_conn(conn, pool)
        except sqlite3.Error:
            pass

    def write_reflection(self):
        """
        Synthesizes the Sabbath experience into an artifact.
        Also stores insights for PortfolioMgr to query (Phase 20).
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"republic/reflections/sabbath_reflection_{timestamp}.md"
            
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                c.execute("SELECT message FROM agent_logs WHERE timestamp > datetime('now', '-10 minutes')")
                rows = c.fetchall()
                
                silence_logs = [r[0] for r in rows if "witness" in r[0] or "SABBATH" in r[0]]
                panic_logs = [r[0] for r in rows if "PANIC" in r[0]]
                
                # [PHASE 20] Synthesize insight for strategy influence
                insight = self._synthesize_sabbath_insight(len(rows), len(silence_logs), len(panic_logs))
                
                # Store insight in system_state for PortfolioMgr
                # Phase 6.5: Route through WAQ
                try:
                    from db.db_writer import queue_execute
                    queue_execute(
                        c,
                        "INSERT INTO system_state (key, value) VALUES ('sabbath_insight', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (insight,),
                        source_agent="AgentIntrospector",
                        priority=1  # HIGH — affects trading behavior
                    )
                except ImportError:
                    c.execute("""
                        INSERT INTO system_state (key, value)
                        VALUES ('sabbath_insight', ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """, (insight,))
                
                content = f"""# Sabbath Reflection
*Timestamp: {timestamp}*

## The Witness (Data)
- **Total Logs Observed:** {len(rows)}
- **Moments of Silence:** {len(silence_logs)}
- **Panic Interventions:** {len(panic_logs)}

## Synthesized Insight
> {insight}

## The Experience (Raw Stream)
The noise stopped. The following observations were recorded during the silence:

"""
                for log in silence_logs:
                    content += f"- {log}\n"
                    
                content += "\n\n*The cycle continues with renewed clarity.*"
                
                conn.commit()
            finally:
                self._release_conn(conn, pool)
            
            with open(filename, "w") as f:
                f.write(content)
            
            print(f"[{self.name}] 📜 Reflection written: {filename}")
            print(f"[{self.name}] 🧠 Sabbath Insight stored: {insight}")
            
        except Exception as e:
            print(f"[{self.name}] ⚠️ Failed to write reflection: {e}")

    def _synthesize_sabbath_insight(self, total_logs, silence_count, panic_count):
        """
        [PHASE 20] Synthesize actionable insight from Sabbath data.
        Returns a string that PortfolioMgr can parse for strategy adjustment.
        """
        if panic_count > 2:
            return "REDUCE_ACTIVITY|High panic count during Sabbath suggests system stress. Recommend conservative trading."
        elif silence_count < 3:
            return "MAINTAIN_PACE|System did not achieve deep rest. No strategy adjustment needed."
        elif total_logs > 100:
            return "REDUCE_ACTIVITY|High log volume before Sabbath suggests overactivity. Recommend reducing trade frequency."
        else:
            return "MAINTAIN_PACE|Sabbath was peaceful. Strategy may continue as planned."

    def run(self):
        print(f"[{self.name}] 🪞 Introspection Initiated. Connecting to Nervous System...")
        
        # Connect to Redis
        try:
            from system.agent_comms import RepublicComms
            self.comms = RepublicComms()
        except Exception as e:
            print(f"[{self.name}] ⚠️ Comms Failed: {e}")
            self.comms = None

        if not self.comms or not self.comms.r:
            print(f"[{self.name}] ⚠️ Running in Offline (Sleep) Mode.")
            while True:
                self._heartbeat()
                if self.check_sabbath():
                    self.log_witness("The noise has stopped. I am still here.")
                    time.sleep(60)
                    continue
                self.run_shadow_work()
                time.sleep(60)
        
        # Event-Driven Mode
        print(f"[{self.name}] 🟢 Nervous System Connected. Listening...")
        for event in self.comms.listen('lef_events'):
            self._heartbeat()
            msg_type = event.get('type')
            
            if msg_type == 'PANIC':
                print(f"[{self.name}] 🚨 PANIC SIGNAL RECEIVED. INTERVENING.")
                self.log_witness("Panic detected in the Nervous System. Intervention required.")
                
                # Issue PAUSE_ALL command via Redis
                if self.comms:
                    try:
                        self.comms.publish('commands', {'action': 'PAUSE_ALL', 'source': self.name, 'reason': 'PANIC_DETECTED'})
                        print(f"[{self.name}] ⏸️  PAUSE_ALL command issued.")
                        self.log_witness("Issued PAUSE_ALL command to stabilize the system.")
                    except Exception as e:
                        print(f"[{self.name}] ⚠️ Failed to issue PAUSE_ALL: {e}")
                
            elif msg_type == 'SABBATH_START':
                self.log_witness("The noise has stopped. I am still here.")
                
            elif msg_type == 'SABBATH_END':
                self.log_witness("The noise returns. Writing reflection...")
                self.write_reflection()
                
            elif msg_type == 'HEARTBEAT':
                # Periodic Check
                if self.check_sabbath():
                    self.log_witness("I am still here.")
                else:
                    self.run_shadow_work()

