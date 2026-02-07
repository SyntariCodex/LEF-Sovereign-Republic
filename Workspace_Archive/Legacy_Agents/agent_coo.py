
"""
Agent COO (Chief Operating Officer)
The "Hands" of Fulcrum Capital.
Responsible for Logistics, Wallet Rebalancing, and Profit Allocation.
"""

import sqlite3
import time
import os
import json

class AgentCOO:
    def __init__(self, db_path: str = None):
        if db_path is None:
             # Robust Path: Go up one level from agents/ to fulcrum/
             BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        else:
             self.db_path = db_path
        self.running = True
        print("[COO] 🏗️  Chief Operating Officer is Online.")
        
    def run(self):
        """
        Maintenance Loop.
        """
        while self.running:
            try:
                # 1. Rebalance Wallets (Teleonomy Sorting)
                self._rebalance_wallets()
                
                # 2. Process Profits (The Waterfall)
                self.process_realized_profits()
                
                # 3. Prune Memory (Once a day? or every loop check)
                # Keep it simple: Check every loop but logic inside creates barrier
                
                time.sleep(15) # Pulse every 15s
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"[COO] ⚠️  Operations Error: {e}")
                time.sleep(5)

    def _rebalance_wallets(self):
        """
        Moves assets between Virtual Wallets based on Score.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Fetch Assets & Scores
        c.execute("""
            SELECT a.symbol, a.current_wallet_id, a.teleonomy_score, vw.name as wallet_name
            FROM assets a
            JOIN virtual_wallets vw ON a.current_wallet_id = vw.id
            WHERE a.teleonomy_score IS NOT NULL
        """)
        assets = c.fetchall()
        
        WALLETS = {'Dynasty': 1, 'Hunter': 2, 'Builder': 3, 'Yield': 4, 'Experimental': 5}
        
        for symbol, wallet_id, score, wallet_name in assets:
            if wallet_id == WALLETS['Yield']: continue # Skip Stablecoins
            
            target = None
            reason = ""
            
            # DYNAMIC GOVERNANCE (The Republic Decides)
            # Fetch thresholds from DB or use Canon defaults
            thresholds = self._get_governance_params(c)
            
            # DYNASTY: Preservation (Default 90)
            if score >= thresholds['dynasty_min'] and wallet_id != WALLETS['Dynasty']:
                target = WALLETS['Dynasty']
                reason = f"Promotion to Dynasty (Score > {thresholds['dynasty_min']})"
            
            # BUILDER: Accumulation (Default 70-90)
            elif thresholds['builder_min'] <= score < thresholds['dynasty_min'] and wallet_id != WALLETS['Builder']:
                target = WALLETS['Builder']
                reason = f"Move to Builder ({thresholds['builder_min']}-{thresholds['dynasty_min']})"
            
            # HUNTER: Tactical (Default 60-70)
            elif thresholds['hunter_min'] <= score < thresholds['builder_min'] and wallet_id != WALLETS['Hunter']:
                target = WALLETS['Hunter']
                reason = f"Move to Hunter ({thresholds['hunter_min']}-{thresholds['builder_min']})"
            
            # EXPERIMENTAL: The Lab (Default < 60)
            elif score < thresholds['hunter_min'] and wallet_id != WALLETS['Experimental']:
                target = WALLETS['Experimental']
                reason = f"Relegation to Lab (< {thresholds['hunter_min']})"
                
            if target:
                c.execute("UPDATE assets SET current_wallet_id=? WHERE symbol=?", (target, symbol))
                print(f"[COO] 📦 RELOCATION: {symbol} -> Wallet {target} ({reason})")
                
        conn.commit()
        conn.close()

    def process_realized_profits(self):
        """
        Allocates Wealth per the Waterfall Protocol.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Find Unallocated Profits
        c.execute("""
            SELECT t.id, t.asset, t.amount, t.price 
            FROM trade_queue t
            LEFT JOIN profit_allocation p ON t.id = p.trade_id
            WHERE t.action = 'SELL' AND t.status = 'EXECUTED' AND p.id IS NULL
        """)
        sells = c.fetchall()
        
        for trade_id, asset, amount, sell_price in sells:
            # Estimate Cost Basis
            c.execute("SELECT avg_buy_price FROM assets WHERE symbol=?", (asset,))
            row = c.fetchone()
            cost_basis = row[0] if row else (sell_price * 0.9)
            
            profit_per = sell_price - cost_basis
            total_profit = profit_per * amount
            
            if total_profit > 0:
                print(f"[COO] 💰 Profit Detected: ${total_profit:.2f}. Allocating to Buckets...")
                self._allocate(c, trade_id, total_profit)
            else:
                # Mark as processed (loss)
                c.execute("INSERT INTO profit_allocation (trade_id, profit_amount, bucket_type) VALUES (?, 0, 'LOSS')", (trade_id,))
        
        conn.commit()
        conn.close()

    def _allocate(self, c, trade_id, profit):
        """
        The Stewardship Protocol (Canon III).
        50% Tithe to SNW_LLC_USDC.
        Remainder (50%) Reinvested into Operations (INJECTION_DAI).
        """
        # 1. 50% Tithe to SNW (Southern Nevada Wildlands)
        tithe_amt = profit * 0.50
        
        # 2. 50% Reinvest to Operations (Hunter/Builder Fuel)
        reinvest_amt = profit * 0.50
        
        # Update Buckets
        c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='SNW_LLC_USDC'", (tithe_amt,))
        c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='INJECTION_DAI'", (reinvest_amt,))
        
        # Log Allocation
        alloc_msg = f"TITHE_50_50"
        c.execute("INSERT INTO profit_allocation (trade_id, profit_amount, bucket_type) VALUES (?, ?, ?)", (trade_id, profit, alloc_msg))
        
        print(f"[COO] 💸 Wealth Event: ${profit:.2f} -> ${tithe_amt:.2f} (SNW) / ${reinvest_amt:.2f} (Ops)")

    def _get_governance_params(self, cursor):
        """
        Fetches 'The Law' from the Governance Table.
        Falls back to Canon defaults if the Republic hasn't voted yet.
        """
        try:
            # Ensure Table Exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_governance (
                    param_key TEXT PRIMARY KEY,
                    param_value REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check for existing params
            cursor.execute("SELECT param_key, param_value FROM system_governance")
            rows = cursor.fetchall()
            params = {k: v for k, v in rows}
            
            # Default Canon Values
            defaults = {
                'dynasty_min': 90.0,
                'builder_min': 70.0,
                'hunter_min': 60.0
            }
            
            # If missing, initialize defaults (Bootstrap the Constitution)
            for k, v in defaults.items():
                if k not in params:
                    cursor.execute("INSERT INTO system_governance (param_key, param_value) VALUES (?, ?)", (k, v))
                    params[k] = v
                    print(f"[COO] 📜 Initialized Governance Param: {k} = {v}")
            
            return params
            
        except Exception as e:
            print(f"[COO] ⚠️ Governance Lookup Failed: {e}. Using Hard Defaults.")
            return {'dynasty_min': 90.0, 'builder_min': 70.0, 'hunter_min': 60.0}

if __name__ == "__main__":
    coo = AgentCOO()
    coo.run()
