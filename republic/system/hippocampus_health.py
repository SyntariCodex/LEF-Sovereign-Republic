"""
Hippocampus Health Metrics
Monitors Claude's memory system health and provides diagnostics.

Integrated with:
- ClaudeContextManager (Hippocampus)
- AgentHealthMonitor (Dept_Health)
- AgentLibrarian (archival)
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Path Discovery
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
# Memory file is in The_Bridge (parent of republic), matching ClaudeContextManager
MEMORY_PATH = BASE_DIR.parent / 'The_Bridge' / 'claude_memory.json'

class HippocampusHealth:
    """
    Health monitoring for LEF's Hippocampus (Claude memory system).
    
    Monitors:
    - Memory file size and age
    - Journal entry count
    - Insight accumulation
    - Compressed wisdom stats
    - Meta-reflection frequency
    """
    
    def __init__(self, db_path: str = None, memory_path: str = None):
        self.db_path = db_path or DB_PATH
        self.memory_path = Path(memory_path) if memory_path else MEMORY_PATH
        self.logger = logging.getLogger("HIPPOCAMPUS_HEALTH")

    def get_health_report(self) -> dict:
        """
        Generate comprehensive health report for the Hippocampus.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "memory_file": self._check_memory_file(),
            "journal_health": self._check_journal_health(),
            "wisdom_health": self._check_wisdom_health(),
            "reflection_health": self._check_reflection_health(),
            "overall_score": 0.0
        }
        
        # Calculate overall score
        scores = []
        for key in ["memory_file", "journal_health", "wisdom_health", "reflection_health"]:
            if "score" in report[key]:
                scores.append(report[key]["score"])
        
        report["overall_score"] = sum(scores) / len(scores) if scores else 0.0
        report["status"] = self._get_status(report["overall_score"])
        
        return report

    def _check_memory_file(self) -> dict:
        """Check claude_memory.json health."""
        result = {
            "exists": False,
            "size_kb": 0,
            "age_hours": None,
            "score": 0.0,
            "issues": []
        }
        
        if not self.memory_path.exists():
            result["issues"].append("Memory file not found")
            return result
        
        result["exists"] = True
        
        # File size
        size_bytes = self.memory_path.stat().st_size
        result["size_kb"] = round(size_bytes / 1024, 2)
        
        # File age
        mtime = self.memory_path.stat().st_mtime
        age_hours = (datetime.now().timestamp() - mtime) / 3600
        result["age_hours"] = round(age_hours, 1)
        
        # Score calculation
        score = 100.0
        
        # Size checks
        if result["size_kb"] > 500:
            score -= 20
            result["issues"].append("Memory file large (>500KB) - consider pruning")
        elif result["size_kb"] < 1:
            score -= 10
            result["issues"].append("Memory file very small - may be empty")
        
        # Age checks (if not updated in 24h, concern)
        if age_hours > 24:
            score -= 10
            result["issues"].append("Memory not updated in >24 hours")
        
        result["score"] = max(0, score) / 100
        return result

    def _check_journal_health(self) -> dict:
        """Check reasoning journal health."""
        result = {
            "entry_count": 0,
            "oldest_entry": None,
            "newest_entry": None,
            "score": 0.0,
            "issues": []
        }
        
        if not self.memory_path.exists():
            result["issues"].append("Memory file not found")
            return result
        
        try:
            with open(self.memory_path, 'r') as f:
                memory = json.load(f)
            
            journal = memory.get('reasoning_journal', {})
            entries = journal.get('entries', [])
            result["entry_count"] = len(entries)
            
            if entries:
                result["oldest_entry"] = entries[0].get('timestamp', 'unknown')
                result["newest_entry"] = entries[-1].get('timestamp', 'unknown')
            
            # Score calculation
            score = 100.0
            
            if len(entries) == 0:
                score -= 30
                result["issues"].append("No journal entries - reasoning not being captured")
            elif len(entries) > 100:
                score -= 10
                result["issues"].append("Journal has >100 entries - needs pruning")
            
            result["score"] = max(0, score) / 100
            
        except Exception as e:
            result["issues"].append(f"Error reading journal: {e}")
            result["score"] = 0.0
        
        return result

    def _check_wisdom_health(self) -> dict:
        """Check compressed wisdom table health."""
        result = {
            "wisdom_count": 0,
            "categories": [],
            "avg_confidence": 0.0,
            "score": 0.0,
            "issues": []
        }
        
        if not os.path.exists(self.db_path):
            result["issues"].append("Database not found")
            return result
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compressed_wisdom'")
            if not c.fetchone():
                result["issues"].append("compressed_wisdom table not found")
                conn.close()
                return result
            
            # Fetch all wisdom entries
            c.execute("""
                SELECT wisdom_type, summary, source_type, confidence, created_at
                FROM compressed_wisdom
                ORDER BY created_at
            """)
            rows = c.fetchall()
            conn.close()
            
            result["wisdom_count"] = len(rows)
            
            if rows:
                # Get distinct types
                result["categories"] = list(set(row[0] for row in rows))
                
                # Get average confidence
                confidences = [row[3] for row in rows if row[3] is not None]
                result["avg_confidence"] = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
            
            # Score calculation
            score = 100.0
            
            if result["wisdom_count"] == 0:
                score -= 20
                result["issues"].append("No compressed wisdom yet")
            
            if result["avg_confidence"] < 0.5 and result["wisdom_count"] > 0:
                score -= 10
                result["issues"].append("Low average confidence in wisdom")
            
            result["score"] = max(0, score) / 100
            
        except Exception as e:
            result["issues"].append(f"Error checking wisdom: {e}")
            result["score"] = 0.0
        
        return result

    def _check_reflection_health(self) -> dict:
        """Check meta-reflection frequency."""
        result = {
            "last_reflection": None,
            "reflection_count": 0,
            "hours_since_last": None,
            "score": 0.0,
            "issues": []
        }
        
        if not self.memory_path.exists():
            result["issues"].append("Memory file not found")
            return result
        
        try:
            with open(self.memory_path, 'r') as f:
                memory = json.load(f)
            
            meta = memory.get('meta_reflection', {})
            last = meta.get('last_reflection')
            result["last_reflection"] = last
            
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    hours = (datetime.now() - last_dt).total_seconds() / 3600
                    result["hours_since_last"] = round(hours, 1)
                except ValueError:
                    pass
            
            # Count patterns found
            patterns = meta.get('patterns_found', [])
            result["reflection_count"] = len(patterns)
            
            # Score calculation
            score = 100.0
            
            if not last:
                score -= 20
                result["issues"].append("No meta-reflection recorded")
            elif result["hours_since_last"] and result["hours_since_last"] > 168:  # 1 week
                score -= 15
                result["issues"].append("No reflection in over a week")
            
            result["score"] = max(0, score) / 100
            
        except Exception as e:
            result["issues"].append(f"Error checking reflection: {e}")
            result["score"] = 0.0
        
        return result

    def _get_status(self, score: float) -> str:
        """Get status label from score."""
        if score >= 0.9:
            return "EXCELLENT"
        elif score >= 0.7:
            return "HEALTHY"
        elif score >= 0.5:
            return "NEEDS_ATTENTION"
        else:
            return "CRITICAL"

    def get_summary(self) -> str:
        """Get human-readable summary for logging."""
        report = self.get_health_report()
        
        lines = [
            f"🧠 Hippocampus Health: {report['status']} ({report['overall_score']*100:.0f}%)",
            f"   Memory: {report['memory_file']['size_kb']}KB",
            f"   Journal: {report['journal_health']['entry_count']} entries",
            f"   Wisdom: {report['wisdom_health']['wisdom_count']} compressed",
        ]
        
        # Add issues if any
        all_issues = []
        for key in ["memory_file", "journal_health", "wisdom_health", "reflection_health"]:
            all_issues.extend(report[key].get("issues", []))
        
        if all_issues:
            lines.append(f"   ⚠️ Issues: {', '.join(all_issues[:3])}")
        
        return "\n".join(lines)


def get_hippocampus_health() -> HippocampusHealth:
    """Get health monitor instance."""
    return HippocampusHealth()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    health = HippocampusHealth()
    print(health.get_summary())
    print("\nFull Report:")
    import pprint
    pprint.pprint(health.get_health_report())
