"""
Phase 16 — Task 16.1: Central Event Bus subscriber.
Collects events from orphaned Redis channels and routes them
to consciousness_feed so they don't broadcast into the void.

Channels subscribed:
  events          -> 5 agents publish (agent_info, postmortem, civics, coin_mgr, steward)
  system_alerts   -> agent_immune (APOPTOSIS_TRIGGERED) — also covered by Task 15.10
  lef_speaks      -> the_voice.py — LEF's voice output
  lef_wants_to_speak -> interiority_engine.py — speech intents
  republic:lef_feedback -> intent_listener.py — feedback from intent dispatch
"""

import threading
import json
import logging
import queue
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    """Subscribe to Redis channels that previously had no listeners."""

    CHANNELS = {
        # Phase 15 — original channels
        'events': 'republic_event',
        'system_alerts': 'system_alert',
        'lef_speaks': 'lef_speech',
        'lef_wants_to_speak': 'speech_intent',
        'republic:lef_feedback': 'intent_feedback',
        # Fix 17-C — consciousness-relevant channels
        'commands': 'system_command',          # Introspector PAUSE_ALL, emergency commands
        'competition:intel': 'competitive_intel',  # Scout intelligence about competitors
        'sleep_state': 'sleep_transition',     # Sleep/wake state changes
    }

    def __init__(self, redis_client):
        self.redis = redis_client
        self._running = False
        # Phase 36: Async write queue — DB writes don't block the event loop (IDN-05)
        self._write_queue = queue.Queue(maxsize=1000)
        self._writer_thread = None

    def start(self):
        """Start listening on all channels in a daemon thread."""
        if not self.redis:
            logger.warning("[EventBus] No Redis client — cannot subscribe")
            return
        self._running = True
        # Phase 36: Start the async DB writer thread (IDN-05)
        self._writer_thread = threading.Thread(target=self._db_writer_loop, daemon=True, name="EventBus-Writer")
        self._writer_thread.start()
        thread = threading.Thread(target=self._listen, daemon=True, name="EventBus")
        thread.start()
        logger.info(f"[EventBus] Subscribed to {len(self.CHANNELS)} channels: {list(self.CHANNELS.keys())}")

    def stop(self):
        self._running = False

    def _listen(self):
        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(*self.CHANNELS.keys())

            for message in pubsub.listen():
                if not self._running:
                    break
                if message['type'] != 'message':
                    continue

                channel = message['channel']
                if isinstance(channel, bytes):
                    channel = channel.decode('utf-8')

                category = self.CHANNELS.get(channel, 'unknown_event')

                try:
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')

                    # Phase 36: Queue the write instead of blocking (IDN-05)
                    try:
                        self._write_queue.put_nowait(
                            (f'EventBus:{channel}', data[:2000], category)
                        )
                    except queue.Full:
                        logger.warning(f"[EventBus] Write queue full — dropping {channel} event")
                except Exception as e:
                    logger.warning(f"[EventBus] Failed to process {channel} message: {e}")

        except Exception as e:
            logger.error(f"[EventBus] Listener error: {e}")

    def _db_writer_loop(self):
        """Phase 36: Async DB writer — drains the write queue without blocking the event loop."""
        while self._running:
            try:
                agent_name, content, category = self._write_queue.get(timeout=2.0)
                try:
                    from db.db_helper import db_connection, translate_sql
                    with db_connection() as conn:
                        c = conn.cursor()
                        c.execute(translate_sql(
                            "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                            "VALUES (?, ?, ?, NOW())"
                        ), (agent_name, content, category))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"[EventBus] DB write failed: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[EventBus] Writer loop error: {e}")
