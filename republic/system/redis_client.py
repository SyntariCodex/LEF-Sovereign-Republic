"""
Shared Redis Client Singleton

Provides a single Redis connection for all agents, eliminating the pattern
where each agent creates its own redis.Redis() instance.

Usage:
    from system.redis_client import get_redis
    
    r = get_redis()
    if r:
        r.set("key", "value")
        r.get("key")
"""

import os
import logging

_client = None
_connection_failed = False

logger = logging.getLogger(__name__)


def get_redis():
    """
    Get the shared Redis client.
    
    Returns:
        Redis client or None if connection failed
    """
    global _client, _connection_failed
    
    # Don't retry if we already know it's down
    if _connection_failed:
        return None
    
    if _client is None:
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
            # Test connection
            _client.ping()
            logger.info(f"[REDIS] 🔌 Shared client connected to {host}:{port}")
        except Exception as e:
            logger.warning(f"[REDIS] ⚠️ Connection failed: {e}")
            _connection_failed = True
            _client = None
    
    return _client


def reset_client():
    """Reset the client (useful for reconnection after failure)."""
    global _client, _connection_failed
    _client = None
    _connection_failed = False


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
