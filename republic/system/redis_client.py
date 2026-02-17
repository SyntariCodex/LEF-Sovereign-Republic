"""
Shared Redis Client Singleton

Provides a single Redis connection for all agents, eliminating the pattern
where each agent creates its own redis.Redis() instance.

Phase 21.2a: All writes include TTL via redis_set() wrapper
Phase 21.2b: Exponential backoff reconnection (no permanent failure flag)
Phase 21.2c: Failure logging for visibility

Usage:
    from system.redis_client import get_redis, redis_set, redis_get

    r = get_redis()
    if r:
        r.set("key", "value")   # Direct (no TTL — legacy)

    # Preferred (Phase 21.2a — TTL always applied):
    redis_set("key", "value")              # default 300s TTL
    redis_set("price:BTC", "97000", 300)   # explicit TTL
    val = redis_get("key")                 # logs if Redis down
"""

import os
import time
import logging

_client = None
_last_attempt = 0
_backoff = 5  # seconds, doubles up to 300 on failure

logger = logging.getLogger(__name__)

# TTL defaults per key prefix (Phase 21.2a)
_TTL_DEFAULTS = {
    'price:':      300,   # 5 min — refreshed every cycle
    'rsi:':        300,
    'sma:':        300,
    'macd:':       300,
    'sentiment:':  3600,  # 1 hour
    'market:':     3600,
    'safety:':     60,    # 1 min — safety state must be fresh
    'system:':     600,   # 10 min
    'risk_model:': 300,
    'portfolio:':  300,
    'analysis:':   86400, # 24 hours
    'daat:':       120,   # 2 min
}
_DEFAULT_TTL = 300  # 5 minutes for unmatched keys


def _get_ttl_for_key(key: str) -> int:
    """Look up the appropriate TTL for a Redis key based on prefix."""
    for prefix, ttl in _TTL_DEFAULTS.items():
        if key.startswith(prefix):
            return ttl
    return _DEFAULT_TTL


def get_redis():
    """
    Get the shared Redis client with exponential backoff reconnection.

    Returns:
        Redis client or None if connection unavailable

    Phase 21.2b: No permanent failure flag. Retries with backoff (5s → 300s).
    """
    global _client, _last_attempt, _backoff

    # If we have a client, verify it's alive
    if _client is not None:
        try:
            _client.ping()
            _backoff = 5  # Reset on success
            return _client
        except Exception:
            logger.warning("[REDIS] Connection lost — will attempt reconnection")
            _client = None

    # Respect backoff timer
    now = time.time()
    if now - _last_attempt < _backoff:
        return None
    _last_attempt = now

    try:
        import redis
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', 6379))

        _client = redis.Redis(
            host=host,
            port=port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        _client.ping()
        _backoff = 5  # Reset on success
        logger.info(f"[REDIS] Connected to {host}:{port}")
        # Phase 30.4: Metrics
        try:
            from system.metrics import Metrics
            Metrics.gauge('redis.connected', 1)
        except Exception:
            pass
        return _client

    except Exception as e:
        _backoff = min(_backoff * 2, 300)  # Double up to 5 min max
        # Phase 30.4: Metrics
        try:
            from system.metrics import Metrics
            Metrics.gauge('redis.connected', 0)
        except Exception:
            pass
        # Phase 30.2: Alert when Redis down for extended period (backoff >= 160 ≈ 5+ min)
        if _backoff >= 160:
            try:
                from system.alerting import send_alert
                send_alert('high', 'Redis unavailable',
                           {'backoff_seconds': _backoff, 'error': str(e)})
            except Exception:
                pass
        logger.warning(
            "[REDIS] Connection failed (next retry in %ds): %s",
            _backoff, e
        )
        _client = None
        return None


def redis_set(key: str, value, ttl: int = None) -> bool:
    """
    Set a Redis key with automatic TTL (Phase 21.2a).

    Args:
        key:   Redis key
        value: Value to set
        ttl:   TTL in seconds (auto-detected from key prefix if None)

    Returns:
        True if set successfully, False if Redis unavailable

    Phase 21.2c: Logs when Redis is down.
    """
    r = get_redis()
    if r is None:
        logger.debug("[REDIS] DOWN — skipped SET %s", key)
        return False
    try:
        if ttl is None:
            ttl = _get_ttl_for_key(key)
        r.set(key, value, ex=ttl)
        return True
    except Exception as e:
        logger.warning("[REDIS] SET %s failed: %s", key, e)
        return False


def redis_get(key: str, default=None):
    """
    Get a Redis key value.

    Args:
        key:     Redis key
        default: Value to return if key not found or Redis down

    Returns:
        Value or default

    Phase 21.2c: Logs when Redis is down.
    """
    r = get_redis()
    if r is None:
        logger.debug("[REDIS] DOWN — skipped GET %s", key)
        return default
    try:
        val = r.get(key)
        return val if val is not None else default
    except Exception as e:
        logger.warning("[REDIS] GET %s failed: %s", key, e)
        return default


def reset_client():
    """Reset the client (useful for reconnection after failure)."""
    global _client, _backoff
    _client = None
    _backoff = 5


def is_available() -> bool:
    """Check if Redis is available."""
    r = get_redis()
    if r:
        try:
            r.ping()
            return True
        except Exception:
            return False
    return False
