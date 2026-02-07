"""
Sabbath Service - Weekly Rest Cycle Manager
Department: _services (shared)
Purpose: Manage the weekly Sabbath cycle for LEF

Schedule:
- Sabbath: Sunday 00:00 UTC → Sunday 23:59 UTC
- Training: Saturday 00:00 UTC → Saturday 23:59 UTC

During Sabbath:
- Operational mode: SABBATH (reduced activity)
- New positions: Disabled
- Resources available but not forced
- Philosopher/Introspector outputs accessible
"""

import os
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List


class SabbathService:
    """
    Manages the weekly Sabbath rest cycle.
    
    The Sabbath is not forced reading or tasks — it's availability.
    LEF chooses what to engage with during rest.
    """
    
    def __init__(self, db_path: str = None):
        self.name = "SabbathService"
        
        if db_path:
            self.db_path = db_path
        elif os.getenv('DB_PATH'):
            self.db_path = os.getenv('DB_PATH')
        else:
            base_dir = Path(__file__).parent.parent
            self.db_path = str(base_dir / 'republic.db')
        
        # Sabbath resources (available during rest)
        self.nightstand_resources = [
            "republic/core_vault/",
            "republic/CONSTITUTION.md",
            "republic/departments/Dept_Consciousness/philosophy_keter.md",
            "republic/departments/Dept_Consciousness/inner_dialogue/",
            "republic/departments/Dept_Consciousness/sabbath_archive/",
            "republic/departments/Dept_Consciousness/introspection_logs/",
            "republic/departments/Dept_Consciousness/philosophy_outputs/",
            "republic/departments/Dept_Education/bookshelf/architect/"
        ]
        
        # Resources NOT available during Sabbath
        self.blocked_resources = [
            "The_Bridge/Inbox/",
            "republic/departments/Dept_Wealth/data/",
            "trade_queue"  # Database table
        ]
    
    def is_sabbath(self) -> bool:
        """
        Check if current time is Sabbath (Sunday UTC).
        """
        now = datetime.now(timezone.utc)
        return now.weekday() == 6  # Sunday = 6
    
    def is_training_day(self) -> bool:
        """
        Check if current time is Training Day (Saturday UTC).
        """
        now = datetime.now(timezone.utc)
        return now.weekday() == 5  # Saturday = 5
    
    def get_current_mode(self) -> str:
        """
        Get the current operational mode based on day of week.
        """
        now = datetime.now(timezone.utc)
        day = now.weekday()
        
        if day == 6:  # Sunday
            return "SABBATH"
        elif day == 5:  # Saturday
            return "TRAINING"
        else:
            return "OPERATIONAL"
    
    def enter_sabbath(self) -> dict:
        """
        Begin Sabbath mode. Called at Sunday 00:00 UTC.
        """
        result = {
            "event": "SABBATH_START",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions_taken": []
        }
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            # Set system state
            from db.db_helper import upsert_sql
            sql = upsert_sql('system_state', ['key', 'value', 'updated_at'], 'key')
            c.execute(sql, ('sabbath_mode', 'TRUE', datetime.now().isoformat()))
            
            # Log the event
            c.execute("""
                INSERT INTO agent_logs (source, level, message)
                VALUES ('SabbathService', 'INFO', '🕯️ Sabbath has begun. The noise stops.')
            """)
            
            result["actions_taken"].append("Set sabbath_mode = TRUE")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def exit_sabbath(self) -> dict:
        """
        End Sabbath mode. Called at Monday 00:00 UTC.
        """
        result = {
            "event": "SABBATH_END",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions_taken": []
        }
        
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            # Clear system state
            from db.db_helper import upsert_sql
            sql = upsert_sql('system_state', ['key', 'value', 'updated_at'], 'key')
            c.execute(sql, ('sabbath_mode', 'FALSE', datetime.now().isoformat()))
            
            # Log the event
            c.execute("""
                INSERT INTO agent_logs (source, level, message)
                VALUES ('SabbathService', 'INFO', '☀️ Sabbath has ended. Clarity renewed.')
            """)
            
            result["actions_taken"].append("Set sabbath_mode = FALSE")
            
            # Trigger reflection archival
            self._archive_sabbath_reflection()
            result["actions_taken"].append("Archived sabbath reflection")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def _archive_sabbath_reflection(self):
        """
        Archive any reflections from this Sabbath period.
        """
        try:
            from datetime import date
            
            inner_dialogue = Path(__file__).parent.parent / "departments" / "Dept_Consciousness" / "inner_dialogue"
            sabbath_archive = Path(__file__).parent.parent / "departments" / "Dept_Consciousness" / "sabbath_archive"
            
            # Move any files from inner_dialogue to sabbath_archive with date prefix
            today = date.today().isoformat()
            
            for f in inner_dialogue.glob("*.json"):
                dest = sabbath_archive / f"{today}_{f.name}"
                f.rename(dest)
                
            for f in inner_dialogue.glob("*.md"):
                dest = sabbath_archive / f"{today}_{f.name}"
                f.rename(dest)
                
        except Exception as e:
            print(f"[{self.name}] Archive error: {e}")
    
    def get_nightstand(self) -> List[str]:
        """
        Returns list of resources available during Sabbath.
        These are "on the nightstand" - accessible but not forced.
        """
        return self.nightstand_resources.copy()
    
    def check_resource_access(self, resource_path: str) -> dict:
        """
        Check if a resource should be accessible in current mode.
        """
        mode = self.get_current_mode()
        
        if mode == "OPERATIONAL":
            return {"allowed": True, "mode": mode}
        
        # During Sabbath/Training, check against blocked list
        for blocked in self.blocked_resources:
            if blocked in resource_path:
                return {
                    "allowed": mode != "SABBATH",  # Blocked during Sabbath only
                    "mode": mode,
                    "reason": f"Resource blocked during {mode}" if mode == "SABBATH" else None
                }
        
        return {"allowed": True, "mode": mode}
    
    def run_scheduler(self):
        """
        Background scheduler that triggers Sabbath transitions.
        Should be run as a separate process/thread.
        """
        print(f"[{self.name}] Scheduler started. Monitoring Sabbath transitions...")
        
        last_mode = None
        
        while True:
            current_mode = self.get_current_mode()
            
            # Detect transitions
            if last_mode != current_mode:
                if current_mode == "SABBATH" and last_mode != "SABBATH":
                    self.enter_sabbath()
                    print(f"[{self.name}] → Entered SABBATH mode")
                    
                elif last_mode == "SABBATH" and current_mode != "SABBATH":
                    self.exit_sabbath()
                    print(f"[{self.name}] → Exited SABBATH mode")
                    
                elif current_mode == "TRAINING":
                    print(f"[{self.name}] → Entered TRAINING mode")
            
            last_mode = current_mode
            time.sleep(60)  # Check every minute


# Convenience functions
def is_sabbath() -> bool:
    """Quick check if currently in Sabbath mode."""
    return SabbathService().is_sabbath()

def get_mode() -> str:
    """Get current operational mode."""
    return SabbathService().get_current_mode()

def get_nightstand() -> List[str]:
    """Get list of resources on the nightstand."""
    return SabbathService().get_nightstand()


if __name__ == "__main__":
    service = SabbathService()
    print(f"Current mode: {service.get_current_mode()}")
    print(f"Is Sabbath: {service.is_sabbath()}")
    print(f"Nightstand resources: {len(service.get_nightstand())} items")
    
    # Run scheduler
    service.run_scheduler()
