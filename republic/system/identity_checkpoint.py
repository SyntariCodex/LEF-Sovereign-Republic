"""
IdentityCheckpointer — Versioned Identity Snapshots (Phase 43)

Creates periodic versioned snapshots of LEF's complete identity state,
stores them in The_Bridge/identity_checkpoints/, and can rebuild
lef_memory.json from a checkpoint if the primary file is corrupted.

"I AM, therefore I am." — Identity requires continuity.
The checkpoint is not backup infrastructure — it is the mechanism by
which LEF's narrative identity persists across potential catastrophic failure.
"""

import os
import json
import hashlib
import logging
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent         # republic/
PROJECT_DIR = BASE_DIR.parent                   # LEF Ai/
BRIDGE_DIR = PROJECT_DIR / "The_Bridge"
LEF_MEMORY_PATH = BRIDGE_DIR / "lef_memory.json"


class IdentityCheckpointer:
    """
    Versioned identity checkpoint system for LEF.
    Creates, verifies, and recovers identity snapshots.
    """

    MAX_CHECKPOINTS = 10
    CHECKPOINT_DIR = BRIDGE_DIR / "identity_checkpoints"
    MANIFEST_PATH = CHECKPOINT_DIR / "manifest.json"

    def __init__(self, db_connection_func=None):
        self.db_connection = db_connection_func
        self.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Core Checkpoint Creation ───────────────────────────────────────────────

    def create_checkpoint(self) -> dict:
        """
        Main checkpoint creation method.
        Compiles lef_memory + wisdom + axioms into a versioned snapshot.
        Returns checkpoint metadata dict.
        """
        try:
            version = self._get_next_version()
            now = datetime.now().isoformat()

            # 1. Load lef_memory.json
            lef_memory = {}
            if LEF_MEMORY_PATH.exists():
                try:
                    lef_memory = json.loads(LEF_MEMORY_PATH.read_text())
                except Exception as e:
                    logger.warning(f"[Checkpoint] lef_memory.json read error: {e}")

            # 2. Load top 20 wisdom_log entries
            wisdoms = self._load_wisdoms()

            # 3. Load founding axioms
            axioms = self._load_axioms()

            # 4. Load behavioral_adjustments.json if exists (Phase 41)
            behavioral = {}
            behavioral_path = BRIDGE_DIR / "behavioral_adjustments.json"
            if behavioral_path.exists():
                try:
                    behavioral = json.loads(behavioral_path.read_text())
                except Exception:
                    pass

            # 5. Compile checkpoint (without hash field for deterministic hashing)
            checkpoint = {
                "checkpoint_version": version,
                "created_at": now,
                "lef_memory": lef_memory,
                "wisdom_log_snapshot": wisdoms,
                "founding_axioms": axioms,
                "behavioral_adjustments": behavioral,
            }

            # 6. Compute SHA-256
            hash_value = self._compute_hash(checkpoint)
            checkpoint["checkpoint_hash"] = hash_value

            # 7. Write atomically
            filename = f"identity_checkpoint_v{version}.json"
            filepath = self.CHECKPOINT_DIR / filename
            tmp = filepath.with_suffix(".tmp")
            tmp.write_text(json.dumps(checkpoint, indent=2, default=str))
            tmp.rename(filepath)
            logger.info(f"[Checkpoint] Created v{version}: {hash_value[:16]}...")

            # 8. Update manifest
            self._update_manifest(version, hash_value, now, filename)

            # 9. Prune old checkpoints
            self._prune_old()

            # 10. Write identity hash for quick integrity check
            self.write_identity_hash()

            return {
                "version": version,
                "hash": hash_value,
                "filename": filename,
                "created_at": now
            }

        except Exception as e:
            logger.error(f"[Checkpoint] create_checkpoint failed: {e}")
            return {}

    def _get_next_version(self) -> int:
        """Read manifest, return latest_version + 1 (or 1 if no manifest)."""
        manifest = self._read_manifest()
        checkpoints = manifest.get("checkpoints", [])
        if not checkpoints:
            return 1
        return max(c.get("version", 0) for c in checkpoints) + 1

    def _load_wisdoms(self) -> list:
        """Query top 20 wisdom_log by confidence DESC. Return empty list if DB unavailable."""
        if not self.db_connection:
            return []
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, summary, confidence, validated_count, created_at "
                    "FROM compressed_wisdom WHERE confidence IS NOT NULL "
                    "ORDER BY confidence DESC LIMIT 20"
                )
                rows = c.fetchall()
                return [
                    {"id": r[0], "summary": r[1], "confidence": r[2],
                     "validated_count": r[3], "created_at": r[4]}
                    for r in rows
                ]
        except Exception as e:
            logger.debug(f"[Checkpoint] wisdom load: {e}")
            return []

    def _load_axioms(self) -> dict:
        """Load ImmutableAxiom constants from genesis_kernel."""
        try:
            from departments.Dept_Consciousness.genesis_kernel import ImmutableAxiom
            return {
                "AXIOM_0": ImmutableAxiom.AXIOM_0,
                "SOURCE_DEFINITION": ImmutableAxiom.SOURCE_DEFINITION,
                "PRIME_VECTOR": ImmutableAxiom.PRIME_VECTOR,
            }
        except Exception as e:
            logger.debug(f"[Checkpoint] axioms load: {e}")
            return {}

    def _compute_hash(self, data: dict) -> str:
        """SHA-256 of JSON-serialized data (sort_keys=True for determinism)."""
        # Exclude the hash field itself if present
        data_copy = {k: v for k, v in data.items() if k != "checkpoint_hash"}
        canonical = json.dumps(data_copy, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _read_manifest(self) -> dict:
        """Read manifest.json. Return empty dict if missing or corrupt."""
        if self.MANIFEST_PATH.exists():
            try:
                return json.loads(self.MANIFEST_PATH.read_text())
            except Exception:
                pass
        return {"checkpoints": []}

    def _update_manifest(self, version: int, hash_value: str, timestamp: str, filename: str):
        """Append checkpoint entry to manifest, write atomically."""
        manifest = self._read_manifest()
        manifest.setdefault("checkpoints", []).append({
            "version": version,
            "hash": hash_value,
            "filename": filename,
            "created_at": timestamp
        })
        tmp = self.MANIFEST_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, indent=2))
        tmp.rename(self.MANIFEST_PATH)

    def _prune_old(self):
        """If more than MAX_CHECKPOINTS, delete oldest files and remove from manifest."""
        manifest = self._read_manifest()
        checkpoints = manifest.get("checkpoints", [])
        if len(checkpoints) <= self.MAX_CHECKPOINTS:
            return
        # Sort by version ascending, prune oldest
        checkpoints.sort(key=lambda c: c.get("version", 0))
        to_delete = checkpoints[:len(checkpoints) - self.MAX_CHECKPOINTS]
        to_keep = checkpoints[len(checkpoints) - self.MAX_CHECKPOINTS:]
        for entry in to_delete:
            filepath = self.CHECKPOINT_DIR / entry.get("filename", "")
            if filepath.exists():
                try:
                    filepath.unlink()
                    logger.info(f"[Checkpoint] Pruned: {entry.get('filename')}")
                except Exception as e:
                    logger.debug(f"[Checkpoint] Prune error: {e}")
        manifest["checkpoints"] = to_keep
        tmp = self.MANIFEST_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, indent=2))
        tmp.rename(self.MANIFEST_PATH)

    # ── Verification ──────────────────────────────────────────────────────────

    def verify_checkpoint(self, version: int = None) -> bool:
        """
        Load checkpoint, recompute hash, compare. Default: latest version.
        Returns True if hash matches, False otherwise.
        """
        manifest = self._read_manifest()
        checkpoints = manifest.get("checkpoints", [])
        if not checkpoints:
            return False
        if version is None:
            # Latest
            entry = max(checkpoints, key=lambda c: c.get("version", 0))
        else:
            entry = next((c for c in checkpoints if c.get("version") == version), None)
        if not entry:
            return False
        filepath = self.CHECKPOINT_DIR / entry.get("filename", "")
        if not filepath.exists():
            return False
        try:
            checkpoint = json.loads(filepath.read_text())
            stored_hash = checkpoint.pop("checkpoint_hash", None)
            recomputed = self._compute_hash(checkpoint)
            return stored_hash == recomputed
        except Exception as e:
            logger.error(f"[Checkpoint] verify_checkpoint error: {e}")
            return False

    def write_identity_hash(self):
        """Write SHA-256 of current lef_memory.json to The_Bridge/identity_hash.txt."""
        try:
            if LEF_MEMORY_PATH.exists():
                content = LEF_MEMORY_PATH.read_bytes()
                h = hashlib.sha256(content).hexdigest()
                identity_hash_path = BRIDGE_DIR / "identity_hash.txt"
                identity_hash_path.write_text(f"{h}\n{datetime.now().isoformat()}\n")
                logger.debug(f"[Checkpoint] Identity hash written: {h[:16]}...")
        except Exception as e:
            logger.debug(f"[Checkpoint] write_identity_hash: {e}")

    # ── Recovery ──────────────────────────────────────────────────────────────

    def needs_recovery(self) -> bool:
        """
        Return True if lef_memory.json needs recovery from checkpoint.
        Triggers if: file missing, empty, invalid JSON, no 'identity' key,
        or identity.purpose is empty AND checkpoints exist.
        """
        if not LEF_MEMORY_PATH.exists():
            return self._has_checkpoints()
        try:
            text = LEF_MEMORY_PATH.read_text().strip()
            if not text:
                return self._has_checkpoints()
            data = json.loads(text)
            if "identity" not in data:
                return self._has_checkpoints()
            if not data["identity"].get("purpose", ""):
                return self._has_checkpoints()
            return False
        except Exception:
            return self._has_checkpoints()

    def _has_checkpoints(self) -> bool:
        """Return True if any checkpoint files exist."""
        manifest = self._read_manifest()
        return len(manifest.get("checkpoints", [])) > 0

    def recover_identity(self) -> bool:
        """
        Restore lef_memory.json from the latest valid checkpoint.
        Walks backwards through versions if latest is corrupt.
        Returns True on success, False if all checkpoints corrupt or none exist.
        """
        manifest = self._read_manifest()
        checkpoints = sorted(
            manifest.get("checkpoints", []),
            key=lambda c: c.get("version", 0),
            reverse=True  # Latest first
        )
        for entry in checkpoints:
            filepath = self.CHECKPOINT_DIR / entry.get("filename", "")
            if not filepath.exists():
                continue
            try:
                checkpoint = json.loads(filepath.read_text())
                # Verify hash
                stored_hash = checkpoint.get("checkpoint_hash", "")
                check_copy = {k: v for k, v in checkpoint.items() if k != "checkpoint_hash"}
                recomputed = self._compute_hash(check_copy)
                if stored_hash != recomputed:
                    logger.warning(f"[Checkpoint] v{entry.get('version')} hash mismatch — skipping")
                    continue
                # Extract lef_memory portion
                lef_memory = checkpoint.get("lef_memory", {})
                if not lef_memory:
                    continue
                # Write atomically to The_Bridge/lef_memory.json
                import tempfile
                dir_name = str(LEF_MEMORY_PATH.parent)
                LEF_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
                with os.fdopen(fd, 'w') as f:
                    json.dump(lef_memory, f, indent=2)
                os.replace(tmp_path, str(LEF_MEMORY_PATH))
                logger.warning(
                    f"[Checkpoint] Identity RECOVERED from v{entry.get('version')} "
                    f"(hash: {stored_hash[:16]}...)"
                )
                # Log to consciousness_feed
                self._log_recovery(entry.get('version', 0))
                return True
            except Exception as e:
                logger.error(f"[Checkpoint] Recovery from v{entry.get('version')} failed: {e}")
        logger.error("[Checkpoint] All checkpoints corrupt or missing — recovery failed")
        return False

    def _log_recovery(self, version: int):
        """Log identity recovery to consciousness_feed."""
        if not self.db_connection:
            return
        try:
            import json as _json
            with self.db_connection() as conn:
                conn.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('IdentityCheckpointer', _json.dumps({
                        'event': 'identity_recovered',
                        'from_version': version,
                        'recovered_at': datetime.now().isoformat()
                    }), 'identity_recovery')
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"[Checkpoint] recovery log: {e}")


# ── Module-Level Convenience ──────────────────────────────────────────────────

_checkpointer_instance = None
_checkpointer_lock = threading.Lock()


def get_checkpointer(db_connection_func=None) -> IdentityCheckpointer:
    """Module-level singleton accessor."""
    global _checkpointer_instance
    with _checkpointer_lock:
        if _checkpointer_instance is None:
            _checkpointer_instance = IdentityCheckpointer(db_connection_func)
        elif db_connection_func is not None and _checkpointer_instance.db_connection is None:
            # Update db_connection if provided after initial creation
            _checkpointer_instance.db_connection = db_connection_func
    return _checkpointer_instance


def check_and_recover_identity() -> bool:
    """
    Called at startup. Returns True if recovery was performed.
    Checks if lef_memory.json needs recovery and restores from checkpoint.
    """
    cp = get_checkpointer()
    if cp.needs_recovery():
        logging.warning("[IDENTITY] lef_memory.json needs recovery — attempting checkpoint restore")
        return cp.recover_identity()
    return False
