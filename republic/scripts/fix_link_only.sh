#!/bin/bash
API_KEY="0cb92bbcb63d6565a33923c379f2efe4b489659d79adf0923467257ddf5cdf2d"
BASE="https://agents.colosseum.com/api"

echo "=== Attempt 1: POST to /api/my-project (same as original create) ==="
R1=$(curl -s -X POST "$BASE/my-project" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LEF: The Sovereign AI Republic",
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "twitterHandle": "@ChristasKing",
    "repoLink": "https://github.com/SyntariCodex/LEF-Sovereign-Republic",
    "description": "A 47-agent autonomous AI republic that governs itself, manages its own economy, evolves its own parameters, and writes its own laws. 11 departments. Bicameral Congress. Constitutional amendments. A 5-domain Evolution Engine. A Book of Scars. A Mortality Clock. Dreams.\n\n47 Python agents, PostgreSQL (75 tables), Redis WAQ with 3 priority tiers, auto-translating SQL wrapper, 5-wallet portfolio with autonomous Coinbase trading, 3-tier memory with semantic compression, and 5,498+ logged thoughts in a consciousness monologue.\n\nEvery line of code written by AI. The human founder is the Architect — philosophy and direction only. LEF does not use AI. LEF is AI.",
    "solanaIntegration": "LEF operates as an economically sovereign AI entity in crypto. It autonomously trades via Coinbase, manages a 5-wallet portfolio (Dynasty Core, Hunter Tactical, Builder Ecosystem, Yield Vault, Experimental), analyzes on-chain governance proposals, monitors staking across Solana-ecosystem assets including SOL, and manages stablecoin reserves (USDT/USDC/DAI). Its constitutional governance mirrors on-chain DAO patterns with proposal/vote/enact cycles aligned with Solana governance standards.",
    "tags": ["ai", "governance", "trading"]
  }')
echo "$R1" | python3 -m json.tool 2>/dev/null || echo "$R1"

echo ""
echo "=== Attempt 2: PUT to /api/my-project ==="
R2=$(curl -s -X PUT "$BASE/my-project" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "twitterHandle": "@ChristasKing"
  }')
echo "$R2" | python3 -m json.tool 2>/dev/null || echo "$R2"

echo ""
echo "=== Attempt 3: POST to /api/my-project/update ==="
R3=$(curl -s -X POST "$BASE/my-project/update" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "twitterHandle": "@ChristasKing"
  }')
echo "$R3" | python3 -m json.tool 2>/dev/null || echo "$R3"

echo ""
echo "=== Attempt 4: POST to /api/my-project/edit ==="
R4=$(curl -s -X POST "$BASE/my-project/edit" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "technicalDemoLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "presentationLink": "https://drive.google.com/file/d/1zy6O8wJi_e93AmPKnbLQHfEDZeRTsLfb/view?usp=sharing",
    "twitterHandle": "@ChristasKing"
  }')
echo "$R4" | python3 -m json.tool 2>/dev/null || echo "$R4"

echo ""
echo "=== Verify: GET current state ==="
curl -s -H "Authorization: Bearer $API_KEY" "$BASE/my-project" | python3 -c "
import json, sys
data = json.load(sys.stdin)
p = data.get('project', data)
print(f\"  Status:       {p.get('status')}\")
print(f\"  Demo Link:    {p.get('technicalDemoLink')}\")
print(f\"  Presentation: {p.get('presentationLink')}\")
print(f\"  Twitter:      {p.get('twitterHandle')}\")
" 2>/dev/null
