#!/bin/bash
# run_docker.sh
# Professional Launch Protocol (Docker)

echo "========================================"
echo " 🐳 INITIALIZING DOCKER FLEET"
echo "========================================"

# 0. Argument Parsing
RUN_TESTS=false
for arg in "$@"
do
    case $arg in
        --test|-t)
        RUN_TESTS=true
        shift # Remove --test from processing
        ;;
    esac
done

if [ "$RUN_TESTS" = true ]; then
    echo "[SCRIPT] 🧪 Running Tests..."
    
    # Check for Venv
    if [ -f "republic/venv/bin/activate" ]; then
        echo "[SCRIPT] 🐍 Activating Venv..."
        source republic/venv/bin/activate
    fi

    # Check if pytest is installed
    if ! python3 -m pytest --version &> /dev/null; then
        echo "pytest not found. Installing..."
        python3 -m pip install pytest
    fi
    
    export PYTHONPATH=$PYTHONPATH:.
    python3 -m pytest tests/ -v
    
    if [ $? -ne 0 ]; then
        echo "❌ TESTS FAILED. Aborting deployment."
        exit 1
    fi
    echo "✅ Tests Passed."
fi

# 1. Cleanup Legacy Processes
echo "[SCRIPT] 🧹 Cleaning up local Python processes..."
pkill -f "python3 republic/main.py"
pkill -f "python3 fulcrum/main.py"
pkill -f "python3.*main.py"
rm -f /tmp/republic.lock
rm -f republic/republic.db-wal
rm -f republic/republic.db-shm

# 2. Build & Launch
echo "[SCRIPT] 🏗️  Building Containers..."
docker-compose down
docker-compose up --build -d

echo "========================================"
echo " ✅ FLEET DEPLOYED (Containerized)"
echo "========================================"
echo "Commands:"
echo "  View Logs:    docker-compose logs -f"
echo "  Stop System:  docker-compose down"
echo "  Shell Access: docker exec -it lef-core bash"
echo "========================================"
echo "Tailing logs now (Ctrl+C to exit view, System keeps running)..."
sleep 2
docker-compose logs -f -n 50
