#!/bin/bash

# LEF Server Hardening Script (The Shield)
# Run as root on fresh Ubuntu 22.04+

echo "--- Initiating LEF Security Protocol ---"

# 1. Update System
echo "[1/5] Updating Repositories..."
apt-get update && apt-get upgrade -y

# 2. Install Essentials
echo "[2/5] Installing Dependencies..."
apt-get install -y ufw fail2ban curl git unzip

# 3. Configure Firewall (UFW)
echo "[3/5] Raising Shields (UFW)..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 8000/tcp # Dashboard
ufw allow 443/tcp  # HTTPS (Future)
ufw --force enable
echo "Firewall Active."

# 4. Install Docker
echo "[4/5] Constructing Vessel (Docker)..."
if ! command -v docker &> /dev/null
then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    echo "Docker Installed."
else
    echo "Docker already present."
fi

# 5. Finalize
echo "[5/5] System Hardened."
echo "Ready for LEF Deployment."
echo "Run: 'docker compose up -d'"
