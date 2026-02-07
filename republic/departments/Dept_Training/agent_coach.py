"""
AgentCoach (The Sensei)
Department: Dept_Training
Role: Automated Training Scheduler.
- Wakes up every 12-24 hours.
- Picks a random scenario.
- Runs 'train_lef.py'.
- Records the result to 'memory_experiences'.
- Updates 'wealth_strategy.json' if a better config is found (Future).
"""
import time
import random
import os
import logging
import json

class AgentCoach:
    def __init__(self, db_path=None):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # republic/
        self.db_path = db_path or os.path.join(BASE_DIR, 'republic.db')
        logging.info("[COACH] 🥋 The Sensei is Meditating.")
        self.scenarios_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios')

    def run(self):
        """Active Loop"""
        while True:
            try:
                # 1. Wait for Training Schedule (e.g. Every 8 hours - 3x / day)
                # Chance per minute: 1 / 480 mins = 0.002
                
                if random.random() < 0.002: # ~Once every 8 hours
                    self.train()
                
                time.sleep(60)
            except Exception as e:
                logging.error(f"[COACH] Error: {e}")
                time.sleep(60)

    def train(self):
        """Executes a Training Session (Competition)"""
        logging.info("[COACH] 🔔 DOJO OPEN. Starting Competition...")
        
        # 1. Pick Random Scenario
        if not os.path.exists(self.scenarios_dir):
            logging.error("[COACH] No scenarios found!")
            return
            
        scenarios = [f for f in os.listdir(self.scenarios_dir) if f.endswith('.json')]
        if not scenarios:
            return
            
        scenario = random.choice(scenarios)
        scenario_path = os.path.join(self.scenarios_dir, scenario)
        
        logging.info(f"[COACH] Selected Scenario: {scenario}")
        
        # 2. Run Competition (In-Process Import)
        try:
            # Dynamic import to avoid circular dependency at top level
            import sys
            # Add republic root
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            from departments.Dept_Training.arena import Competition
            
            print(f"[COACH] 🏟️  Invoking The Arena...")
            comp = Competition(scenario_path)
            comp.run() # This prints the leaderboard
            
            logging.info(f"[COACH] ✅ Competition Complete: {scenario}")

        except Exception as e:
            logging.error(f"[COACH] Competition Error: {e}")

if __name__ == "__main__":
    coach = AgentCoach()
    coach.run()
