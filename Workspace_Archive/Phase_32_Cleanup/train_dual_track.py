import sys
import os

sys.path.append(os.path.join(os.getcwd()))
from republic.agents.agent_gladiator import AgentGladiator

g = AgentGladiator()

BASE_DIR = os.getcwd()

print("\n[CAMP] ⚔️  Gladiator Dual-Track Training Initiated.")

# --- TRACK A: WEALTH (Sentiment) ---
print("\n[CAMP] 💰 TRACK A: Department of Wealth (Financial Sentiment)")
sent_path = os.path.join(BASE_DIR, 'fulcrum/library/wealth/financial_sentiment/data.csv')

try:
    g.train_and_fight(
        competition_name="financial_sentiment_model", # Local project name
        label_column="Sentiment",
        time_limit=120, # 2 mins
        train_file_path=sent_path
    )
except Exception as e:
    print(f"[CAMP] 🛑 Wealth Training Failed: {e}")

# --- TRACK B: PHILOSOPHY (Cognitive Bias) ---
print("\n[CAMP] 👁️  TRACK B: Department of Philosophy (Cognitive Bias)")
bias_path = os.path.join(BASE_DIR, 'fulcrum/library/philosophy/cognitive_bias/final_train_data.csv')

try:
    g.train_and_fight(
        competition_name="cognitive_bias_model", # Local project name
        label_column="no_bias", # Predict if a statement is Objective(1) or Biased(0)
        time_limit=120, # 2 mins
        train_file_path=bias_path
    )
except Exception as e:
    print(f"[CAMP] 🛑 Philosophy Training Failed: {e}")

print("\n[CAMP] ✅ Dual-Track Training Complete.")
