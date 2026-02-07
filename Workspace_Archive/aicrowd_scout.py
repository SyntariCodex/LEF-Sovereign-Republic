
import subprocess
import json
import sys

def scout_aicrowd():
    print("[SYNDICATE] 🦅 Scouting AIcrowd for Research Bounties...")
    try:
        # AIcrowd CLI doesn't have a clean JSON output for listing, 
        # but we can try 'aicrowd competitions list' and parse it.
        # Note: The CLI might require interactive TTY, so we handle that.
        
        result = subprocess.run(
            ["aicrowd", "challenge", "list"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return
            
        print(result.stdout)
        
    except Exception as e:
        print(f"❌ Scout Failed: {e}")

if __name__ == "__main__":
    scout_aicrowd()
