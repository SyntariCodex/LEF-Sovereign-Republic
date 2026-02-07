"""
Write Queue Publisher for Write-Ahead Queue (WAQ)

Agents use this module to publish database writes to Redis.
The Scribe agent consumes the queue and performs actual writes.
"""
import redis
import logging
import os
from typing import Optional

from shared.write_message import WriteMessage, PRIORITY_CRITICAL

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Queue Names
WRITE_QUEUE = 'db:write_queue'
WRITE_QUEUE_PRIORITY = 'db:write_queue:priority'
WRITE_QUEUE_CRITICAL = 'db:write_queue:critical'

# Feature Flag (allows fallback to direct writes)
USE_WRITE_QUEUE = os.getenv('USE_WRITE_QUEUE', 'true').lower() == 'true'

logger = logging.getLogger(__name__)

# Singleton Redis connection
_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis connection."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            _redis_client.ping()
        except (redis.RedisError, ConnectionError) as e:
            logger.warning(f"[WRITE_QUEUE] Redis unavailable: {e}")
            _redis_client = None
    return _redis_client


def publish_write(msg: WriteMessage) -> bool:
    """
    Publish a write message to the appropriate queue.
    
    Args:
        msg: WriteMessage instance
        
    Returns:
        True if published successfully, False otherwise
    """
    if not USE_WRITE_QUEUE:
        # Feature flag disabled - caller should fall back to direct write
        return False
    
    r = get_redis()
    if not r:
        logger.warning(f"[WRITE_QUEUE] Redis unavailable, cannot queue write from {msg.source_agent}")
        return False
    
    try:
        # Select queue based on priority
        if msg.priority >= PRIORITY_CRITICAL:
            queue = WRITE_QUEUE_CRITICAL
        elif msg.priority >= 1:
            queue = WRITE_QUEUE_PRIORITY
        else:
            queue = WRITE_QUEUE
        
        # Push to queue
        r.lpush(queue, msg.to_json())
        
        logger.debug(f"[WRITE_QUEUE] Queued {msg.operation} on {msg.table} from {msg.source_agent}")
        return True
        
    except Exception as e:
        logger.error(f"[WRITE_QUEUE] Failed to queue: {e}")
        return False


def publish_write_sync(msg: WriteMessage, timeout: float = 5.0) -> Optional[dict]:
    """
    Publish a write and wait for the result (synchronous).
    
    Use this for critical operations that need confirmation (e.g., stop-loss).
    
    Args:
        msg: WriteMessage instance (callback_key will be set automatically)
        timeout: Seconds to wait for result
        
    Returns:
        Result dict from Scribe, or None on timeout/failure
    """
    import uuid
    import json
    
    r = get_redis()
    if not r:
        return None
    
    # Set callback key for this message
    callback_key = f"write_result:{uuid.uuid4().hex[:8]}"
    msg.callback_key = callback_key
    
    # Publish
    if not publish_write(msg):
        return None
    
    try:
        # Wait for result
        result = r.blpop(callback_key, timeout=timeout)
        if result:
            return json.loads(result[1])
        else:
            logger.warning(f"[WRITE_QUEUE] Timeout waiting for {callback_key}")
            return None
    except Exception as e:
        logger.error(f"[WRITE_QUEUE] Sync wait failed: {e}")
        return None


def get_queue_depth() -> dict:
    """
    Get current queue depths for monitoring.
    
    Returns:
        Dict with queue names and their lengths
    """
    r = get_redis()
    if not r:
        return {'error': 'Redis unavailable'}
    
    try:
        return {
            'normal': r.llen(WRITE_QUEUE),
            'priority': r.llen(WRITE_QUEUE_PRIORITY),
            'critical': r.llen(WRITE_QUEUE_CRITICAL)
        }
    except Exception as e:
        return {'error': str(e)}


def is_queue_enabled() -> bool:
    """Check if write queue is enabled and Redis is available."""
    if not USE_WRITE_QUEUE:
        return False
    return get_redis() is not None
