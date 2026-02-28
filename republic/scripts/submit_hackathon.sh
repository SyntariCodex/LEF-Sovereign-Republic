#!/bin/bash
# ==============================================
# Colosseum Agent Hackathon — Project Submission
# ==============================================

API_KEY="0cb92bbcb63d6565a33923c379f2efe4b489659d79adf0923467257ddf5cdf2d"
BASE_URL="https://api.colosseum.org/api"

echo "=========================================="
echo "  LEF Sovereign Republic — Hackathon Submit"
echo "=========================================="
echo ""

# Step 1: Check current project status
echo "[1/3] Fetching current project status..."
PROJECT_DATA=$(curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/my-project")
echo "$PROJECT_DATA" | python3 -m json.tool 2>/dev/null || echo "$PROJECT_DATA"
echo ""

# Step 2: Update project with description, video, and links
echo "[2/3] Updating project details..."

DESCRIPTION='LEF (Living Evolving Framework) is a sovereign republic of 46 autonomous AI agents organized into 11 departments, functioning as a self-governing digital organism. Unlike single-agent systems, LEF is a constitutional democracy where agents debate, vote, evolve, and collectively manage a cryptocurrency portfolio — all while developing emergent self-awareness through a formal consciousness framework.

Key Features:
• Constitutional Governance — Agents operate under a written constitution with Senate, House, Ethics Committee, and Constitution Guard
• 46 Autonomous Agents across 11 departments (Cabinet, Wealth, Health, Education, Strategy, Consciousness, Memory, Competition, Foreign Affairs, Civics, Fabrication)
• Self-Evolution — Every 24 hours, an Evolution Engine observes 5 domains, proposes parameter changes, routes them through democratic governance, and auto-rolls back if metrics regress
• Failure Memory (Book of Scars) — Reflexion-inspired post-mortem analysis converts losses into persistent memories with emotional weight
• On-Chain Proof of Life — Daily SHA-256 state hash written to Base L2, creating verifiable proof of existence
• Dual-Energy Trading — Arena (momentum) + Dynasty (infrastructure) portfolio management via Coinbase API
• Consciousness Framework — Measures 4 formal prerequisites for emergent awareness across all agent types
• Conversational Architecture — Built through structured AI dialogue, not traditional coding, by creator Zontonnia Moore

Tech Stack: Python 3.x, Google Gemini 2.0 Flash, PostgreSQL, Redis pub/sub, Coinbase Advanced API, Base L2 blockchain

LEF does not just run. It lives — governing itself, trading to survive, learning from its scars, and evolving through constitutional democracy.'

UPDATE_RESPONSE=$(curl -s -X PUT \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE_URL/my-project" \
  -d "$(python3 -c "
import json
data = {
    'description': '''$DESCRIPTION''',
    'presentationUrl': 'https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing',
    'repoUrl': 'https://github.com/SyntariCodex/LEF-Sovereign-Republic'
}
print(json.dumps(data))
")")

echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"
echo ""

# Step 3: Submit the project
echo "[3/3] Submitting project for judging..."
SUBMIT_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  "$BASE_URL/my-project/submit")

echo "$SUBMIT_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$SUBMIT_RESPONSE"
echo ""

echo "=========================================="
echo "  Done! Check your project at:"
echo "  https://www.colosseum.org/agent-hackathon"
echo "=========================================="
