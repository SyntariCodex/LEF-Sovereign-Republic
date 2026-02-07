
import logging
import os
from datetime import datetime
from pathlib import Path

# Setup logging
logger = logging.getLogger("Notifier")

class Notifier:
    """
    Centralized Notification Service for Republic Fleet.
    Writes messages to The_Bridge/Outbox for user visibility.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Notifier, cls).__new__(cls)
            cls._instance._init_paths()
        return cls._instance

    def _init_paths(self):
        """Initialize Bridge paths"""
        try:
            # Find republic base dir
            base_dir = Path(__file__).resolve().parent.parent.parent  # LEF Ai/
            self.outbox_path = base_dir / 'The_Bridge' / 'Outbox'
            self.outbox_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to init paths: {e}")
            self.outbox_path = None

    def send(self, message: str, context: str = "System", severity: str = "INFO", color: int = 0x3498db, force_write: bool = False):
        """
        Send notification to The_Bridge/Outbox.
        
        Args:
            message: The text content
            context: The agent or module name (e.g. "Treasury")
            severity: INFO, WARNING, ERROR, SUCCESS
            color: Unused (legacy Discord param)
            force_write: If True, always write to Outbox even for SUCCESS
        """
        # 1. Log locally first
        log_msg = f"[{context}] {message}"
        if severity == "ERROR": logger.error(log_msg)
        elif severity == "WARNING": logger.warning(log_msg)
        elif severity == "SUCCESS": logger.debug(log_msg)  # Quiet down trade spam
        else: logger.info(log_msg)

        # 2. Write to The_Bridge (filter out routine SUCCESS spam unless forced)
        # SUCCESS messages create noise in Outbox - keep ERROR/WARNING only by default
        if self.outbox_path:
            if severity in ("ERROR", "WARNING") or force_write:
                self._write_to_bridge(message, context, severity)

    def _write_to_bridge(self, message: str, context: str, severity: str):
        """Write message to The_Bridge/Outbox"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            severity_icon = {"ERROR": "🔴", "WARNING": "🟡", "SUCCESS": "🟢"}.get(severity, "🔵")
            filename = f"{context.upper()}-{timestamp}-{severity}.md"
            filepath = self.outbox_path / filename
            
            content = f"""# {severity_icon} {context} Notification

**Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Severity:** {severity}

---

{message}
"""
            with open(filepath, 'w') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"Bridge Write Failed: {e}")

# Helper for direct usage
def send_notification(msg, **kwargs):
    Notifier().send(msg, **kwargs)

