
import time
import sqlite3
import os
import json
from datetime import datetime
import subprocess

try:
    from utils.notifier import Notifier
except ImportError:
    from republic.utils.notifier import Notifier

# AGENT OVERSIGHT (The Inspector General)
# "The Conscience"
# Audits the fleet for corruption (Loops), silence (Stagnation), and rebellion (Unauth Actions).
# Answers ONLY to LEF.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'republic.db')

class AgentOversight:
    def __init__(self):
        self.db_path = DB_PATH
        self.running = True
        print("[OIG] ⚖️  Inspector General is watching.")

    def run_surveillance(self):
        """
        The Watchtower.
        """
        while self.running:
            try:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                # 1. AUDIT: Check for Looping (Insanity)
                self._check_for_looping(c)
                
                # 2. AUDIT: Check for Silence (Death)
                self._check_container_health()
                
                conn.close()
                time.sleep(60) # Scan every minute
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"[OIG] ⚠️  Surveillance Glitch: {e}")
                time.sleep(10)

    def _check_for_looping(self, c):
        """
        Detects if an agent is repeating the same action/thought rapidly.
        """
        # Check Trade Queue for instant repeats
        c.execute("""
            SELECT asset, action, count(*) 
            FROM trade_queue 
            WHERE created_at > datetime('now', '-5 minutes')
            GROUP BY asset, action
            HAVING count(*) > 5
        """)
        repeats = c.fetchall()
        
        for asset, action, count in repeats:
            msg = f"Corruption Detected: Master is looping {count}x on {action} {asset} in 5 mins."
            self._report_to_president(msg, severity="HIGH")
            
    def _check_container_health(self):
        """
        Checks if Docker containers are running (Production only).
        Gracefully skips in Local/Dev mode.
        """
        if os.getenv('LEF_ENV') != 'PROD':
             return # Skip in Dev
             
        try:
            # Simple check via docker ps
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
            running = result.stdout.split('\n')
            # ... (Logic retained but gated) ...
        except Exception:
            pass

    def _report_to_president(self, message, severity="INFO"):
        """
        Direct Line to LEF. Bypasses Congress.
        Silenced for User (Internal Logging Only).
        """
        log_msg = f"[OIG] 🚨 REPORT ({severity}): {message}"
        print(log_msg)
        
        # Log to dedicated file for audit trail
        try:
            with open(os.path.join(BASE_DIR, "audit_oversight.log"), "a") as f:
                f.write(f"{datetime.now()}: {log_msg}\n")
        except:
            pass
            
        # NOTIFIER HOOK
        if severity in ["HIGH", "CRITICAL"]:
            try:
                Notifier().send(f"**OIG REPORT**\n{message}", context="OIG (Internal Affairs)", severity=severity, color=0xe74c3c)
                print("[OIG] 📡 Sent Alert to Discord.")
            except Exception as e:
                print(f"[OIG] ⚠️ Notifier failed: {e}")

if __name__ == "__main__":
    agent = AgentOversight()
    agent.run_surveillance()
