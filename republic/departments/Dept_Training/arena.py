"""
The Arena (Simulator V2)
Supports Competitions between Strategies.
"""
import sqlite3
import json
import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


# Configure Logging
logging.basicConfig(level=logging.ERROR) # Only show errors, we print our own report

# Adjust Path
# Adjust Path to Republic Root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from db.db_setup import init_db
from departments.Dept_Wealth.agent_portfolio_mgr import AgentPortfolioMgr

TRAINING_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training.db')

class MockRedis:
    """
    Lightweight mock for training environment (by design).
    Isolates training from production Redis.
    """
    def __init__(self): self.store = {}
    def get(self, key): return self.store.get(key)
    def set(self, key, value): self.store[key] = value

class StrategyPlayer:
    """Base class for a player in the competition."""
    def __init__(self, name, initial_capital=10000.0):
        self.name = name
        self.cash = initial_capital
        self.holdings = 0.0
        self.trades = []
        self.history = [] # Value over time
        
    def decide(self, price, rsi, sma):
        return None # Return ('BUY', usd_amount) or ('SELL', unit_amount)
        
    def execute(self, action, amount, price, timestamp):
        if action == 'BUY':
            cost = amount
            if self.cash >= cost:
                units = cost / price
                self.cash -= cost
                self.holdings += units
                self.trades.append({'time': timestamp, 'side': 'BUY', 'price': price, 'amt': cost})
                return True
        elif action == 'SELL':
            units = amount
            if self.holdings >= units:
                proceeds = units * price
                self.holdings -= units
                self.cash += proceeds
                self.trades.append({'time': timestamp, 'side': 'SELL', 'price': price, 'amt': proceeds})
                return True
        return False
        
    def get_value(self, price):
        return self.cash + (self.holdings * price)

class HodlPlayer(StrategyPlayer):
    def decide(self, price, rsi, sma):
        if self.cash > 0:
            return ('BUY', self.cash)
        return None

class DegenPlayer(StrategyPlayer):
    """Buys if RSI < 30, Sells if RSI > 70. 100% position size."""
    def decide(self, price, rsi, sma):
        val = self.get_value(price)
        if rsi < 30 and self.cash > 10:
             return ('BUY', self.cash)
        elif rsi > 70 and self.holdings > 0:
             return ('SELL', self.holdings)
        return None

class LefPlayer(StrategyPlayer):
    """Wraps the actual AgentPortfolioMgr logic."""
    def __init__(self, name, db_path, redis):
        super().__init__(name)
        self.agent = AgentPortfolioMgr(db_path=db_path)
        self.agent.r = redis
        # Monkey patch load_config to prevent reload
        self.agent.load_config = lambda: None
        
        # Ensure Arena is configured
        if 'ARENA' not in self.agent.strategy_config:
            self.agent.strategy_config['ARENA'] = {}
        self.agent.strategy_config['ARENA']['trade_size_usd'] = 2000.0 # Bet size
        self.agent.strategy_config['ARENA']['LADDER_SELLS'] = [{"threshold": 0.20, "sell_pct": 0.5}, {"threshold": 0.50, "sell_pct": 1.0}]

        # We need to bridge the Agent's DB output to this Player's execution
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def prepare_state(self, price, rsi, sma, asset):
        # Update Redis so Agent sees the world
        self.agent.r.set(f"price:{asset}", price)
        self.agent.r.set(f"rsi:{asset}", rsi)
        self.agent.r.set(f"sma:{asset}", sma)
        
        # Update DB assets so Agent sees its holdings
        # We cheat and sync the Agent's DB knowledge with our Player state
        self.cursor.execute("DELETE FROM assets WHERE symbol=?", (asset,))
        if self.holdings > 0:
             avg_price = price # Simplified
             self.cursor.execute("INSERT INTO assets (symbol, quantity, avg_buy_price) VALUES (?, ?, ?)", (asset, self.holdings, avg_price))
             
        self.cursor.execute("UPDATE stablecoin_buckets SET balance=? WHERE bucket_type='INJECTION_DAI'", (self.cash,))
        self.conn.commit()

    def decide(self, price, rsi, sma):
        # 1. Run Agent Cycle
        self.agent.run_cycle()
        
        # 2. Check Trade Queue
        self.cursor.execute("SELECT rowid, action, amount, reason FROM trade_queue WHERE status IN ('NEW', 'APPROVED')")
        orders = self.cursor.fetchall()
        
        decision = None
        for order in orders:
            oid, action, amount, reason = order
            decision = (action, amount)
            
            # Clear Queue
            self.cursor.execute("UPDATE trade_queue SET status='FILLED' WHERE rowid=?", (oid,))
            self.conn.commit()
            break # Only one action per tick for simplicity
            
        return decision

class Competition:
    def __init__(self, scenario_file):
        if os.path.exists(TRAINING_DB_PATH): os.remove(TRAINING_DB_PATH)
        init_db(TRAINING_DB_PATH) # Needed for LEF Agent
        
        with open(scenario_file, 'r') as f:
            self.scenario = json.load(f)
            
        self.candles = self.scenario['data']
        self.asset = self.scenario['asset'].split('-')[0]
        self.mock_redis = MockRedis()
        
        # Players
        self.players = [
            HodlPlayer("HODLBot"),
            DegenPlayer("DegenBot"),
            LefPlayer("LEF_Prime", TRAINING_DB_PATH, self.mock_redis)
        ]
        
    def calculate_ta(self, history):
         # RSI
         period = 14
         if len(history) < period + 1: rsi = 50.0
         else:
             deltas = [history[i] - history[i-1] for i in range(1, len(history))]
             gains = [d if d > 0 else 0 for d in deltas]
             losses = [-d if d < 0 else 0 for d in deltas]
             avg_gain = sum(gains[-period:]) / period
             avg_loss = sum(losses[-period:]) / period
             if avg_loss == 0: rsi = 100.0
             else: rsi = 100 - (100 / (1 + (avg_gain/avg_loss)))
             
         # SMA
         sma_p = 50
         if len(history) < sma_p: sma = history[-1]
         else: sma = sum(history[-sma_p:]) / sma_p
         
         return rsi, sma

    def run(self):
        print(f"🏟️  STARTING COMPETITION: {self.scenario['name']}")
        price_history = []
        
        start_time = time.time()
        
        for i, candle in enumerate(self.candles):
            ts, _, _, _, price, _ = candle
            price_history.append(price)
            rsi, sma = self.calculate_ta(price_history)
            
            # Agents Act
            for p in self.players:
                # Prepare (if needed)
                if isinstance(p, LefPlayer):
                    p.prepare_state(price, rsi, sma, self.asset)
                    
                # Decide
                decision = p.decide(price, rsi, sma)
                
                # Execute
                if decision:
                    action, amt = decision
                    p.execute(action, amt, price, ts)
                    
            # Progress
            if i % 100 == 0:
                print(f"\rStep {i}/{len(self.candles)} | Price: ${price:.2f}", end="")
                
        print(f"\n✅ Competition Finished in {time.time() - start_time:.2f}s")
        self.generare_report(price_history[-1])

    def generare_report(self, final_price):
        print("\n🏆 LEADERBOARD 🏆")
        print(f"Scenario: {self.scenario['name']} | Final Price: ${final_price:.2f}")
        print("-" * 60)
        print(f"{'PLAYER':<15} | {'FINAL VALUE':<15} | {'ROI':<10} | {'TRADES':<6}")
        print("-" * 60)
        
        ranked = sorted(self.players, key=lambda p: p.get_value(final_price), reverse=True)
        
        for p in ranked:
            val = p.get_value(final_price)
            roi = ((val - 10000) / 10000) * 100
            print(f"{p.name:<15} | ${val:,.2f}       | {roi:+.2f}%    | {len(p.trades):<6}")
        print("-" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario', help='Scenario file')
    args = parser.parse_args()
    
    path = os.path.join(BASE_DIR, 'training', 'scenarios', args.scenario)
    if os.path.exists(path):
        comp = Competition(path)
        comp.run()
    else:
        print("Scenario not found")
