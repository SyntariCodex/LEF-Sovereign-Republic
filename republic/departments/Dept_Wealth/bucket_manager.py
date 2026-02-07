"""
Stablecoin Bucket Manager
Manages profit allocation to USDT (IRS), USDC (SNW/LLC), DAI (injections).

Phase 1: Routes profits to appropriate buckets for tax compliance and operations.
"""

import sqlite3
from typing import Dict, Optional
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


class BucketManager:
    """
    Manages stablecoin buckets for profit allocation.
    
    Buckets:
    - IRS_USDT: 30% of profits → Tax payments
    - SNW_LLC_USDC: 50% of profits → SNW/LLC operations (earns interest)
    - INJECTION_DAI: 100% of injections → Capital injections
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            import os
            import sys
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if BASE_DIR not in sys.path:
                sys.path.insert(0, BASE_DIR)
            self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        else:
            self.db_path = db_path
        self.profit_allocation = {
            'IRS_USDT': 0.30,      # 30% to IRS bucket
            'SNW_LLC_USDC': 0.0,   # STUBBED: Was 50%, reactivate when SNW funding begins
            'RESERVE': 0.70        # 70% stays in trading wallets (was 20%, absorbed SNW's 50%)
        }
    
    def allocate_profit(self, profit_amount: float, trade_id: Optional[int] = None) -> Dict[str, float]:
        """
        Allocates realized profit to stablecoin buckets.
        
        Args:
            profit_amount: Profit from trade (must be positive)
            trade_id: Optional trade ID for tracking
        
        Returns:
            Dict showing allocation breakdown
        """
        if profit_amount <= 0:
            return {}
        
        allocations = {}
        
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Allocate to IRS bucket (USDT)
            irs_amount = profit_amount * self.profit_allocation['IRS_USDT']
            if irs_amount > 0:
                c.execute("""
                    UPDATE stablecoin_buckets 
                    SET balance = balance + ?, last_updated = CURRENT_TIMESTAMP
                    WHERE bucket_type = 'IRS_USDT'
                """, (irs_amount,))
                allocations['IRS_USDT'] = irs_amount
            
            # Allocate to SNW/LLC bucket (USDC) — STUBBED
            # snw_amount = profit_amount * self.profit_allocation['SNW_LLC_USDC']
            # if snw_amount > 0:
            #     c.execute("""
            #         UPDATE stablecoin_buckets 
            #         SET balance = balance + ?, last_updated = CURRENT_TIMESTAMP
            #         WHERE bucket_type = 'SNW_LLC_USDC'
            #     """, (snw_amount,))
            #     allocations['SNW_LLC_USDC'] = snw_amount
            
            # Log allocation
            if trade_id:
                for bucket_type, amount in allocations.items():
                    c.execute("""
                        INSERT INTO profit_allocation (trade_id, profit_amount, bucket_type)
                        VALUES (?, ?, ?)
                    """, (trade_id, amount, bucket_type))
            
            conn.commit()
        
        return allocations
    
    def add_injection(self, injection_amount: float) -> bool:
        """
        Adds capital injection to DAI bucket.
        
        Args:
            injection_amount: Amount to inject (in USD)
        
        Returns:
            True if successful
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE stablecoin_buckets 
                SET balance = balance + ?, last_updated = CURRENT_TIMESTAMP
                WHERE bucket_type = 'INJECTION_DAI'
            """, (injection_amount,))
            conn.commit()
        
        return True
    
    def withdraw_from_dai(self, amount: float) -> bool:
        """
        Withdraws from DAI bucket for capital injections.
        
        Args:
            amount: Amount to withdraw
        
        Returns:
            True if successful, False if insufficient balance
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Check balance
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type = 'INJECTION_DAI'")
            balance = c.fetchone()[0]
            
            if balance < amount:
                return False
            
            # Withdraw
            c.execute("""
                UPDATE stablecoin_buckets 
                SET balance = balance - ?, last_updated = CURRENT_TIMESTAMP
                WHERE bucket_type = 'INJECTION_DAI'
            """, (amount,))
            
            conn.commit()
            return True
    
    def get_bucket_balances(self) -> Dict[str, Dict]:
        """
        Gets current balances for all buckets.
        
        Returns:
            Dict with bucket info: {bucket_type: {balance, stablecoin, purpose, interest_rate}}
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                SELECT bucket_type, stablecoin, purpose, balance, interest_rate, last_updated
                FROM stablecoin_buckets
            """)
            
            buckets = {}
            for row in c.fetchall():
                bucket_type, stablecoin, purpose, balance, interest_rate, last_updated = row
                buckets[bucket_type] = {
                    'stablecoin': stablecoin,
                    'purpose': purpose,
                    'balance': balance,
                    'interest_rate': interest_rate,
                    'last_updated': last_updated
                }
            
            return buckets
    
    def calculate_interest(self, days: int = 30) -> Dict[str, float]:
        """
        Calculates interest earned on buckets over time period.
        
        Args:
            days: Number of days to calculate interest for
        
        Returns:
            Dict with interest earned per bucket
        """
        buckets = self.get_bucket_balances()
        interest = {}
        
        for bucket_type, info in buckets.items():
            balance = info['balance']
            rate = info['interest_rate']
            
            if balance > 0 and rate > 0:
                # Simple interest calculation
                daily_rate = rate / 365.0
                interest_earned = balance * daily_rate * days
                interest[bucket_type] = interest_earned
            else:
                interest[bucket_type] = 0.0
        
        return interest
    
    def get_total_wealth(self) -> Dict[str, float]:
        """
        Gets total wealth across all buckets.
        
        Returns:
            Dict with breakdown: {total, by_bucket, with_interest}
        """
        buckets = self.get_bucket_balances()
        
        total = sum(info['balance'] for info in buckets.values())
        by_bucket = {k: v['balance'] for k, v in buckets.items()}
        
        # Calculate projected interest (30 days)
        interest_30d = self.calculate_interest(30)
        with_interest_30d = total + sum(interest_30d.values())
        
        return {
            'total': total,
            'by_bucket': by_bucket,
            'interest_30d': interest_30d,
            'with_interest_30d': with_interest_30d
        }
    
    def withdraw_for_irs(self, amount: float) -> bool:
        """
        Withdraws from IRS bucket for tax payments.
        
        Args:
            amount: Amount to withdraw
        
        Returns:
            True if successful, False if insufficient balance
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Check balance
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type = 'IRS_USDT'")
            balance = c.fetchone()[0]
            
            if balance < amount:
                return False
            
            # Withdraw
            c.execute("""
                UPDATE stablecoin_buckets 
                SET balance = balance - ?, last_updated = CURRENT_TIMESTAMP
                WHERE bucket_type = 'IRS_USDT'
            """, (amount,))
            
            conn.commit()
            return True
    
    def withdraw_for_snw_llc(self, amount: float) -> bool:
        """
        Withdraws from SNW/LLC bucket for operations.
        
        Args:
            amount: Amount to withdraw
        
        Returns:
            True if successful, False if insufficient balance
        """
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Check balance
            c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type = 'SNW_LLC_USDC'")
            balance = c.fetchone()[0]
            
            if balance < amount:
                return False
            
            # Withdraw
            c.execute("""
                UPDATE stablecoin_buckets 
                SET balance = balance - ?, last_updated = CURRENT_TIMESTAMP
                WHERE bucket_type = 'SNW_LLC_USDC'
            """, (amount,))
            
            conn.commit()
            return True

# Usage Example
if __name__ == "__main__":
    manager = BucketManager()
    
    # Test profit allocation
    print("Allocating $1000 profit...")
    allocations = manager.allocate_profit(1000.0)
    print(f"Allocations: {allocations}")
    
    # Get balances
    balances = manager.get_bucket_balances()
    print("\nBucket Balances:")
    for bucket_type, info in balances.items():
        print(f"  {bucket_type}: ${info['balance']:,.2f} ({info['stablecoin']})")
    
    # Get total wealth
    wealth = manager.get_total_wealth()
    print(f"\nTotal Wealth: ${wealth['total']:,.2f}")
    print(f"With 30-day interest: ${wealth['with_interest_30d']:,.2f}")