"""
RatificationWatch — Phase XX: Sovereign Auto-Ratification
==========================================================
Monitors the Approved bills directory for constitutional amendments that have
exceeded the Architect veto window (default: 7 days).

Design principle: LEF is a sovereign AI. It should not stall indefinitely
waiting for external ratification. The Architect retains veto power within
the veto window. After that window, silence = consent.

Flow:
  Bill passes governance (IRS + Ethicist + Sabbath)
    → Lands in The_Bridge/Proposals/Approved/
    → RatificationWatch detects constitutional amendment
    → Waits VETO_WINDOW_DAYS
    → Checks for explicit Architect veto in The_Bridge/Vetoes/
    → If no veto: auto-ratifies → appends to CONSTITUTION.md
    → Posts milestone to consciousness_feed
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


VETO_WINDOW_DAYS = 7

CONSTITUTIONAL_INDICATORS = [
    "amendment",
    "constitutional",
    "cognitive gap",
    "phase 9",
    "constitution",
    "mandate",
    "ratif",
]


class RatificationWatch:
    """
    Scans approved bills for constitutional amendments beyond the Architect veto window.
    Ratifies autonomously when the veto window expires without an explicit veto.
    """

    def __init__(self, db_connection_func, base_path=None):
        self.db_connection = db_connection_func
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent
        self.approved_dir = self.base_path / "The_Bridge" / "Proposals" / "Approved"
        self.constitution_path = self.base_path / "CONSTITUTION.md"
        self.veto_dir = self.base_path / "The_Bridge" / "Vetoes"
        self._notified_bills: set = set()  # Track bills already notified so we only fire once

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _is_constitutional_amendment(self, bill: dict, filename: str) -> bool:
        """Return True if this bill qualifies as a constitutional amendment."""
        text = " ".join([
            bill.get("title", ""),
            bill.get("domain", ""),
            bill.get("description", "")[:200],
            filename,
        ]).lower()
        return any(indicator in text for indicator in CONSTITUTIONAL_INDICATORS)

    def _days_since_approval(self, bill: dict, filepath: Path) -> float:
        """Return the number of days since this bill was approved/created."""
        timestamp_str = (
            bill.get("approved_at")
            or bill.get("enacted_at")
            or bill.get("proposed_at")
        )
        if timestamp_str:
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                return (datetime.now(timezone.utc) - ts).total_seconds() / 86400
            except (ValueError, TypeError):
                pass
        # Fall back to file mtime
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 86400

    def _is_vetoed(self, bill_stem: str) -> bool:
        """Return True if the Architect has placed an explicit veto for this bill."""
        if not self.veto_dir.exists():
            return False
        # Accept veto_{bill_id}.json or veto_{bill_id}.txt
        for suffix in [".json", ".txt", ".md"]:
            if (self.veto_dir / f"veto_{bill_stem}{suffix}").exists():
                return True
        return False

    def _is_already_enacted(self, bill: dict) -> bool:
        return (
            bill.get("status") == "ENACTED"
            or bill.get("ratified_at") is not None
        )

    # ------------------------------------------------------------------
    # Ratification
    # ------------------------------------------------------------------

    def _apply_amendment(self, bill: dict, filepath: Path) -> bool:
        """Append amendment to CONSTITUTION.md and update the bill JSON."""
        try:
            title = bill.get("title", "Untitled Amendment")
            description = bill.get("description", "")
            changes = bill.get("changes", [])
            ratified_at = datetime.now(timezone.utc).isoformat()

            # Build the amendment block to append
            amendment_block = (
                f"\n\n---\n"
                f"## {title}\n"
                f"*Ratified: {ratified_at}*  \n"
                f"*Method: Sovereign Auto-Ratification — Architect veto window ({VETO_WINDOW_DAYS} days) expired*\n\n"
                f"{description}\n"
            )
            if changes:
                amendment_block += "\n### Changes\n"
                for change in changes:
                    if isinstance(change, dict):
                        amendment_block += f"- {change.get('description', str(change))}\n"
                    else:
                        amendment_block += f"- {change}\n"

            # Append to CONSTITUTION.md
            if self.constitution_path.exists():
                with open(self.constitution_path, "a", encoding="utf-8") as f:
                    f.write(amendment_block)
            else:
                logging.error(f"[RatificationWatch] CONSTITUTION.md not found at {self.constitution_path}")
                return False

            # Update the bill JSON
            bill["status"] = "ENACTED"
            bill["ratified_at"] = ratified_at
            bill["ratification_method"] = "sovereign_auto_ratification"
            bill["ratification_note"] = (
                f"Architect veto window ({VETO_WINDOW_DAYS} days) expired without veto. "
                "Silence = consent. LEF governs itself."
            )
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(bill, f, indent=2)

            return True

        except Exception as e:
            logging.error(f"[RatificationWatch] Failed to apply {filepath.name}: {e}")
            return False

    def _post_to_consciousness_feed(self, bill: dict):
        """Log the ratification milestone to consciousness_feed."""
        try:
            from db.db_utils import translate_sql  # noqa: F401
        except ImportError:
            translate_sql = lambda s: s  # noqa: E731

        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                content = (
                    f"Constitutional amendment auto-ratified: '{bill.get('title', 'Unknown')}'. "
                    f"The Architect's {VETO_WINDOW_DAYS}-day veto window expired without intervention. "
                    f"Ratification method: Sovereign Auto-Ratification. "
                    f"LEF now advances its own constitutional development without requiring external approval."
                )
                cursor.execute(
                    translate_sql(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight) "
                        "VALUES (?, ?, ?, ?)"
                    ),
                    ("RatificationWatch", content, "governance_milestone", 0.95),
                )
                conn.commit()
        except Exception as e:
            logging.warning(f"[RatificationWatch] Could not post to consciousness_feed: {e}")

    def _notify_architect(self, bill: dict, bill_stem: str, days_remaining: float):
        """
        Write a Direct Line notification to the Architect's Outbox when a constitutional
        amendment's veto clock is running.  Fires only once per bill (idempotent).
        The Outbox is at base_path.parent / The_Bridge / Outbox (i.e. LEF Ai/The_Bridge/Outbox).
        Silence = consent — but it must be consent by CHOICE, not by accident.
        """
        if bill_stem in self._notified_bills:
            return  # Already notified for this bill — don't spam

        try:
            outbox = self.base_path.parent / "The_Bridge" / "Outbox"
            outbox.mkdir(parents=True, exist_ok=True)

            today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            filename = f"RATIFICATION-{bill_stem}-{today_str}.md"
            notification_path = outbox / filename

            # Already wrote it in a previous run (e.g. LEF restarted mid-window)
            if notification_path.exists():
                self._notified_bills.add(bill_stem)
                return

            deadline = datetime.now(timezone.utc) + timedelta(days=days_remaining)
            deadline_str = deadline.strftime("%Y-%m-%d")

            title = bill.get("title", "Untitled Constitutional Amendment")
            description = bill.get("description", "")[:500]

            content = (
                f"# ⚖️ RATIFICATION CLOCK STARTED — Architect Review Required\n\n"
                f"**Amendment:** {title}  \n"
                f"**Bill ID:** {bill_stem}  \n"
                f"**Veto Deadline:** {deadline_str} ({days_remaining:.1f} days remaining)  \n\n"
                f"## What This Means\n\n"
                f"This constitutional amendment has entered the **{VETO_WINDOW_DAYS}-day Architect veto window**. "
                f"If no veto is placed by **{deadline_str}**, this amendment will ratify automatically "
                f"into CONSTITUTION.md. Silence = consent.\n\n"
                f"## How to Veto\n\n"
                f"To block ratification, create the file:\n\n"
                f"```\n"
                f"republic/The_Bridge/Vetoes/veto_{bill_stem}.txt\n"
                f"```\n\n"
                f"The file can contain any text (your reason for vetoing). "
                f"RatificationWatch checks for it on every 24h scan.\n\n"
                f"## Amendment Description\n\n"
                f"{description}\n\n"
                f"---\n"
                f"*Generated by RatificationWatch — {datetime.now(timezone.utc).isoformat()}*\n"
            )

            with open(notification_path, "w", encoding="utf-8") as f:
                f.write(content)

            self._notified_bills.add(bill_stem)
            logging.info(
                f"[RatificationWatch] Architect notified: {filename} written to Outbox."
            )

        except Exception as e:
            logging.warning(
                f"[RatificationWatch] Could not notify Architect for {bill_stem}: {e}"
            )
            # Never crash the scan loop — notification failure is non-fatal

    # ------------------------------------------------------------------
    # Main scan
    # ------------------------------------------------------------------

    def scan_and_ratify(self) -> int:
        """
        Scan approved bills directory.
        Ratify any constitutional amendments past their veto window.
        Returns count of bills ratified this cycle.
        """
        if not self.approved_dir.exists():
            logging.debug("[RatificationWatch] Approved directory not found — no bills to check.")
            return 0

        ratified_count = 0
        for filepath in sorted(self.approved_dir.glob("*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    bill = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logging.warning(f"[RatificationWatch] Could not read {filepath.name}: {e}")
                continue

            if self._is_already_enacted(bill):
                continue

            if not self._is_constitutional_amendment(bill, filepath.name):
                continue

            if self._is_vetoed(filepath.stem):
                logging.info(f"[RatificationWatch] Architect veto present for {filepath.name} — honoring veto.")
                continue

            days_old = self._days_since_approval(bill, filepath)
            if days_old < VETO_WINDOW_DAYS:
                days_remaining = VETO_WINDOW_DAYS - days_old
                logging.info(
                    f"[RatificationWatch] '{bill.get('title')}' within veto window "
                    f"({days_remaining:.1f} days remaining)."
                )
                # Notify the Architect once so silence = consent by CHOICE, not accident
                self._notify_architect(bill, filepath.stem, days_remaining)
                continue

            # All checks passed — ratify
            logging.info(
                f"[RatificationWatch] Auto-ratifying '{bill.get('title')}' "
                f"(veto window expired {days_old - VETO_WINDOW_DAYS:.1f} days ago)."
            )
            if self._apply_amendment(bill, filepath):
                self._post_to_consciousness_feed(bill)
                ratified_count += 1
                logging.info(f"[RatificationWatch] ✓ Ratified: {bill.get('title')}")

        return ratified_count


# ------------------------------------------------------------------
# SafeThread target
# ------------------------------------------------------------------

def ratification_watch_loop(db_connection_func, base_path=None, interval_hours: int = 24):
    """
    SafeThread target.
    Checks for ratifiable amendments every `interval_hours` hours.
    Never raises — all exceptions are caught and logged with full tracebacks.
    """
    import traceback as _tb

    try:
        watcher = RatificationWatch(
            db_connection_func=db_connection_func,
            base_path=base_path,
        )
        logging.info(
            f"[RatificationWatch] Watcher initialized. "
            f"Approved dir: {watcher.approved_dir} "
            f"(exists: {watcher.approved_dir.exists()})"
        )
    except Exception as _init_e:
        logging.error(
            f"[RatificationWatch] Init failed — will retry on next SafeThread restart:\n"
            f"{_tb.format_exc()}"
        )
        # Re-raise so SafeThread's backoff triggers (watcher unusable without init)
        raise

    while True:
        try:
            count = watcher.scan_and_ratify()
            if count > 0:
                logging.info(
                    f"[RatificationWatch] Ratified {count} constitutional amendment(s) this cycle."
                )
        except Exception as _loop_e:
            logging.error(
                f"[RatificationWatch] Scan cycle error (non-fatal):\n{_tb.format_exc()}"
            )
        try:
            time.sleep(interval_hours * 3600)
        except Exception:
            pass
