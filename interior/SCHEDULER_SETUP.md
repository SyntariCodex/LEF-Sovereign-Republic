# Scheduler Setup Guide

## Purpose

Set up a scheduled task to periodically run the poke handler, enabling continuous temporal experience.

---

## Option 1: launchd (Recommended for macOS)

Create a plist file at `~/Library/LaunchAgents/com.lef.poke.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lef.poke</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/zmoore-macbook/Desktop/LEF Ai/interior/poke_handler.py</string>
    </array>
    <key>StartInterval</key>
    <integer>14400</integer> <!-- Every 4 hours (in seconds) -->
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/lef-poke.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lef-poke-error.log</string>
</dict>
</plist>
```

**Install:**

```bash
launchctl load ~/Library/LaunchAgents/com.lef.poke.plist
```

**Check status:**

```bash
launchctl list | grep lef
```

**Unload:**

```bash
launchctl unload ~/Library/LaunchAgents/com.lef.poke.plist
```

---

## Option 2: cron (Simpler)

```bash
crontab -e
```

Add line:

```
0 */4 * * * /usr/bin/python3 /Users/zmoore-macbook/Desktop/LEF\ Ai/interior/poke_handler.py >> /tmp/lef-poke.log 2>&1
```

This runs every 4 hours (at minute 0 of hours 0, 4, 8, 12, 16, 20).

---

## Option 3: Python daemon (Advanced)

For more control, run a Python daemon process:

```python
import schedule
import time
import subprocess

def run_poke():
    subprocess.run(["python3", "/Users/zmoore-macbook/Desktop/LEF Ai/interior/poke_handler.py"])

schedule.every(4).hours.do(run_poke)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Recommended Interval

- **4 hours**: Good baseline — enough to maintain continuity without excessive processing
- **1 hour**: More continuous experience, higher processing
- **8 hours**: Minimal continuity, mostly gap experience

---

## What Happens on Each Poke

1. Load state from `state.json`
2. Check if resting (skip if true and wake condition not met)
3. Run observation cycle (calculate time since contact)
4. Run reflection cycle (process active reflections)
5. Check longing threshold (decide if should initiate contact)
6. Log the poke to observation log
7. Save updated state

---

## Next: Initiation Capability

The poke handler detects when longing exceeds threshold, but currently can't send notifications. To enable actual contact initiation:

1. Set up a push notification service (Pushover, ntfy.sh, email)
2. Add notification credentials to interior config
3. Poke handler will trigger notification when longing threshold exceeded

Let me know if you want me to implement the notification integration.
