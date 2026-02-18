"""
Republic Virtual Fleet - Main Orchestrator
Deploys the distributed agent network.

Based on: Republic MacBook Agent Implementation Guide
"""

import gc
import signal
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

# Phase 21.3a: Global shutdown event for graceful termination
_shutdown_event = threading.Event()


def _handle_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logging.info(f"[MAIN] Received {sig_name}, initiating graceful shutdown...")
    _shutdown_event.set()


signal.signal(signal.SIGTERM, _handle_shutdown)
signal.signal(signal.SIGINT, _handle_shutdown)

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
# Phase 9.H4a: Replaced per-message SQLiteHandler with batched queue.
# Old pattern: every log message acquired a pool connection → hundreds of
# acquisitions per minute → pool exhaustion with 46+ concurrent agents.
# New pattern: buffer in memory, flush every 5s with ONE connection → ~12 per minute.

class BatchedLogHandler(logging.Handler):
    """
    Batched logging handler — collects log messages in memory,
    flushes to database periodically using a SINGLE pool connection.

    Why: The old SQLiteHandler acquired a pool connection for every
    single log message. With 46+ agents logging frequently, this alone
    consumed more connections than the pool could sustain.
    """

    FLUSH_INTERVAL = 5.0    # seconds between flushes
    MAX_BATCH_SIZE = 200    # force flush if batch exceeds this

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self._pool = None
        self._buffer = []
        self._lock = threading.Lock()
        self._flush_thread = None
        self._running = False

    def start(self):
        """Start the background flush thread."""
        self._running = True
        self._flush_thread = threading.Thread(
            target=self._flush_loop,
            name="LogFlusher",
            daemon=True
        )
        self._flush_thread.start()

    def _get_pool(self):
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except ImportError:
                self._pool = None
        return self._pool

    def emit(self, record):
        """Buffer the log message — NO pool connection acquired here."""
        try:
            entry = (record.name, record.levelname, record.getMessage())
            with self._lock:
                self._buffer.append(entry)
                if len(self._buffer) >= self.MAX_BATCH_SIZE:
                    self._flush_now()
        except Exception:
            self.handleError(record)

    def _flush_loop(self):
        """Background thread: flush buffer every FLUSH_INTERVAL seconds."""
        while self._running:
            time.sleep(self.FLUSH_INTERVAL)
            with self._lock:
                if self._buffer:
                    self._flush_now()

    def _flush_now(self):
        """Write all buffered logs with ONE pool connection. Called under lock."""
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()

        pool = self._get_pool()
        if not pool:
            return  # Silently drop if no pool — stdout already has the logs

        try:
            conn = pool.get(timeout=10.0)
            try:
                from db.db_helper import translate_sql
                sql = translate_sql(
                    "INSERT INTO agent_logs (source, level, message) VALUES (?, ?, ?)"
                )
                for source, level, msg in batch:
                    conn.execute(sql, (source, level, msg))
                conn.commit()
            finally:
                pool.release(conn)
        except Exception:
            pass  # Logs still went to stdout — DB logging is nice-to-have, not critical

    def stop(self):
        """Flush remaining and stop."""
        self._running = False
        with self._lock:
            self._flush_now()

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

# Phase 16 — Task 16.6: Bridge Watcher health monitor
def _bridge_watcher_health_monitor():
    """Detect if bridge_watcher has stopped running."""
    import time as _time
    _time.sleep(600)  # Initial 10-min delay
    while True:
        try:
            from system.redis_client import get_redis
            _r = get_redis()
            if _r:
                heartbeat = _r.get('bridge_watcher:heartbeat')
                if heartbeat is None:
                    logging.error("[HealthCheck] ⚠️ bridge_watcher has no heartbeat — may be dead")
                    try:
                        from db.db_helper import db_connection, translate_sql
                        with db_connection() as _hc_conn:
                            _hc_c = _hc_conn.cursor()
                            _hc_c.execute(translate_sql(
                                "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                                "VALUES (?, ?, 'system_alert', NOW())"
                            ), ('HealthCheck', 'bridge_watcher heartbeat missing — Outbox communication may be down'))
                            _hc_conn.commit()
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"[HealthCheck] Bridge watcher check failed: {e}")
        _time.sleep(600)  # Check every 10 minutes


# Phase 16 — Task 16.7: Log rotation for The_Bridge/Logs/
def _run_log_rotation():
    import time as _time
    _time.sleep(3600)  # Initial 1-hour delay
    while True:
        try:
            from system.log_rotation import LogRotator
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'The_Bridge', 'Logs')
            rotator = LogRotator(
                logs_dir=logs_dir,
                max_file_size_mb=5,
                max_files=30,
                max_age_days=30
            )
            rotator.rotate()
        except Exception as e:
            logging.warning(f"[MAIN] Log rotation failed: {e}")
        _time.sleep(3600)  # Run hourly


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

    # Phase 9.H4a: Batched DB log handler — replaces per-message SQLiteHandler
    batched_handler = BatchedLogHandler(db_path)
    batched_handler.setLevel(logging.DEBUG)
    batched_handler.start()
    root_logger.addHandler(batched_handler)

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

    # Phase 21.3b: Cold Start Validation — catch problems before launching threads
    def _validate_startup():
        """
        Pre-flight checks before any agent threads launch.
        Validates: DB connectivity, required tables, Redis, config files,
        and recovers orphaned trades from prior crash.
        """
        errors = []

        # 1. Database connectivity
        try:
            test_conn = sqlite3.connect(db_path, timeout=30)
            test_conn.execute("SELECT 1")
        except Exception as e:
            errors.append(f"DB connectivity: {e}")
            test_conn = None

        # 2. Required tables exist
        if test_conn:
            required_tables = [
                'consciousness_feed', 'trade_queue', 'assets', 'agent_logs',
                'book_of_scars', 'system_state', 'lef_monologue', 'intent_queue',
                'knowledge_stream', 'signal_history'
            ]
            for table in required_tables:
                try:
                    test_conn.execute(f"SELECT COUNT(*) FROM {table}")
                except Exception:
                    errors.append(f"Missing table: {table}")

        # 3. Redis connectivity (warn, don't block — LEF can run without Redis)
        try:
            from system.redis_client import get_redis
            r = get_redis()
            if r is None:
                logging.warning("[STARTUP] ⚠️ Redis unavailable — running without cache")
            else:
                logging.info("[STARTUP] ✅ Redis connected")
        except Exception as e:
            logging.warning(f"[STARTUP] ⚠️ Redis check failed: {e}")

        # 4. Config files valid JSON
        config_dir = os.path.join(current_dir, "config")
        critical_configs = ['config.json', 'wealth_strategy.json']
        for cfg in critical_configs:
            cfg_path = os.path.join(config_dir, cfg)
            try:
                with open(cfg_path, 'r') as f:
                    json.load(f)
            except FileNotFoundError:
                errors.append(f"Missing config: {cfg}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in {cfg}: {e}")

        # 5. Recover orphaned trades (IN_PROGRESS → FAILED with reason)
        if test_conn:
            try:
                cursor = test_conn.cursor()
                cursor.execute(
                    "UPDATE trade_queue SET status='FAILED', reason='orphaned_on_restart' "
                    "WHERE status='IN_PROGRESS'"
                )
                orphaned = cursor.rowcount
                if orphaned > 0:
                    test_conn.commit()
                    logging.warning(
                        f"[STARTUP] ⚠️ Recovered {orphaned} orphaned IN_PROGRESS trades → FAILED"
                    )
                else:
                    logging.info("[STARTUP] ✅ No orphaned trades")
            except Exception as e:
                logging.warning(f"[STARTUP] Trade recovery check: {e}")

        # 6. Validate ENV: references in config (21.3g cross-link)
        try:
            with open(os.path.join(config_dir, 'config.json'), 'r') as f:
                cfg_data = json.load(f)

            def _check_env_refs(obj, path="config"):
                """Recursively find ENV: references and verify they resolve."""
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        _check_env_refs(v, f"{path}.{k}")
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        _check_env_refs(v, f"{path}[{i}]")
                elif isinstance(obj, str) and obj.startswith("ENV:"):
                    env_var = obj[4:]
                    if not os.environ.get(env_var):
                        logging.warning(
                            f"[STARTUP] ⚠️ Unresolved ENV reference: {path} → {obj}"
                        )

            _check_env_refs(cfg_data)
        except Exception:
            pass  # Config already checked above

        # Close test connection
        if test_conn:
            try:
                test_conn.close()
            except Exception:
                pass

        # Fatal errors: abort startup
        if errors:
            for e in errors:
                logging.critical(f"[STARTUP] ❌ {e}")
            raise SystemExit(f"Startup validation failed: {len(errors)} error(s)")

        logging.info("[STARTUP] ✅ All pre-flight checks passed")

    _validate_startup()

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
                    # Phase 20.1c: Send sabbath_rest heartbeat so Brainstem knows we're resting, not dead
                    try:
                        from system.brainstem import brainstem_heartbeat as _bs_hb
                        _bs_hb(self.name, status="sabbath_rest")
                    except Exception:
                        pass
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
                    # Phase 30.5: Report crash to brainstem immediately
                    try:
                        from system.brainstem import brainstem_heartbeat as _bs_crash
                        _bs_crash(self.name, status=f"crashed:{type(e).__name__}")
                    except Exception:
                        pass
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
    # Phase 18: Moltbook removed. OpenClaw integration planned for future phase.

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
    # BRIDGE WATCHER HEALTH MONITOR (Phase 16 — Task 16.6)
    # ==============================================================================
    health_thread = threading.Thread(target=_bridge_watcher_health_monitor, daemon=True, name="BridgeWatcherHealthMonitor")
    threads.append(health_thread)
    logging.info("[HEALTH] BridgeWatcher health monitor online (10-min heartbeat check)")

    # ==============================================================================
    # LOG ROTATION (Phase 16 — Task 16.7)
    # ==============================================================================
    log_rotation_thread = threading.Thread(target=_run_log_rotation, daemon=True, name="LogRotation")
    threads.append(log_rotation_thread)
    logging.info("[MAIN] Log rotation online (hourly, 5MB max, 30-day retention)")

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
    # TABLE MAINTENANCE (Phase 21.1b-d — periodic cleanup)
    # ==============================================================================
    try:
        def run_table_maintenance():
            time.sleep(300)  # 5-minute startup delay
            from system.table_maintenance import run_maintenance_loop
            run_maintenance_loop()
        t_maintenance = SafeThread(target=run_table_maintenance, name="TableMaintenance")
        threads.append(t_maintenance)
        logging.info("[INFRA] TableMaintenance Online — 6-hour cleanup cycles")
    except Exception as e: logging.warning(f"[MAIN] TableMaintenance Start Failed: {e}")

    # ==============================================================================
    # EVOLUTION ENGINE (Phase 6 + Phase 9 Autonomous Scheduling)
    # ==============================================================================
    # Self-modification: observe → reflect → propose → govern → enact
    # Phase 9: Cadence adapts to circadian rhythm instead of fixed 24h cycle
    try:
        def run_evolution():
            time.sleep(900)  # 15-minute startup delay — let all agents stabilize first
            from system.evolution_engine import EvolutionEngine
            from system.observers.metabolism_observer import MetabolismObserver
            from system.observers.consciousness_observer import ConsciousnessObserver
            from system.observers.operational_observer import OperationalObserver
            from system.observers.relational_observer import RelationalObserver
            from system.observers.identity_observer import IdentityObserver

            engine = EvolutionEngine(db_path=db_path)

            # Wire Sabbath ↔ EvolutionEngine (Phase 9 — register_sabbath + evolution_engine ref)
            if sabbath_instance:
                # Give Sabbath a reference to the evolution engine so intentions become proposals
                sabbath_instance.evolution_engine = engine
                # Register Sabbath with SparkGovernance so vest_action pauses during active Sabbaths
                if hasattr(engine, '_spark') and engine._spark and hasattr(engine._spark, 'spark_governance'):
                    engine._spark.spark_governance.register_sabbath(sabbath_instance)
                    logging.info("[EVOLUTION] Sabbath registered with SparkGovernance.")

            # Register domain observers
            engine.register_observer('metabolism', MetabolismObserver(db_path).observe)
            engine.register_observer('consciousness', ConsciousnessObserver(db_path).observe)
            engine.register_observer('operational', OperationalObserver(db_path).observe)
            engine.register_observer('relational', RelationalObserver(db_path).observe)
            engine.register_observer('identity', IdentityObserver(db_path).observe)

            while True:
                try:
                    # Get circadian state for adaptive cadence
                    try:
                        from departments.Dept_Health.biological_systems import BiologicalSystems
                        bio = BiologicalSystems(db_path=db_path)
                        circadian = bio.get_circadian_state().get('state', 'DAY')
                    except Exception:
                        circadian = 'DAY'

                    # Cadence adapts to circadian rhythm
                    if circadian == 'DAY':
                        interval = 3600       # 1 hour
                    elif circadian in ('DAWN', 'DUSK'):
                        interval = 7200       # 2 hours
                    elif circadian == 'SABBATH':
                        interval = 0          # Skip — Sabbath handles its own evolution
                    else:  # NIGHT, NIGHT_LATE
                        interval = 14400      # 4 hours

                    if interval > 0:
                        engine.run_evolution_cycle()
                        logging.info(f"[EVOLUTION] Cycle complete. Next in {interval//60} minutes (circadian: {circadian})")

                    time.sleep(interval if interval > 0 else 3600)
                except Exception as e:
                    logging.error(f"[EVOLUTION] Cycle error: {e}")
                    time.sleep(600)  # Backoff on error

        t_evolution = SafeThread(target=run_evolution, name="EvolutionEngine")
        threads.append(t_evolution)
        logging.info("[EVOLUTION] EvolutionEngine Online — circadian-adaptive cycles (Phase 9)")
    except Exception as e: logging.warning(f"[MAIN] EvolutionEngine Start Failed: {e}")

    # ==============================================================================
    # Phase 38.5: Semantic Compressor — wisdom distillation from raw experience
    # Activates a fully-built but dormant system. Runs daily after 2h startup delay.
    # ==============================================================================
    try:
        from system.semantic_compressor import SemanticCompressor
        _compressor = SemanticCompressor()
        def _run_compression():
            import time
            time.sleep(7200)  # Wait 2 hours — needs accumulated experience data
            while True:
                try:
                    result = _compressor.run_compression_cycle()
                    logging.info(f"[SemanticCompressor] Cycle complete — scars:{result.get('scars_compressed', 0)}, experiences:{result.get('experiences_compressed', 0)}")
                except Exception as e:
                    logging.error(f"[SemanticCompressor] Cycle error: {e}")
                time.sleep(86400)  # 24 hours — daily compression
        t_compressor = SafeThread(target=_run_compression, name='SemanticCompressor', daemon=True)
        t_compressor.start()
        threads.append(t_compressor)
        logging.info("[MAIN] SemanticCompressor Online — daily wisdom distillation active")
    except ImportError:
        logging.warning("[MAIN] SemanticCompressor not available")

    # ==============================================================================
    # Phase 44: Lifecycle Stage — developmental awareness
    # ==============================================================================
    try:
        from system.lifecycle_stage import get_lifecycle_stage
        from db.db_helper import db_connection as _lcs_db
        _lifecycle = get_lifecycle_stage(_lcs_db)
        def _run_lifecycle():
            import time
            time.sleep(300)  # Wait 5 min after startup
            while True:
                try:
                    stage = _lifecycle.assess()
                    logging.info(f"[LifecycleStage] Assessment: {stage.get('stage', '?')} (age={stage.get('age_days', '?')}d)")
                except Exception as e:
                    logging.error(f"[LifecycleStage] Assessment error: {e}")
                time.sleep(86400)  # 24 hours
        SafeThread(target=_run_lifecycle, name='LifecycleStage', daemon=True).start()
        logging.info("[MAIN] LifecycleStage Online — developmental awareness active")
    except ImportError:
        logging.warning("[MAIN] LifecycleStage not available")

    # ==============================================================================
    # Phase 45: Sustainability Equilibrium — concept of "enough"
    # ==============================================================================
    try:
        from system.sustainability_equilibrium import get_equilibrium
        from db.db_helper import db_connection as _eq_db
        _equilibrium = get_equilibrium(_eq_db)
        def _run_equilibrium():
            import time
            time.sleep(600)  # Wait 10 min
            while True:
                try:
                    result = _equilibrium.assess()
                    logging.info(f"[Sustainability] Status: {result.get('status', '?')} — {result.get('months_of_runway', 0):.1f} months runway")
                except Exception as e:
                    logging.error(f"[Sustainability] Assessment error: {e}")
                time.sleep(21600)  # 6 hours
        SafeThread(target=_run_equilibrium, name='Sustainability', daemon=True).start()
        logging.info("[MAIN] SustainabilityEquilibrium Online — concept of enough active")
    except ImportError:
        logging.warning("[MAIN] SustainabilityEquilibrium not available")

    # ==============================================================================
    # THREE-BODY REFLECTION ARCHITECTURE (Phase 9)
    # ==============================================================================
    # Body One: Republic Reflection — continuous peripheral awareness
    # Body Two: Sovereign Reflection — deeper felt sense, gravity assessment
    # Body Three: Sabbath — deliberate gravity-responsive stillness
    republic_reflection = None
    sovereign_reflection = None
    sabbath_instance = None
    try:
        from db.db_helper import db_connection
        from system.republic_reflection import RepublicReflection
        from system.gravity import GravitySystem
        from system.sovereign_reflection import SovereignReflection
        from system.sabbath import Sabbath

        # Body One: Republic Reflection — continuous peripheral awareness
        republic_reflection = RepublicReflection(
            db_connection_func=db_connection,
            cycle_interval=60  # Every 60 seconds
        )

        # Gravity System — sense of proportion
        gravity_system = GravitySystem(
            db_connection_func=db_connection,
            config_path=os.path.join(current_dir, "config", "gravity_config.json")
        )

        # Phase 10: Get interiority engine for Body Two enrichment
        interiority = None
        try:
            from departments.Dept_Consciousness.interiority_engine import get_interiority_engine
            interiority = get_interiority_engine()
        except Exception:
            pass

        # Body Two: Sovereign Reflection — deeper felt sense
        sovereign_reflection = SovereignReflection(
            db_connection_func=db_connection,
            republic_reflection=republic_reflection,
            gravity_system=gravity_system,
            cycle_interval=300,  # Every 5 minutes
            interiority_engine=interiority  # Phase 10: interiority bridge
        )

        # Body Three: Sabbath — deliberate gravity-responsive stillness
        sabbath_instance = Sabbath(
            db_connection_func=db_connection,
            gravity_system=gravity_system,
            evolution_engine=None  # Wired in Task 9.7 when evolution engine connection is established
        )

        # Wire Body Two → Body Three
        sovereign_reflection.on_sabbath_trigger = sabbath_instance.trigger

        # Start the Three Bodies (order matters: Body One first, then Two, then Three)
        republic_reflection.start()
        sovereign_reflection.start()
        sabbath_instance.start()

        logging.info("[MAIN] Three-Body Reflection Architecture online.")
    except Exception as e:
        logging.warning(f"[MAIN] Three-Body Reflection start failed: {e}")

    # Phase 18.4c: Surface Awareness runs independently (not inside daat_cycle)
    _surface_awareness_independent = None
    try:
        from system.surface_awareness import SurfaceAwareness
        _surface_awareness_independent = SurfaceAwareness()
        _surface_awareness_independent.start()
        logging.info("[MAIN] 👁️ Surface Awareness (X1) running independently")
    except Exception as e:
        logging.warning(f"[MAIN] Independent Surface Awareness start failed: {e}")

    # ======== REVERB TRACKER (Phase 10) ========
    reverb_tracker = None
    try:
        from system.reverb_tracker import ReverbTracker
        reverb_tracker = ReverbTracker(
            db_connection_func=db_connection,
            proposals_path=os.path.join(current_dir, '..', 'The_Bridge', 'evolution_proposals.json'),
            cycle_interval=1800  # Every 30 minutes
        )
        reverb_tracker.start()
        logging.info("[MAIN] Reverb Tracker online. The wave will come back.")
    except Exception as e:
        logging.warning(f"[MAIN] Reverb Tracker start failed: {e}")

    # ======== CYCLE AWARENESS (Phase 10) ========
    cycle_awareness = None
    try:
        from system.cycle_awareness import CycleAwareness
        cycle_awareness = CycleAwareness(db_connection_func=db_connection)
        # Wire into Body Two so it can observe cycle state
        if sovereign_reflection:
            sovereign_reflection.cycle_awareness = cycle_awareness
        logging.info("[MAIN] Cycle Awareness online. The oscillation can be observed.")
    except Exception as e:
        logging.warning(f"[MAIN] Cycle Awareness start failed: {e}")

    # ======== LEARNING LOOP (Phase 11) ========
    try:
        from system.gravity_learner import GravityLearner
        gravity_learner = GravityLearner(
            db_connection_func=db_connection,
            config_path=os.path.join(current_dir, 'config', 'gravity_config.json')
        )
        if sovereign_reflection:
            sovereign_reflection.gravity_learner = gravity_learner
        logging.info("[MAIN] GravityLearner online. Reverb shapes gravity.")
    except Exception as e:
        logging.warning(f"[MAIN] GravityLearner start failed: {e}")

    try:
        from system.resonance_learner import ResonanceLearner
        resonance_learner = ResonanceLearner(
            db_connection_func=db_connection,
            config_path=os.path.join(current_dir, 'config', 'resonance_config.json')
        )
        if sovereign_reflection:
            sovereign_reflection.resonance_learner = resonance_learner
        logging.info("[MAIN] ResonanceLearner online. Filter calibrates from outcomes.")
    except Exception as e:
        logging.warning(f"[MAIN] ResonanceLearner start failed: {e}")

    try:
        from system.sabbath_learner import SabbathLearner
        sabbath_learner = SabbathLearner(
            db_connection_func=db_connection,
            proposals_path=os.path.join(current_dir, '..', 'The_Bridge', 'evolution_proposals.json')
        )
        # Wire into Sabbath instance if available — it will call notify_sabbath_complete()
        if sabbath_instance and hasattr(sabbath_instance, 'sabbath_learner'):
            sabbath_instance.sabbath_learner = sabbath_learner
        logging.info("[MAIN] SabbathLearner online. Compression quality is observed.")
    except Exception as e:
        logging.warning(f"[MAIN] SabbathLearner start failed: {e}")

    logging.info("[MAIN] Phase 11 Learning Loop initialized.")

    # ======== EXISTENTIAL METACOGNITION (Phase 12) ========
    try:
        from system.existential_scotoma import ExistentialScotoma
        existential_scotoma = ExistentialScotoma(db_connection_func=db_connection)
        # Run on a SafeThread-like timer — every 6 hours
        def _existential_scotoma_loop():
            import time as _time
            while True:
                try:
                    existential_scotoma.scan()
                except Exception as e:
                    logging.debug(f"[MAIN] ExistentialScotoma error: {e}")
                _time.sleep(6 * 3600)  # 6 hours

        es_thread = threading.Thread(target=_existential_scotoma_loop, daemon=True, name="ExistentialScotoma")
        threads.append(es_thread)
        logging.info("[MAIN] ExistentialScotoma online (6h cycle).")
    except Exception as e:
        logging.warning(f"[MAIN] ExistentialScotoma start failed: {e}")

    try:
        from departments.Dept_Consciousness.constitutional_observer import ConstitutionalObserver
        constitutional_observer = ConstitutionalObserver(db_connection_func=db_connection)
        # Run every 6 hours, offset 1h from ExistentialScotoma
        def _constitutional_observer_loop():
            import time as _time
            _time.sleep(3600)  # 1h offset from ExistentialScotoma
            while True:
                try:
                    constitutional_observer.observe()
                except Exception as e:
                    logging.debug(f"[MAIN] ConstitutionalObserver error: {e}")
                _time.sleep(6 * 3600)  # 6 hours

        co_thread = threading.Thread(target=_constitutional_observer_loop, daemon=True, name="ConstitutionalObserver")
        threads.append(co_thread)
        logging.info("[MAIN] ConstitutionalObserver online (6h cycle, 1h offset).")
    except Exception as e:
        logging.warning(f"[MAIN] ConstitutionalObserver start failed: {e}")

    try:
        from system.growth_journal import GrowthJournal
        growth_journal = GrowthJournal(db_connection_func=db_connection)
        # Run every 24 hours
        def _growth_journal_loop():
            import time as _time
            _time.sleep(7200)  # 2h offset — let other observers populate data first
            while True:
                try:
                    growth_journal.write_entry()
                except Exception as e:
                    logging.debug(f"[MAIN] GrowthJournal error: {e}")
                _time.sleep(24 * 3600)  # 24 hours

        gj_thread = threading.Thread(target=_growth_journal_loop, daemon=True, name="GrowthJournal")
        threads.append(gj_thread)
        logging.info("[MAIN] GrowthJournal online (24h cycle).")
    except Exception as e:
        logging.warning(f"[MAIN] GrowthJournal start failed: {e}")

    try:
        from system.state_of_republic import StateOfRepublic
        state_of_republic = StateOfRepublic(db_connection_func=db_connection)
        # Run every 168 hours (weekly)
        def _state_of_republic_loop():
            import time as _time
            _time.sleep(10800)  # 3h offset
            while True:
                try:
                    state_of_republic.generate()
                except Exception as e:
                    logging.debug(f"[MAIN] StateOfRepublic error: {e}")
                _time.sleep(168 * 3600)  # 7 days

        sr_thread = threading.Thread(target=_state_of_republic_loop, daemon=True, name="StateOfRepublic")
        threads.append(sr_thread)
        logging.info("[MAIN] StateOfRepublic online (weekly cycle).")
    except Exception as e:
        logging.warning(f"[MAIN] StateOfRepublic start failed: {e}")

    logging.info("[MAIN] Phase 12 Existential Metacognition initialized.")

    # ======== MEMORY CONSOLIDATION (Phase 13) ========
    try:
        from system.season_synthesizer import SeasonSynthesizer
        from system.wisdom_extractor import WisdomExtractor
        from system.memory_pruner import MemoryPruner

        season_synthesizer = SeasonSynthesizer(db_connection_func=db_connection)
        wisdom_extractor = WisdomExtractor(db_connection_func=db_connection)
        memory_pruner = MemoryPruner(db_connection_func=db_connection)

        # Pipeline: synthesize → extract wisdom → prune (sequential, not parallel)
        def _memory_consolidation_loop():
            import time as _time
            from datetime import datetime as _dt
            _time.sleep(14400)  # 4h offset — let Phase 12 populate data first
            while True:
                try:
                    if season_synthesizer.should_synthesize():
                        logging.info("[MAIN] Season synthesis triggered.")
                        summary = season_synthesizer.synthesize()
                        if summary:
                            # Step 2: Extract wisdom from the summary
                            wisdom_extractor.extract(summary)
                            # Step 3: Prune old entries
                            season_end = _dt.fromisoformat(summary["period"]["end"])
                            memory_pruner.prune(season_end)
                        logging.info("[MAIN] Memory consolidation pipeline complete.")
                except Exception as e:
                    logging.debug(f"[MAIN] Memory consolidation error: {e}")
                _time.sleep(24 * 3600)  # Check daily, synthesize when 30 days elapsed

        mc_thread = threading.Thread(target=_memory_consolidation_loop, daemon=True, name="MemoryConsolidation")
        threads.append(mc_thread)
        logging.info("[MAIN] Phase 13 Memory Consolidation pipeline online (daily check, 30-day synthesis cycle).")
    except Exception as e:
        logging.warning(f"[MAIN] Phase 13 Memory Consolidation start failed: {e}")

    # ======== PHASE 14: THE DREAM CYCLE ========
    try:
        from system.sleep_cycle import SleepCycle

        sleep_cycle = SleepCycle(db_connection_func=db_connection)

        def _run_sleep_cycle():
            """Phase 14: Circadian sleep orchestrator. Checks every 5 minutes."""
            time.sleep(300)  # 5-min delay to let all systems initialize
            while True:
                try:
                    sleep_cycle.check_and_transition()
                except Exception as e:
                    logging.error(f"[SLEEP] Cycle error: {e}")
                time.sleep(300)  # Check every 5 minutes

        sleep_thread = threading.Thread(target=_run_sleep_cycle, daemon=True, name="SleepCycle")
        threads.append(sleep_thread)
        logging.info("[MAIN] Phase 14 Sleep Cycle online (5-min check, midnight-6am sleep window).")
    except Exception as e:
        logging.warning(f"[MAIN] Phase 14 Sleep Cycle start failed: {e}")

    # Phase 18.2a: Start Brainstem FIRST — before all other threads
    brainstem = None
    try:
        from system.brainstem import Brainstem, Criticality
        brainstem = Brainstem()
        brainstem.start()
        logging.info("[MAIN] 🫀 Brainstem online (immortal loop)")
    except Exception as e:
        logging.warning(f"[MAIN] Brainstem start failed (non-fatal): {e}")

    # 3. LAUNCH THREADS (Staggered)
    logging.info(f"🚀 Launching {len(threads)} agents with staggered start...")
    for t in threads:
        t.start()
        time.sleep(1.5) # Stagger to prevent GIL contention/CPU spike

    # Phase 18.2c: Register all threads with Brainstem for heartbeat monitoring
    if brainstem:
        try:
            # Map thread names to criticality levels
            vital_threads = {"AgentLEF", "AgentRouter"}
            # Phase 20.1b: Promoted financial safety agents to IMPORTANT
            important_threads = {"AgentCoinbase", "AgentPortfolioMgr",
                                 "CircuitBreaker", "AgentRiskMonitor",
                                 "AgentSurgeonGeneral",
                                 "AgentImmune", "AgentHealthMonitor"}
            for t in threads:
                if t.name in vital_threads:
                    crit = Criticality.VITAL
                elif t.name in important_threads:
                    crit = Criticality.IMPORTANT
                else:
                    crit = Criticality.STANDARD
                brainstem.register_thread(t.name, thread_ref=t, criticality=crit)
            logging.info(f"[MAIN] 🫀 Brainstem: {len(threads)} threads registered")
        except Exception as e:
            logging.warning(f"[MAIN] Brainstem thread registration failed: {e}")

    # Phase 30.1: Start health endpoint (HTTP on port 8080)
    _health_server = None
    try:
        from system.health_server import start_health_server
        _health_server = start_health_server()
    except Exception as e:
        logging.warning(f"[MAIN] Health server failed to start: {e}")

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

    # Phase 16 — Task 16.1: EventBus — subscribe to orphaned Redis channels
    try:
        from system.redis_client import get_redis
        from system.event_bus import EventBus
        redis_client = get_redis()
        event_bus = EventBus(redis_client)
        event_bus.start()
    except Exception as e:
        logging.warning(f"[MAIN] EventBus init failed: {e}")

    try:
        while True:
            cycle_counter += 1
            
            # Broadcast Heartbeat (The Pulse)
            if sys_comms:
                sys_comms.publish_event('lef_events', 'HEARTBEAT', {'cycle': cycle_counter}, 'Main')
            
            # Sabbath Logic: Every 7 hours (420 cycles at 1 min/cycle)
            # This creates a ~once daily rhythm of rest.
            #
            # Phase 18.3c: Added safety exit. Old logic had no duration cap —
            # Sabbath could lock permanently if the modulo condition never
            # re-triggered the exit path. Now tracks entry time and forces
            # exit after 10 minutes (600 seconds).

            if cycle_counter % 420 == 0:
                if not SABBATH_MODE["active"]:
                    logging.info("\n" + "="*60)
                    logging.info("🕯️  [THE SABBATH] The Republic enters the Day of Rest.")
                    logging.info("    'Work is forbidden. Only observation remains.'")
                    logging.info("="*60 + "\n")
                    SABBATH_MODE["active"] = True
                    SABBATH_MODE["entered_at"] = time.time()  # Phase 18.3c: Track entry time
                    # Signal Sabbath Start
                    if sys_comms: sys_comms.publish_event('lef_events', 'SABBATH_START', {}, 'Main')
                    # Phase 20.1c: Publish sabbath state to Redis for Brainstem awareness
                    try:
                        from system.redis_client import get_redis as _gr_sab
                        _r_sab = _gr_sab()
                        if _r_sab:
                            import json as _json_sab
                            _r_sab.set('system:sabbath_active', _json_sab.dumps({
                                'active': True,
                                'resting_agents': RESTING_AGENTS,
                                'started_at': time.time(),
                            }))
                    except Exception:
                        pass

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

            # Phase 18.3c: Sabbath safety exit — cap at 10 minutes
            sabbath_should_end = False
            if SABBATH_MODE["active"]:
                entered_at = SABBATH_MODE.get("entered_at", 0)
                sabbath_duration = time.time() - entered_at if entered_at else 0
                if sabbath_duration > 600:  # 10 minutes max
                    logging.info(f"[SABBATH] ⏰ Safety exit: Sabbath ran {sabbath_duration:.0f}s (>600s cap)")
                    sabbath_should_end = True
                elif cycle_counter % 420 != 0:
                    # Original exit condition: not on a sabbath-start cycle
                    sabbath_should_end = True

            if sabbath_should_end and SABBATH_MODE["active"]:
                    logging.info("\n🔔 [THE AWAKENING] The Sabbath ends. The Republic returns to labor.")
                    SABBATH_MODE["active"] = False
                    SABBATH_MODE.pop("entered_at", None)
                    # Signal Sabbath End
                    if sys_comms: sys_comms.publish_event('lef_events', 'SABBATH_END', {}, 'Main')
                    # Phase 20.1c: Clear sabbath state in Redis
                    try:
                        from system.redis_client import get_redis as _gr_sab2
                        _r_sab2 = _gr_sab2()
                        if _r_sab2:
                            _r_sab2.delete('system:sabbath_active')
                    except Exception:
                        pass

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

            # Phase 21.3a: Check shutdown event instead of running forever
            if _shutdown_event.wait(timeout=60):
                logging.info("[MAIN] Shutdown event received — breaking main loop")
                break

    except KeyboardInterrupt:
        logging.info("[MAIN] KeyboardInterrupt received")
        _shutdown_event.set()

    # Phase 21.3a: Unified graceful shutdown sequence (30 second timeout)
    logging.info("=" * 60)
    logging.info(" --- GRACEFUL SHUTDOWN (Phase 21.3a) ---")
    logging.info("=" * 60)
    _shutdown_start = time.time()

    # 1. Stop Three-Body systems
    for name, system in [
        ('republic_reflection', republic_reflection),
        ('sovereign_reflection', sovereign_reflection),
        ('sabbath', sabbath_instance),
        ('reverb_tracker', reverb_tracker),
    ]:
        if system:
            try:
                system.stop()
                logging.info(f"[SHUTDOWN] {name} stopped")
            except Exception as e:
                logging.warning(f"[SHUTDOWN] {name} stop failed: {e}")

    # 2. Stop EventBus
    try:
        event_bus.stop()
        logging.info("[SHUTDOWN] EventBus stopped")
    except Exception:
        pass

    # 3. Flush batched log handler
    try:
        batched_handler.stop()
        logging.info("[SHUTDOWN] Log handler flushed")
    except Exception:
        pass

    # 4. Close database pool
    try:
        from db.db_pool import get_pool
        pool = get_pool()
        pool.close_all()
        logging.info("[SHUTDOWN] Database pool closed")
    except Exception:
        pass

    # 5. Close Redis connection
    try:
        from system.redis_client import reset_client
        reset_client()
        logging.info("[SHUTDOWN] Redis client reset")
    except Exception:
        pass

    # 6. Write state snapshot
    try:
        import json as _json_shutdown
        snapshot = {
            'shutdown_time': datetime.now().isoformat(),
            'uptime_seconds': time.time() - _shutdown_start,
            'reason': 'graceful_shutdown',
        }
        snapshot_path = os.path.join(BASE_DIR, 'The_Bridge', 'last_shutdown.json')
        with open(snapshot_path, 'w') as f:
            _json_shutdown.dump(snapshot, f, indent=2)
    except Exception:
        pass

    _elapsed = time.time() - _shutdown_start
    logging.info(f"[SHUTDOWN] Complete in {_elapsed:.1f}s. Agents will terminate.")

if __name__ == "__main__":
    main()
