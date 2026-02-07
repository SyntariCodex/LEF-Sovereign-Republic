#!/usr/bin/env python3
import os
import time
import subprocess
import sys
from datetime import datetime

# CONFIGURATION
# Watch everything in root except these:
IGNORE_DIRS = {'.git', '__pycache__', 'venv', '.idea', '.vscode', 'logs', 'The_Bridge'} 
EXTENSIONS = {'.py', '.sh', '.html', '.json', '.md'} 
POLL_INTERVAL = 3 # Seconds
GIT_CHECK_INTERVAL = 30 # Check github every 30s

class Guardian:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.last_mtimes = {}
        self.last_git_check = 0
        self.running = True
        print(f"[GUARDIAN] 🛡️  System Active in: {root_dir}")
        print(f"[GUARDIAN] 📡 Remote Watch: Checking GitHub every {GIT_CHECK_INTERVAL}s")
        print(f"[GUARDIAN] 📂 Local Watch: {', '.join(EXTENSIONS)} files")
        
    def check_remote_changes(self):
        """
        Checks if the remote branch (GitHub) is ahead of local.
        """
        if time.time() - self.last_git_check < GIT_CHECK_INTERVAL:
            return False
            
        self.last_git_check = time.time()
        
        try:
            # 1. Fetch remote stats (silent)
            subprocess.run(["git", "fetch"], cwd=self.root_dir, capture_output=True)
            
            # 2. Check if we are behind
            # git rev-list --count HEAD..origin/main
            # Assuming 'main' is the branch. Can standardize to 'HEAD..@{u}' for upstream.
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..@{u}"],
                cwd=self.root_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                count = int(result.stdout.strip())
                if count > 0:
                    print(f"\n[GUARDIAN] 🚨 REMOTE ALERT: {count} new commit(s) on GitHub!")
                    print(f"[GUARDIAN] ⚠️  The other instance has updated the code. PLEASE PULL NOW.")
                    return True
                    
        except Exception:
            pass # Git might not be configured or network down
            
        return False

    def scan_local_files(self):
        """
        Recursively scans all files in root_dir for modifications.
        """
        changed = False
        current_mtimes = {}
        
        for root, dirs, files in os.walk(self.root_dir):
            # Prune ignore dirs in-place
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in EXTENSIONS:
                    full_path = os.path.join(root, file)
                    try:
                        mtime = os.stat(full_path).st_mtime
                        current_mtimes[full_path] = mtime
                        
                        # Check against last known
                        if full_path in self.last_mtimes:
                            if mtime > self.last_mtimes[full_path]:
                                rel_path = os.path.relpath(full_path, self.root_dir)
                                print(f"[GUARDIAN] 📝 Local Change: {rel_path}")
                                changed = True
                    except OSError:
                        pass
                            
        self.last_mtimes = current_mtimes
        return changed

    def run_diagnostics(self):
        """
        Triggers the test suite.
        """
        print("-" * 40)
        print(f"[GUARDIAN] ⚡ Running Diagnostics...")
        
        try:
            # Run the test script
            result = subprocess.run(
                ["./run_docker.sh", "--test"], 
                cwd=self.root_dir,
                capture_output=False 
            )
            
            if result.returncode == 0:
                print(f"[GUARDIAN] ✅ CODE HEALTHY.")
            else:
                print(f"[GUARDIAN] ❌ TEST FAILURES DETECTED.")
                print(f"[GUARDIAN] !!! RUN '/fix' TO REPAIR !!!")
                
        except Exception as e:
            print(f"[GUARDIAN] Execution Error: {e}")

    def start_loop(self):
        # Initial baseline
        self.scan_local_files()
        
        try:
            while self.running:
                time.sleep(POLL_INTERVAL)
                
                # 1. Check Local Files
                if self.scan_local_files():
                    time.sleep(1) # buffer for save completion
                    self.run_diagnostics()
                    self.scan_local_files() # Reset baseline
                    
                # 2. Check Remote GitHub
                self.check_remote_changes()
                    
        except KeyboardInterrupt:
            print("\n[GUARDIAN] 🛡️  Deactivating.")

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    guardian = Guardian(root)
    guardian.start_loop()
