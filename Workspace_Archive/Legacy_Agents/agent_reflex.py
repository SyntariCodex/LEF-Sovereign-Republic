
import sqlite3
import time
import json
import os
import redis

# AGENT REFLEX (The Coach)
# Implements "Pain/Pleasure" learning.
# Monitors PnL in specific regimes and adjusts CIO risk parameters.

# Robust Path Logic
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

class AgentReflex:
    def __init__(self):
        print("[REFLEX] 🥋 Coach entering the Dojo...")
        self.db_path = DB_PATH
        self.r = None
        try:
            self.r = redis.Redis(host='localhost', port=6379, db=0)
            self.r.ping()
        except:
            print("[REFLEX] ⚠️  Redis not found. Reflexes dulled.")

    def run_cycle(self):
        """
        Main Loop: Check recent performance -> Adjust Risk.
        """
        while True:
            try:
                self.evaluate_performance()
                time.sleep(30) # Review every 30s
            except Exception as e:
                print(f"[REFLEX] ⚠️  Coach stumbled: {e}")
                time.sleep(30)

    def evaluate_performance(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 1. Identify Current Regime (Weather)
        c.execute("SELECT regime FROM regime_history ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        current_regime = row[0] if row else "UNKNOWN"
        
        # 2. Check recent trades in this regime (last 10)
        # We need to know if we WON or LOST. 
        # For simplicity in this v1, we check if we sold for profit recently.
        
        # Check 'realized_pnl' table (populated by Coinbase on sell)
        # We assume such a table exists or we query trade_queue for SELLS
        c.execute("SELECT profit_amount FROM realized_pnl ORDER BY id DESC LIMIT 10")
        recent_pnl = c.fetchall()
        
        if not recent_pnl:
            conn.close()
            return

        wins = 0
        losses = 0
        total_profit = 0.0
        
        for p in recent_pnl:
            val = p[0]
            if val > 0: wins += 1
            else: losses += 1
            total_profit += val
            
        total = wins + losses
        if total < 3: return # Need more data
        
        win_rate = wins / total
        
        # 3. Formulate Feedback (Pain/Pleasure)
        action = None
        reason = ""
        
        # 3. Formulate Feedback (Pain/Pleasure)
        action = None
        reason = ""
        
        # Calculate Max Drawdown (Simulated from PnL stream)
        # We start with 0 pnl. Lowest point relative to peak.
        peak = 0
        current = 0
        max_dd = 0
        for p in recent_pnl:
            val = p[0]
            current += val
            peak = max(peak, current)
            dd = peak - current
            max_dd = max(max_dd, dd)
            
        # COACHING LOGIC (The S-Tier Trainer)
        
        # A. UNIVERSAL RULES (Fundamentals)
        if max_dd > 500: # $500 Drawdown tolerance
             action = "DECREASE_RISK"
             reason = f"Max Drawdown violated (${max_dd:.2f}). Tighten up."
             
        elif win_rate < 0.35:
             action = "DECREASE_RISK"
             reason = f"Win Rate Critical ({win_rate*100:.0f}%). You are tilting."

        # B. REGIME SPECIFIC RULES (Context)
        elif current_regime == "ACCUMULATION":
             if losses > wins:
                 # In accumulation, we expect chop. If losing money, risk is too high.
                 action = "DECREASE_RISK"
                 reason = "Chopped up in Accumulation. Stop scalping."
                 
        elif current_regime == "MANIC":
             if win_rate > 0.6:
                 # In Manic, push it.
                 action = "INCREASE_RISK"
                 reason = "Riding the Manic Wave successfully. Press the advantage."
                 
        elif current_regime == "CRASH":
             if losses > 0:
                 action = "DECREASE_RISK" # Zero tolerance in crash
                 reason = "caught longing a knife. Stop."
        
        elif win_rate > 0.70 and total_profit > 0 and not action:
            # PLEASURE SIGNAL (Default)
            action = "INCREASE_RISK"
            reason = f"Win Rate Excellent ({win_rate*100:.0f}%) in {current_regime}. Heating up."
            
        # 4. Issue Directive to CIO
        if action:
            self.issue_directive(c, action, reason)
            
        conn.close()

    def issue_directive(self, c, action, reason):
        # Determine payload
        multiplier_delta = -0.1 if action == "DECREASE_RISK" else 0.05
        
        # Check if we already complained recently
        c.execute("SELECT id FROM lef_directives WHERE directive_type='REFLEX_ADJUSTMENT' AND status='PENDING'")
        if c.fetchone():
            return # Don't spam
            
        print(f"[REFLEX] 🧠 REFLEX ARC: {action} ({reason})")
        
        c.execute("INSERT INTO lef_directives (directive_type, payload) VALUES (?, ?)", 
                  ('REFLEX_ADJUSTMENT', json.dumps({
                      'action': action,
                      'delta': multiplier_delta,
                      'reason': reason
                  })))
        c.connection.commit()

if __name__ == "__main__":
    agent = AgentReflex()
    agent.run_cycle()
