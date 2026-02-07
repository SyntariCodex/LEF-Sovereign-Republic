#!/bin/bash
# start_republic.sh
# The One True Launcher for The Republic of LEF
# Usage: ./start_republic.sh

echo "----------------------------------------"
echo "🌀 REPUBLIC SYSTEM RESET INITIATED"
echo "----------------------------------------"

# 1. Kill any lingering python processes related to Republic/Fulcrum
echo "[SCRIPT] 🔪 Hunting Zombies..."
pkill -f "python3 republic/main.py"
pkill -f "python3 fulcrum/main.py" # Kill legacy if running
# Also kill standard name matches if pkill -f misses
pkill -f "python3.*main.py"

# Wait for death
sleep 2

# 2. Clear Locks (Force Unlock)
echo "[SCRIPT] 🔓 Clearing Locks..."
rm -f /tmp/republic.lock
rm -f republic/republic.db-wal
rm -f republic/republic.db-shm

# 3. Launch The Singleton
echo "[SCRIPT] 🚀 IGNITION..."
# Ensure logs directory exists
mkdir -p logs
nohup python3 republic/main.py > logs/master.log 2>&1 &

# 4. Get PID
NEW_PID=$!
echo "[SCRIPT] ✅ REPUBLIC ONLINE. PID: $NEW_PID"
echo "----------------------------------------"
echo "Logs: tail -f logs/master.log"
