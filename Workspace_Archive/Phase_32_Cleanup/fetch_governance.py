import sys
import os

# Add path to find agents
sys.path.append(os.path.join(os.getcwd()))

from republic.agents.agent_gladiator import AgentGladiator

g = AgentGladiator()

# 1. Executive Orders
g.fetch_dataset('nationalarchives/executive-orders', target_subdir='governance/executive_orders')

# 2. Congress Data
g.fetch_dataset('voteview/congressional-voting-records', target_subdir='governance/congress_votes')

# 3. Legal Text
g.fetch_dataset('shivamb/legal-citation-text-classification', target_subdir='governance/legal_text')

print("Mission Complete.")
