import sys
import os

sys.path.append(os.path.join(os.getcwd()))
from republic.agents.agent_gladiator import AgentGladiator

g = AgentGladiator()

print("[CAMP] 📥 Fetching Track A (Wealth)...")
g.fetch_dataset('sbhatti/financial-sentiment-analysis', target_subdir='wealth/financial_sentiment')

print("[CAMP] 📥 Fetching Track B (Philosophy)...")
g.fetch_dataset('chinmaypisal1718/cognitive-bias-classification-dataset', target_subdir='philosophy/cognitive_bias')

print("[CAMP] ✅ Fetch Complete.")
