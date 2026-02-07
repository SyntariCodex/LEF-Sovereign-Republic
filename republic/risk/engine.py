
import os
import json
from datetime import datetime

class RiskEngine:
    def __init__(self, db_path=None):
        if db_path:
            self.db_path = db_path
        else:
            # Default path resolution
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, 'republic.db')
        
        self._pool = None
            
        # Risk Constants
        self.STARTING_CAPITAL = 10000.0
        self.PROFIT_TARGET_THRESHOLD = 15000.0 # Start harvesting above $15k
        self.MAX_DRAWDOWN_THRESHOLD = 8000.0   # Stop trading below $8k

    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool

    def _get_conn(self):
        """Get a connection from the pool or fallback to direct connect."""
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=30.0), pool
        else:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=30.0), None

    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()
        
    def evaluate_portfolio_health(self):
        """
        Global Health Check.
        Returns: status (str), reason (str), action_items (list)
        """
        total_value = self._calculate_total_equity()
        
        status = "HEALTHY"
        action = "NONE"
        reason = f"Equity: ${total_value:,.2f}"
        
        # 1. Check for Massive Gains (Force Harvest)
        if total_value > self.PROFIT_TARGET_THRESHOLD:
            surplus = total_value - self.STARTING_CAPITAL
            status = "EUPHORIA"
            action = "FORCE_HARVEST"
            reason = f"Portfolio ATH (${total_value:,.2f}). Surplus: ${surplus:,.2f}. Harvest time."
            
        # 2. Check for Critical Drawdown
        elif total_value < self.MAX_DRAWDOWN_THRESHOLD:
            status = "CRITICAL"
            action = "DEFENSIVE_HALT"
            reason = f"Portfolio Drawdown Reached (${total_value:,.2f}). Halting Buys."
            
        return {
            "status": status,
            "action": action,
            "reason": reason,
            "equity": total_value
        }
        
    def _calculate_total_equity(self):
        """
        Calculates realistic liquidation value of portfolio.
        """
        conn, pool = self._get_conn()
        try:
            c = conn.cursor()
            
            # 1. Cash
            try:
                c.execute("SELECT sum(balance) FROM stablecoin_buckets")
                row = c.fetchone()
                cash = row[0] if row and row[0] else 0.0
            except sqlite3.Error:
                cash = 0.0
                
            # 2. Assets (using value_usd which is updated by Sentinel/Master)
            c.execute("SELECT sum(value_usd) FROM assets WHERE quantity > 0")
            row = c.fetchone()
            assets_val = row[0] if row and row[0] else 0.0
            
            return cash + assets_val
        finally:
            self._release_conn(conn, pool)

    def get_harvest_targets(self, amount_to_raise=1000.0):
        """
        Identifies assets to sell to raise 'amount_to_raise'.
        Strategy: Sell biggest bags first (rebalancing).
        """
        conn, pool = self._get_conn()
        try:
            c = conn.cursor()
            
            c.execute("SELECT symbol, quantity, value_usd FROM assets WHERE quantity > 0 ORDER BY value_usd DESC")
            holdings = c.fetchall()
            
            targets = []
            raised_so_far = 0.0
            
            for symbol, qty, val_usd in holdings:
                if raised_so_far >= amount_to_raise:
                    break
                    
                # Don't sell everything, just trim
                # Max trim per asset = 30% of position size
                trim_usd = val_usd * 0.30 
                
                # Or if we need less than that, take what we need
                needed = amount_to_raise - raised_so_far
                sell_usd = min(trim_usd, needed)
                
                # Calculate quantity
                if val_usd > 0:
                    sell_qty = qty * (sell_usd / val_usd)
                    targets.append({
                        "asset": symbol,
                        "action": "SELL",
                        "amount": sell_qty, # This is quantity, not USD
                        "estimated_usd": sell_usd,
                        "reason": "Risk Engine Harvest"
                    })
                    raised_so_far += sell_usd
                    
            return targets
        finally:
            self._release_conn(conn, pool)

if __name__ == "__main__":
    engine = RiskEngine()
    health = engine.evaluate_portfolio_health()
    print(json.dumps(health, indent=2))
    
    if health['action'] == "FORCE_HARVEST":
        print("\n[SUGGESTED TRADES]")
        from pprint import pprint
        pprint(engine.get_harvest_targets(amount_to_raise=2000))

