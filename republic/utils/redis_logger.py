import logging
import json
import time
import os
import redis

class RedisHandler(logging.Handler):
    """
    A logging handler that pushes logs to a Redis list (Queue).
    This avoids direct DB locking during high-concurrency log events.
    """
    def __init__(self, key="logs:queue", host=None, port=6379, db=0):
        super().__init__()
        self.key = key
        self.redis_host = host or os.getenv("REDIS_HOST", "localhost")
        self.redis_port = port
        self.redis_db = db
        try:
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db, decode_responses=True)
        except Exception as e:
            # Fallback if Redis is dead?
            # Ideally we print to stderr because we can't log if the logger fails
            print(f"[RedisHandler] ⚠️ Failed to connect to Redis: {e}")
            self.redis_client = None

    def emit(self, record):
        if not self.redis_client:
            return

        try:
            # Format the entry similar to what SQLiteHandler did
            log_entry = {
                "timestamp": self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "agent_name": record.name,
                "message": record.getMessage(),
                "created_at": time.time()
            }
            
            # Use JSON string for the Redis list
            self.redis_client.rpush(self.key, json.dumps(log_entry))
            
        except Exception as e:
            # Last resort error handling
            print(f"[RedisHandler] Failed to emit log: {e}")
