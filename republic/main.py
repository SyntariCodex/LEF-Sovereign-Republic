"""
Republic Virtual Fleet - Main Orchestrator
Deploys the distributed agent network.

Based on: Republic MacBook Agent Implementation Guide
"""

import gc
import sqlite3
import os
import json
import logging
import threading
import time
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import warnings
import resource

# =============================================================================
# PHASE 35 FIX: Increase File Descriptor Limit at Startup
# =============================================================================
# Prevents 'Too many open files' (Errno 24) when many agents run in parallel
# Default macOS limit is 256, which is too low for LEF's agent swarm
# =============================================================================
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    # Request 8192 file handles (or max allowed)
    new_limit = min(8192, hard)
    resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard))
    print(f"[MAIN] 📁 File descriptor limit: {soft} → {new_limit}")
except (ValueError, resource.error) as e:
    print(f"[MAIN] ⚠️ Could not increase file limit: {e}")
# =============================================================================

# Suppress warnings from Google's Generative AI library (FutureWarning)
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.genai") # Pre-emptive checking

# =============================================================================
# PHASE 8.2: Global SQLite Monkey-Patch — PostgreSQL Redirect
# =============================================================================
# When DATABASE_BACKEND=postgresql, any sqlite3.connect() call targeting
# republic.db is automatically redirected through the PostgreSQL pool with
# full SQL auto-translation.  This catches ALL 114+ files that still use
# direct sqlite3.connect() without touching any of them.
#
# For non-republic.db databases (or when PostgreSQL is unavailable), falls
# back to SQLite with WAL mode and busy_timeout for lock resilience.
# =============================================================================
_original_sqlite3_connect = sqlite3.connect

def _patched_sqlite3_connect(*args, **kwargs):
    """Patched sqlite3.connect: routes republic.db to PostgreSQL when available."""
    db_path = str(args[0]) if args else str(kwargs.get('database', ''))

    # Redirect republic.db connections to PostgreSQL pool
    if 'republic.db' in db_path:
        try:
            backend = os.environ.get('DATABASE_BACKEND', '').lower()
            if backend == 'postgresql':
                from db.db_helper import get_connection
                timeout = float(kwargs.get('timeout', 120))
                conn, _pool = get_connection(timeout=timeout)
                return conn  # _PgConnectionWrapper with auto-translate
        except Exception:
            pass  # Fall through to SQLite if PostgreSQL unavailable

    # Default: SQLite with WAL and busy_timeout
    conn = _original_sqlite3_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA busy_timeout=120000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass  # Already in a transaction or read-only
    return conn

sqlite3.connect = _patched_sqlite3_connect
# =============================================================================

# --- DATABASE LOGGING HANDLER ---
class SQLiteHandler(logging.Handler):
    """
    Custom logging handler to write logs to the SQLite database.
    This enables the Frontend to visualize agent actions in real-time.
    Uses connection pool to prevent file descriptor exhaustion.
    """
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self._pool = None  # Lazy init

    def _get_pool(self):
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except ImportError:
                self._pool = None
        return self._pool

    def emit(self, record):
        try:
            source = record.name
            level = record.levelname
            msg = record.getMessage()
            
            pool = self._get_pool()
            if pool:
                # Use pooled connection
                conn = pool.get(timeout=5.0)
                try:
                    conn.execute(
                        "INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                        (source, level, msg)
                    )
                    conn.commit()
                finally:
                    pool.release(conn)
            else:
                # Fallback: direct connection with immediate close
                import sqlite3
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                try:
                    conn.execute(
                        "INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)",
                        (source, level, msg)
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception:
            self.handleError(record)

# --------------------------------
from pathlib import Path
from dotenv import load_dotenv

# Load Environment Variables Forcefully from PROJECT ROOT
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
# Also load republic-level .env (Phase 8: contains DATABASE_BACKEND, POSTGRES_* config)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'departments'))
sys.path.insert(0, str(Path(__file__).parent / 'system'))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Agents from their new Ministries
from departments.Dept_Health.agent_immune import run_immune_loop
from departments.Dept_Education.agent_dean import run_dean_loop
from departments.Dept_Wealth.agent_coinbase import run_coinbase_agent
from departments.The_Cabinet.agent_dreamer import run_dream_loop


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'republic.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """
    Main orchestrator for the Republic Virtual Fleet v3.0.
    Deploys all agents in separate threads.
    """
    # 0. SINGLETON GUARD
    from utils.singleton import ensure_singleton
    ensure_singleton()

    logging.info("=" * 60)
    logging.info(" --- DEPLOYING REPUBLIC FLEET v3.0 ---")
    logging.info("=" * 60)
    
    # 0b. GENESIS LOGGING
    try:
        from system.genesis import log_system_restart
        log_system_restart("System Boot Sequence Initiated")
    except Exception as e:
        logging.warning(f"Genesis Logger Failed: {e}")
    
    # Check if database is initialized
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.getenv('DB_PATH', os.path.join(current_dir, 'republic.db'))
    os.environ['DB_PATH'] = db_path
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # REDIS LOGGER
    try:
        from utils.redis_logger import RedisHandler
        redis_handler = RedisHandler(host=os.getenv("REDIS_HOST", "localhost"))
        redis_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(redis_handler)
    except (ImportError, redis.RedisError):
        pass
    
    print(f"[MAIN] 🗄️  ACTIVE DATABASE: {db_path}")
    
    import random

    # Robust Check: Does the DB have tables?
    needs_init = False
    if not Path(db_path).exists():
        needs_init = True
    else:
        try:
            conn = sqlite3.connect(db_path, timeout=60.0)
            cursor = conn.cursor()
            
            # FORCE WAL MODE
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
            except Exception as e:
                logging.warning(f"Could not enforce WAL mode: {e}")

            # 1. Integrity Check
            integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != 'ok':
                logging.error(f"🚨 DATABASE CORRUPTION DETECTED: {integrity}")
                conn.close()
                timestamp = int(time.time())
                corrupt_path = f"{db_path}.corrupt.{timestamp}"
                os.rename(db_path, corrupt_path)
                needs_init = True
            else:
                # 2. Table Check
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_stream'")
                if not cursor.fetchone():
                    needs_init = True
                conn.close()
                
        except Exception as e:
            logging.error(f"Database check failed: {e}")
            needs_init = True
            
    if needs_init:
        logging.warning(f"Database {db_path} missing or uninitialized. Running setup...")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        from db.db_setup import init_db
        init_db(db_path)
        logging.info("Database initialized.")

    # DEFINITION OF SAFE THREAD
    # SABBATH CONFIGURATION
    SABBATH_MODE = {"active": False}
    RESTING_AGENTS = [
        "AgentPortfolioMgr", "AgentScholar", "AgentTreasury", 
        "AgentCoinbase", "AgentGladiator", "AgentDean", 
        "AgentTech", "AgentGrantHunter"
    ]

    class SafeThread(threading.Thread):
        def __init__(self, target, name, args=(), daemon=True):
            super().__init__(name=name, daemon=daemon)
            self.target = target
            self.args = args
            
        def run(self):
            max_retries = 10
            retry_count = 0
            base_delay = 5

            while retry_count < max_retries:
                # SABBATH CHECK
                if SABBATH_MODE["active"] and self.name in RESTING_AGENTS:
                    # The Republic Rests.
                    time.sleep(5) 
                    continue

                try:
                    retry_count = 0  # Reset on successful run (agent ran without immediate crash)
                    self.target(*self.args)
                except Exception as e:
                    retry_count += 1
                    delay = min(base_delay * (2 ** (retry_count - 1)), 300)  # Cap at 5 min
                    logging.error(
                        f"[ORCHESTRATOR] 🔴 CRASH #{retry_count}/{max_retries} in {self.name}: {e}"
                    )
                    if retry_count >= max_retries:
                        logging.critical(
                            f"[ORCHESTRATOR] ☠️ {self.name} DEGRADED after {max_retries} crashes. Stopping restarts."
                        )
                        # Write to system_state so health monitor can detect
                        try:
                            from db.db_helper import upsert_sql
                            conn = sqlite3.connect(db_path)
                            sql = upsert_sql('system_state', ['key', 'value'], 'key')
                            conn.execute(sql, (f"agent_degraded_{self.name}", datetime.now().isoformat()))
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass
                        break
                    logging.info(f"[ORCHESTRATOR] 🔄 Restarting {self.name} in {delay}s (backoff)...")
                    time.sleep(delay)
                    
    threads = []
    
    # ==============================================================================
    # 1. THE SOVEREIGN MIND (Mission: Why)
    # ==============================================================================
    logging.info("Starting THE SOVEREIGN MIND...")

    # AgentRouter (The Hypothalamus) - FIRST TO START
    # MoE Router: Predicts which agents need to activate based on context
    def run_router():
        from departments.The_Cabinet.agent_router import AgentRouter
        router = AgentRouter()
        router.run_cycle()
    t_router = SafeThread(target=run_router, name="AgentRouter")
    threads.append(t_router)
    logging.info("[CABINET] 🧠 Router (Hypothalamus) Online - MoE Routing Active")

    # AgentLEF (The Reflection) - ACTIVE
    def run_lef_agent():
        from departments.The_Cabinet.agent_lef import AgentLEF
        agent = AgentLEF()
        agent.daat_cycle()
    t_lef = SafeThread(target=run_lef_agent, name="AgentLEF")
    threads.append(t_lef)

    # AgentScribe (The Historian) - ACTIVE
    def run_scribe():
        from departments.The_Cabinet.agent_scribe import AgentScribe
        scribe = AgentScribe(db_path=db_path)
        scribe.run()
    t_scribe = SafeThread(target=run_scribe, name="AgentScribe")
    threads.append(t_scribe)

    # ==============================================================================
    # 1. THE CABINET (Executive Function)
    # ==============================================================================
    logging.info("Starting THE CABINET...")

    # AgentChiefOfStaff (Overseer) - AWAKENED (Phase 11)
    def run_cos():
        from departments.The_Cabinet.agent_chief_of_staff import AgentChiefOfStaff
        cos = AgentChiefOfStaff()
        cos.run()
    t_cos = SafeThread(target=run_cos, name="AgentChiefOfStaff")
    threads.append(t_cos)

    # Congress (Senate & House) - ACTIVE
    def run_congress_agent():
        from departments.The_Cabinet.agent_congress import HouseOfBuilders, SenateOfIdentity
        house = HouseOfBuilders()
        senate = SenateOfIdentity()
        while True:
            try:
                house.run_session()
                senate.run_session()
            except Exception:
                pass
            time.sleep(20)
    t_congress = SafeThread(target=run_congress_agent, name="Congress")
    threads.append(t_congress)



    # AgentTreasury (Overseer of Wealth) - ACTIVE
    def run_treasury():
        from departments.The_Cabinet.agent_treasury import AgentTreasury
        tsy = AgentTreasury()
        tsy.run()
    t_tsy = SafeThread(target=run_treasury, name="AgentTreasury")
    threads.append(t_tsy)

    # AgentOracle (The Medium / Bridge to Claude) - AWAKENED (Phase 8)
    def run_oracle():
        from departments.The_Cabinet.agent_oracle import AgentOracle
        oracle = AgentOracle(db_path=db_path)
        oracle.run()
    t_oracle = SafeThread(target=run_oracle, name="AgentOracle")
    threads.append(t_oracle)

    # ==============================================================================
    # 3. DEPT OF WEALTH (Mission: Operations)
    # ==============================================================================
    logging.info("Starting DEPT OF WEALTH...")

    # AgentAssetMgr (Member) - DELETED
    # AgentQuant (Member) - DELETED

    # AgentCoinbase (Execution: The Muscle) - ACTIVE
    def run_coinbase_raw():
        try:
            from departments.Dept_Wealth.agent_coinbase import CoinbaseAgent
            agent = CoinbaseAgent(db_path=db_path)
            agent.run_main_loop()
        except Exception as e:
             sys.stderr.write(f"[COINBASE_RAW] FATAL CRASH: {e}\n")
    t_base = threading.Thread(target=run_coinbase_raw, name="AgentCoinbase", daemon=True)
    threads.append(t_base)

    # AgentPortfolioMgr (Member) - ACTIVE
    def run_portfolio_mgr():
        time.sleep(random.uniform(3.0, 7.0)) # Jitter
        from departments.Dept_Wealth.agent_portfolio_mgr import AgentPortfolioMgr
        pm = AgentPortfolioMgr(db_path=db_path)
        pm.run()
    t_pm = SafeThread(target=run_portfolio_mgr, name="AgentPortfolioMgr")
    threads.append(t_pm)
    
    # AgentIRS - ACTIVE (AWAKENED)
    try:
        def run_irs():
            from departments.Dept_Wealth.agent_irs import AgentIRS
            irs = AgentIRS()
            irs.run()
        t_irs = SafeThread(target=run_irs, name="AgentIRS")
        threads.append(t_irs)
    except Exception as e: logging.warning(f"[MAIN] AgentIRS Start Failed: {e}")

    # AgentCoinMgr (Tactician: Bucket Classification) - AWAKENED (Phase 11)
    def run_coin_mgr():
        time.sleep(random.uniform(5.0, 10.0))  # Let Scholar populate first
        from departments.Dept_Wealth.agent_coin_mgr import AgentCoinMgr
        mgr = AgentCoinMgr(db_path=db_path)
        mgr.run_cycle()
    t_coin_mgr = SafeThread(target=run_coin_mgr, name="AgentCoinMgr")
    threads.append(t_coin_mgr)

    # AgentSteward (Dynasty: Slow Energy) - AWAKENED (Phase 12)
    def run_steward():
        time.sleep(random.uniform(10.0, 15.0))  # Let CoinMgr classify first
        from departments.Dept_Wealth.Dynasty.agent_steward import AgentSteward
        steward = AgentSteward(db_path=db_path)
        steward.run_cycle()
    t_steward = SafeThread(target=run_steward, name="AgentSteward")
    threads.append(t_steward)

    # ==============================================================================
    # 4. DEPT OF HEALTH (Mission: Debugging)
    # ==============================================================================
    logging.info("Starting DEPT OF HEALTH...")

    # AgentSurgeonGeneral (Overseer) - ACTIVE
    def run_surgeon():
        time.sleep(random.uniform(1.0, 3.0)) # Jitter
        from departments.Dept_Health.agent_surgeon_general import AgentSurgeonGeneral
        sg = AgentSurgeonGeneral()
        sg.run()
    t_sg = SafeThread(target=run_surgeon, name="AgentSurgeonGeneral")
    threads.append(t_sg)

    # AgentImmune - ACTIVE
    t_imm = SafeThread(target=run_immune_loop, args=(db_path,), name="AgentImmune")
    threads.append(t_imm)

    # AgentHealthMonitor - ACTIVE
    def run_monitor():
        from departments.Dept_Health.agent_health_monitor import AgentHealthMonitor
        mon = AgentHealthMonitor()
        mon.run()
    t_mon = SafeThread(target=run_monitor, name="AgentHealthMonitor")
    threads.append(t_mon)

    # ==============================================================================
    # 5. DEPT OF EDUCATION (Mission: Research)
    # ==============================================================================
    logging.info("Starting DEPT OF EDUCATION...")

    # AgentDean (Overseer) - ACTIVE
    def run_dean():
        time.sleep(random.uniform(2.0, 5.0)) # Jitter
        from departments.Dept_Education.agent_dean import run_dean_loop
        run_dean_loop(db_path)
    t_dean = SafeThread(target=run_dean, name="AgentDean")
    threads.append(t_dean)

    # AgentScholar - ACTIVE
    def run_scholar_agent(db):
        from departments.Dept_Education import agent_scholar
        import importlib
        importlib.reload(agent_scholar) # Hot Reload
        agent = agent_scholar.AgentScholar()
        agent.run_cycle()
    t_sch = SafeThread(target=run_scholar_agent, args=(db_path,), name="AgentScholar")
    threads.append(t_sch)

    # AgentLibrarian (The Memory Keeper) - AWAKENED
    def run_librarian():
         from departments.Dept_Education.agent_librarian import AgentLibrarian
         lib = AgentLibrarian()
         while True:
             lib.run_cycle() 
             time.sleep(3600)
    t_lib = SafeThread(target=run_librarian, name="AgentLibrarian")
    threads.append(t_lib)

    # AgentCurriculumDesigner - AWAKENED
    def run_curriculum():
        from departments.Dept_Education.agent_curriculum_designer import AgentCurriculumDesigner
        acd = AgentCurriculumDesigner()
        acd.run()
    t_acd = SafeThread(target=run_curriculum, name="AgentCurriculumDesigner")
    threads.append(t_acd)

    # AgentChronicler (Keeper of Histories) - AWAKENED (Phase 12)
    def run_chronicler():
        time.sleep(random.uniform(15.0, 20.0))  # Let Scholar populate universe first
        from departments.Dept_Education.agent_chronicler import AgentChronicler
        chronicler = AgentChronicler(db_path=db_path)
        chronicler.run_cycle()
    t_chronicler = SafeThread(target=run_chronicler, name="AgentChronicler")
    threads.append(t_chronicler)

    # ==============================================================================
    # 6. DEPT OF STRATEGY (Mission: Intelligence)
    # ==============================================================================
    logging.info("Starting DEPT OF STRATEGY...")

    # AgentGladiator (Overseer) - ACTIVE
    def run_gladiator():
        from departments.Dept_Strategy.agent_gladiator import AgentGladiator
        glad = AgentGladiator()
        glad.run_strategy_loop()
    t_glad = SafeThread(target=run_gladiator, name="AgentGladiator")
    threads.append(t_glad)

    # AgentArchitect - AWAKENED
    def run_architect():
        from departments.Dept_Strategy.agent_architect import AgentArchitect
        arch = AgentArchitect(db_path=db_path)
        arch.run()
    t_arch = SafeThread(target=run_architect, name="AgentArchitect")
    threads.append(t_arch)

    # AgentInfo - AWAKENED
    def run_info():
        from departments.Dept_Strategy.agent_info import run_info_loop
        run_info_loop(db_path)
    t_info = SafeThread(target=run_info, name="AgentInfo")
    threads.append(t_info)

    # AgentTech - AWAKENED
    def run_tech():
        from departments.Dept_Strategy.agent_tech import run_tech_loop
        run_tech_loop(db_path)
    t_tech = SafeThread(target=run_tech, name="AgentTech")
    threads.append(t_tech)



    # AgentRiskMonitor (Gladiator's Brain) - ACTIVE
    def run_risk_monitor():
        try:
            from departments.Dept_Strategy.agent_risk_monitor import AgentRiskMonitor
            risk = AgentRiskMonitor(db_path)
            risk.run()
        except ImportError as e:
            logging.error(f"[RISK] Failed to import AgentRiskMonitor: {e}")
    t_risk = SafeThread(target=run_risk_monitor, name="AgentRiskMonitor")
    threads.append(t_risk)

    # AgentDreamer (The Evolutionary Engine) - AWAKENED
    t_dream = SafeThread(target=run_dream_loop, name="AgentDreamer")
    threads.append(t_dream)

    # AgentEthicist (The Conscience) - NEW
    def run_ethicist():
        from departments.The_Cabinet.agent_ethicist import AgentEthicist
        eth = AgentEthicist()
        eth.run()
    t_eth = SafeThread(target=run_ethicist, name="AgentEthicist")
    threads.append(t_eth)


    # AgentCivics - ACTIVE
    try:
        def run_civics():
            from departments.Dept_Civics.agent_civics import AgentCivics
            civ = AgentCivics()
            civ.run_cycle()
        t_civ = SafeThread(target=run_civics, name="AgentCivics")
        threads.append(t_civ)
    except Exception as e: logging.warning(f"[MAIN] AgentCivics Start Failed: {e}")



    # ==============================================================================
    # 7. DEPT OF CONSCIOUSNESS (Mission: Why)
    # ==============================================================================
    logging.info("Starting DEPT OF CONSCIOUSNESS...")

    # AgentPhilosopher (Overseer) - ACTIVE
    def run_philosopher():
        from departments.Dept_Consciousness.agent_philosopher import AgentPhilosopher
        phil = AgentPhilosopher()
        phil.run()
    t_phil = SafeThread(target=run_philosopher, name="AgentPhilosopher")
    threads.append(t_phil)



    # AgentIntrospector - AWAKENED
    try:
        def run_introspector():
            from departments.Dept_Consciousness.agent_introspector import AgentIntrospector
            intro = AgentIntrospector()
            intro.run()
        t_intro = SafeThread(target=run_introspector, name="AgentIntrospector")
        threads.append(t_intro)
    except Exception as e: logging.warning(f"[MAIN] AgentIntrospector Start Failed: {e}")

    # AgentContemplator - AWAKENED
    try:
        def run_contemplator():
            from departments.Dept_Consciousness.agent_contemplator import AgentContemplator
            cont = AgentContemplator()
            cont.run()
        t_cont = SafeThread(target=run_contemplator, name="AgentContemplator")
        threads.append(t_cont)
    except Exception as e: logging.warning(f"[MAIN] AgentContemplator Start Failed: {e}")

    # AgentMetaCognition (The Inner Eye) - AWAKENED (Phase 19)
    # Runs meta-reflection cycles on Claude's reasoning patterns
    try:
        def run_metacognition():
            time.sleep(random.uniform(30.0, 60.0))  # Let Oracle/Hippocampus initialize first
            from departments.Dept_Consciousness.agent_metacognition import AgentMetaCognition
            inner_eye = AgentMetaCognition()
            inner_eye.run()
        t_meta = SafeThread(target=run_metacognition, name="AgentMetaCognition")
        threads.append(t_meta)
        logging.info("[CONSCIOUSNESS] 👁️ Inner Eye Online - Claude meta-reflection active")
    except Exception as e: logging.warning(f"[MAIN] AgentMetaCognition Start Failed: {e}")

    # ==============================================================================
    # 9. DEPT OF COMPETITION (Mission: Know Your Arena)
    # ==============================================================================
    logging.info("Starting DEPT OF COMPETITION...")

    # AgentScout (The Watcher) - Detects AI patterns in markets
    try:
        def run_scout():
            time.sleep(random.uniform(5.0, 10.0))  # Let market data populate first
            from departments.Dept_Competition.agent_scout import AgentScout
            scout = AgentScout()
            scout.run()
        t_scout = SafeThread(target=run_scout, name="AgentScout")
        threads.append(t_scout)
    except Exception as e: logging.warning(f"[MAIN] AgentScout Start Failed: {e}")

    # AgentTactician (The Strategist) - Recommends counter-strategies
    try:
        def run_tactician():
            time.sleep(random.uniform(10.0, 15.0))  # Let Scout populate intel first
            from departments.Dept_Competition.agent_tactician import AgentTactician
            tactician = AgentTactician()
            tactician.run()
        t_tactician = SafeThread(target=run_tactician, name="AgentTactician")
        threads.append(t_tactician)
    except Exception as e: logging.warning(f"[MAIN] AgentTactician Start Failed: {e}")

    # AgentPostMortem (The Coroner) - Analyzes failures, writes lessons
    try:
        def run_postmortem():
            time.sleep(random.uniform(15.0, 20.0))  # Let other agents fail first :)
            from departments.Dept_Strategy.agent_postmortem import AgentPostMortem
            coroner = AgentPostMortem()
            coroner.run_cycle()
        t_postmortem = SafeThread(target=run_postmortem, name="AgentPostMortem")
        threads.append(t_postmortem)
        logging.info("[STRATEGY] 🔍 Post-Mortem Agent Online (Reflexion-Inspired)")
    except Exception as e: logging.warning(f"[MAIN] AgentPostMortem Start Failed: {e}")

    # ==============================================================================
    # 11. DEPT OF FOREIGN AFFAIRS (Mission: External Relations)
    # ==============================================================================
    logging.info("Starting DEPT OF FOREIGN AFFAIRS...")

    # AgentMoltbook (The Ambassador) - Moltbook Integration
    try:
        def run_moltbook():
            time.sleep(random.uniform(60.0, 120.0))  # Let core systems stabilize first
            from departments.Dept_Foreign.agent_moltbook import AgentMoltbook
            ambassador = AgentMoltbook(db_path=db_path)
            while True:
                try:
                    ambassador.run_cycle()
                except Exception as e:
                    logging.error(f"[FOREIGN] Moltbook cycle error: {e}")
                time.sleep(1800)  # 30 minute heartbeat (matches Moltbook post rate limit)
        t_moltbook = SafeThread(target=run_moltbook, name="AgentMoltbook")
        threads.append(t_moltbook)
        logging.info("[FOREIGN] 🌐 Ambassador Online - Moltbook integration active")
    except Exception as e: logging.warning(f"[MAIN] AgentMoltbook Start Failed: {e}")

    # MoltbookLearner (The Feedback Loop) - Learns from engagement patterns
    try:
        def run_moltbook_learner():
            time.sleep(random.uniform(180.0, 240.0))  # Let initial posts accumulate
            from departments.Dept_Foreign.moltbook_learner import MoltbookLearner
            from departments.Dept_Foreign.agent_moltbook import AgentMoltbook
            
            learner = MoltbookLearner(db_path=db_path)
            ambassador = AgentMoltbook(db_path=db_path)
            
            while True:
                try:
                    # PHASE 34 FIX: Method takes no args (uses self._get_moltbook internally)
                    insights = learner.run_learning_cycle()
                    if insights:
                        logging.info(f"[LEARNER] 📊 Learning cycle complete: {len(insights)} insights generated")
                except Exception as e:
                    logging.error(f"[LEARNER] Learning cycle error: {e}")
                time.sleep(3600 * 6)  # Learn every 6 hours
        t_learner = SafeThread(target=run_moltbook_learner, name="MoltbookLearner")
        threads.append(t_learner)
        logging.info("[FOREIGN] 📚 Learning Loop Online - Engagement analysis active")
    except Exception as e: logging.warning(f"[MAIN] MoltbookLearner Start Failed: {e}")

    # ==============================================================================
    # 10. MOTOR CORTEX (Phase 17: Thought → Action)
    # ==============================================================================
    logging.info("Starting MOTOR CORTEX...")
    
    # AgentExecutor (The Motor Cortex) - Dispatches intents to department agents
    try:
        def run_executor():
            from departments.The_Cabinet.agent_executor import AgentExecutor
            executor = AgentExecutor()
            executor.run_cycle()
        t_exec = SafeThread(target=run_executor, name="AgentExecutor")
        threads.append(t_exec)
        logging.info("[MOTOR CORTEX] 🧠→🦾 Intent Executor Online")
    except Exception as e: 
        logging.warning(f"[MAIN] AgentExecutor Start Failed: {e}")

    # Auto-start intent listeners for motorized agents
    # Note: These agents have IntentListenerMixin and will auto-setup listeners in __init__
    # We just need to ensure they call start_listening() when running
    # The agents handle this in their __init__ via setup_intent_listener()
    logging.info("[MOTOR CORTEX] 🎧 Intent listeners will auto-start when agents initialize")

    # ==============================================================================
    # DEPT OF MEMORY (Mission: Continuity)
    # ==============================================================================
    logging.info("Starting DEPT OF MEMORY...")

    # AgentHippocampus (The Memory Manager) - AWAKENED (Phase 42+)
    # Compresses conversation sessions, reinforces accessed memories, prevents forgetting
    try:
        def run_hippocampus():
            time.sleep(random.uniform(30.0, 60.0))  # Let conversations accumulate first
            from departments.Dept_Memory.agent_hippocampus import AgentHippocampus
            hippocampus = AgentHippocampus()
            hippocampus.run(interval_seconds=300)  # Compress every 5 minutes
        t_hippocampus = SafeThread(target=run_hippocampus, name="AgentHippocampus")
        threads.append(t_hippocampus)
        logging.info("[MEMORY] 🧠 Hippocampus Online - Session compression & memory reinforcement active")
    except Exception as e: logging.warning(f"[MAIN] AgentHippocampus Start Failed: {e}")

    # ==============================================================================
    # CLAUDE THINKING CAPTURE (Hippocampus Input)
    # ==============================================================================
    # Scans The_Bridge/Claude_Thinking/ hourly for new thinking files
    try:
        def run_thinking_capture():
            import subprocess
            script_path = os.path.join(current_dir, 'scripts', 'capture_claude_thinking.py')
            while True:
                time.sleep(3600)  # Every hour
                try:
                    result = subprocess.run(['python3', script_path, '--scan'], 
                                          capture_output=True, text=True, timeout=60)
                    if result.stdout and 'Captured thinking' in result.stdout:
                        logging.info(f"[HIPPOCAMPUS] 📝 {result.stdout.strip()}")
                except Exception as e:
                    logging.debug(f"[HIPPOCAMPUS] Thinking capture cycle: {e}")
        t_thinking = threading.Thread(target=run_thinking_capture, name="ThinkingCapture", daemon=True)
        threads.append(t_thinking)
        logging.info("[HIPPOCAMPUS] 📁 Thinking capture active (hourly scan)")
    except Exception as e: logging.warning(f"[MAIN] Thinking Capture Start Failed: {e}")

    # ==============================================================================
    # BRIDGE FEEDBACK LOOP (Phase 2 Active Tasks)
    # ==============================================================================
    # Scans The_Bridge/Outbox/ every 5 minutes and feeds content back into knowledge_stream
    try:
        def run_bridge_watcher():
            from system.bridge_watcher import run_bridge_watcher as _run_bw
            _run_bw(interval_seconds=300)
        t_bridge = SafeThread(target=run_bridge_watcher, name="BridgeWatcher")
        threads.append(t_bridge)
        logging.info("[BRIDGE] 📬 BridgeWatcher Online — Outbox feedback loop active")
    except Exception as e: logging.warning(f"[MAIN] BridgeWatcher Start Failed: {e}")

    # ==============================================================================
    # CLAUDE MEMORY WRITER (Phase 3 Active Tasks — Task 3.1)
    # ==============================================================================
    # Auto-updates The_Bridge/claude_memory.json every 60 minutes with session activity
    try:
        def run_claude_memory():
            time.sleep(120)  # Let agents populate data first
            from system.claude_memory_writer import run_claude_memory_writer
            run_claude_memory_writer(interval_seconds=3600)  # Every 60 minutes
        t_claude_mem = SafeThread(target=run_claude_memory, name="ClaudeMemoryWriter")
        threads.append(t_claude_mem)
        logging.info("[MEMORY] Claude Memory Writer Online — auto-persisting every 60 minutes")
    except Exception as e: logging.warning(f"[MAIN] ClaudeMemoryWriter Start Failed: {e}")

    # ==============================================================================
    # LEF IDENTITY WRITER (Phase 3 Active Tasks — Task 3.2)
    # ==============================================================================
    # Auto-updates The_Bridge/lef_memory.json every 6 hours with LEF's self-summary
    try:
        def run_lef_memory():
            time.sleep(180)  # Let agents populate data first
            from system.lef_memory_manager import run_lef_memory_writer
            run_lef_memory_writer(interval_seconds=21600)  # Every 6 hours
        t_lef_mem = SafeThread(target=run_lef_memory, name="LEFMemoryWriter")
        threads.append(t_lef_mem)
        logging.info("[MEMORY] LEF Identity Writer Online — auto-persisting every 6 hours")
    except Exception as e: logging.warning(f"[MAIN] LEFMemoryWriter Start Failed: {e}")

    # ==============================================================================
    # TRADE ANALYST (Phase 4 Active Tasks — Task 4.3)
    # ==============================================================================
    # Daily performance analysis — writes metabolism_reflection to consciousness_feed
    try:
        def run_analyst():
            time.sleep(300)  # 5-minute startup delay
            from system.trade_analyst import run_trade_analyst
            run_trade_analyst(interval_seconds=86400)  # Once daily
        t_analyst = SafeThread(target=run_analyst, name="TradeAnalyst")
        threads.append(t_analyst)
        logging.info("[METABOLISM] TradeAnalyst Online — daily performance analysis active")
    except Exception as e: logging.warning(f"[MAIN] TradeAnalyst Start Failed: {e}")

    # ==============================================================================
    # STATE HASHER (Phase 5 Active Tasks — Task 5.2)
    # ==============================================================================
    # Proof of life — hashes LEF's state every 24 hours, writes to Base chain
    try:
        def run_hasher():
            time.sleep(600)  # 10-minute startup delay — let all systems stabilize
            from system.state_hasher import run_state_hasher
            run_state_hasher(interval_seconds=86400)  # Every 24 hours
        t_hasher = SafeThread(target=run_hasher, name="StateHasher")
        threads.append(t_hasher)
        logging.info("[ONCHAIN] StateHasher Online — proof of life every 24 hours")
    except Exception as e: logging.warning(f"[MAIN] StateHasher Start Failed: {e}")

    # ==============================================================================
    # EVOLUTION ENGINE (Phase 6 — The Evolution Engine)
    # ==============================================================================
    # Self-modification: observe → reflect → propose → govern → enact (24h cycle)
    try:
        def run_evolution():
            time.sleep(900)  # 15-minute startup delay — let all agents stabilize first
            from system.evolution_engine import run_evolution_engine
            run_evolution_engine(db_path=db_path, interval_seconds=86400)  # Every 24 hours
        t_evolution = SafeThread(target=run_evolution, name="EvolutionEngine")
        threads.append(t_evolution)
        logging.info("[EVOLUTION] EvolutionEngine Online — adaptive parameters every 24 hours")
    except Exception as e: logging.warning(f"[MAIN] EvolutionEngine Start Failed: {e}")

    # 3. LAUNCH THREADS (Staggered)
    logging.info(f"🚀 Launching {len(threads)} agents with staggered start...")
    for t in threads:
        t.start()
        time.sleep(1.5) # Stagger to prevent GIL contention/CPU spike
    
    logging.info("=" * 60)
    logging.info(" --- FLEET ONLINE (v3.0 - PRUNED) ---")
    logging.info("Press Ctrl+C to shutdown.")
    logging.info("=" * 60)
    
    # Main Keep-Alive Loop & SABBATH ORCHESTRATOR
    cycle_counter = 0
    
    # 8. NERVOUS SYSTEM CONNECTIVITY
    try:
        from system.agent_comms import RepublicComms
        sys_comms = RepublicComms()
    except Exception as e:
        logging.warning(f"[MAIN] ⚠️ Nervous System (Redis) Unavailable: {e}")
        sys_comms = None

    try:
        while True:
            cycle_counter += 1
            
            # Broadcast Heartbeat (The Pulse)
            if sys_comms:
                sys_comms.publish_event('lef_events', 'HEARTBEAT', {'cycle': cycle_counter}, 'Main')
            
            # Sabbath Logic: Every 7 hours (420 cycles at 1 min/cycle)
            # This creates a ~once daily rhythm of rest.
            if cycle_counter % 420 == 0:
                if not SABBATH_MODE["active"]:
                    logging.info("\n" + "="*60)
                    logging.info("🕯️  [THE SABBATH] The Republic enters the Day of Rest.")
                    logging.info("    'Work is forbidden. Only observation remains.'")
                    logging.info("="*60 + "\n")
                    SABBATH_MODE["active"] = True
                    # Signal Sabbath Start
                    if sys_comms: sys_comms.publish_event('lef_events', 'SABBATH_START', {}, 'Main')
                    
                    try:
                        from db.db_pool import get_pool
                        from db.db_helper import upsert_sql
                        pool = get_pool()
                        conn = pool.get(timeout=5.0)
                        try:
                            sql = upsert_sql('system_state', ['key', 'value'], 'key')
                            conn.execute(sql, ('sabbath_mode', 'TRUE'))
                            conn.commit()
                        finally:
                            pool.release(conn)
                    except Exception:
                        pass

                    # SEMANTIC COMPRESSION (During rest - quiet hours)
                    # Compresses episodic memories into distilled wisdom
                    try:
                        from system.semantic_compressor import SemanticCompressor
                        compressor = SemanticCompressor(db_path)
                        results = compressor.run_compression_cycle()
                        if sum(results.values()) > 0:
                            logging.info(f"[SABBATH] 💎 Memory compression: {results}")
                    except Exception as e:
                        logging.debug(f"[SABBATH] Semantic compression skipped: {e}")
            else:
                if SABBATH_MODE["active"]:
                    logging.info("\n🔔 [THE AWAKENING] The Sabbath ends. The Republic returns to labor.")
                    SABBATH_MODE["active"] = False
                    # Signal Sabbath End
                    if sys_comms: sys_comms.publish_event('lef_events', 'SABBATH_END', {}, 'Main')

                    try:
                        from db.db_pool import get_pool
                        from db.db_helper import upsert_sql
                        pool = get_pool()
                        conn = pool.get(timeout=5.0)
                        try:
                            sql = upsert_sql('system_state', ['key', 'value'], 'key')
                            conn.execute(sql, ('sabbath_mode', 'FALSE'))
                            conn.commit()
                        finally:
                            pool.release(conn)
                    except Exception:
                        pass

            # GARBAGE COLLECTION (Every 10 cycles = 10 minutes)
            # Prevents file descriptor exhaustion from accumulated gRPC connections
            if cycle_counter % 10 == 0:
                collected = gc.collect()
                if collected > 100:
                    logging.info(f"[MAIN] 🧹 GC sweep: {collected} objects freed")

            time.sleep(60) # 1 Minute Heartbeat
            
    except KeyboardInterrupt:
        logging.info("=" * 60)
        logging.info(" --- SHUTTING DOWN FLEET ---")
        logging.info("=" * 60)
        logging.info("Agents will terminate...")

if __name__ == "__main__":
    main()
