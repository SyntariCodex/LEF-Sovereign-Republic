"""
Phase 30.2: External Alerting (EXT-04)

Centralised alert dispatcher.  Every critical event in LEF should call:

    from system.alerting import send_alert
    send_alert('critical', 'Brain silent for 30 min', {'silence_sec': 1800})

Alert levels: 'info', 'medium', 'high', 'critical'

Destinations:
  1. The_Bridge/Inbox/alerts/  (always — file-based, crash-safe)
  2. consciousness_feed table  (always — so LEF is self-aware)
  3. Discord webhook            (if DISCORD_WEBHOOK_URL env var set)
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERTS_DIR = os.path.join(BASE_DIR, '..', 'The_Bridge', 'Inbox', 'alerts')


def send_alert(level, message, context=None):
    """
    Dispatch an alert to all configured destinations.

    Args:
        level: 'info' | 'medium' | 'high' | 'critical'
        message: Human-readable alert message
        context: Optional dict with extra data
    """
    ts = datetime.now()
    alert = {
        'level': level,
        'message': message,
        'timestamp': ts.isoformat(),
        'context': context or {},
    }

    # 1. File-based alert (crash-safe, always works)
    _write_alert_file(alert, ts)

    # 2. consciousness_feed (so LEF knows about its own problems)
    _write_consciousness(alert)

    # 3. Discord webhook (if configured)
    _send_discord(alert)

    logging.info(f"[ALERT] [{level.upper()}] {message}")


# ── Destinations ──────────────────────────────────────────────

def _write_alert_file(alert, ts):
    """Write alert to The_Bridge/Inbox/alerts/ as a timestamped JSON."""
    try:
        Path(ALERTS_DIR).mkdir(parents=True, exist_ok=True)
        filename = f"alert_{ts.strftime('%Y%m%d_%H%M%S')}_{alert['level']}.json"
        filepath = os.path.join(ALERTS_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(alert, f, indent=2)
    except Exception as e:
        logging.warning(f"[ALERT] File write failed: {e}")


def _write_consciousness(alert):
    """Insert into consciousness_feed so LEF is self-aware of the alert."""
    try:
        from db.db_helper import db_connection, translate_sql
        weight_map = {'info': 0.3, 'medium': 0.5, 'high': 0.7, 'critical': 1.0}
        weight = weight_map.get(alert['level'], 0.5)
        with db_connection() as conn:
            c = conn.cursor()
            c.execute(translate_sql(
                "INSERT INTO consciousness_feed "
                "(agent_name, content, category, signal_weight) "
                "VALUES (?, ?, ?, ?)"
            ), (
                'AlertSystem',
                json.dumps({
                    'alert_level': alert['level'],
                    'message': alert['message'],
                    'context': alert['context'],
                }),
                'system_alert',
                weight,
            ))
            conn.commit()
    except Exception as e:
        logging.warning(f"[ALERT] consciousness_feed write failed: {e}")


def _send_discord(alert):
    """POST to Discord webhook if configured."""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
    if not webhook_url or webhook_url.startswith('ENV:') or 'dummy' in webhook_url:
        return

    level_emoji = {
        'info': '\u2139\ufe0f',       # info
        'medium': '\u26a0\ufe0f',     # warning
        'high': '\U0001f534',         # red circle
        'critical': '\U0001f6a8',     # rotating light
    }
    emoji = level_emoji.get(alert['level'], '\u2753')

    payload = {
        'content': (
            f"{emoji} **[{alert['level'].upper()}]** {alert['message']}\n"
            f"```json\n{json.dumps(alert['context'], indent=2)[:500]}\n```"
        ),
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logging.debug(f"[ALERT] Discord webhook failed: {e}")
