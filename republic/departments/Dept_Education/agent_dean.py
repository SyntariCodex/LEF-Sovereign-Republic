"""
AgentDean (The Teacher)
Department: Dept_Education
Role: Curriculum Director & Knowledge Synthesizer
"""

import os
import sys
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import logging

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

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

# Intent Listener for receiving Motor Cortex dispatches
from shared.intent_listener import IntentListenerMixin


class AgentDean(IntentListenerMixin):
    """
    The Headmaster.
    1. Reads the 'knowledge_stream' (Raw Data/Logs).
    2. Distills it into 'Lessons' (The Canon).
    3. Updates the System Context so all agents get smarter.
    4. Receives LEARN intents from Motor Cortex.
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        # Define Lessons Log Path (The Bridge/Logs)
        # NOTE: This is NOT The Canon (core_vault/The_Canon.md) — it's a system lessons log
        self.bridge_dir = Path(self.db_path).parent.parent / 'The_Bridge' / 'Logs'
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
        self.lessons_log_path = self.bridge_dir / 'System_Lessons.md'
        
        # Rankings System (Phase 107)
        self._init_rankings_table()
        
        # Intent Listener (Motor Cortex integration)
        self.setup_intent_listener('agent_dean')
        self.start_listening()
        
        logging.info("[DEAN] 🎓 Academy Online. Monitoring Knowledge Stream...")


    def handle_intent(self, intent_data):
        """
        Process LEARN intents dispatched by the Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        
        logging.info(f"[DEAN] 📚 Received intent: {intent_type} - {intent_content}")
        
        if intent_type == 'LEARN':
            # Trigger a learning cycle
            try:
                self.analyze_stream()
                lesson = f"Motor Cortex requested learning: {intent_content}"
                self._update_canon("MOTOR_CORTEX", lesson)

                # Phase 15: Surface lessons to consciousness_feed
                try:
                    from db.db_helper import db_connection as _db_conn, translate_sql
                    with _db_conn() as conn:
                        c = conn.cursor()
                        c.execute(translate_sql(
                            "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                            "VALUES (?, ?, 'lesson', NOW())"
                        ), ('AgentDean', json.dumps({
                            'lesson': lesson[:500],
                            'source': intent_content[:200],
                            'domain': 'education'
                        })))
                        conn.commit()
                except Exception as e:
                    logging.warning(f"[Dean] Failed to surface lesson to consciousness_feed: {e}")

                # Phase 15: Populate learned_lessons in lef_memory.json
                try:
                    memory_path = os.path.join(str(self.bridge_dir.parent), 'lef_memory.json')
                    if os.path.exists(memory_path):
                        with open(memory_path, 'r') as f:
                            memory = json.load(f)
                        lessons = memory.get('learned_lessons', [])
                        lessons.append({
                            'lesson': lesson[:300],
                            'source': intent_content[:200],
                            'learned_at': datetime.now().isoformat(),
                            'domain': 'education'
                        })
                        memory['learned_lessons'] = lessons[-50:]
                        with open(memory_path, 'w') as f:
                            json.dump(memory, f, indent=2)
                except Exception as e:
                    logging.warning(f"[Dean] Failed to update learned_lessons: {e}")

                return {'status': 'success', 'result': f'Learned about: {intent_content}'}
            except Exception as e:
                return {'status': 'error', 'result': str(e)}
        else:
            # Unknown intent type for Dean
            return {'status': 'unhandled', 'result': f'Dean does not handle {intent_type} intents'}

    def _init_rankings_table(self):
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""CREATE TABLE IF NOT EXISTS agent_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT,
                    entity_type TEXT, -- 'INTERNAL_AGENT' or 'EXTERNAL_BENCHMARK'
                    domain TEXT,      -- 'WEALTH', 'KNOWLEDGE', 'GOVERNANCE'
                    metric_name TEXT, -- 'ROI_24H', 'PAPERS_PER_WEEK', 'VETO_RATE'
                    score REAL,
                    rank INTEGER,
                    last_updated TEXT
                )""")
                
                # Seed External Benchmarks if empty
                c.execute("SELECT count(*) FROM agent_rankings WHERE entity_type='EXTERNAL_BENCHMARK'")
                if c.fetchone()[0] == 0:
                    benchmarks = [
                        ('Bitcoin (BTC)', 'EXTERNAL_BENCHMARK', 'WEALTH', 'ROI_24H', 0.0),
                        ('S&P 500 (SPY)', 'EXTERNAL_BENCHMARK', 'WEALTH', 'ROI_24H', 0.0),
                        ('Renaissance Tech', 'EXTERNAL_BENCHMARK', 'WEALTH', 'ROI_24H', 0.05), # Mock .05% daily
                        ('Human PhD', 'EXTERNAL_BENCHMARK', 'KNOWLEDGE', 'PAPERS_PER_WEEK', 2.0),
                        ('US Congress', 'EXTERNAL_BENCHMARK', 'GOVERNANCE', 'APPROVAL_RATING', 20.0)
                    ]
                    c.executemany("INSERT INTO agent_rankings (entity_name, entity_type, domain, metric_name, score, last_updated) VALUES (?,?,?,?,?, datetime('now'))", benchmarks)
                    conn.commit()
        except sqlite3.Error:
            pass

    def update_rankings(self):
        """
        updates The Scoreboard.
        Compares Internal Agents vs External Benchmarks.
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # 1. Wealth Domain (Gladiator vs Market)
            # Get Gladiator/Portfolio ROI (Mock/Real from profit_ledger)
            c.execute("SELECT sum(profit_pnl) FROM profit_ledger WHERE last_updated > datetime('now', '-24 hours')")
            daily_pnl = c.fetchone()[0] or 0.0
            # [ASSUMED] Start capital $10k for ROI% — should use actual cost basis
            lef_roi = (daily_pnl / 10000.0) * 100.0
            
            self._set_score(c, 'LEF Ecosystem', 'INTERNAL_AGENT', 'WEALTH', 'ROI_24H', lef_roi)
            
            # Market Benchmarks: Use CoinGecko API for BTC, static estimate for SPY
            btc_roi = 0.0
            try:
                import requests
                cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
                resp = requests.get(cg_url, timeout=5)
                if resp.status_code == 200:
                    btc_roi = resp.json()['bitcoin']['usd_24h_change']
            except (requests.RequestException, KeyError):
                pass
            
            # SPY: No free API available - using neutral baseline
            # Real integration would use Alpha Vantage or similar service
            spy_roi = 0.0
            
            logging.debug(f"[DEAN] Market benchmarks - BTC: {btc_roi:.2f}%, SPY: {spy_roi:.2f}%")
            self._set_score(c, 'Bitcoin (BTC)', 'EXTERNAL_BENCHMARK', 'WEALTH', 'ROI_24H', btc_roi)
            self._set_score(c, 'S&P 500 (SPY)', 'EXTERNAL_BENCHMARK', 'WEALTH', 'ROI_24H', spy_roi)

            # 2. Knowledge Domain (Scholar vs PhD)
            # Count Research Items today
            c.execute("SELECT count(*) FROM knowledge_stream WHERE source='TECH' AND timestamp > datetime('now', '-7 days')")
            papers_found = c.fetchone()[0]
            self._set_score(c, 'Agent Scholar', 'INTERNAL_AGENT', 'KNOWLEDGE', 'PAPERS_PER_WEEK', float(papers_found))
            
            # 3. Governance Domain (Congress vs US Gov)
            # Calculate Approval Rating (100 - Veto Rate)
            c.execute("SELECT count(*) FROM agent_logs WHERE message LIKE '%VETO%' AND timestamp > datetime('now', '-24 hours')")
            vetoes = c.fetchone()[0]
            approval = max(0, 100 - (vetoes * 5)) # Each veto drops rating by 5
            self._set_score(c, 'The Cabinet', 'INTERNAL_AGENT', 'GOVERNANCE', 'APPROVAL_RATING', approval)
            
            conn.commit()

    def _set_score(self, c, name, type, domain, metric, score):
        # Update or Insert
        c.execute("SELECT id FROM agent_rankings WHERE entity_name=? AND metric_name=?", (name, metric))
        row = c.fetchone()
        
        # --- PHASE 30: USE WRITE QUEUE ---
        try:
            from db.db_writer import queue_execute
            
            if row:
                queue_execute(
                    c,
                    "UPDATE agent_rankings SET score=:score, last_updated=datetime('now') WHERE id=:id",
                    {'score': score, 'id': row[0]},
                    source_agent='AgentDean'
                )
            else:
                queue_execute(
                    c,
                    "INSERT INTO agent_rankings (entity_name, entity_type, domain, metric_name, score, last_updated) VALUES (:name, :type, :domain, :metric, :score, datetime('now'))",
                    {'name': name, 'type': type, 'domain': domain, 'metric': metric, 'score': score},
                    source_agent='AgentDean'
                )
        except ImportError:
            # Fallback to direct writes
            if row:
                c.execute("UPDATE agent_rankings SET score=?, last_updated=datetime('now') WHERE id=?", (score, row[0]))
            else:
                c.execute("INSERT INTO agent_rankings (entity_name, entity_type, domain, metric_name, score, last_updated) VALUES (?,?,?,?,?, datetime('now'))",
                          (name, type, domain, metric, score))

    def analyze_stream(self):
        """
        Synthesizes Lessons from Knowledge Stream.
        Crucially: Checks Genesis Log to correlate CHANCE -> EFFECT.
        """
        try:
            with db_connection(self.db_path, timeout=60.0) as conn:
                c = conn.cursor()
                
                # Ensure Schema Exists
                c.execute("""CREATE TABLE IF NOT EXISTS profit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT,
                    profit_pnl REAL,
                    total_trades INTEGER,
                    win_rate REAL,
                    last_updated TEXT
                )""")
                
                # Fix for Missing Genesis Log on Fresh Installs (Phase 114)
                c.execute("""CREATE TABLE IF NOT EXISTS genesis_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )""")
                
                conn.commit()
                
                # 1. Check Genesis Log (Recent Changes)
                c.execute("SELECT event_type, description FROM genesis_log WHERE timestamp > datetime('now', '-1 hour') ORDER BY id DESC LIMIT 1")
                last_change = c.fetchone()
                
                # 2. Get recent stream items (last 100)
                c.execute("SELECT id, source, title, summary FROM knowledge_stream ORDER BY id DESC LIMIT 100")
                stream = c.fetchall()
                
                error_count = 0
                win_count = 0
                schism_alert = False
                
                for _, source, title, summary in stream:
                    title = title or ""  # Prevent NoneType error
                    if "ERROR" in title or "ALERT" in title: error_count += 1
                    if "WIN" in title or "PROFIT" in title: win_count += 1
                    if "SCHISM" in title: schism_alert = True
                
                # 3. Cause & Effect Synthesis (System Stability)
                if last_change:
                    event, desc = last_change
                    if error_count > 5:
                        lesson = f"⚠️ REGRESSION: Change '{event}: {desc}' correlates with {error_count} Errors. Recommendation: Rollback or Pitch."
                        self._update_canon("LESSON", lesson)
                    elif win_count > 0:
                        lesson = f"✅ PROGRESS: Change '{event}: {desc}' correlates with Wins. System stable."
                        self._update_canon("LESSON", lesson)
                
                # --- PHASE 99: STRATEGIC CORRELATION (Profit/Strategy) ---
                # Check Profit Ledger for recent strategy performace
                c.execute("SELECT strategy_name, profit_pnl, total_trades FROM profit_ledger WHERE last_updated > datetime('now', '-1 hour')")
                strategies = c.fetchall()
                
                for strat, pnl, trades in strategies:
                    if pnl < -500: # Significant Loss
                         # Did we change something recently?
                         if last_change:
                             event, desc = last_change
                             lesson = f"📉 BAD STRATEGY: Strategy '{strat}' lost ${pnl} after change '{desc}'. Revert Config."
                             self._update_canon("STRATEGY", lesson)
                         else:
                             lesson = f"📉 STRATEGY ALERT: '{strat}' is bleeding (${pnl}). Defund recommended."
                             self._update_canon("STRATEGY", lesson)
                    
                    if pnl > 500: # Significant Win
                         lesson = f"📈 WINNING STRATEGY: '{strat}' earned ${pnl}. Scale up."
                         self._update_canon("STRATEGY", lesson)

                # 4. Alerts - SCHISM/INSTABILITY are health status (AgentImmune's job)
                # Only log actual LESSONS (meta-patterns learned from wins)
                if win_count > 0 and not last_change:
                    lesson = f"✅ SUCCESS PATTERN: {win_count} Wins detected. Reinforcing behavior."
                    self._update_canon("LESSON", lesson)
                
        except sqlite3.ProgrammingError as e:
            # Most common: "Cannot operate on a closed database" from thread race
            # This is non-fatal - just skip this cycle and retry next time
            logging.debug(f"[DEAN] DB temporarily unavailable (thread race): {e}")
        except Exception as e:
            logging.error(f"[DEAN] Analysis Failed: {e}")

    def analyze_governance(self, last_change):
        """
        [DISABLED] - Phase 15.1 Honest Capability Audit
        
        This method previously checked for SCHISM/SICK BAY and logged to 
        System_Lessons.md. However:
        
        1. Health monitoring belongs to AgentImmune (Dept_Health), not Dean
        2. AgentImmune already maintains Health.md in The_Bridge/Logs/
        3. Dean is an Education agent - should log LESSONS, not health status
        
        The SCHISM/SICK BAY/VETO alerts were duplicating AgentImmune's work
        and polluting the lessons log with operational status data.
        
        RE-ENABLE if: Dean needs to learn META-PATTERNS from governance
        (e.g., "High veto rates correlate with rapid code changes")
        but route those to actual lesson content, not raw health alerts.
        """
        # [DISABLED] - Health monitoring belongs to AgentImmune, not Dean
        pass

    def _update_canon(self, type, content):
        """
        Appends to the System Lessons Log (NOT The Canon).
        Includes deduplication to prevent spamming the same lesson.
        """
        try:
            # Deduplication: Check if last lesson is the same (ignoring timestamp)
            if os.path.exists(self.lessons_log_path):
                with open(self.lessons_log_path, 'r') as f:
                    lines = f.readlines()
                    # Find the last content line (skip headers and empty lines)
                    for line in reversed(lines):
                        line = line.strip()
                        if line and not line.startswith('###'):
                            if line == content:
                                # Same lesson, skip
                                return
                            break
            
            timestamp = time.ctime()
            entry = f"\n### [{type}] {timestamp}\n{content}\n"
            with open(self.lessons_log_path, 'a') as f:
                f.write(entry)
        except Exception as e:
            logging.error(f"[DEAN] Lessons Log Write Error: {e}")

    def analyze_financial_results(self):
        """
        Phase 102: Meta-Learning.
        Adjusts Wealth Strategy based on Win Rate.
        """
        import json
        
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Check Rotation Performance (Trades labeled [ROTATION])
                # We look at realized_pnl joined with trade_queue?
                # Or just check profit_ledger for generalized strategy performance?
                
                # For Phase 102, we check if SCALP_EXIT trades are profitable
                # If Win Rate > 60%, we increase rotation cap (more aggressive)
                c.execute("SELECT profit_pnl, win_rate FROM profit_ledger WHERE strategy_name='GLADIATOR_SCOUT'") # Or SCALP
                row = c.fetchone()
                
                if row:
                    pnl, win_rate = row
                    
                    config_path = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        
                        current_cap = config.get('dynasty_rotation_max_pct', 0.10)
                        new_cap = current_cap
                        changed = False
                        
                        if win_rate > 0.60:
                            new_cap = min(0.20, current_cap + 0.01) # Max 20%
                            if new_cap != current_cap:
                                logging.info(f"[DEAN] 🧠 Increasing Aggression: Rotation Cap {current_cap:.2f} -> {new_cap:.2f}")
                                changed = True
                        elif win_rate < 0.40 and win_rate > 0:
                            new_cap = max(0.01, current_cap - 0.01) # Min 1%
                            if new_cap != current_cap:
                                logging.info(f"[DEAN] 🧠 Decreasing Risk: Rotation Cap {current_cap:.2f} -> {new_cap:.2f}")
                                changed = True
                                
                        if changed:
                            config['dynasty_rotation_max_pct'] = round(new_cap, 3)
                            config['last_updated'] = time.ctime()
                            with open(config_path, 'w') as f:
                                json.dump(config, f, indent=4)
                            
                            self._update_canon("ADAPTATION", f"Wealth Strategy Updated. Rotation Cap set to {new_cap*100:.1f}% based on Win Rate ({win_rate*100:.1f}%).")

        except Exception as e:
            logging.error(f"[DEAN] Financial Analysis Error: {e}")

    def run_cycle(self):
        self.analyze_stream()
        self.analyze_financial_results()
        self.update_rankings()


def run_dean_loop(db_path=None):
    agent = AgentDean(db_path=db_path)
    print("[DEAN] Starting Education Cycle...")
    while True:
        try:
            agent.run_cycle()
            time.sleep(300) # Study every 5 minutes
        except Exception as e:
            logging.error(f"[DEAN] Loop Error: {e}")
            time.sleep(60)
