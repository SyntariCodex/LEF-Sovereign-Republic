"""
Phase 30.6: Startup Validation Script (TST-02)

Standalone preflight checks before launching LEF.
Run: python scripts/preflight.py

Checks:
  1. PostgreSQL / SQLite connectivity
  2. Redis connectivity (warn only)
  3. All required tables exist
  4. Config files valid JSON
  5. Required env vars set
  6. Coinbase API key format valid
  7. Gemini API key set
  8. Disk space > 1 GB
  9. File descriptors available
  10. No orphaned IN_PROGRESS trades
"""

import json
import os
import shutil
import resource
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Load .env
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # Manual fallback
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())


def preflight():
    """Run all preflight checks. Returns list of check results."""
    checks = []

    # 1. Database connectivity
    _check_database(checks)
    # 2. Redis
    _check_redis(checks)
    # 3. Required tables
    _check_tables(checks)
    # 4. Config files
    _check_configs(checks)
    # 5. Environment variables
    _check_env_vars(checks)
    # 6. Coinbase API key format
    _check_coinbase_key(checks)
    # 7. Gemini API key
    _check_gemini_key(checks)
    # 8. Disk space
    _check_disk_space(checks)
    # 9. File descriptors
    _check_file_descriptors(checks)
    # 10. Orphaned trades
    _check_orphaned_trades(checks)

    return checks


def _result(name, status, detail):
    return {'check': name, 'status': status, 'detail': detail}


def _check_database(checks):
    backend = os.environ.get('DATABASE_BACKEND', '').lower()
    if backend == 'postgresql':
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.environ.get('POSTGRES_HOST', 'localhost'),
                port=int(os.environ.get('POSTGRES_PORT', 5432)),
                dbname=os.environ.get('POSTGRES_DB', 'republic'),
                user=os.environ.get('POSTGRES_USER', 'republic_user'),
                password=os.environ.get('POSTGRES_PASSWORD', ''),
            )
            conn.cursor().execute("SELECT 1")
            conn.close()
            checks.append(_result('PostgreSQL', 'OK', 'Connected'))
        except Exception as e:
            checks.append(_result('PostgreSQL', 'FAIL', str(e)))
    else:
        import sqlite3
        db_path = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("SELECT 1")
            conn.close()
            checks.append(_result('SQLite', 'OK', f'Connected: {db_path}'))
        except Exception as e:
            checks.append(_result('SQLite', 'FAIL', str(e)))


def _check_redis(checks):
    try:
        import redis
        r = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, db=0)
        r.ping()
        checks.append(_result('Redis', 'OK', 'Connected'))
    except Exception as e:
        checks.append(_result('Redis', 'WARN', f'Unavailable: {e}'))


def _check_tables(checks):
    required = [
        'consciousness_feed', 'trade_queue', 'assets', 'agent_logs',
        'book_of_scars', 'system_state', 'lef_monologue', 'intent_queue',
        'knowledge_stream', 'signal_history', 'stablecoin_buckets',
    ]
    try:
        from db.db_helper import db_connection, translate_sql
        missing = []
        with db_connection() as conn:
            c = conn.cursor()
            for table in required:
                try:
                    c.execute(translate_sql(f"SELECT COUNT(*) FROM {table}"))
                except Exception:
                    missing.append(table)
        if missing:
            checks.append(_result('Tables', 'FAIL', f"Missing: {', '.join(missing)}"))
        else:
            checks.append(_result('Tables', 'OK', f'All {len(required)} tables present'))
    except Exception as e:
        checks.append(_result('Tables', 'FAIL', str(e)))


def _check_configs(checks):
    config_dir = os.path.join(BASE_DIR, 'config')
    configs = ['config.json', 'wealth_strategy.json']
    for cfg in configs:
        path = os.path.join(config_dir, cfg)
        try:
            with open(path) as f:
                json.load(f)
            checks.append(_result(f'Config:{cfg}', 'OK', 'Valid JSON'))
        except FileNotFoundError:
            checks.append(_result(f'Config:{cfg}', 'FAIL', 'File not found'))
        except json.JSONDecodeError as e:
            checks.append(_result(f'Config:{cfg}', 'FAIL', f'Invalid JSON: {e}'))


def _check_env_vars(checks):
    required = ['DB_PATH']
    recommended = ['GEMINI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_req = [v for v in required if not os.environ.get(v)]
    missing_rec = [v for v in recommended if not os.environ.get(v)]
    if missing_req:
        checks.append(_result('EnvVars:Required', 'FAIL', f"Missing: {', '.join(missing_req)}"))
    else:
        checks.append(_result('EnvVars:Required', 'OK', 'All set'))
    if missing_rec:
        checks.append(_result('EnvVars:Recommended', 'WARN', f"Missing: {', '.join(missing_rec)}"))
    else:
        checks.append(_result('EnvVars:Recommended', 'OK', 'All set'))


def _check_coinbase_key(checks):
    try:
        config_path = os.path.join(BASE_DIR, 'config', 'config.json')
        with open(config_path) as f:
            cfg = json.load(f)
        api_key = cfg.get('coinbase', {}).get('api_key', '')
        if api_key.startswith('ENV:'):
            env_val = os.environ.get(api_key[4:], '')
            if env_val and 'organizations/' in env_val:
                checks.append(_result('Coinbase:Key', 'OK', 'Key present (via ENV)'))
            elif env_val:
                checks.append(_result('Coinbase:Key', 'WARN', 'Key set but format unusual'))
            else:
                checks.append(_result('Coinbase:Key', 'WARN', f'{api_key} not resolved'))
        elif 'organizations/' in api_key:
            checks.append(_result('Coinbase:Key', 'OK', 'Key present (inline)'))
        else:
            checks.append(_result('Coinbase:Key', 'WARN', 'Key missing or invalid format'))
    except Exception as e:
        checks.append(_result('Coinbase:Key', 'WARN', str(e)))


def _check_gemini_key(checks):
    key = os.environ.get('GEMINI_API_KEY', '')
    if key and len(key) > 10:
        checks.append(_result('Gemini:Key', 'OK', 'Key present'))
    else:
        checks.append(_result('Gemini:Key', 'WARN', 'GEMINI_API_KEY not set or too short'))


def _check_disk_space(checks):
    try:
        usage = shutil.disk_usage(BASE_DIR)
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 1.0:
            checks.append(_result('DiskSpace', 'FAIL', f'{free_gb:.1f} GB free (< 1 GB)'))
        elif free_gb < 5.0:
            checks.append(_result('DiskSpace', 'WARN', f'{free_gb:.1f} GB free'))
        else:
            checks.append(_result('DiskSpace', 'OK', f'{free_gb:.1f} GB free'))
    except Exception as e:
        checks.append(_result('DiskSpace', 'WARN', str(e)))


def _check_file_descriptors(checks):
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if soft < 1024:
            checks.append(_result('FileDescriptors', 'WARN', f'Limit {soft} (recommend >= 1024)'))
        else:
            checks.append(_result('FileDescriptors', 'OK', f'Limit {soft} (hard: {hard})'))
    except Exception as e:
        checks.append(_result('FileDescriptors', 'WARN', str(e)))


def _check_orphaned_trades(checks):
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "SELECT COUNT(*) FROM trade_queue WHERE status = 'IN_PROGRESS'"
            ))
            row = c.fetchone()
            count = row[0] if row else 0
            if count > 0:
                checks.append(_result('OrphanedTrades', 'WARN',
                                      f'{count} trades stuck in IN_PROGRESS'))
            else:
                checks.append(_result('OrphanedTrades', 'OK', 'No orphaned trades'))
    except Exception as e:
        checks.append(_result('OrphanedTrades', 'WARN', str(e)))


# ── CLI ────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print(" LEF PREFLIGHT CHECK")
    print("=" * 60)

    results = preflight()

    fails = 0
    warns = 0
    for r in results:
        icon = {'OK': '\u2705', 'WARN': '\u26a0\ufe0f', 'FAIL': '\u274c'}.get(r['status'], '?')
        print(f"  {icon}  [{r['status']:4s}] {r['check']:25s} — {r['detail']}")
        if r['status'] == 'FAIL':
            fails += 1
        elif r['status'] == 'WARN':
            warns += 1

    print("=" * 60)
    total = len(results)
    passed = total - fails - warns
    print(f"  {passed}/{total} passed, {warns} warnings, {fails} failures")

    if fails:
        print("\n  PREFLIGHT FAILED — fix critical issues before launching LEF.")
        sys.exit(1)
    elif warns:
        print("\n  PREFLIGHT OK (with warnings) — LEF can launch.")
    else:
        print("\n  ALL CLEAR — LEF is ready.")
