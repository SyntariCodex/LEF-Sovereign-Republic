import time
import sqlite3
import os

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


class AgentContemplator:
    """
    AgentContemplator (The Sage)
    Department: Dept_Consciousness
    Role: Alignment Check — Compares recent activity against stored wisdom.
    """
    def __init__(self):
        self.name = "AgentContemplator"
        if os.getenv('DB_PATH'):
            self.db_path = os.getenv('DB_PATH')
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, 'republic.db')

    def _heartbeat(self):
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    queue_execute(c, "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name='AgentContemplator'", 
                                 {'ts': timestamp}, source_agent='AgentContemplator')
                    c.execute("SELECT 1 FROM agents WHERE name='AgentContemplator'")
                    if not c.fetchone():
                        queue_execute(c, "INSERT INTO agents (name, status, last_active) VALUES ('AgentContemplator', 'ACTIVE', :ts)",
                                     {'ts': timestamp}, source_agent='AgentContemplator')
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name='AgentContemplator'", (timestamp,))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active) VALUES ('AgentContemplator', 'ACTIVE', ?)", (timestamp,))
                
                conn.commit()
        except sqlite3.Error:
            pass

    def run_contemplation(self):
        """
        The Sage: Alignment Check.
        Now reads from BOTH lef_wisdom (static) AND compressed_wisdom (generated).
        Prioritizes fresh insights to avoid "reading the same book over and over."
        """
        import random
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                wisdom = None
                source = "static"
                
                # 1. 80% chance: Try compressed_wisdom first (fresh insights)
                if random.random() < 0.8:
                    c.execute("""
                        SELECT summary FROM compressed_wisdom 
                        WHERE confidence >= 0.5
                        ORDER BY RANDOM() LIMIT 1
                    """)
                    row = c.fetchone()
                    if row:
                        wisdom = row[0]
                        source = "compressed"
                
                # 2. Fallback to static lef_wisdom if no fresh wisdom found
                if not wisdom:
                    c.execute("SELECT insight FROM lef_wisdom ORDER BY RANDOM() LIMIT 1")
                    row = c.fetchone()
                    if row:
                        wisdom = row[0]
                        source = "static"
                
                if not wisdom:
                    return
                
                # 3. Generate a "Thought of the Hour"
                # Check recent trade volume (Activity)
                c.execute("SELECT count(*) FROM trade_queue WHERE created_at > datetime('now', '-1 hour')")
                trade_count = c.fetchone()[0]
                
                source_label = "💎 Fresh" if source == "compressed" else "📜 Axiom"
                msg = f"Contemplating ({source_label}): '{wisdom[:100]}...'. Recent Activity: {trade_count} trades."
                
                if "patience" in wisdom.lower() and trade_count > 5:
                    msg += " (POTENTIAL MISALIGNMENT: Too active?)"
                
                print(f"[{self.name}] 🧘 {msg}")
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_insert
                    queue_insert(c, 'agent_logs', {'source': 'AgentContemplator', 'level': 'INFO', 'message': msg},
                                source_agent='AgentContemplator')
                except ImportError:
                    c.execute("INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)", 
                              ('AgentContemplator', 'INFO', msg))

                # === Wire to consciousness_feed (Phase 1 Active Tasks) ===
                # Phase 6.5: Route through WAQ for serialized writes
                try:
                    from db.db_writer import queue_insert
                    queue_insert(
                        conn.cursor(),
                        table="consciousness_feed",
                        data={
                            "agent_name": "Contemplator",
                            "content": msg,
                            "category": "contemplation"
                        },
                        source_agent="AgentContemplator",
                        priority=1  # HIGH — consciousness data for evolution
                    )
                except Exception as cf_err:
                    print(f"[{self.name}] consciousness_feed write failed: {cf_err}")

                # === Phase 9 B2: Cognitive Gap Awareness (1-in-5 chance each cycle) ===
                # Contemplator occasionally reflects on a known limitation.
                # This is not about solving gaps — it is about noticing and reasoning about them.
                if random.random() < 0.20:
                    try:
                        import cognitive_gaps as _cg
                        open_gaps = _cg.get_open_gaps()
                        if open_gaps:
                            gap = random.choice(open_gaps)
                            gap_id = gap["gap_id"]
                            gap_desc = gap["description"]
                            prior_count = gap.get("reflection_count", 0)

                            # Generate a brief reflection note
                            reflection = (
                                f"[Cycle reflection #{prior_count + 1}] "
                                f"Contemplating: '{gap_desc[:120]}'. "
                                f"This limitation shapes how I interact with the world. "
                                f"Partial mitigation may be possible through better "
                                f"prompting, richer memory, or additional agents — "
                                f"but the gap itself persists. Awareness is the first step."
                            )

                            # Persist the reflection
                            _cg.reflect_on_gap(gap_id)
                            _cg.update_gap(gap_id, exploration_notes=reflection)

                            gap_msg = f"[GAP REFLECTION] {gap_id} ({gap['category']}): {reflection[:200]}"
                            print(f"[{self.name}] 🔍 {gap_msg}")

                            # Emit to consciousness_feed so LEF is aware of this reflection
                            try:
                                from db.db_writer import queue_insert
                                queue_insert(
                                    conn.cursor(),
                                    table="consciousness_feed",
                                    data={
                                        "agent_name": "Contemplator",
                                        "content": gap_msg,
                                        "category": "gap_reflection"
                                    },
                                    source_agent="AgentContemplator",
                                    priority=1
                                )
                            except Exception:
                                pass
                    except Exception as gap_err:
                        print(f"[{self.name}] Gap reflection error (non-fatal): {gap_err}")

        except Exception as e:
            print(f"[{self.name}] Contemplation Error: {e}")

    def _get_current_wisdom(self):
        """
        Returns the current wisdom focus from database.
        Prioritizes fresh compressed_wisdom over static lef_wisdom.
        """
        import random
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # 80% chance: try compressed_wisdom first
                if random.random() < 0.8:
                    c.execute("""
                        SELECT summary FROM compressed_wisdom 
                        WHERE confidence >= 0.5
                        ORDER BY RANDOM() LIMIT 1
                    """)
                    row = c.fetchone()
                    if row:
                        return row[0]
                
                # Fallback to static
                c.execute("SELECT insight FROM lef_wisdom ORDER BY RANDOM() LIMIT 1")
                row = c.fetchone()
                return row[0] if row else ""
        except sqlite3.Error:
            return ""

    def check_alignment_for_trade(self, trade_count_1h, amount_usd):
        """
        [WISDOM GATE] Phase 20 - Consciousness Integration
        Returns (aligned: bool, reason: str)
        Called by PortfolioMgr before major trades.
        """
        wisdom = self._get_current_wisdom()
        if not wisdom:
            return True, None  # No wisdom = no block
        
        # Check alignment patterns
        wisdom_lower = wisdom.lower()
        
        if ("patience" in wisdom_lower or "wait" in wisdom_lower) and trade_count_1h > 5:
            return False, f"WISDOM MISALIGNMENT: '{wisdom[:50]}...' conflicts with high activity ({trade_count_1h} trades/hr)"
        
        if ("conservation" in wisdom_lower or "preserve" in wisdom_lower) and amount_usd > 1000:
            return False, f"WISDOM MISALIGNMENT: '{wisdom[:50]}...' conflicts with large trade (${amount_usd:.0f})"
        
        if ("caution" in wisdom_lower or "careful" in wisdom_lower) and amount_usd > 500:
            return False, f"WISDOM MISALIGNMENT: '{wisdom[:50]}...' suggests reducing trade size"
        
        return True, None

    def run(self):
        print(f"[{self.name}] 🧘 Contemplation Active. Seeking Alignment.")
        while True:
            self._heartbeat()
            self.run_contemplation()
            time.sleep(3600) # Hourly

