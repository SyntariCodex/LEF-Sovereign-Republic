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

# Phase 42: Bridge Q&A integration — check for Architect answers
try:
    from system.bridge_qa import get_bridge_qa
    _QA_AVAILABLE = True
except ImportError:
    _QA_AVAILABLE = False


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
            try:
                from db.db_helper import db_connection as _bw_db_conn, translate_sql as _bw_translate
                with _bw_db_conn() as conn:
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
                        conn.execute(_bw_translate(
                            "INSERT INTO knowledge_stream (source, title, summary) VALUES (?, ?, ?)"
                        ), (source_label, title, content[:5000]))
                        conn.commit()
            except Exception as db_err:
                logging.error(f"[BridgeWatcher] DB write failed for {filename}: {db_err}")

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


_processed_governance = set()


def scan_governance_outcomes():
    """
    Phase 15: Read governance voting outcomes and surface to consciousness.
    LEF must learn from both approvals and rejections.
    """
    global _processed_governance
    import glob

    governance_dir = os.path.join(str(BRIDGE_PATH.parent), 'governance')

    for outcome_type in ['rejected', 'approved']:
        outcome_dir = os.path.join(governance_dir, outcome_type)
        if not os.path.isdir(outcome_dir):
            continue

        cutoff = time.time() - 86400  # Last 24 hours

        for filepath in glob.glob(os.path.join(outcome_dir, '*.json')):
            file_id = os.path.basename(filepath)
            if file_id in _processed_governance:
                continue

            # Only process recent files
            if os.path.getmtime(filepath) < cutoff:
                _processed_governance.add(file_id)
                continue

            try:
                with open(filepath, 'r') as f:
                    outcome = json.load(f)

                from db.db_helper import db_connection, translate_sql
                with db_connection() as conn:
                    c = conn.cursor()
                    c.execute(translate_sql(
                        "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                        "VALUES (?, ?, ?, NOW())"
                    ), ('GovernanceSystem', json.dumps({
                        'outcome': outcome_type,
                        'proposal_title': str(outcome.get('title', 'unknown'))[:200],
                        'reason': str(outcome.get('rejection_reason', outcome.get('approval_reason', '')))[:300],
                        'domain': str(outcome.get('domain', 'unknown'))
                    }), f'governance_{outcome_type}'))
                    conn.commit()

                _processed_governance.add(file_id)
                logging.info(f"[Governance] {outcome_type.upper()} outcome surfaced: {file_id}")

            except Exception as e:
                logging.warning(f"[Governance] Failed to process {filepath}: {e}")
                _processed_governance.add(file_id)  # Don't retry broken files


def scan_answers():
    """Phase 42: Check for Architect answers and route to consciousness_feed."""
    if not _QA_AVAILABLE:
        return []
    qa = get_bridge_qa()
    answers = qa.check_answers()
    qa.expire_old_questions()
    for ans in answers:
        try:
            from db.db_helper import db_connection as _bw_db_conn, translate_sql as _bw_translate
            with _bw_db_conn() as conn:
                c = conn.cursor()
                c.execute(_bw_translate(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)"
                ), ('BridgeQA', json.dumps({
                    'question_id': ans['question_id'],
                    'answer': ans['answer'][:1000],
                    'answered_at': ans.get('answered_at', '')
                }), 'architect_answer'))
                conn.commit()
            logging.info(f"[BridgeWatcher] Answer received: {ans['question_id']}")
        except Exception as e:
            logging.error(f"[BridgeWatcher] Answer routing error: {e}")
    return answers


def run_bridge_watcher(interval_seconds=300):
    """Run the bridge watcher on a timer (default: every 5 minutes)."""
    logging.info("[BridgeWatcher] 📬 Bridge Feedback Loop Online (scanning Outbox)")
    while True:
        # Phase 8.5d: Set heartbeat at START of each cycle, before scans.
        # Previously was after scans — if any scan was slow (pool contention during
        # burst start), the heartbeat was never set and health checks fired false alarms.
        try:
            from system.redis_client import get_redis
            _r = get_redis()
            if _r:
                _r.set('bridge_watcher:heartbeat', datetime.now().isoformat(), ex=600)  # 10-min TTL
        except Exception:
            pass

        try:
            scan_outbox()
            scan_governance_outcomes()  # Phase 15
            scan_answers()  # Phase 42
        except Exception as e:
            logging.error(f"[BridgeWatcher] Scan cycle error: {e}")
        time.sleep(interval_seconds)
