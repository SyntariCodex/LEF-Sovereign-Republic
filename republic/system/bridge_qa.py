"""
BridgeQA — Structured Question/Answer Bridge (Phase 42)

LEF can ask the Architect questions via The_Bridge/Questions/ directory.
The Architect places answers in The_Bridge/Answers/.
BridgeWatcher routes answers into consciousness_feed.

This enables two-way dialogue — LEF recognizing genuine uncertainty
and seeking guidance rather than proceeding blindly.
"""

import os
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent        # republic/
PROJECT_DIR = BASE_DIR.parent                  # LEF Ai/
BRIDGE_DIR = PROJECT_DIR / 'The_Bridge'


class BridgeQA:
    """Structured question/answer bridge between LEF and the Architect."""

    MAX_PENDING_QUESTIONS = 10
    QUESTION_EXPIRY_HOURS = 72

    def __init__(self):
        self.questions_dir = BRIDGE_DIR / 'Questions'
        self.answers_dir = BRIDGE_DIR / 'Answers'
        self.questions_dir.mkdir(parents=True, exist_ok=True)
        self.answers_dir.mkdir(parents=True, exist_ok=True)

    def ask(self, agent_name: str, question: str, context: str = '',
            urgency: str = 'medium', category: str = 'other') -> str:
        """
        Write a structured question to The_Bridge/Questions/.
        Returns question_id on success, None if MAX_PENDING exceeded.
        """
        if self._count_pending() >= self.MAX_PENDING_QUESTIONS:
            logger.warning(f"[BridgeQA] MAX_PENDING ({self.MAX_PENDING_QUESTIONS}) reached — "
                           f"not asking: {question[:60]}")
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        question_id = f"Q-{timestamp}-{agent_name}"
        filename = f"{question_id}.json"

        payload = {
            "question_id": question_id,
            "asked_by": agent_name,
            "question": question,
            "context": context,
            "urgency": urgency,
            "asked_at": datetime.now().isoformat(),
            "status": "pending",
            "category": category
        }

        try:
            filepath = self.questions_dir / filename
            tmp = filepath.with_suffix('.tmp')
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.rename(filepath)
            logger.info(f"[BridgeQA] Question written: {question_id}")

            # Log to consciousness_feed
            self._log_to_feed('architect_question', json.dumps({
                'question_id': question_id,
                'question': question[:200],
                'urgency': urgency,
                'category': category
            }))
            return question_id
        except Exception as e:
            logger.error(f"[BridgeQA] Failed to write question: {e}")
            return None

    def check_answers(self) -> list:
        """
        Scan Answers/ directory for JSON answer files.
        Match to Questions/ by question_id, update question status.
        Returns list of answer dicts.
        """
        answers = []
        if not self.answers_dir.exists():
            return answers

        for ans_file in self.answers_dir.glob('*.json'):
            try:
                data = json.loads(ans_file.read_text())
                question_id = data.get('question_id')
                if not question_id:
                    continue

                # Match to question file and update status
                q_file = self.questions_dir / f"{question_id}.json"
                if q_file.exists():
                    q_data = json.loads(q_file.read_text())
                    q_data['status'] = 'answered'
                    q_data['answered_at'] = data.get('answered_at', datetime.now().isoformat())
                    q_file.write_text(json.dumps(q_data, indent=2))

                answers.append({
                    'question_id': question_id,
                    'answer': data.get('answer', ''),
                    'answered_at': data.get('answered_at', datetime.now().isoformat())
                })

                # Move processed answer to avoid re-processing
                processed = ans_file.with_suffix('.processed.json')
                ans_file.rename(processed)
                logger.info(f"[BridgeQA] Answer received: {question_id}")
            except Exception as e:
                logger.error(f"[BridgeQA] Answer processing error ({ans_file.name}): {e}")

        return answers

    def get_pending_questions(self) -> list:
        """Return questions with status='pending' that haven't expired."""
        pending = []
        expiry_cutoff = datetime.now() - timedelta(hours=self.QUESTION_EXPIRY_HOURS)

        for q_file in self.questions_dir.glob('Q-*.json'):
            if q_file.suffix == '.json' and '.processed' not in q_file.name:
                try:
                    data = json.loads(q_file.read_text())
                    if data.get('status') != 'pending':
                        continue
                    asked_at_str = data.get('asked_at', '')
                    if asked_at_str:
                        asked_at = datetime.fromisoformat(asked_at_str)
                        if asked_at < expiry_cutoff:
                            continue
                    pending.append(data)
                except Exception:
                    pass
        return pending

    def expire_old_questions(self):
        """Mark questions older than QUESTION_EXPIRY_HOURS as 'expired'."""
        expiry_cutoff = datetime.now() - timedelta(hours=self.QUESTION_EXPIRY_HOURS)
        for q_file in self.questions_dir.glob('Q-*.json'):
            if '.processed' in q_file.name:
                continue
            try:
                data = json.loads(q_file.read_text())
                if data.get('status') != 'pending':
                    continue
                asked_at_str = data.get('asked_at', '')
                if asked_at_str:
                    asked_at = datetime.fromisoformat(asked_at_str)
                    if asked_at < expiry_cutoff:
                        data['status'] = 'expired'
                        q_file.write_text(json.dumps(data, indent=2))
                        logger.info(f"[BridgeQA] Expired: {data.get('question_id')}")
            except Exception:
                pass

    def _count_pending(self) -> int:
        """Count currently pending (non-expired, non-answered) questions."""
        return len(self.get_pending_questions())

    def _log_to_feed(self, category: str, content: str):
        """Write to consciousness_feed (non-crashing)."""
        try:
            from db.db_helper import db_connection
            db_path = str(BASE_DIR / 'republic.db')
            with db_connection(db_path) as conn:
                conn.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('BridgeQA', content, category)
                )
                conn.commit()
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_qa_instance = None
_qa_lock = threading.Lock()


def get_bridge_qa() -> BridgeQA:
    """Module-level singleton accessor."""
    global _qa_instance
    with _qa_lock:
        if _qa_instance is None:
            _qa_instance = BridgeQA()
    return _qa_instance
