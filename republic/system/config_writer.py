"""
Safe config writer for the Evolution Engine.
Handles reading, modifying, backing up, and writing JSON config files.

Safety requirements:
- ALWAYS backup before writing
- Atomic writes (temp file + rename) to prevent corruption on crash
- Validate JSON before writing
- Key path validation (don't create nested keys that don't exist)

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md
"""

import os
import json
import shutil
import tempfile
import logging
import glob
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Backup directory
BASE_DIR = Path(__file__).parent.parent.parent  # LEF Ai root
CONFIG_BACKUP_DIR = BASE_DIR / 'The_Bridge' / 'config_backups'
MAX_BACKUPS_PER_FILE = 10


class ConfigWriter:
    """Safe, generic config writer for JSON config files."""

    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir) if backup_dir else CONFIG_BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def read_config(self, config_path: str) -> dict:
        """Read a JSON config file. Return empty dict if not found."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"[CONFIG] File not found: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"[CONFIG] Invalid JSON in {config_path}: {e}")
            return {}

    def get_value(self, config: dict, key_path: str):
        """
        Get value at dot-notation key path.
        e.g., get_value(config, 'DYNASTY.take_profit') -> 0.50
        Returns None if key path doesn't exist.
        """
        keys = key_path.split('.')
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def set_value(self, config: dict, key_path: str, value) -> tuple:
        """
        Set value at dot-notation key path.
        Returns (modified_config, old_value) tuple.
        Does NOT write to file.

        Raises KeyError if intermediate keys don't exist
        (will not create nested structures that don't exist).
        """
        keys = key_path.split('.')
        current = config

        # Navigate to parent of target key
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(
                    f"[CONFIG] Key path '{key_path}' invalid: "
                    f"intermediate key '{key}' does not exist"
                )

        # Set the final key
        final_key = keys[-1]
        if not isinstance(current, dict):
            raise KeyError(
                f"[CONFIG] Key path '{key_path}' invalid: "
                f"parent is not a dict"
            )

        old_value = current.get(final_key)
        current[final_key] = value
        return config, old_value

    def backup_config(self, config_path: str) -> str:
        """
        Copy config to The_Bridge/config_backups/{name}_{timestamp}.json
        Prune to keep only last MAX_BACKUPS_PER_FILE backups per file.
        Returns backup path.
        """
        config_path = Path(config_path)
        if not config_path.exists():
            logger.warning(f"[CONFIG] Cannot backup non-existent file: {config_path}")
            return ""

        # Create backup filename
        stem = config_path.stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{stem}_{timestamp}.json"
        backup_path = self.backup_dir / backup_name

        # Copy file
        shutil.copy2(str(config_path), str(backup_path))
        logger.info(f"[CONFIG] Backup created: {backup_path}")

        # Prune old backups for this file
        self._prune_backups(stem)

        return str(backup_path)

    def _prune_backups(self, file_stem: str):
        """Keep only the last MAX_BACKUPS_PER_FILE backups for a given config file."""
        pattern = str(self.backup_dir / f"{file_stem}_*.json")
        backups = sorted(glob.glob(pattern))

        if len(backups) > MAX_BACKUPS_PER_FILE:
            to_remove = backups[:len(backups) - MAX_BACKUPS_PER_FILE]
            for old_backup in to_remove:
                try:
                    os.remove(old_backup)
                    logger.debug(f"[CONFIG] Pruned old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"[CONFIG] Failed to prune backup {old_backup}: {e}")

    def write_config(self, config_path: str, config: dict) -> bool:
        """
        Write config to file. ALWAYS backup first.
        Uses atomic write (write to temp, then rename) to prevent corruption.
        Returns True on success, False on failure.
        """
        config_path = Path(config_path)

        # Backup first (if file exists)
        if config_path.exists():
            backup = self.backup_config(str(config_path))
            if not backup:
                logger.error("[CONFIG] Backup failed, aborting write")
                return False

        # Validate the config is valid JSON by round-tripping
        try:
            serialized = json.dumps(config, indent=2, default=str)
            json.loads(serialized)  # Validate
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"[CONFIG] Config validation failed: {e}")
            return False

        # Atomic write: write to temp file in same directory, then rename
        config_dir = config_path.parent
        config_dir.mkdir(parents=True, exist_ok=True)

        try:
            fd, tmp_path = tempfile.mkstemp(
                suffix='.json.tmp',
                dir=str(config_dir)
            )
            with os.fdopen(fd, 'w') as f:
                f.write(serialized)
                f.write('\n')

            # Atomic rename (on POSIX systems)
            os.replace(tmp_path, str(config_path))
            logger.info(f"[CONFIG] Written: {config_path}")
            return True

        except Exception as e:
            logger.error(f"[CONFIG] Write failed: {e}")
            # Clean up temp file if it exists
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def rollback(self, config_path: str) -> bool:
        """
        Restore most recent backup for a config file.
        Emergency rollback mechanism.
        Returns True on success, False if no backup found.
        """
        config_path = Path(config_path)
        stem = config_path.stem

        pattern = str(self.backup_dir / f"{stem}_*.json")
        backups = sorted(glob.glob(pattern))

        if not backups:
            logger.error(f"[CONFIG] No backups found for {stem}")
            return False

        latest_backup = backups[-1]
        try:
            shutil.copy2(latest_backup, str(config_path))
            logger.info(f"[CONFIG] Rolled back {config_path} from {latest_backup}")
            return True
        except Exception as e:
            logger.error(f"[CONFIG] Rollback failed: {e}")
            return False

    def safe_modify(self, config_path: str, key_path: str, new_value) -> tuple:
        """
        Convenience method: read → set → write in one call.
        Returns (success: bool, old_value, error_msg: str).
        """
        config = self.read_config(config_path)
        if not config:
            return False, None, f"Failed to read {config_path}"

        try:
            config, old_value = self.set_value(config, key_path, new_value)
        except KeyError as e:
            return False, None, str(e)

        success = self.write_config(config_path, config)
        if success:
            return True, old_value, ""
        else:
            return False, None, f"Failed to write {config_path}"
