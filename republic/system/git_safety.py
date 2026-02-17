"""
Git Safety Wrapper

Provides git-based snapshots and rollback for LEF's self-evolution.
Before any self-modification, LEF creates a snapshot. If the change
causes degradation, LEF can rollback to the snapshot.

Usage:
    from system.git_safety import GitSafety
    
    git = GitSafety()
    if git.verify_repo():
        snapshot_id = git.create_snapshot("BILL-2026-001")
        # ... make changes ...
        # If something goes wrong:
        git.rollback_to_snapshot(snapshot_id)
"""

import os
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("LEF.GitSafety")

# Base directory (LEF Ai root)
BASE_DIR = Path(__file__).parent.parent.parent

# Phase 36: Explicit file patterns for staging (never use git add -A)
SAFE_FILE_PATTERNS = [
    "republic/*.py",
    "republic/**/*.py",
    "republic/**/*.json",
    "republic/**/*.md",
    "republic/**/*.sol",
    "External Observer Reports/*.md",
    "The_Bridge/*.json",
    "The_Bridge/*.md",
    "public/*.html",
    "public/*.css",
    "public/*.js",
]

# Phase 36: Files that must NEVER be staged (secrets, credentials, keys)
FORBIDDEN_PATTERNS = [
    "wallet_encrypted.json",
    ".env",
    "*.pem",
    "*.key",
    "*credentials*",
    "*secret*",
    "*_key.json",
    "*.p12",
    "*.pfx",
]


class GitSafety:
    """
    Git wrapper for safe self-evolution.
    
    All changes LEF makes to itself are wrapped in git commits,
    enabling rollback if changes cause system degradation.
    """
    
    def __init__(self, repo_path: str = None):
        """
        Initialize git safety wrapper.
        
        Args:
            repo_path: Path to git repository (defaults to LEF Ai root)
        """
        self.repo_path = Path(repo_path) if repo_path else BASE_DIR
        self._verified = None
        
    def verify_repo(self) -> bool:
        """
        Verify we're inside a git repository.
        
        Returns:
            True if git repo exists and is valid
        """
        if self._verified is not None:
            return self._verified
            
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            self._verified = result.returncode == 0
            
            if self._verified:
                logger.info(f"[GIT] ✅ Repository verified at {self.repo_path}")
            else:
                logger.warning(f"[GIT] ⚠️ Not a git repository: {self.repo_path}")
                
            return self._verified
            
        except Exception as e:
            logger.error(f"[GIT] Failed to verify repository: {e}")
            self._verified = False
            return False
    
    def create_snapshot(self, bill_id: str, message: str = None) -> str:
        """
        Create a snapshot (commit) before making changes.
        
        Args:
            bill_id: The bill ID triggering this change
            message: Optional commit message (auto-generated if not provided)
            
        Returns:
            Snapshot ID (commit hash) or None if failed
        """
        if not self.verify_repo():
            logger.error("[GIT] Cannot create snapshot: not a git repository")
            return None
            
        try:
            # Phase 36: Stage with explicit file patterns (never git add -A)
            self._safe_stage_files()

            # Create commit
            commit_msg = message or f"[LEF-AUTO] {bill_id}: Pre-change snapshot"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg, "--allow-empty"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Check if nothing to commit
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    logger.info(f"[GIT] No changes to commit for {bill_id}")
                    # Return current HEAD as snapshot
                    return self._get_current_commit()
                else:
                    logger.error(f"[GIT] Commit failed: {result.stderr}")
                    return None
            
            # Get the commit hash
            snapshot_id = self._get_current_commit()
            logger.info(f"[GIT] 📸 Snapshot created: {snapshot_id[:8]} ({bill_id})")
            
            return snapshot_id
            
        except Exception as e:
            logger.error(f"[GIT] Failed to create snapshot: {e}")
            return None
    
    def create_post_change_commit(self, bill_id: str, description: str) -> str:
        """
        Create a commit after changes are made.
        
        Args:
            bill_id: The bill ID that triggered this change
            description: Brief description of what changed
            
        Returns:
            Commit hash or None if failed
        """
        if not self.verify_repo():
            return None
            
        try:
            # Phase 36: Stage with explicit file patterns (never git add -A)
            self._safe_stage_files()

            # Create commit with bill reference
            commit_msg = f"[LEF-AUTO] {bill_id}: {description}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    logger.info(f"[GIT] No changes to commit after {bill_id}")
                    return self._get_current_commit()
                else:
                    logger.error(f"[GIT] Post-change commit failed: {result.stderr}")
                    return None
            
            commit_id = self._get_current_commit()
            logger.info(f"[GIT] ✅ Post-change commit: {commit_id[:8]} ({bill_id})")
            
            return commit_id
            
        except Exception as e:
            logger.error(f"[GIT] Failed to create post-change commit: {e}")
            return None
    
    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """
        Rollback to a previous snapshot.
        
        WARNING: This discards all changes after the snapshot!
        
        Args:
            snapshot_id: The commit hash to rollback to
            
        Returns:
            True if rollback successful
        """
        if not self.verify_repo():
            return False
            
        if not snapshot_id:
            logger.error("[GIT] Cannot rollback: no snapshot ID provided")
            return False
            
        try:
            # Hard reset to the snapshot
            result = subprocess.run(
                ["git", "reset", "--hard", snapshot_id],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"[GIT] Rollback failed: {result.stderr}")
                return False
                
            logger.warning(f"[GIT] 🔙 ROLLBACK to {snapshot_id[:8]} complete")
            return True
            
        except Exception as e:
            logger.error(f"[GIT] Rollback failed: {e}")
            return False
    
    def get_recent_commits(self, count: int = 10) -> list:
        """
        Get recent commit history.
        
        Args:
            count: Number of commits to return
            
        Returns:
            List of dicts with commit info
        """
        if not self.verify_repo():
            return []
            
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%H|%s|%ai"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
                
            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 2)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                        "date": parts[2] if len(parts) > 2 else ""
                    })
                    
            return commits
            
        except Exception as e:
            logger.error(f"[GIT] Failed to get commit history: {e}")
            return []
    
    def _safe_stage_files(self):
        """
        Phase 36: Stage files using explicit patterns instead of git add -A.
        After staging, check for and unstage any forbidden (secret) files.
        """
        # Stage only safe file patterns
        for pattern in SAFE_FILE_PATTERNS:
            try:
                subprocess.run(
                    ["git", "add", "--", pattern],
                    cwd=self.repo_path,
                    capture_output=True,
                    timeout=15
                )
            except Exception:
                pass  # Pattern may not match any files — that's fine

        # Check staged files for secrets and unstage them
        self._unstage_forbidden()

    def _unstage_forbidden(self):
        """
        Phase 36: Check staged files against forbidden patterns.
        Automatically unstage any files that match secret/credential patterns.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode != 0:
                return

            staged_files = result.stdout.strip().split('\n')
            for filepath in staged_files:
                if not filepath:
                    continue
                filename = os.path.basename(filepath).lower()
                for pattern in FORBIDDEN_PATTERNS:
                    # Simple pattern match (supports * prefix/suffix)
                    pat = pattern.lower()
                    match = False
                    if pat.startswith('*') and pat.endswith('*'):
                        match = pat[1:-1] in filename
                    elif pat.startswith('*'):
                        match = filename.endswith(pat[1:])
                    elif pat.endswith('*'):
                        match = filename.startswith(pat[:-1])
                    else:
                        match = filename == pat

                    if match:
                        logger.warning(f"[GIT] 🚫 Unstaging forbidden file: {filepath} (matched {pattern})")
                        subprocess.run(
                            ["git", "reset", "HEAD", "--", filepath],
                            cwd=self.repo_path,
                            capture_output=True,
                            timeout=10
                        )
                        break

        except Exception as e:
            logger.error(f"[GIT] Failed to check staged files: {e}")

    def _get_current_commit(self) -> str:
        """Get the current HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None


# Convenience function
def create_safety_snapshot(bill_id: str) -> str:
    """Quick helper to create a snapshot before changes."""
    return GitSafety().create_snapshot(bill_id)


def rollback_change(snapshot_id: str) -> bool:
    """Quick helper to rollback to a snapshot."""
    return GitSafety().rollback_to_snapshot(snapshot_id)


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    git = GitSafety()
    if git.verify_repo():
        print("✅ Git repository verified")
        
        commits = git.get_recent_commits(5)
        print(f"\nRecent commits:")
        for c in commits:
            print(f"  {c['hash'][:8]}: {c['message']}")
    else:
        print("❌ Not a git repository")
