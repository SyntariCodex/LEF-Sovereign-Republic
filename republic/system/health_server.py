"""
Phase 30.1: Health Endpoint (EXT-01)

Lightweight HTTP server on port 8080.
  /health  -> JSON system health (200 OK or 503 Degraded)
  /metrics -> JSON runtime metrics (counters, gauges, histograms)

Started as a daemon thread from main.py.  Does NOT import heavy
dependencies at module level so it can boot fast.

Usage in main.py:
    from system.health_server import start_health_server
    start_health_server()
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

_start_time = time.time()
HEALTH_PORT = int(os.getenv('HEALTH_PORT', '8080'))


def _collect_health():
    """Gather system health from all subsystems."""
    health = {
        'healthy': True,
        'timestamp': datetime.now().isoformat(),
        'uptime_seconds': round(time.time() - _start_time, 1),
        'db_pool': {'status': 'unknown'},
        'redis': {'connected': False},
        'brainstem': {'status': 'unknown'},
        'consciousness': {'last_thought': None, 'cycle_count': 0},
        'financial': {'circuit_breaker_level': -1, 'defcon': -1, 'pending_orders': 0},
    }

    problems = []

    # 1. Database pool
    try:
        from db.db_pool import pool_status
        ps = pool_status()
        health['db_pool'] = ps
        utilization = ps.get('active', 0) / max(ps.get('pool_size', 1), 1)
        if utilization > 0.90:
            problems.append('db_pool_near_exhaustion')
    except Exception as e:
        health['db_pool'] = {'status': 'error', 'error': str(e)}
        problems.append('db_pool_error')

    # 2. Redis
    try:
        from system.redis_client import is_available
        health['redis']['connected'] = is_available()
        if not health['redis']['connected']:
            problems.append('redis_down')
    except Exception:
        problems.append('redis_import_error')

    # 3. Brainstem
    try:
        from system.brainstem import _brainstem_instance
        if _brainstem_instance:
            bs = _brainstem_instance.get_status()
            health['brainstem'] = {
                'running': bs.get('running', False),
                'registered_threads': bs.get('registered_threads', 0),
                'degraded_agents': bs.get('degraded_agents', []),
                'brain_silence_seconds': bs.get('brain_silence_seconds', 0),
            }
            if bs.get('degraded_agents'):
                problems.append('agents_degraded')
            if bs.get('brain_silence_seconds', 0) > 1800:
                problems.append('brain_silence')
        else:
            health['brainstem'] = {'status': 'not_started'}
    except Exception:
        pass

    # 4. Consciousness
    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            # Last consciousness entry
            c.execute(translate_sql(
                "SELECT content, timestamp FROM consciousness_feed "
                "ORDER BY id DESC LIMIT 1"
            ))
            row = c.fetchone()
            if row:
                health['consciousness']['last_thought'] = str(row[1])
            # Cycle count (last 24h)
            c.execute(translate_sql(
                "SELECT COUNT(*) FROM consciousness_feed "
                "WHERE category = 'metacognition' AND timestamp > NOW() - INTERVAL '24 hours'"
            ))
            count_row = c.fetchone()
            health['consciousness']['cycle_count'] = count_row[0] if count_row else 0
    except Exception:
        pass

    # 5. Financial state
    try:
        from system.circuit_breaker import get_circuit_breaker
        cb = get_circuit_breaker()
        cb_status = cb.check_portfolio_health()
        health['financial']['circuit_breaker_level'] = cb_status.get('level', -1)
        health['financial']['portfolio_value_usd'] = cb_status.get('portfolio_value_usd', 0)
        if cb_status.get('level', 0) >= 3:
            problems.append('circuit_breaker_high')
    except Exception:
        pass

    try:
        from system.redis_client import redis_get
        defcon = redis_get('safety:defcon_level') or redis_get('risk_model:defcon')
        if defcon:
            health['financial']['defcon'] = int(defcon)
    except Exception:
        pass

    try:
        from db.db_helper import db_connection, translate_sql
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "SELECT COUNT(*) FROM trade_queue WHERE status IN ('PENDING', 'APPROVED', 'IN_PROGRESS')"
            ))
            row = c.fetchone()
            health['financial']['pending_orders'] = row[0] if row else 0
    except Exception:
        pass

    # Determine overall health
    if problems:
        health['healthy'] = False
        health['problems'] = problems

    return health


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for health and metrics endpoints."""

    def do_GET(self):
        if self.path == '/health':
            status = _collect_health()
            code = 200 if status['healthy'] else 503
            self._respond(code, status)
        elif self.path == '/metrics':
            try:
                from system.metrics import Metrics
                self._respond(200, Metrics.snapshot())
            except Exception as e:
                self._respond(500, {'error': str(e)})
        else:
            self._respond(404, {'error': 'Not found. Use /health or /metrics'})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        """Suppress default request logging to reduce noise."""
        pass


def start_health_server(port=None):
    """Start the health server on a daemon thread. Safe to call multiple times."""
    port = port or HEALTH_PORT
    try:
        server = HTTPServer(('0.0.0.0', port), _HealthHandler)
        thread = threading.Thread(
            target=server.serve_forever,
            name='HealthServer',
            daemon=True,
        )
        thread.start()
        logging.info(f"[HEALTH] Server listening on http://0.0.0.0:{port}/health")
        return server
    except OSError as e:
        logging.warning(f"[HEALTH] Could not start health server on port {port}: {e}")
        return None
