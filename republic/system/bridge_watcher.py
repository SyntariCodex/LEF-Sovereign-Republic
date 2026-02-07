"""
BridgeWatcher — Closes the Bridge feedback loop.
Scans The_Bridge/Outbox for new files and feeds them into knowledge_stream
so other agents (Philosopher, Introspector, etc.) can process outbound content.

Phase 2 Active Tasks — Task 2.3
"""

import os
import json
import sqlite3
import logging
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # republic/
BRIDGE_PATH = BASE_DIR.parent / "The_Bridge"


def scan_outbox(bridge_path=None, db_path=None):
    """Scan The_Bridge/Outbox for new files and feed them into knowledge_stream."""
    bridge_path = bridge_path or str(BRIDGE_PATH)
    db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

    outbox_path = os.path.join(bridge_path, "Outbox")
    tracker_path = os.path.join(bridge_path, ".outbox_processed.json")

    # Load already-processed filenames
    processed = set()
    if os.path.exists(tracker_path):
        try:
            with open(tracker_path, 'r') as f:
                processed = set(json.load(f))
        except Exception:
            processed = set()

    if not os.path.exists(outbox_path):
        return []

    new_files = []
    for filename in os.listdir(outbox_path):
        filepath = os.path.join(outbox_path, filename)
        if not os.path.isfile(filepath):
            continue
        if filename in processed or filename.startswith('.'):
            continue

        try:
            with open(filepath, 'r') as f:
                content = f.read()

            if not content.strip():
                processed.add(filename)
                continue

            # Determine source agent from filename pattern
            if filename.startswith('REPLY_'):
                source_label = 'BRIDGE_OUTBOX:Philosopher'
            elif filename.startswith('ORACLE_'):
                source_label = 'BRIDGE_OUTBOX:Oracle'
            elif filename.startswith('DIRECT_'):
                source_label = 'BRIDGE_OUTBOX:DirectLine'
            else:
                source_label = f'BRIDGE_OUTBOX:{filename}'

            # Extract a title from the first line
            title = content.split('\n')[0][:100].strip()
            if not title:
                title = filename

            # Feed into knowledge_stream
            # Phase 6.5: Route through WAQ for serialized writes
            conn = sqlite3.connect(db_path, timeout=30)
            try:
                from db.db_writer import queue_insert
                queue_insert(
                    conn.cursor(),
                    table="knowledge_stream",
                    data={
                        "source": source_label,
                        "title": title,
                        "summary": content[:5000]
                    },
                    source_agent="BridgeWatcher",
                    priority=0  # NORMAL — knowledge ingestion
                )
            except ImportError:
                conn.execute(
                    "INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)",
                    (source_label, title, content[:5000])
                )
                conn.commit()
            conn.close()

            new_files.append(filename)
            processed.add(filename)
            logging.info(f"[BridgeWatcher] 📬 Fed back: {filename}")

        except Exception as e:
            logging.error(f"[BridgeWatcher] Failed to process {filename}: {e}")

    # Save updated tracker
    try:
        with open(tracker_path, 'w') as f:
            json.dump(sorted(list(processed)), f, indent=2)
    except Exception:
        pass

    if new_files:
        logging.info(f"[BridgeWatcher] Processed {len(new_files)} new Outbox files")

    return new_files


def run_bridge_watcher(interval_seconds=300):
    """Run the bridge watcher on a timer (default: every 5 minutes)."""
    logging.info("[BridgeWatcher] 📬 Bridge Feedback Loop Online (scanning Outbox)")
    while True:
        try:
            scan_outbox()
        except Exception as e:
            logging.error(f"[BridgeWatcher] Scan cycle error: {e}")
        time.sleep(interval_seconds)
