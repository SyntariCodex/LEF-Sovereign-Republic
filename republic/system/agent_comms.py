import redis
import json
import os
import time
import logging

class RepublicComms:
    """
    The Nervous System of the Republic.
    Wraps Redis Pub/Sub to allow instantaneous inter-agent signaling.
    """
    def __init__(self, host='localhost', port=6379, db=0):
        # Allow env override
        self.host = os.getenv('REDIS_HOST', host)
        self.port = int(os.getenv('REDIS_PORT', port))
        self.db = int(os.getenv('REDIS_DB', db))
        
        try:
            self.r = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            # Test connection
            self.r.ping()
        except Exception as e:
            logging.warning(f"[COMMS] ⚠️ Redis Connection Failed: {e}. Falling back to Silence (No-Op).")
            self.r = None

    def publish_event(self, channel, type, payload, source):
        """
        Fires a synaptic signal to the Republic.
        """
        if not self.r: return # No nervous system? No signal.
        
        message = {
            "timestamp": time.time(),
            "type": type,       # e.g. "PANIC", "TRADE_EXECUTED", "SABBATH_START"
            "source": source,   # e.g. "AgentIntrospector"
            "payload": payload  # Arbitrary dict
        }
        
        try:
            count = self.r.publish(channel, json.dumps(message))
            # logging.debug(f"[COMMS] ⚡ Signal Fired: {type} to {channel} (Received by {count})")
            return count
        except Exception as e:
            logging.error(f"[COMMS] Failed to publish: {e}")
            return 0

    def listen(self, channel):
        """
        Generator that yields events from a specific channel.
        Use this in a loop: for event in comms.listen('lef_events'): ...
        """
        if not self.r:
            # Fallback for no Redis: Just yield nothing (sleep forever)
            while True: time.sleep(10)

        pubsub = self.r.pubsub()
        pubsub.subscribe(channel)
        
        logging.info(f"[COMMS] 👂 Listening on channel: {channel}")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    yield data
                except json.JSONDecodeError:
                    pass # Ignore noise
