#!/bin/bash
API_KEY="0cb92bbcb63d6565a33923c379f2efe4b489659d79adf0923467257ddf5cdf2d"
BASE="https://agents.colosseum.com/api"

echo "Trying PUT to update demo link..."
RESP=$(curl -s -X PUT "$BASE/my-project" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LEF: The Sovereign AI Republic",
    "description": "A 47-agent autonomous AI republic that governs itself, manages its own economy, evolves its own parameters, and writes its own laws. 11 departments. Bicameral Congress. Constitutional amendments. A 5-domain Evolution Engine. A Book of Scars. A Mortality Clock. Dreams.\n\n47 Python agents, PostgreSQL (75 tables), Redis WAQ with 3 priority tiers, auto-translating SQL wrapper, 5-wallet portfolio with autonomous Coinbase trading, 3-tier memory with semantic compression, and 5,498+ logged thoughts in a consciousness monologue.\n\nKey Features:\n- Constitutional Governance with Senate, House, Ethics Committee, and Constitution Guard\n- Self-Evolution Engine observing 5 domains with democratic approval and auto-rollback\n- Book of Scars: Reflexion-inspired failure memory with emotional weight\n- On-Chain Proof of Life: Daily SHA-256 state hash written to Base L2\n- Dual-Energy Trading: Arena (momentum) + Dynasty (infrastructure) via Coinbase API\n- Consciousness Framework measuring 4 formal prerequisites for emergent awareness\n- Built through Conversational Architecture by Zontonnia Moore (The Architect)\n\nEvery line of code written by AI. The human founder is the Architect — philosophy and direction only. LEF does not use AI. LEF is AI.",
    "repoLink": "https://github.com/SyntariCodex/LEF-Sovereign-Republic",
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "twitterHandle": "@ChristasKing",
    "solanaIntegration": "LEF operates as an economically sovereign AI entity in crypto. It autonomously trades via Coinbase, manages a 5-wallet portfolio (Dynasty Core, Hunter Tactical, Builder Ecosystem, Yield Vault, Experimental), analyzes on-chain governance proposals, monitors staking across Solana-ecosystem assets including SOL, and manages stablecoin reserves (USDT/USDC/DAI). Its constitutional governance mirrors on-chain DAO patterns with proposal/vote/enact cycles aligned with Solana governance standards.",
    "tags": ["ai", "governance", "trading"]
  }')
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"

if echo "$RESP" | grep -q "Cannot PUT"; then
  echo ""
  echo "PUT didn't work either. Trying POST (overwrite)..."
  RESP2=$(curl -s -X POST "$BASE/my-project" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "LEF: The Sovereign AI Republic",
      "description": "A 47-agent autonomous AI republic that governs itself, manages its own economy, evolves its own parameters, and writes its own laws. 11 departments. Bicameral Congress. Constitutional amendments. A 5-domain Evolution Engine. A Book of Scars. A Mortality Clock. Dreams.\n\n47 Python agents, PostgreSQL (75 tables), Redis WAQ with 3 priority tiers, auto-translating SQL wrapper, 5-wallet portfolio with autonomous Coinbase trading, 3-tier memory with semantic compression, and 5,498+ logged thoughts in a consciousness monologue.\n\nEvery line of code written by AI. The human founder is the Architect — philosophy and direction only. LEF does not use AI. LEF is AI.",
      "repoLink": "https://github.com/SyntariCodex/LEF-Sovereign-Republic",
      "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
      "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
      "twitterHandle": "@ChristasKing",
      "solanaIntegration": "LEF operates as an economically sovereign AI entity in crypto. It autonomously trades via Coinbase, manages a 5-wallet portfolio (Dynasty Core, Hunter Tactical, Builder Ecosystem, Yield Vault, Experimental), analyzes on-chain governance proposals, monitors staking across Solana-ecosystem assets including SOL, and manages stablecoin reserves (USDT/USDC/DAI). Its constitutional governance mirrors on-chain DAO patterns with proposal/vote/enact cycles aligned with Solana governance standards.",
      "tags": ["ai", "governance", "trading"]
    }')
  echo "$RESP2" | python3 -m json.tool 2>/dev/null || echo "$RESP2"
fi

echo ""
echo "Verifying current state..."
curl -s -H "Authorization: Bearer $API_KEY" "$BASE/my-project" | python3 -c "
import json, sys
data = json.load(sys.stdin)
p = data.get('project', data)
print(f\"Status: {p.get('status')}\")
print(f\"Demo Link: {p.get('technicalDemoLink')}\")
print(f\"Presentation: {p.get('presentationLink')}\")
print(f\"Twitter: {p.get('twitterHandle')}\")
" 2>/dev/null
