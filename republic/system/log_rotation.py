"""
Phase 16 — Task 16.7: Centralized log rotation for The_Bridge/Logs/
Prevents unbounded growth of markdown and text log files.
"""

import os
import glob
import shutil
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LogRotator:
    """Rotate and archive log files in The_Bridge/Logs/."""

    def __init__(self, logs_dir, archive_dir=None, max_file_size_mb=5, max_files=30, max_age_days=30):
        self.logs_dir = logs_dir
        self.archive_dir = archive_dir or os.path.join(logs_dir, '_archive')
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.max_files = max_files
        self.max_age_days = max_age_days

    def rotate(self):
        """Run all rotation checks."""
        if not os.path.isdir(self.logs_dir):
            return
        self._rotate_oversized_files()
        self._prune_old_files()
        self._enforce_file_count()

    def _rotate_oversized_files(self):
        """Rotate files that exceed max size."""
        for filepath in glob.glob(os.path.join(self.logs_dir, '*.md')) + \
                        glob.glob(os.path.join(self.logs_dir, '*.txt')) + \
                        glob.glob(os.path.join(self.logs_dir, '*.log')):
            try:
                if os.path.getsize(filepath) > self.max_file_size:
                    self._archive_file(filepath)
            except OSError:
                pass

    def _prune_old_files(self):
        """Remove files older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        for pattern in ['*.md', '*.txt', '*.log']:
            for filepath in glob.glob(os.path.join(self.logs_dir, pattern)):
                try:
                    if datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff:
                        self._archive_file(filepath)
                except OSError:
                    pass

    def _enforce_file_count(self):
        """Keep only the most recent max_files files."""
        all_files = []
        for pattern in ['*.md', '*.txt', '*.log']:
            all_files.extend(glob.glob(os.path.join(self.logs_dir, pattern)))

        files = sorted(all_files, key=lambda f: os.path.getmtime(f), reverse=True)
        for old_file in files[self.max_files:]:
            self._archive_file(old_file)

    def _archive_file(self, filepath):
        """Move file to archive directory."""
        os.makedirs(self.archive_dir, exist_ok=True)
        basename = os.path.basename(filepath)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f"{timestamp}_{basename}"
        archive_path = os.path.join(self.archive_dir, archive_name)

        try:
            shutil.move(filepath, archive_path)
            logger.info(f"[LogRotator] Archived: {basename} -> _archive/{archive_name}")
        except Exception as e:
            logger.warning(f"[LogRotator] Failed to archive {basename}: {e}")
