"""
Trade Validator - Sanity Checks for LEF Trading

Prevents numerical overflow and unrealistic trades by validating:
1. Position sizes (max per asset, max total)
2. Trade amounts (reasonable quantities)
3. Proceeds calculations (reality checks)
4. Price sanity (within expected ranges)

Usage:
    from system.trade_validator import TradeValidator
    
    validator = TradeValidator()
    is_valid, reason = validator.validate_trade(
        asset='BTC',
        action='BUY',
        amount_qty=0.5,
        price=45000.0,
        proceeds=22500.0
    )
"""

import logging
from typing import Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradingLimits:
    """
    Constitutional trading limits for LEF.
    These are hard caps that prevent runaway calculations.
    """
    # Position limits (per asset)
    MAX_POSITION_VALUE_USD: float = 50000.0  # Max $50K in any single asset
    MAX_POSITION_PCT_NAV: float = 0.25       # Max 25% of NAV in single position
    
    # Trade limits (per trade)
    MAX_TRADE_VALUE_USD: float = 10000.0     # Max $10K per trade
    MIN_TRADE_VALUE_USD: float = 1.0         # Min $1 per trade
    
    # Quantity sanity limits (prevents overflow)
    MAX_QUANTITY_NORMAL: float = 1e12        # 1 trillion - reasonable for memecoins
    MAX_QUANTITY_MICRO: float = 1e15         # 1 quadrillion - extreme edge case
    OVERFLOW_THRESHOLD: float = 1e18         # If we see this, it's definitely overflow
    
    # Proceeds sanity limits
    MAX_PROCEEDS_USD: float = 100000.0       # Max $100K proceeds per trade
    MAX_PROFIT_PER_TRADE: float = 50000.0    # Max $50K profit per trade
    
    # Price sanity (per token)
    MIN_PRICE_USD: float = 1e-12             # Floor for micro-cap tokens
    MAX_PRICE_USD: float = 1e6               # $1M cap (covers BTC growth)
    
    # Reality checks
    MAX_NAV: float = 1e9                     # $1B NAV cap (definitely overflow if exceeded)
    STARTING_CAPITAL: float = 8000.0         # Constitutional starting capital


class TradeValidator:
    """
    Validates trades before execution to prevent overflow and unrealistic values.
    """
    
    def __init__(self, limits: Optional[TradingLimits] = None):
        self.limits = limits or TradingLimits()
    
    def validate_quantity(self, asset: str, quantity: float) -> Tuple[bool, str]:
        """
        Check if quantity is within sane bounds.
        """
        if quantity <= 0:
            return False, f"Quantity must be positive, got {quantity}"
        
        # Check for obvious overflow
        if quantity >= self.limits.OVERFLOW_THRESHOLD:
            logger.error(f"[VALIDATOR] 🚨 OVERFLOW DETECTED: {asset} quantity {quantity:,.0f}")
            return False, f"Quantity overflow: {quantity:,.0f} exceeds {self.limits.OVERFLOW_THRESHOLD:,.0f}"
        
        # Check for extreme but possibly valid quantities (memecoins)
        if quantity >= self.limits.MAX_QUANTITY_MICRO:
            logger.warning(f"[VALIDATOR] ⚠️ Extreme quantity: {asset} = {quantity:,.0f}")
            return False, f"Quantity {quantity:,.0f} exceeds micro limit {self.limits.MAX_QUANTITY_MICRO:,.0f}"
        
        # Normal validation
        if quantity >= self.limits.MAX_QUANTITY_NORMAL:
            logger.warning(f"[VALIDATOR] ⚠️ Large quantity: {asset} = {quantity:,.0f}")
            # Allow but warn - memecoins can have billions of tokens
        
        return True, "OK"
    
    def validate_price(self, asset: str, price: float) -> Tuple[bool, str]:
        """
        Check if price is within expected range.
        """
        if price <= 0:
            return False, f"Price must be positive, got {price}"
        
        if price < self.limits.MIN_PRICE_USD:
            return False, f"Price {price} below minimum {self.limits.MIN_PRICE_USD}"
        
        if price > self.limits.MAX_PRICE_USD:
            return False, f"Price ${price:,.2f} exceeds maximum ${self.limits.MAX_PRICE_USD:,.2f}"
        
        return True, "OK"
    
    def validate_proceeds(self, asset: str, proceeds: float, action: str) -> Tuple[bool, str]:
        """
        Check if proceeds/cost is within sane bounds.
        """
        if proceeds <= 0:
            return False, f"Proceeds must be positive, got {proceeds}"
        
        # Flag any trade with proceeds over our max
        if proceeds > self.limits.MAX_PROCEEDS_USD:
            logger.error(f"[VALIDATOR] 🚨 PROCEEDS OVERFLOW: {action} {asset} = ${proceeds:,.2f}")
            return False, f"Proceeds ${proceeds:,.2f} exceeds maximum ${self.limits.MAX_PROCEEDS_USD:,.2f}"
        
        return True, "OK"
    
    def validate_trade(
        self, 
        asset: str, 
        action: str, 
        amount_qty: float, 
        price: float,
        proceeds: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Full trade validation.
        
        Args:
            asset: Token symbol
            action: 'BUY' or 'SELL'
            amount_qty: Number of tokens
            price: Price per token in USD
            proceeds: Optional pre-calculated proceeds (will verify)
            
        Returns:
            (is_valid, reason)
        """
        # 1. Validate quantity
        valid, reason = self.validate_quantity(asset, amount_qty)
        if not valid:
            return False, reason
        
        # 2. Validate price
        valid, reason = self.validate_price(asset, price)
        if not valid:
            return False, reason
        
        # 3. Calculate and validate proceeds
        calculated_proceeds = amount_qty * price
        
        if proceeds is not None:
            # Verify provided proceeds matches calculation (within tolerance)
            tolerance = 0.01  # 1% tolerance for floating point
            if abs(calculated_proceeds - proceeds) / max(calculated_proceeds, proceeds) > tolerance:
                return False, f"Proceeds mismatch: calculated ${calculated_proceeds:,.2f} vs provided ${proceeds:,.2f}"
        
        valid, reason = self.validate_proceeds(asset, calculated_proceeds, action)
        if not valid:
            return False, reason
        
        # 4. Validate trade size against limits
        if calculated_proceeds > self.limits.MAX_TRADE_VALUE_USD:
            logger.warning(f"[VALIDATOR] Trade exceeds max size: ${calculated_proceeds:,.2f} > ${self.limits.MAX_TRADE_VALUE_USD:,.2f}")
            return False, f"Trade value ${calculated_proceeds:,.2f} exceeds limit ${self.limits.MAX_TRADE_VALUE_USD:,.2f}"
        
        if calculated_proceeds < self.limits.MIN_TRADE_VALUE_USD:
            return False, f"Trade value ${calculated_proceeds:,.2f} below minimum ${self.limits.MIN_TRADE_VALUE_USD:,.2f}"
        
        logger.info(f"[VALIDATOR] ✅ Trade validated: {action} {amount_qty:,.4f} {asset} @ ${price:,.4f} = ${calculated_proceeds:,.2f}")
        return True, "OK"
    
    def validate_profit_allocation(self, realized_gain: float) -> Tuple[bool, str]:
        """
        Validate profit amount before allocation to buckets.
        """
        if realized_gain <= 0:
            return False, f"Realized gain must be positive, got {realized_gain}"
        
        if realized_gain > self.limits.MAX_PROFIT_PER_TRADE:
            logger.error(f"[VALIDATOR] 🚨 PROFIT OVERFLOW: ${realized_gain:,.2f}")
            return False, f"Profit ${realized_gain:,.2f} exceeds maximum ${self.limits.MAX_PROFIT_PER_TRADE:,.2f}"
        
        return True, "OK"
    
    def cap_quantity(self, quantity: float, price: float) -> float:
        """
        Cap quantity to keep trade within limits.
        Returns adjusted quantity.
        """
        max_qty = self.limits.MAX_TRADE_VALUE_USD / price
        if quantity > max_qty:
            logger.warning(f"[VALIDATOR] Capping quantity from {quantity:,.4f} to {max_qty:,.4f}")
            return max_qty
        return quantity
    
    def is_overflow(self, value: float) -> bool:
        """
        Quick check for obvious overflow values.
        """
        return value >= self.limits.OVERFLOW_THRESHOLD


# Singleton for global access
_validator_instance = None

def get_validator() -> TradeValidator:
    """Get the global validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = TradeValidator()
    return _validator_instance


def validate_trade(asset: str, action: str, amount_qty: float, price: float) -> Tuple[bool, str]:
    """Convenience function for quick validation."""
    return get_validator().validate_trade(asset, action, amount_qty, price)


if __name__ == "__main__":
    # Test cases
    validator = TradeValidator()
    
    print("=== Trade Validator Tests ===\n")
    
    # Valid trade
    valid, reason = validator.validate_trade("BTC", "BUY", 0.1, 45000.0)
    print(f"Valid trade: {valid} - {reason}")
    
    # Overflow quantity
    valid, reason = validator.validate_trade("PEPE", "SELL", 1e20, 0.00001)
    print(f"Overflow quantity: {valid} - {reason}")
    
    # Extreme proceeds
    valid, reason = validator.validate_trade("SOL", "BUY", 1000000, 150.0)
    print(f"Extreme proceeds: {valid} - {reason}")
    
    # Valid memecoin trade
    valid, reason = validator.validate_trade("BONK", "BUY", 100000000, 0.00001)  # $1000
    print(f"Valid memecoin: {valid} - {reason}")
    
    # Profit validation
    valid, reason = validator.validate_profit_allocation(5000.0)
    print(f"Valid profit: {valid} - {reason}")
    
    valid, reason = validator.validate_profit_allocation(1e15)
    print(f"Overflow profit: {valid} - {reason}")
