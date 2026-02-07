import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.getcwd()))
from republic.agents.agent_gladiator import AgentGladiator

# 1. Load Data
BASE_DIR = os.getcwd()
VOTES_PATH = os.path.join(BASE_DIR, 'fulcrum/library/governance/congress_votes/HSall_votes.csv')
MEMBERS_PATH = os.path.join(BASE_DIR, 'fulcrum/library/governance/congress_votes/HSall_members.csv')

print("[GOV] 📜 Loading Congress Data...")
try:
    df_votes = pd.read_csv(VOTES_PATH)
    df_members = pd.read_csv(MEMBERS_PATH)
    
    # optimize memory usage (dataset can be large)
    # keep only recent congresses (e.g. last 20) to speed up demo
    max_congress = df_votes['congress'].max()
    min_congress = max(1, max_congress - 20) 
    print(f"[GOV] Filtering for Congress {min_congress}-{max_congress}...")
    
    df_votes = df_votes[df_votes['congress'] >= min_congress]
    
    # 2. Merge
    print("[GOV] 🔗 Merging Votes & Members...")
    # Merge on icpsr (and maybe congress if party switch, but icpsr is person)
    # Actually members has 'congress' too
    df_merged = pd.merge(df_votes, df_members[['congress', 'icpsr', 'party_code', 'state_abbrev', 'bioname']], 
                         on=['congress', 'icpsr'], how='inner')
    
    # 3. Create Training Set
    # Target: cast_code
    # Features: rollnumber, party_code, state_abbrev, chamber
    train_df = df_merged[['cast_code', 'rollnumber', 'party_code', 'state_abbrev', 'chamber']]
    
    # Save temp train file
    temp_train_path = os.path.join(BASE_DIR, 'fulcrum/temp_gov_train.csv')
    train_df.to_csv(temp_train_path, index=False)
    print(f"[GOV] Training Set Ready: {len(train_df)} records. Saved to {temp_train_path}")
    
    # 4. Train
    print("[GOV] 🏛️  Sending to Gladiator...")
    g = AgentGladiator()
    g.train_and_fight(
        competition_name="governance_model",
        label_column="cast_code",
        time_limit=120, # 2 mins
        train_file_path=temp_train_path
    )
    
    # Clean up
    if os.path.exists(temp_train_path):
        os.remove(temp_train_path)
    
    print("[GOV] ✅ Governance Model Trained.")
    
except Exception as e:
    print(f"[GOV] 🛑 Error: {e}")
