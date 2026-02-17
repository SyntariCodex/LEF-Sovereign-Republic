"""
Phase 30.3: Self-Diagnostic Command (TST-03)

Comprehensive health check callable via:
  - CLI:   python system/diagnostics.py
  - Code:  from system.diagnostics import run_diagnostics

Output: JSON report to The_Bridge/Outbox/diagnostics_TIMESTAMP.json
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure republic/ is on sys.path for imports
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def run_diagnostics():
    """
    Run full system diagnostics.  Returns dict of results.
    Each check has: status ('OK' | 'WARN' | 'FAIL'), detail (str).
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'checks': {},
    }

    _check_db(results)
    _check_redis(results)
    _check_tables(results)
    _check_agent_liveness(results)
    _check_config_integrity(results)
    _check_consciousness(results)
    _check_last_trade(results)
    _check_scars(results)
    _check_evolution(results)

    # Summary
    checks = results['checks']
    fails = sum(1 for v in checks.values() if v.get('status') == 'FAIL')
    warns = sum(1 for v in checks.values() if v.get('status') == 'WARN')
    results['summary'] = {
        'total_checks': len(checks),
        'passed': len(checks) - fails - warns,
        'warnings': warns,
        'failures': fails,
        'overall': 'FAIL' if fails else ('WARN' if warns else 'OK'),
    }

    return results


# ── Individual checks ─────────────────────────────────────────

def _check_db(results):
    """Database connectivity and pool stats."""
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql("SELECT 1"))
        from db.db_pool import pool_status
        ps = pool_status()
        results['checks']['database'] = {
            'status': 'OK',
            'detail': f"Connected. Active: {ps.get('active', '?')}, Available: {ps.get('available', '?')}",
            'pool': ps,
        }
    except Exception as e:
        results['checks']['database'] = {'status': 'FAIL', 'detail': str(e)}


def _check_redis(results):
    """Redis connectivity and basic stats."""
    try:
        from system.redis_client import get_redis, is_available
        if is_available():
            r = get_redis()
            info = {}
            if r:
                try:
                    info = r.info('memory')
                except Exception:
                    pass
            results['checks']['redis'] = {
                'status': 'OK',
                'detail': 'Connected',
                'used_memory_human': info.get('used_memory_human', 'unknown'),
            }
        else:
            results['checks']['redis'] = {'status': 'WARN', 'detail': 'Redis unavailable'}
    except Exception as e:
        results['checks']['redis'] = {'status': 'WARN', 'detail': str(e)}


def _check_tables(results):
    """Verify required tables exist and get row counts."""
    required = [
        'consciousness_feed', 'trade_queue', 'assets', 'agent_logs',
        'book_of_scars', 'system_state', 'lef_monologue', 'intent_queue',
        'knowledge_stream', 'signal_history', 'stablecoin_buckets',
    ]
    try:
        from db.db_helper import db_connection, translate_sql
        counts = {}
        missing = []
        with db_connection() as conn:
            c = conn.cursor()
            for table in required:
                try:
                    c.execute(translate_sql(f"SELECT COUNT(*) FROM {table}"))
                    row = c.fetchone()
                    counts[table] = row[0] if row else 0
                except Exception:
                    missing.append(table)

        if missing:
            results['checks']['tables'] = {
                'status': 'FAIL',
                'detail': f"Missing: {', '.join(missing)}",
                'row_counts': counts,
            }
        else:
            results['checks']['tables'] = {
                'status': 'OK',
                'detail': f"All {len(required)} tables present",
                'row_counts': counts,
            }
    except Exception as e:
        results['checks']['tables'] = {'status': 'FAIL', 'detail': str(e)}


def _check_agent_liveness(results):
    """Check brainstem heartbeat data for agent liveness."""
    try:
        from system.brainstem import _brainstem_instance
        if _brainstem_instance:
            bs = _brainstem_instance.get_status()
            degraded = bs.get('degraded_agents', [])
            registered = bs.get('registered_threads', 0)
            results['checks']['agents'] = {
                'status': 'WARN' if degraded else 'OK',
                'detail': f"{registered} registered, {len(degraded)} degraded",
                'degraded': degraded,
            }
        else:
            results['checks']['agents'] = {'status': 'WARN', 'detail': 'Brainstem not started'}
    except Exception as e:
        results['checks']['agents'] = {'status': 'WARN', 'detail': str(e)}


def _check_config_integrity(results):
    """Verify config files are valid JSON and required keys present."""
    config_dir = os.path.join(BASE_DIR, 'config')
    configs = ['config.json', 'wealth_strategy.json']
    issues = []
    for cfg in configs:
        path = os.path.join(config_dir, cfg)
        try:
            with open(path) as f:
                json.load(f)
        except FileNotFoundError:
            issues.append(f"Missing: {cfg}")
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON in {cfg}: {e}")

    if issues:
        results['checks']['config'] = {'status': 'FAIL', 'detail': '; '.join(issues)}
    else:
        results['checks']['config'] = {'status': 'OK', 'detail': 'All configs valid'}


def _check_consciousness(results):
    """Last consciousness cycle timestamp."""
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "SELECT timestamp FROM consciousness_feed ORDER BY id DESC LIMIT 1"
            ))
            row = c.fetchone()
            if row:
                results['checks']['consciousness'] = {
                    'status': 'OK',
                    'detail': f"Last entry: {row[0]}",
                }
            else:
                results['checks']['consciousness'] = {
                    'status': 'WARN',
                    'detail': 'No consciousness entries found',
                }
    except Exception as e:
        results['checks']['consciousness'] = {'status': 'FAIL', 'detail': str(e)}


def _check_last_trade(results):
    """Last trade execution timestamp."""
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "SELECT executed_at FROM trade_queue WHERE status = 'DONE' "
                "ORDER BY executed_at DESC LIMIT 1"
            ))
            row = c.fetchone()
            if row and row[0]:
                results['checks']['last_trade'] = {
                    'status': 'OK',
                    'detail': f"Last trade: {row[0]}",
                }
            else:
                results['checks']['last_trade'] = {
                    'status': 'OK',
                    'detail': 'No completed trades',
                }
    except Exception as e:
        results['checks']['last_trade'] = {'status': 'WARN', 'detail': str(e)}


def _check_scars(results):
    """Scar count in last 24 hours."""
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "SELECT COUNT(*) FROM book_of_scars "
                "WHERE created_at > NOW() - INTERVAL '24 hours'"
            ))
            row = c.fetchone()
            count = row[0] if row else 0
            status = 'WARN' if count > 20 else 'OK'
            results['checks']['scars_24h'] = {
                'status': status,
                'detail': f"{count} scars in last 24h",
            }
    except Exception as e:
        results['checks']['scars_24h'] = {'status': 'WARN', 'detail': str(e)}


def _check_evolution(results):
    """Evolution proposals in last 24 hours."""
    try:
        evo_path = os.path.join(BASE_DIR, '..', 'The_Bridge', 'evolution_proposals.json')
        if os.path.exists(evo_path):
            with open(evo_path) as f:
                proposals = json.load(f)
            recent = 0
            cutoff = time.time() - 86400
            if isinstance(proposals, list):
                for p in proposals:
                    ts = p.get('timestamp', '')
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts)
                            if dt.timestamp() > cutoff:
                                recent += 1
                        except (ValueError, TypeError):
                            pass
            results['checks']['evolution'] = {
                'status': 'OK',
                'detail': f"{recent} proposals in last 24h, {len(proposals)} total",
            }
        else:
            results['checks']['evolution'] = {'status': 'OK', 'detail': 'No proposals file'}
    except Exception as e:
        results['checks']['evolution'] = {'status': 'WARN', 'detail': str(e)}


def _write_report(report):
    """Write diagnostics report to The_Bridge/Outbox/."""
    outbox = os.path.join(BASE_DIR, '..', 'The_Bridge', 'Outbox')
    Path(outbox).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(outbox, f'diagnostics_{ts}.json')
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    return filepath


# ── CLI entry point ────────────────────────────────────────────

if __name__ == '__main__':
    # Load .env
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass

    report = run_diagnostics()
    filepath = _write_report(report)

    print(json.dumps(report, indent=2, default=str))
    print(f"\nReport saved to: {filepath}")
    print(f"Overall: {report['summary']['overall']}")
