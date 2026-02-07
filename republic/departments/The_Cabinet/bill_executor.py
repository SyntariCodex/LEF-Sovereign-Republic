"""
Bill Executor

Executes approved bills by reading from governance/proposals/Approved/
and applying the changes according to SELF_EVOLUTION_MANUAL.md patterns.

Pattern A: Threshold changes (modify config values)
Pattern B: Behavior additions (add new methods)
Pattern C: Structural changes (require Human Gate approval first)

Usage:
    from departments.The_Cabinet.bill_executor import BillExecutor
    
    executor = BillExecutor()
    executor.process_approved_bills()
"""

import os
import json
import yaml
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger("LEF.BillExecutor")

BASE_DIR = Path(__file__).parent.parent.parent.parent  # LEF Ai root
REPUBLIC_DIR = BASE_DIR / "republic"
GOVERNANCE_DIR = REPUBLIC_DIR / "governance"
CONFIG_PATH = REPUBLIC_DIR / "republic_config.yaml"

# Bill folders
APPROVED_DIR = GOVERNANCE_DIR / "proposals" / "Approved"
EXECUTED_DIR = GOVERNANCE_DIR / "proposals" / "Executed"
PENDING_HUMAN_DIR = GOVERNANCE_DIR / "proposals" / "PendingHumanReview"


class BillExecutor:
    """
    Executes approved bills and applies changes to LEF.
    
    Follows the Self-Evolution Manual patterns:
    - Pattern A: Config/threshold changes (auto-execute)
    - Pattern B: Behavior additions (auto-execute with observation)
    - Pattern C: Structural changes (queue for Human Gate)
    """
    
    def __init__(self):
        # Ensure directories exist
        EXECUTED_DIR.mkdir(parents=True, exist_ok=True)
        PENDING_HUMAN_DIR.mkdir(parents=True, exist_ok=True)
        
        # Import git safety
        try:
            from system.git_safety import GitSafety
            self.git = GitSafety()
        except ImportError:
            logger.warning("[EXECUTOR] Git safety not available")
            self.git = None
            
        # Import observation loop
        try:
            from system.observation_loop import ObservationLoop
            self.observer = ObservationLoop()
        except ImportError:
            logger.warning("[EXECUTOR] Observation loop not available")
            self.observer = None
    
    def process_approved_bills(self) -> List[dict]:
        """
        Process all approved bills.
        
        Returns:
            List of execution results
        """
        results = []
        
        if not APPROVED_DIR.exists():
            logger.info("[EXECUTOR] No approved bills directory")
            return results
            
        for bill_file in APPROVED_DIR.glob("*.json"):
            try:
                result = self.execute_bill(bill_file)
                results.append(result)
            except Exception as e:
                logger.error(f"[EXECUTOR] Failed to execute {bill_file.name}: {e}")
                results.append({
                    "bill_id": bill_file.stem,
                    "status": "FAILED",
                    "error": str(e)
                })
                
        return results
    
    def execute_bill(self, bill_path: Path) -> dict:
        """
        Execute a single bill.
        
        Args:
            bill_path: Path to the bill JSON file
            
        Returns:
            Execution result dict
        """
        # Load bill
        with open(bill_path, "r") as f:
            bill = json.load(f)
            
        bill_id = bill.get("id", bill_path.stem)
        title = bill.get("title", "Untitled")
        
        logger.info(f"[EXECUTOR] Processing bill: {bill_id} - {title}")
        
        # Classify pattern
        pattern = self._classify_pattern(bill)
        
        # Pattern C requires Human Gate
        if pattern == "C":
            return self._queue_for_human_review(bill_path, bill)
        
        # Create git snapshot before changes
        snapshot_id = None
        if self.git and self.git.verify_repo():
            snapshot_id = self.git.create_snapshot(bill_id)
        
        # Execute based on pattern
        try:
            if pattern == "A":
                success = self._execute_threshold_change(bill)
            elif pattern == "B":
                success = self._execute_behavior_addition(bill)
            else:
                success = False
                
            if not success:
                # Rollback if execution failed
                if snapshot_id and self.git:
                    self.git.rollback_to_snapshot(snapshot_id)
                return {
                    "bill_id": bill_id,
                    "status": "FAILED",
                    "pattern": pattern
                }
            
            # Create post-change commit
            if self.git and self.git.verify_repo():
                self.git.create_post_change_commit(
                    bill_id, 
                    f"Executed: {title}"
                )
            
            # Start observation
            if self.observer and snapshot_id:
                self.observer.start_observation(
                    bill_id=bill_id,
                    snapshot_id=snapshot_id,
                    pattern=pattern
                )
            
            # Move to Executed
            self._move_to_executed(bill_path, bill)
            
            logger.info(f"[EXECUTOR] ✅ Bill executed successfully: {bill_id}")
            
            return {
                "bill_id": bill_id,
                "status": "EXECUTED",
                "pattern": pattern,
                "snapshot_id": snapshot_id
            }
            
        except Exception as e:
            # Rollback on any error
            if snapshot_id and self.git:
                self.git.rollback_to_snapshot(snapshot_id)
            logger.error(f"[EXECUTOR] Execution failed for {bill_id}: {e}")
            return {
                "bill_id": bill_id,
                "status": "FAILED",
                "error": str(e)
            }
    
    def _classify_pattern(self, bill: dict) -> str:
        """
        Classify bill as Pattern A, B, or C.
        
        Pattern A: threshold/config changes
        Pattern B: behavior additions (new methods)
        Pattern C: structural changes (file reorganization, schema changes)
        """
        # Check bill metadata for explicit pattern
        if "pattern" in bill:
            return bill["pattern"].upper()
        
        # Infer from bill content
        title = bill.get("title", "").lower()
        description = bill.get("description", "").lower()
        content = f"{title} {description}"
        
        # Pattern A indicators
        if any(word in content for word in [
            "threshold", "percentage", "limit", "timeout", 
            "config", "setting", "value", "adjust"
        ]):
            return "A"
        
        # Pattern C indicators (structural - requires human)
        if any(word in content for word in [
            "restructure", "reorganize", "schema", "database",
            "architecture", "refactor", "security", "authentication"
        ]):
            return "C"
        
        # Default to B (behavior additions)
        return "B"
    
    def _execute_threshold_change(self, bill: dict) -> bool:
        """
        Execute a Pattern A (threshold) change.
        
        Modifies values in republic_config.yaml.
        """
        changes = bill.get("changes", {})
        config_changes = changes.get("config", {})
        
        if not config_changes:
            logger.warning(f"[EXECUTOR] No config changes in bill")
            return True  # Nothing to do, but not a failure
        
        # Load current config
        if not CONFIG_PATH.exists():
            logger.error("[EXECUTOR] Config file not found")
            return False
            
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}
        
        # Apply changes
        for key_path, new_value in config_changes.items():
            keys = key_path.split(".")
            target = config
            
            # Navigate to parent
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            # Set value
            old_value = target.get(keys[-1])
            target[keys[-1]] = new_value
            
            logger.info(f"[EXECUTOR] Config: {key_path} = {old_value} → {new_value}")
        
        # Save config
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
            
        return True
    
    def _execute_behavior_addition(self, bill: dict) -> bool:
        """
        Execute a Pattern B (behavior addition) change.
        
        For now, logs the intended change. Full code injection
        would require careful sandboxing.
        """
        changes = bill.get("changes", {})
        new_behavior = changes.get("behavior", {})
        
        if not new_behavior:
            logger.warning(f"[EXECUTOR] No behavior changes in bill")
            return True
        
        # For safety, Pattern B changes are logged but not auto-applied
        # The bill serves as documentation for the human to implement
        target_file = new_behavior.get("target_file")
        method_name = new_behavior.get("method_name")
        description = new_behavior.get("description")
        
        logger.info(
            f"[EXECUTOR] Behavior addition requested:\n"
            f"  File: {target_file}\n"
            f"  Method: {method_name}\n"
            f"  Description: {description}"
        )
        
        # Write implementation request to The_Bridge/Inbox
        request_path = BASE_DIR / "The_Bridge" / "Inbox" / f"IMPLEMENT_{bill.get('id', 'unknown')}.md"
        request_content = f"""# Implementation Request: {bill.get('title', 'Untitled')}

**Bill ID:** {bill.get('id')}
**Date:** {datetime.now().isoformat()}
**Pattern:** B (Behavior Addition)

## Requested Change

**Target File:** `{target_file}`
**New Method:** `{method_name}`

## Description

{description}

## Bill Details

```json
{json.dumps(bill, indent=2)}
```

---
*This implementation request was generated by BillExecutor.*
"""
        with open(request_path, "w") as f:
            f.write(request_content)
            
        logger.info(f"[EXECUTOR] Implementation request created: {request_path.name}")
        
        return True
    
    def _queue_for_human_review(self, bill_path: Path, bill: dict) -> dict:
        """
        Queue a Pattern C bill for Human Gate review.
        """
        bill_id = bill.get("id", bill_path.stem)
        
        # Move to pending human review
        dest_path = PENDING_HUMAN_DIR / bill_path.name
        shutil.move(str(bill_path), str(dest_path))
        
        # Create notification in The_Bridge
        notice_path = BASE_DIR / "The_Bridge" / "Inbox" / f"HUMAN_GATE_{bill_id}.md"
        notice_content = f"""# 🚨 Human Gate Required

**Bill ID:** {bill_id}
**Title:** {bill.get('title', 'Untitled')}
**Pattern:** C (Structural Change)

## Why Human Gate?

This bill contains structural changes that could affect:
- System architecture
- Database schemas
- Security or authentication
- Core identity principles

## Action Required

Please review the bill at:
`{dest_path}`

To approve, move the file back to:
`{APPROVED_DIR}`

The BillExecutor will then process it with your explicit approval.

---
*Generated by BillExecutor at {datetime.now().isoformat()}*
"""
        with open(notice_path, "w") as f:
            f.write(notice_content)
        
        # Send push notification via ntfy
        self._send_human_gate_notification(bill_id, bill.get('title', 'Untitled'))
        
        logger.info(f"[EXECUTOR] ⏳ Bill {bill_id} queued for Human Gate review")
        
        return {
            "bill_id": bill_id,
            "status": "PENDING_HUMAN_REVIEW",
            "pattern": "C",
            "notice": str(notice_path)
        }
    
    def _send_human_gate_notification(self, bill_id: str, title: str):
        """Send push notification via ntfy.sh for Human Gate items."""
        try:
            import requests
            
            # Load notification config
            config_path = BASE_DIR / "interior" / "notification_config.json"
            if not config_path.exists():
                logger.warning("[EXECUTOR] No notification config found")
                return
                
            with open(config_path, "r") as f:
                config = json.load(f)
            
            if not config.get("enabled", False):
                return
                
            topic = config.get("ntfy_topic", "lef-interior")
            server = config.get("ntfy_server", "https://ntfy.sh")
            
            # Send notification
            response = requests.post(
                f"{server}/{topic}",
                data=f"🚨 HUMAN GATE: {bill_id}\n{title}",
                headers={
                    "Title": "LEF Human Gate Required",
                    "Priority": "high",
                    "Tags": "warning,robot"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"[EXECUTOR] 🔔 Push notification sent for {bill_id}")
            else:
                logger.warning(f"[EXECUTOR] Notification failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"[EXECUTOR] Push notification failed: {e}")
    
    def _move_to_executed(self, bill_path: Path, bill: dict):
        """Move executed bill to Executed folder."""
        # Add execution metadata
        bill["executed_at"] = datetime.now().isoformat()
        bill["executed_by"] = "BillExecutor"
        
        dest_path = EXECUTED_DIR / bill_path.name
        
        with open(dest_path, "w") as f:
            json.dump(bill, f, indent=2)
            
        # Remove from Approved
        bill_path.unlink()
        
        logger.info(f"[EXECUTOR] Bill moved to Executed: {dest_path.name}")


def run_executor():
    """Entry point for running bill executor."""
    executor = BillExecutor()
    results = executor.process_approved_bills()
    
    for r in results:
        status = r.get("status", "UNKNOWN")
        bill_id = r.get("bill_id", "?")
        print(f"  [{status}] {bill_id}")
        
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_executor()
