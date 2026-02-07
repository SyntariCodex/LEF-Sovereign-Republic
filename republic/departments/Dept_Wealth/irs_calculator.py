"""
IRS Tax Calculator for Fulcrum
Calculates tax obligations for cryptocurrency trading in USA (Henderson, NV).

Features:
- Federal income tax (short-term vs long-term capital gains)
- State tax (Nevada has no state income tax)
- Self-employment tax (if applicable)
- Quarterly estimated tax payments
- Dynamic calculation based on realized gains
"""

from typing import Dict, Optional
from datetime import datetime
import sqlite3

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


class IRSCalculator:
    """
    Calculates IRS tax obligations for cryptocurrency trading.
    
    Location: Henderson, NV, USA
    - No state income tax (Nevada)
    - Federal tax only
    - Short-term capital gains: taxed as ordinary income
    - Long-term capital gains: preferential rates
    """
    
    # 2024 Federal Tax Brackets (Single Filer)
    FEDERAL_BRACKETS = [
        (0, 0.10),      # 10% up to $11,000
        (11000, 0.12),  # 12% $11,001-$44,725
        (44725, 0.22),  # 22% $44,726-$95,375
        (95375, 0.24),  # 24% $95,376-$182,050
        (182050, 0.32), # 32% $182,051-$231,250
        (231250, 0.35), # 35% $231,251-$578,125
        (578125, 0.37)  # 37% $578,126+
    ]
    
    # Long-term Capital Gains Rates (2024)
    LTCG_BRACKETS = [
        (0, 0.0),       # 0% up to $44,625
        (44625, 0.15),  # 15% $44,626-$492,300
        (492300, 0.20)  # 20% $492,301+
    ]
    
    # Self-employment tax rate (if trading is primary income)
    SE_TAX_RATE = 0.1413  # 14.13% (12.4% Social Security + 2.9% Medicare)
    SE_THRESHOLD = 400.0   # Only applies if net earnings > $400
    
    def __init__(self, db_path: str = None, location: str = "Henderson, NV, USA"):
        if db_path is None:
            import os
            import sys
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if BASE_DIR not in sys.path:
                sys.path.insert(0, BASE_DIR)
            self.db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
        else:
            self.db_path = db_path
        self.location = location
        self.is_nevada = "NV" in location or "Nevada" in location
        
        # Track tax year data
        self.tax_year_start = datetime(datetime.now().year, 1, 1)
        self.tax_year_end = datetime(datetime.now().year, 12, 31)
        
    def calculate_tax_on_gain(self, gain: float, holding_period_days: int, 
                             other_income: float = 0.0) -> Dict[str, float]:
        """
        Calculate tax on a capital gain.
        
        Args:
            gain: Realized capital gain (profit)
            holding_period_days: Days asset was held before sale
            other_income: Other income for the year (for bracket calculation)
        
        Returns:
            Dict with tax breakdown: {federal_tax, state_tax, total_tax, rate}
        """
        if gain <= 0:
            return {
                'federal_tax': 0.0,
                'state_tax': 0.0,
                'total_tax': 0.0,
                'effective_rate': 0.0,
                'is_long_term': False
            }
        
        # Determine if long-term (held > 365 days)
        is_long_term = holding_period_days > 365
        
        # Calculate federal tax
        if is_long_term:
            # Long-term capital gains (preferential rates)
            federal_tax = self._calculate_ltcg_tax(gain, other_income)
            effective_rate = federal_tax / gain if gain > 0 else 0.0
        else:
            # Short-term capital gains (taxed as ordinary income)
            federal_tax = self._calculate_ordinary_income_tax(gain, other_income)
            effective_rate = federal_tax / gain if gain > 0 else 0.0
        
        # Nevada has no state income tax
        state_tax = 0.0
        
        # Self-employment tax (if applicable)
        # Note: This is simplified - actual SE tax calculation is more complex
        se_tax = 0.0
        if gain > self.SE_THRESHOLD:
            # Simplified: apply SE tax to net trading income
            # In reality, SE tax applies to net earnings from self-employment
            se_tax = gain * self.SE_TAX_RATE * 0.5  # Only 50% is deductible
        
        total_tax = federal_tax + state_tax + se_tax
        
        return {
            'federal_tax': federal_tax,
            'state_tax': state_tax,
            'se_tax': se_tax,
            'total_tax': total_tax,
            'effective_rate': total_tax / gain if gain > 0 else 0.0,
            'is_long_term': is_long_term
        }
    
    def _calculate_ordinary_income_tax(self, income: float, other_income: float = 0.0) -> float:
        """Calculate federal income tax on ordinary income (short-term gains)."""
        total_income = income + other_income
        tax = 0.0
        prev_bracket = 0.0
        
        for bracket_floor, rate in self.FEDERAL_BRACKETS:
            if total_income > bracket_floor:
                taxable_in_bracket = min(total_income, bracket_floor) - prev_bracket
                if taxable_in_bracket > 0:
                    tax += taxable_in_bracket * rate
                prev_bracket = bracket_floor
            else:
                break
        
        # Calculate tax on the additional income
        if total_income > prev_bracket:
            remaining = total_income - prev_bracket
            # Find the highest bracket rate
            highest_rate = self.FEDERAL_BRACKETS[-1][1]
            for bracket_floor, rate in reversed(self.FEDERAL_BRACKETS):
                if total_income > bracket_floor:
                    highest_rate = rate
                    break
            tax += remaining * highest_rate
        
        return tax
    
    def _calculate_ltcg_tax(self, gain: float, other_income: float = 0.0) -> float:
        """Calculate federal tax on long-term capital gains."""
        # Long-term gains stack on top of ordinary income
        total_income = other_income + gain
        
        # Determine which bracket the total income falls into
        tax = 0.0
        
        for bracket_floor, rate in self.LTCG_BRACKETS:
            if total_income > bracket_floor:
                # Calculate tax on the portion in this bracket
                prev_bracket = self.LTCG_BRACKETS[self.LTCG_BRACKETS.index((bracket_floor, rate)) - 1][0] if self.LTCG_BRACKETS.index((bracket_floor, rate)) > 0 else 0
                taxable_in_bracket = min(total_income, bracket_floor) - prev_bracket
                if taxable_in_bracket > 0:
                    tax += taxable_in_bracket * rate
            else:
                break
        
        # Handle top bracket
        if total_income > self.LTCG_BRACKETS[-1][0]:
            remaining = total_income - self.LTCG_BRACKETS[-1][0]
            tax += remaining * self.LTCG_BRACKETS[-1][1]
        
        return tax
    
    def estimate_monthly_tax_obligation(self, year_to_date_gains: float, 
                                       month: Optional[int] = None) -> Dict[str, float]:
        """
        Estimate monthly tax obligation based on year-to-date gains.
        
        Uses conservative estimate: assumes all gains are short-term (higher tax rate).
        Includes quarterly estimated tax payment logic.
        
        Args:
            year_to_date_gains: Total realized gains for the year so far
            month: Current month (1-12), defaults to current month
        
        Returns:
            Dict with estimated tax obligation and breakdown
        """
        if month is None:
            month = datetime.now().month
        
        # Project annual gains (conservative: assume current pace continues)
        months_elapsed = month
        if months_elapsed > 0:
            projected_annual_gains = year_to_date_gains * (12.0 / months_elapsed)
        else:
            projected_annual_gains = year_to_date_gains
        
        # Calculate tax on projected annual gains (assume short-term for conservatism)
        tax_info = self.calculate_tax_on_gain(projected_annual_gains, 0)
        
        # Quarterly estimated tax payments (due: April, June, September, January)
        # We'll calculate what should have been paid so far
        quarterly_payment = tax_info['total_tax'] / 4.0
        
        # Determine which quarter we're in
        if month <= 3:
            quarters_due = 0  # Q1 not due yet
        elif month <= 5:
            quarters_due = 1  # Q1 due in April
        elif month <= 8:
            quarters_due = 2  # Q1, Q2 due
        elif month <= 12:
            quarters_due = 3  # Q1, Q2, Q3 due
        else:
            quarters_due = 4  # All quarters due
        
        estimated_monthly = quarterly_payment  # Monthly withdrawal amount
        total_estimated_due = quarterly_payment * quarters_due
        
        # Calculate what should be in IRS bucket
        # Conservative: set aside 30% of gains monthly, but adjust based on actual tax calculation
        recommended_monthly_set_aside = max(
            estimated_monthly,
            year_to_date_gains * 0.30  # At least 30% of gains
        )
        
        return {
            'projected_annual_gains': projected_annual_gains,
            'projected_annual_tax': tax_info['total_tax'],
            'quarterly_payment': quarterly_payment,
            'estimated_monthly': estimated_monthly,
            'recommended_monthly_set_aside': recommended_monthly_set_aside,
            'total_estimated_due': total_estimated_due,
            'quarters_due': quarters_due,
            'effective_tax_rate': tax_info['effective_rate']
        }
    
    def get_year_to_date_gains(self, year: Optional[int] = None) -> float:
        """
        Get total realized gains for the current tax year from database.
        
        Args:
            year: Tax year (defaults to current year)
        
        Returns:
            Total realized gains (profits) for the year
        """
        if year is None:
            year = datetime.now().year
        
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Get all profitable trades for the year
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            
            c.execute("""
                SELECT SUM(profit) 
                FROM trade_history 
                WHERE profit > 0 
                AND date >= ? AND date <= ?
            """, (year_start, year_end))
            
            result = c.fetchone()
            total_gains = result[0] if result[0] else 0.0
        
        return total_gains
    
    def calculate_quarterly_reallocation(self, irs_balance: float, 
                                        estimated_annual_tax: float) -> Dict[str, float]:
        """
        Calculate if excess funds should be reallocated from IRS bucket to DAI bucket.
        
        Logic:
        - If IRS bucket has more than 120% of estimated annual tax obligation, reallocate excess
        - Reallocation happens quarterly (every 3 months)
        
        Args:
            irs_balance: Current balance in IRS_USDT bucket
            estimated_annual_tax: Estimated total tax for the year
        
        Returns:
            Dict with reallocation recommendation: {should_reallocate, excess_amount, reason}
        """
        # Safety buffer: keep 120% of estimated tax in IRS bucket
        target_balance = estimated_annual_tax * 1.20
        
        if irs_balance > target_balance:
            excess = irs_balance - target_balance
            return {
                'should_reallocate': True,
                'excess_amount': excess,
                'current_balance': irs_balance,
                'target_balance': target_balance,
                'reason': f'IRS bucket has ${excess:,.2f} excess above 120% of estimated tax obligation'
            }
        else:
            return {
                'should_reallocate': False,
                'excess_amount': 0.0,
                'current_balance': irs_balance,
                'target_balance': target_balance,
                'reason': 'IRS bucket balance is within safe range'
            }

# Usage Example
if __name__ == "__main__":
    calculator = IRSCalculator()
    
    # Test tax calculation
    print("Testing IRS Tax Calculator...")
    print(f"Location: {calculator.location}")
    print(f"Nevada (no state tax): {calculator.is_nevada}\n")
    
    # Short-term gain
    st_gain = 10000.0
    st_tax = calculator.calculate_tax_on_gain(st_gain, 100)  # 100 days = short-term
    print(f"Short-term gain: ${st_gain:,.2f}")
    print(f"  Federal tax: ${st_tax['federal_tax']:,.2f}")
    print(f"  Effective rate: {st_tax['effective_rate']*100:.2f}%\n")
    
    # Long-term gain
    lt_gain = 10000.0
    lt_tax = calculator.calculate_tax_on_gain(lt_gain, 400)  # 400 days = long-term
    print(f"Long-term gain: ${lt_gain:,.2f}")
    print(f"  Federal tax: ${lt_tax['federal_tax']:,.2f}")
    print(f"  Effective rate: {lt_tax['effective_rate']*100:.2f}%\n")
    
    # Monthly estimate
    ytd_gains = 50000.0
    monthly_est = calculator.estimate_monthly_tax_obligation(ytd_gains, month=6)
    print(f"Year-to-date gains: ${ytd_gains:,.2f} (Month 6)")
    print(f"  Projected annual: ${monthly_est['projected_annual_gains']:,.2f}")
    print(f"  Recommended monthly set-aside: ${monthly_est['recommended_monthly_set_aside']:,.2f}")
