
import os
import csv
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load Environment (for KAGGLE_API_TOKEN)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from republic.agents.agent_gladiator import AgentGladiator

# Config
TARGETS_CSV = os.path.join(os.path.dirname(__file__), 'fulcrum/library/wealth/mercenary_targets.csv')
MIN_REWARD = 500000 # $500k
NOW = datetime.now()

def parse_reward(reward_str):
    # "2,207,152 Usd" -> 2207152
    try:
        clean = reward_str.lower().replace('usd', '').replace(',', '').strip()
        return int(clean)
    except:
        return 0

def main():
    print("[CAMPAIGN] 🏴‍☠️  Operation Bounty Hunter Initiated.")
    
    if not os.path.exists(TARGETS_CSV):
        print(f"[CAMPAIGN] 🛑 Missing Targets CSV: {TARGETS_CSV}")
        return

    # Load Targets
    df = pd.read_csv(TARGETS_CSV)
    
    # Initialize Gladiator
    g = AgentGladiator()
    g.update_status("CAMPAIGN: Assessing Targets")
    
    active_targets = []
    
    for _, row in df.iterrows():
        # Parse Deadline
        try:
            deadline_str = str(row['deadline'])
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
            
            if deadline < NOW:
                continue # Expired
            
            # Parse Reward
            reward = parse_reward(row['reward'])
            if reward < MIN_REWARD:
                continue # Too small
                
            # Valid Target
            # Slug extraction from URL
            # https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3
            slug = row['ref'].split('/')[-1]
            if not slug:
                slug = row['ref'] # Fallback
                
            active_targets.append({
                'slug': slug,
                'reward': reward,
                'deadline': deadline,
                'category': row['category']
            })
            
        except Exception as e:
            print(f"[CAMPAIGN] ⚠️ Parse Error on row: {row['ref']} - {e}")
            continue

    print(f"[CAMPAIGN] 🎯 Found {len(active_targets)} High-Value Active Targets.")
    
    # Sort by Reward (Greedy)
    active_targets.sort(key=lambda x: x['reward'], reverse=True)
    
    for t in active_targets:
        print(f"[CAMPAIGN] ⚔️  Target: {t['slug']} (${t['reward']:,})")
        # Fetch Data
        g.prepare_arena(t['slug'])
        
    g.update_status("CAMPAIGN: Data Acquired")
    print("[CAMPAIGN] ✅ All targets acquired. Ready for Analysis.")

if __name__ == "__main__":
    main()
