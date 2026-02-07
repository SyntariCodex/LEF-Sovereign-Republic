import sys
import os

# Add path
sys.path.append(os.path.join(os.getcwd()))

from republic.agents.agent_gladiator import AgentGladiator

g = AgentGladiator()

print("\n[CAMP] ⛺ Welcome to Gladiator Training Camp.")

# 1. House Prices (Regression)
print("\n[CAMP] 🏠 Target: House Prices")
try:
    g.train_and_fight(
        competition_name="house-prices-advanced-regression-techniques", 
        label_column="SalePrice",
        time_limit=60 # Short training for speed
    )
except Exception as e:
    print(f"[CAMP] 🛑 House Prices Failed: {e}")

# 2. Spaceship Titanic (Binary Class)
print("\n[CAMP] 🚀 Target: Spaceship Titanic")
try:
    g.train_and_fight(
        competition_name="spaceship-titanic", 
        label_column="Transported",
        time_limit=60
    )
except Exception as e:
    print(f"[CAMP] 🛑 Spaceship Failed: {e}")

# 3. NLP Disaster Tweets (Text)
print("\n[CAMP] 🐦 Target: NLP Disaster Tweets")
try:
    g.train_and_fight(
        competition_name="nlp-getting-started", 
        label_column="target",
        time_limit=60
    )
except Exception as e:
    print(f"[CAMP] 🛑 NLP Failed: {e}")

print("\n[CAMP] ✅ Training Complete.")
