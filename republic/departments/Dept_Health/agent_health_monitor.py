"""
AgentHealthMonitor (The Surgeon General)
Department: Dept_Health
Role: Monitoring System Integrity, Neural Pathways (Redis), and Component Liveness.
"""
import time
import logging
import psutil
import os
import sys
import sqlite3
import json
import redis
import subprocess
from datetime import datetime, timedelta

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


# Path Setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
TOOLS_DIR = os.path.join(BASE_DIR, 'republic', 'tools')

# Intent Listener for Motor Cortex integration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object

class AgentHealthMonitor(IntentListenerMixin):
    def __init__(self):
        super().__init__()
        logging.info("[HEALTH] 🏥 Surgeon General Online. Diagnostic Systems Initializing...")
        self.db_path = DB_PATH
        self.r = None

        # Brain Silent threshold-based alerting (Phase 5.5)
        # Only alert at specific thresholds, not every minute
        self._brain_silent_thresholds = [120, 360, 1440]  # 2h, 6h, 24h in minutes
        self._brain_silent_alerted = set()  # Track which thresholds have been alerted
        self._last_daily_alert = None  # For daily reminders after 24h

        # Scheduled Audits (Phase 20 Enhancement)
        self.last_honesty_audit = None
        self.last_feature_audit = None
        self.audit_schedule = {
            'honesty': {'frequency_hours': 24, 'preferred_hour': 3},      # Daily at 3am
            'feature': {'frequency_hours': 168, 'preferred_hour': 3}      # Weekly (Sunday 3am)
        }
        
        # Connect to Redis - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
            if self.r:
                logging.info("[HEALTH] 🟢 Neural Network (Redis) Connected.")
        except ImportError:
            # Fallback to direct connection
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
                logging.info("[HEALTH] 🟢 Neural Network (Redis) Connected.")
            except (redis.RedisError, ConnectionError):
                self.r = None
                logging.error("[HEALTH] 🔴 CRITICAL: Neural Network (Redis) Disconnected.")
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_health_monitor')
        self.start_listening()

    def _check_brain_silent(self, minutes_since: float, report: list, current_status: str) -> str:
        """
        Threshold-based Brain Silent alerting (Phase 5.5).

        Instead of alerting every 60 seconds, only alert at:
        - 2 hours (120 min) — INFO level
        - 6 hours (360 min) — WARNING level
        - 24 hours (1440 min) — WARNING level
        - After 24 hours — one daily reminder

        Returns the updated status string.
        """
        if minutes_since <= self._brain_silent_thresholds[0]:
            # Under 2 hours — reset alert tracking, brain is considered active enough
            self._brain_silent_alerted.clear()
            self._last_daily_alert = None
            return current_status

        # Check each threshold
        for threshold in self._brain_silent_thresholds:
            if minutes_since >= threshold and threshold not in self._brain_silent_alerted:
                self._brain_silent_alerted.add(threshold)
                hours = threshold // 60
                if threshold <= 120:
                    logging.info(f"[HEALTH] Brain Silent ({hours}h). No monologue in {int(minutes_since)}m.")
                else:
                    logging.warning(f"[HEALTH] Brain Silent ({hours}h+). No monologue in {int(minutes_since)}m.")
                    report.append(f"Brain Silent ({int(minutes_since)}m).")
                    current_status = "COMA"

        # After 24 hours: one daily reminder
        if minutes_since >= 1440:
            now = datetime.now()
            if self._last_daily_alert is None or (now - self._last_daily_alert).total_seconds() > 86400:
                self._last_daily_alert = now
                days = int(minutes_since // 1440)
                logging.warning(f"[HEALTH] ⚠️ Brain Silent ({days}d). Daily reminder.")
                report.append(f"Brain Silent ({days}d).")
                current_status = "COMA"

        return current_status

    def handle_intent(self, intent_data):
        """
        Process CHECK_HEALTH intents from Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_id = intent_data.get('intent_id')
        
        logging.info(f"[HEALTH] 🏥 Received intent: {intent_type}")
        
        if intent_type == 'CHECK_HEALTH':
            # Run health check
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            
            status = 'HEALTHY'
            issues = []
            
            if cpu > 85: 
                issues.append(f'High CPU: {cpu}%')
                status = 'STRESSED'
            if ram > 85:
                issues.append(f'High RAM: {ram}%')
                status = 'STRESSED'
            if not self.r:
                issues.append('Redis offline')
                status = 'DEGRADED'
            
            health_report = {
                'status': status,
                'cpu': cpu,
                'ram': ram,
                'issues': issues,
                'redis': self.r is not None
            }
            
            self.send_feedback(intent_id, 'COMPLETE', 
                f"System {status}: CPU {cpu}%, RAM {ram}%", 
                health_report)
            
            return {'status': 'success', 'health': health_report}
        
        return {'status': 'unknown_intent', 'type': intent_type}

    def run(self):
        """
        Main Diagnostic Loop.
        Runs every 60 seconds to verifying system integrity.
        """
        while True:
            try:
                report = []
                status = "HEALTHY"
                
                # 1. Hardware Vitals
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                if cpu > 85 or ram > 85:
                    report.append(f"High Load (CPU {cpu}%/RAM {ram}%)")
                    status = "STRESSED"

                # 2. Neural Pathways (Price Feeds)
                if self.r:
                    # Check for generic ticker to ensure updates are flowing
                    # We check 'price:BTC' or 'price:AVAX' as bellwethers
                    try:
                        price = self.r.get("price:AVAX")
                        if not price:
                            report.append("CRITICAL: Price Feeds Missing (Redis empty).")
                            status = "BLIND"
                        else:
                            pass # Feed is active
                    except redis.RedisError:
                        report.append("Redis Error")
                else:
                    report.append("Redis Offline")
                    status = "SEVERED"

                # 3. Wealth Strategy File
                config_path = os.path.join(BASE_DIR, 'config', 'wealth_strategy.json')
                if not os.path.exists(config_path):
                    report.append("Wealth Strategy Config Missing.")
                    status = "CONFUSED"

                # 4. Database Integrity & Consciousness
                conn = None
                pool = None
                try:
                    # Use pool if available
                    try:
                        from db.db_pool import get_pool
                        pool = get_pool()
                        conn = pool.get(timeout=5)
                    except ImportError:
                        pool = None
                        # Fall back to context manager pattern (will be closed in finally)
                        with db_connection(self.db_path) as _conn:
                            c = _conn.cursor()
                            # Check recent thoughts (Consciousness Liveness)
                            c.execute("SELECT timestamp FROM lef_monologue ORDER BY id DESC LIMIT 1")
                            row = c.fetchone()
                            if row and row[0]:
                                ts_val = row[0]
                                if isinstance(ts_val, (int, float)):
                                    last_thought_time = datetime.fromtimestamp(ts_val)
                                else:
                                    try:
                                        last_thought_time = datetime.fromisoformat(str(ts_val))
                                    except (ValueError, TypeError):
                                        last_thought_time = datetime.now()
                                minutes_since = (datetime.now() - last_thought_time).total_seconds() / 60
                                status = self._check_brain_silent(minutes_since, report, status)
                        # Skip the pool-based logic since we used context manager
                        conn = None

                    if conn:
                        c = conn.cursor()
                        # Check recent thoughts (Consciousness Liveness)
                        c.execute("SELECT timestamp FROM lef_monologue ORDER BY id DESC LIMIT 1")
                        row = c.fetchone()
                        if row and row[0]:
                            ts_val = row[0]
                            if isinstance(ts_val, (int, float)):
                                last_thought_time = datetime.fromtimestamp(ts_val)
                            else:
                                try:
                                    last_thought_time = datetime.fromisoformat(str(ts_val))
                                except (ValueError, TypeError):
                                    last_thought_time = datetime.now()
                            minutes_since = (datetime.now() - last_thought_time).total_seconds() / 60
                            status = self._check_brain_silent(minutes_since, report, status)
                    
                except Exception as e:
                    report.append(f"DB Access Error: {e}")
                    status = "CORRUPTED"
                finally:
                    if conn and pool:
                        pool.release(conn)
                    elif conn:
                        conn.close()

                # 5. Hippocampus Health (Memory System)
                try:
                    from system.hippocampus_health import get_hippocampus_health
                    hipp_health = get_hippocampus_health()
                    hipp_report = hipp_health.get_health_report()
                    
                    if hipp_report["overall_score"] < 0.5:
                        report.append(f"Hippocampus: {hipp_report['status']}")
                        if status == "HEALTHY":
                            status = "MEMORY_DEGRADED"
                    
                    # Log detailed health every 10 cycles
                    if hasattr(self, '_cycle_count'):
                        self._cycle_count += 1
                    else:
                        self._cycle_count = 0
                    
                    if self._cycle_count % 10 == 0:
                        logging.info(hipp_health.get_summary())
                        
                except Exception as e:
                    logging.debug(f"[HEALTH] Hippocampus health check skipped: {e}")

                # REPORTING
                if status == "HEALTHY":
                    print(f"[HEALTH] ✅ SYSTEM NORMAL (CPU {cpu}% | RAM {ram}% | Brain Active | Eyes Open)")
                else:
                    print(f"[HEALTH] ⚠️ SYSTEM ALERT ({status}): {', '.join(report)}")
                
                # SCHEDULED AUDITS (Phase 20)
                self._check_scheduled_audits()
                    
            except Exception as e:
                logging.error(f"[HEALTH] Diagnostic Failure: {e}")
            
            time.sleep(60) # Scan every minute
    
    def _check_scheduled_audits(self):
        """
        Check if any scheduled audits are due and run them.
        Audits run at low-traffic hours (3am by default).
        """
        now = datetime.now()
        current_hour = now.hour
        
        # Only run audits during preferred hour (3am default) to minimize impact
        if current_hour != self.audit_schedule['honesty']['preferred_hour']:
            return
        
        # Check Honesty/Structural Audit (Daily)
        if self.last_honesty_audit is None or \
           (now - self.last_honesty_audit).total_seconds() > self.audit_schedule['honesty']['frequency_hours'] * 3600:
            logging.info("[HEALTH] ⏰ Scheduled Honesty Audit triggered...")
            try:
                self.run_honesty_audit()
                self._run_structural_audit()
                self.last_honesty_audit = now
                logging.info("[HEALTH] ✅ Scheduled Honesty Audit complete.")
            except Exception as e:
                logging.error(f"[HEALTH] Scheduled Honesty Audit failed: {e}")
        
        # Check Feature Completeness Audit (Weekly - Sunday)
        if now.weekday() == 6:  # Sunday
            if self.last_feature_audit is None or \
               (now - self.last_feature_audit).total_seconds() > self.audit_schedule['feature']['frequency_hours'] * 3600:
                logging.info("[HEALTH] ⏰ Scheduled Feature Completeness Audit triggered...")
                try:
                    self._run_feature_audit()
                    self.last_feature_audit = now
                    logging.info("[HEALTH] ✅ Scheduled Feature Audit complete.")
                except Exception as e:
                    logging.error(f"[HEALTH] Scheduled Feature Audit failed: {e}")
    
    def _run_structural_audit(self):
        """Run the Structural Integrity Audit tool."""
        audit_script = os.path.join(TOOLS_DIR, 'structural_integrity_audit.py')
        if os.path.exists(audit_script):
            result = subprocess.run(['python3', audit_script], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("[HEALTH] 🏗️ Structural Integrity Audit completed successfully.")
            else:
                logging.warning(f"[HEALTH] Structural Audit returned code {result.returncode}")
        else:
            logging.warning("[HEALTH] Structural audit script not found.")
    
    def _run_feature_audit(self):
        """Run the Feature Completeness Audit tool."""
        audit_script = os.path.join(TOOLS_DIR, 'feature_completeness_audit.py')
        if os.path.exists(audit_script):
            result = subprocess.run(['python3', audit_script], capture_output=True, text=True)
            if result.returncode == 0:
                logging.info("[HEALTH] 📊 Feature Completeness Audit completed successfully.")
            else:
                logging.warning(f"[HEALTH] Feature Audit returned code {result.returncode}")
        else:
            logging.warning("[HEALTH] Feature audit script not found.")

    def run_honesty_audit(self):
        """
        Honesty Audit Protocol.
        Scans all agents for placeholder/partial implementations.
        Outputs report to The_Bridge/Logs/HonestyAudit_<date>.md
        
        Should be called periodically (weekly) or manually.
        """
        from datetime import datetime
        
        logging.info("[HEALTH] 🔍 HONESTY AUDIT: Scanning all agents...")
        
        findings = {
            'PLACEHOLDER': [],
            'PARTIAL': [],
            'NOT_IMPLEMENTED': [],
            'SIMULATED': [],
            'TODO': [],
            'HARDCODED': []
        }
        
        # Scan all agent files using throttled scanner
        agent_dirs = [
            os.path.join(BASE_DIR, 'republic', 'departments'),
        ]
        
        # Use throttled scanner to prevent file handle exhaustion
        try:
            from system.directory_scanner import walk_dir_throttled
        except ImportError:
            walk_dir_throttled = None
        
        for agent_dir in agent_dirs:
            if walk_dir_throttled:
                dir_walker = walk_dir_throttled(agent_dir, filter_ext='.py')
            else:
                dir_walker = os.walk(agent_dir)
            
            for root, dirs, files in dir_walker:
                for file in files:
                    if file.endswith('.py') and file.startswith('agent_'):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                lines = content.split('\n')
                                
                                for i, line in enumerate(lines):
                                    line_lower = line.lower()
                                    line_num = i + 1
                                    
                                    if '[placeholder]' in line_lower:
                                        findings['PLACEHOLDER'].append({
                                            'file': file, 'line': line_num, 
                                            'content': line.strip()[:80]
                                        })
                                    elif '[partial]' in line_lower:
                                        findings['PARTIAL'].append({
                                            'file': file, 'line': line_num,
                                            'content': line.strip()[:80]
                                        })
                                    elif '[not implemented]' in line_lower or 'not implemented' in line_lower:
                                        findings['NOT_IMPLEMENTED'].append({
                                            'file': file, 'line': line_num,
                                            'content': line.strip()[:80]
                                        })
                                    elif '[simulated]' in line_lower:
                                        findings['SIMULATED'].append({
                                            'file': file, 'line': line_num,
                                            'content': line.strip()[:80]
                                        })
                                    elif 'todo' in line_lower and '#' in line:
                                        findings['TODO'].append({
                                            'file': file, 'line': line_num,
                                            'content': line.strip()[:80]
                                        })
                                    elif 'hardcoded' in line_lower or 'hardcode' in line_lower:
                                        findings['HARDCODED'].append({
                                            'file': file, 'line': line_num,
                                            'content': line.strip()[:80]
                                        })
                        except Exception as e:
                            logging.error(f"[HEALTH] Audit scan error on {file}: {e}")
        
        # Generate Report
        total_issues = sum(len(v) for v in findings.values())
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        
        report = f"""# Honesty Audit Report
**Generated:** {datetime.now().isoformat()}
**Total Issues Found:** {total_issues}

## Summary
| Category | Count |
|----------|-------|
| PLACEHOLDER | {len(findings['PLACEHOLDER'])} |
| PARTIAL | {len(findings['PARTIAL'])} |
| NOT_IMPLEMENTED | {len(findings['NOT_IMPLEMENTED'])} |
| SIMULATED | {len(findings['SIMULATED'])} |
| TODO | {len(findings['TODO'])} |
| HARDCODED | {len(findings['HARDCODED'])} |

---

"""
        for category, items in findings.items():
            if items:
                report += f"## {category}\n\n"
                for item in items:
                    report += f"- **{item['file']}:{item['line']}** - `{item['content']}`\n"
                report += "\n"
        
        # Calculate Honesty Score
        honesty_score = max(0, 100 - (total_issues * 2))  # Each issue costs 2 points
        report += f"""---

## Honesty Score: {honesty_score}%

**Interpretation:**
- 90-100%: Fully Honest - All code does what it claims
- 70-89%: Mostly Honest - Minor placeholders remain
- 50-69%: Partial Honesty - Significant gaps exist
- <50%: Dishonest - More claims than functionality
"""
        
        # Save to The_Bridge/Logs (at project root, not in republic/)
        project_root = os.path.dirname(BASE_DIR)
        logs_dir = os.path.join(project_root, 'The_Bridge', 'Logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        report_path = os.path.join(logs_dir, f'HonestyAudit_{timestamp}.md')
        try:
            with open(report_path, 'w') as f:
                f.write(report)
            logging.info(f"[HEALTH] 📋 Honesty Audit saved to: {report_path}")
            print(f"[HEALTH] 📋 HONESTY AUDIT COMPLETE: Score {honesty_score}% | {total_issues} issues | {report_path}")
        except Exception as e:
            logging.error(f"[HEALTH] Failed to save audit report: {e}")
        
        return {'score': honesty_score, 'issues': total_issues, 'report_path': report_path}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AgentHealthMonitor()
    agent.run()
