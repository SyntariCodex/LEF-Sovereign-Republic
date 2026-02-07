import sys
import os

sys.path.append(os.path.join(os.getcwd()))
from republic.agents.agent_gladiator import AgentGladiator

g = AgentGladiator()

print("[CAMP] 📥 Fetching Remaining Datasets...")

# Track A: Wealth (Time Series - Crypto)
# Target: jessevent/all-crypto-currencies (Good general dataset)
print("[CAMP] 💰 Fetching Crypto Data (Wealth/Time Series)...")
g.fetch_dataset('jessevent/all-crypto-currencies', target_subdir='wealth/crypto_market')

# Track B: Philosophy (Intent - Chatbot)
# Target: bitext/training-dataset-for-chatbots-virtual-assistants
print("[CAMP] 👁️  Fetching Intent Data (Philosophy/RDA)...")
g.fetch_dataset('bitext/training-dataset-for-chatbots-virtual-assistants', target_subdir='philosophy/intent_data')

print("[CAMP] ✅ Fetch Complete.")
