# Fulcrum Production Deployment Guide (Operation Ironclad)

## Overview
This guide outlines the steps to deploy the Fulcrum Virtual Fleet to a generic Cloud VPS (Virtual Private Server), such as DigitalOcean Lower/Basic Droplets or AWS EC2 t3.micro.

**Recommended Specs:**
- **OS:** Ubuntu 22.04 LTS (or newer)
- **RAM:** 2GB minimum (4GB recommended for extended memory logs)
- **Storage:** 20GB+ SSD

---

## 1. Server Security (First Line of Defense)
Before deploying code, harden the server.

### Connect as Root
```bash
ssh root@your_vps_ip
```

### Update & Upgrade
```bash
apt update && apt upgrade -y
```

### Configure Firewall (UFW)
Open only necessary ports.
```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 8000/tcp  # Dashboard
# ufw allow 443/tcp # If using Nginx/SSL later
ufw enable
```
*Note: Ensure you allow SSH before enabling UFW to avoid locking yourself out.*

### Create Non-Root User (Best Practice)
```bash
adduser fulcrum
usermod -aG sudo fulcrum
su - fulcrum
```

---

## 2. Environment Setup

### Install Docker & Docker Compose
```bash
# Get Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### Clone Repository / Upload Code
You can use `git clone` if using a private repo, or `scp` from your local machine.
```bash
# Local Machine
scp -r "Desktop/LEF Ai" fulcrum@your_vps_ip:~/fulcrum_fleet
```

---

## 3. Configuration

### Create Production .env
Never commit `.env` to git. Create it on the server.
```bash
cd ~/fulcrum_fleet
nano .env
```

**Content:**
```bash
# API Keys (Coinbase)
COINBASE_API_KEY=your_key_here
COINBASE_API_SECRET=your_secret_here

# Simulation Settings
SANDBOX_MODE=FALSE   # Set to TRUE for testing, FALSE for real money
SIMULATION_MODE=FALSE

# Paths (Docker Internal Defaults)
DB_PATH=/app/database/fulcrum.db
REDIS_HOST=lef-redis
AM_I_IN_DOCKER=true
```

---

## 4. Launch Sequence

### Build & Deploy
```bash
docker compose build --no-cache
docker compose up -d
```

### Verification
Check if all systems are green.
```bash
docker ps
# Ensure all containers (lef-core, lef-dashboard, lef-redis, lef-dojo) are "Up".
```

### Logs
Monitor the Brain.
```bash
docker logs -f lef-core
```

---

## 5. Maintenance & Monitoring

### Dashboard
Access at `http://your_vps_ip:8000`.

### Healthchecks
The system now includes auto-healing healthchecks.
- **Dashboard:** Checks `/health` endpoint.
- **Database:** Checks integrity on startup. If corrupt, it auto-renames and resets.

### Updates
To update code:
1. `git pull` (or re-upload)
2. `docker compose build`
3. `docker compose up -d` (Recreates only changed containers)

### Emergency Stop
```bash
docker compose down
```
To wipe data (Nuclear Reset):
```bash
docker compose down -v
```
