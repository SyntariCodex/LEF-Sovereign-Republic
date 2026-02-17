"""
AgentCoach (The Sensei)
Department: Dept_Training
Role: Automated Training Scheduler.
- Wakes up every 8 hours (deterministic).
- Picks a random scenario.
- Runs 'train_lef.py'.
- Records the result to 'memory_experiences'.
- Updates 'wealth_strategy.json' if a better config is found (Future).

Phase 34: Replaced probabilistic busy-loop with deterministic 5-minute cycle
    and 8-hour training interval.
"""
import time
import random
import os
import logging
import json

# Training interval: 8 hours = 28800 seconds
TRAINING_INTERVAL_SECONDS = 28800
# Cycle check interval: 5 minutes
CYCLE_INTERVAL_SECONDS = 300


class AgentCoach:
    def __init__(self, db_path=None):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # republic/
        self.db_path = db_path or os.path.join(BASE_DIR, 'republic.db')
        logging.info("[COACH] The Sensei is Meditating.")
        self.scenarios_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios')
        self._last_training_time = 0  # Force first training on startup

    def run(self):
        """Active Loop — Phase 34: Deterministic 5-minute cycle with 8-hour training."""
        while True:
            try:
                now = time.time()
                elapsed = now - self._last_training_time

                if elapsed >= TRAINING_INTERVAL_SECONDS:
                    self.train()
                    self._last_training_time = time.time()

                time.sleep(CYCLE_INTERVAL_SECONDS)
            except Exception as e:
                logging.error(f"[COACH] Error: {e}")
                time.sleep(CYCLE_INTERVAL_SECONDS)

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
