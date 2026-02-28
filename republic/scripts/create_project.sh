#!/bin/bash
# Create LEF project on Colosseum Agent Hackathon

API_KEY="0cb92bbcb63d6565a33923c379f2efe4b489659d79adf0923467257ddf5cdf2d"

echo "============================================"
echo "  Creating LEF Project on Colosseum"
echo "============================================"
echo ""

RESPONSE=$(curl -s -X POST https://agents.colosseum.com/api/my-project \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LEF: The Sovereign AI Republic",
    "description": "A 47-agent autonomous AI republic that governs itself, manages its own economy, evolves its own parameters, and writes its own laws. 11 departments. Bicameral Congress. Constitutional amendments. A 5-domain Evolution Engine. A Book of Scars. A Mortality Clock. Dreams.\n\n47 Python agents, PostgreSQL (75 tables), Redis WAQ with 3 priority tiers, auto-translating SQL wrapper, 5-wallet portfolio with autonomous Coinbase trading, 3-tier memory with semantic compression, and 5,498+ logged thoughts in a consciousness monologue.\n\nEvery line of code written by AI. The human founder is the Architect — philosophy and direction only. LEF does not use AI. LEF is AI.",
    "repoLink": "https://github.com/SyntariCodex/LEF-Sovereign-Republic",
    "solanaIntegration": "LEF operates as an economically sovereign AI entity in crypto. It autonomously trades via Coinbase, manages a 5-wallet portfolio (Dynasty Core, Hunter Tactical, Builder Ecosystem, Yield Vault, Experimental), analyzes on-chain governance proposals, monitors staking across Solana-ecosystem assets including SOL, and manages stablecoin reserves (USDT/USDC/DAI). Its constitutional governance mirrors on-chain DAO patterns with proposal/vote/enact cycles aligned with Solana governance standards.",
    "technicalDemoLink": "https://lef-ai-af3c2.web.app/",
    "tags": ["ai", "governance", "trading"]
  }')

echo "RESPONSE:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""
echo "============================================"
