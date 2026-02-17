import redis
import json
import os
import time
import logging

# Phase 36: Reconnection parameters (IDN-06)
RECONNECT_BASE_DELAY = 5      # 5 seconds initial backoff
RECONNECT_MAX_DELAY = 60      # 60 seconds max backoff
RECONNECT_MAX_RETRIES = 10    # Give up after 10 attempts


class RepublicComms:
    """
    The Nervous System of the Republic.
    Wraps Redis Pub/Sub to allow instantaneous inter-agent signaling.
    Phase 36: Auto-reconnect on Redis drop with exponential backoff.
    """
    def __init__(self, host='localhost', port=6379, db=0):
        # Allow env override
        self.host = os.getenv('REDIS_HOST', host)
        self.port = int(os.getenv('REDIS_PORT', port))
        self.db = int(os.getenv('REDIS_DB', db))
        self._reconnect_attempts = 0

        self._connect()

    def _connect(self):
        """Establish Redis connection."""
        try:
            self.r = redis.Redis(
                host=self.host, port=self.port, db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=10
            )
            self.r.ping()
            self._reconnect_attempts = 0
        except Exception as e:
            logging.warning(f"[COMMS] Redis Connection Failed: {e}. Falling back to Silence (No-Op).")
            self.r = None

    def _reconnect(self) -> bool:
        """
        Phase 36: Auto-reconnect with exponential backoff (IDN-06).
        Returns True if reconnected, False if max retries exhausted.
        """
        for attempt in range(1, RECONNECT_MAX_RETRIES + 1):
            delay = min(RECONNECT_BASE_DELAY * (2 ** (attempt - 1)), RECONNECT_MAX_DELAY)
            logging.info(f"[COMMS] Reconnect attempt {attempt}/{RECONNECT_MAX_RETRIES} in {delay}s...")
            time.sleep(delay)
            try:
                self.r = redis.Redis(
                    host=self.host, port=self.port, db=self.db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10
                )
                self.r.ping()
                self._reconnect_attempts = 0
                logging.info(f"[COMMS] Reconnected to Redis on attempt {attempt}")
                return True
            except Exception as e:
                logging.warning(f"[COMMS] Reconnect attempt {attempt} failed: {e}")
                self.r = None

        logging.error(f"[COMMS] Failed to reconnect after {RECONNECT_MAX_RETRIES} attempts")
        return False

    def publish_event(self, channel, type, payload, source):
        """
        Fires a synaptic signal to the Republic.
        Phase 36: Auto-reconnects on publish failure.
        """
        if not self.r:
            return 0

        message = {
            "timestamp": time.time(),
            "type": type,
            "source": source,
            "payload": payload
        }

        try:
            count = self.r.publish(channel, json.dumps(message))
            return count
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logging.warning(f"[COMMS] Publish failed (connection lost): {e}")
            if self._reconnect():
                try:
                    count = self.r.publish(channel, json.dumps(message))
                    return count
                except Exception:
                    pass
            return 0
        except Exception as e:
            logging.error(f"[COMMS] Failed to publish: {e}")
            return 0

    def listen(self, channel):
        """
        Generator that yields events from a specific channel.
        Phase 36: Auto-reconnects on connection drop (IDN-06).
        """
        while True:
            if not self.r:
                if not self._reconnect():
                    # Max retries exhausted — sleep and try again later
                    time.sleep(RECONNECT_MAX_DELAY)
                    continue

            try:
                pubsub = self.r.pubsub()
                pubsub.subscribe(channel)
                logging.info(f"[COMMS] Listening on channel: {channel}")

                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            yield data
                        except json.JSONDecodeError:
                            pass
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logging.warning(f"[COMMS] Connection lost on {channel}: {e}. Reconnecting...")
                self.r = None
                # Loop will trigger _reconnect on next iteration
            except Exception as e:
                logging.error(f"[COMMS] Listen error on {channel}: {e}")
                time.sleep(RECONNECT_BASE_DELAY)
