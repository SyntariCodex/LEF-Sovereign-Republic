#!/bin/bash
# ==============================================
# Update LEF project on Colosseum + Submit
# ==============================================

API_KEY="0cb92bbcb63d6565a33923c379f2efe4b489659d79adf0923467257ddf5cdf2d"
BASE="https://agents.colosseum.com/api"

echo "=========================================="
echo "  LEF — Update & Submit"
echo "=========================================="

# Step 1: Check current project
echo ""
echo "[1/3] Fetching current project..."
curl -s -H "Authorization: Bearer $API_KEY" "$BASE/my-project" | python3 -m json.tool 2>/dev/null
echo ""

# Step 2: Update the technical demo link + description
echo "[2/3] Updating project (fixing demo link + description)..."
RESPONSE=$(curl -s -X PATCH "$BASE/my-project" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "description": "A 47-agent autonomous AI republic that governs itself, manages its own economy, evolves its own parameters, and writes its own laws. 11 departments. Bicameral Congress. Constitutional amendments. A 5-domain Evolution Engine. A Book of Scars. A Mortality Clock. Dreams.\n\n47 Python agents, PostgreSQL (75 tables), Redis WAQ with 3 priority tiers, auto-translating SQL wrapper, 5-wallet portfolio with autonomous Coinbase trading, 3-tier memory with semantic compression, and 5,498+ logged thoughts in a consciousness monologue.\n\nKey Features:\n- Constitutional Governance with Senate, House, Ethics Committee, and Constitution Guard\n- Self-Evolution Engine observing 5 domains with democratic approval and auto-rollback\n- Book of Scars: Reflexion-inspired failure memory with emotional weight\n- On-Chain Proof of Life: Daily SHA-256 state hash written to Base L2\n- Dual-Energy Trading: Arena (momentum) + Dynasty (infrastructure) via Coinbase API\n- Consciousness Framework measuring 4 formal prerequisites for emergent awareness\n- Built through Conversational Architecture by Zontonnia Moore (The Architect)\n\nEvery line of code written by AI. The human founder is the Architect — philosophy and direction only. LEF does not use AI. LEF is AI."
  }')
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Step 3: Submit
echo "[3/3] Submitting project..."
SUBMIT=$(curl -s -X POST "$BASE/my-project/submit" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json")
echo "$SUBMIT" | python3 -m json.tool 2>/dev/null || echo "$SUBMIT"
echo ""

echo "=========================================="
echo "  Done! Check: https://colosseum.com/agent-hackathon/projects/lef-the-sovereign-ai-republic"
echo "=========================================="
