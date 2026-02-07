"""
MEVProtection (The Invisible Hand)
Anti-frontrunning strategies for centralized exchange trading.

Since LEF trades on Coinbase (CEX), traditional Flashbots doesn't apply.
This module implements CEX-specific MEV protection:
- Timing randomization (unpredictable execution)
- Order splitting (iceberg orders)
- Slippage guards (abort if price moved)
- Whale detection (unusual volume warning)

Usage:
    from republic.system.mev_protection import get_mev_protection
    
    mev = get_mev_protection()
    rec = mev.get_execution_recommendation("BTC", 1000)
    if rec['delay']: time.sleep(rec['delay'])
    if rec['split']: orders = mev.split_large_order(1000, rec['max_slice'])
"""

import random
import time
import logging
import os
import redis
from typing import Dict, List, Optional, Tuple


class MEVProtection:
    """
    Anti-frontrunning strategies for CEX trading.
    
    Protects against:
    - Pattern-based frontrunning (timing randomization)
    - Large order detection (iceberg splitting)
    - Price manipulation (slippage guards)
    - Whale sandwiching (volume anomaly detection)
    """
    
    # Configuration thresholds
    LARGE_ORDER_USD = 500.0          # Orders above this get split
    MAX_SLICE_USD = 200.0            # Maximum slice size
    MIN_DELAY_SEC = 0.5              # Minimum random delay
    MAX_DELAY_SEC = 3.0              # Maximum random delay
    SLIPPAGE_TOLERANCE = 0.02        # 2% max acceptable slippage
    VOLUME_SPIKE_THRESHOLD = 3.0     # 3x average = suspicious
    
    def __init__(self, redis_client=None):
        """Initialize MEV protection with optional Redis for market data."""
        if redis_client:
            self.r = redis_client
        else:
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                self.r = redis.Redis(host=redis_host, port=6379, db=0)
                self.r.ping()
            except (redis.RedisError, ConnectionError):
                self.r = None
                logging.debug("[MEV] Redis unavailable, some features limited")
    
    def randomize_timing(self, delay_range: Tuple[float, float] = None) -> float:
        """
        Generate random delay before execution.
        
        Prevents pattern-based frontrunning by making execution timing
        unpredictable to observers.
        
        Returns:
            Delay in seconds to wait before executing
        """
        if delay_range is None:
            delay_range = (self.MIN_DELAY_SEC, self.MAX_DELAY_SEC)
        
        delay = random.uniform(delay_range[0], delay_range[1])
        logging.debug(f"[MEV] 🎲 Randomized delay: {delay:.2f}s")
        return delay
    
    def split_large_order(
        self,
        amount_usd: float,
        max_slice: float = None
    ) -> List[float]:
        """
        Split large orders into smaller chunks (iceberg strategy).
        
        Large orders are visible targets for sandwich attacks.
        Splitting makes them harder to detect and exploit.
        
        Args:
            amount_usd: Total order size in USD
            max_slice: Maximum size per slice (defaults to MAX_SLICE_USD)
            
        Returns:
            List of slice amounts
        """
        if max_slice is None:
            max_slice = self.MAX_SLICE_USD
        
        if amount_usd <= max_slice:
            return [amount_usd]
        
        slices = []
        remaining = amount_usd
        
        while remaining > 0:
            # Random slice size between 50% and 100% of max
            # Adds unpredictability to order patterns
            slice_size = min(
                remaining,
                random.uniform(max_slice * 0.5, max_slice)
            )
            slices.append(round(slice_size, 2))
            remaining -= slice_size
        
        logging.info(f"[MEV] 🧊 Iceberg: ${amount_usd:.2f} → {len(slices)} slices")
        return slices
    
    def check_slippage_guard(
        self,
        symbol: str,
        intended_price: float,
        tolerance: float = None
    ) -> Tuple[bool, float]:
        """
        Check if current price is within acceptable range of intended price.
        
        Aborts trade if price has moved too much since order was generated,
        which could indicate manipulation or rapid market movement.
        
        Args:
            symbol: Asset symbol
            intended_price: Price when order was generated
            tolerance: Maximum acceptable deviation (default 2%)
            
        Returns:
            (is_safe, current_price) tuple
        """
        if tolerance is None:
            tolerance = self.SLIPPAGE_TOLERANCE
        
        current_price = self._get_current_price(symbol)
        if current_price is None:
            logging.warning(f"[MEV] Cannot check slippage - no price for {symbol}")
            return True, intended_price  # Allow trade, best effort
        
        deviation = abs(current_price - intended_price) / intended_price
        is_safe = deviation <= tolerance
        
        if not is_safe:
            logging.warning(
                f"[MEV] ⚠️ SLIPPAGE GUARD: {symbol} moved {deviation*100:.2f}% "
                f"(intended: ${intended_price:.2f}, current: ${current_price:.2f})"
            )
        
        return is_safe, current_price
    
    def detect_whale_activity(self, symbol: str) -> Dict:
        """
        Detect unusual volume that could indicate whale manipulation.
        
        High volume spikes often precede sandwich attacks or pump-and-dumps.
        
        Returns:
            Dict with 'suspicious', 'volume_ratio', 'recommendation'
        """
        if not self.r:
            return {'suspicious': False, 'volume_ratio': 1.0, 'recommendation': 'PROCEED'}
        
        try:
            # Get recent volume from Redis (populated by AgentGladiator)
            volume_key = f"volume_24h:{symbol}"
            avg_volume_key = f"volume_avg:{symbol}"
            
            current_vol = self.r.get(volume_key)
            avg_vol = self.r.get(avg_volume_key)
            
            if not current_vol or not avg_vol:
                return {'suspicious': False, 'volume_ratio': 1.0, 'recommendation': 'PROCEED'}
            
            ratio = float(current_vol) / float(avg_vol)
            suspicious = ratio > self.VOLUME_SPIKE_THRESHOLD
            
            if suspicious:
                logging.warning(f"[MEV] 🐋 WHALE ALERT: {symbol} volume {ratio:.1f}x normal")
            
            return {
                'suspicious': suspicious,
                'volume_ratio': round(ratio, 2),
                'recommendation': 'CAUTION' if suspicious else 'PROCEED'
            }
        except Exception as e:
            logging.debug(f"[MEV] Whale detection error: {e}")
            return {'suspicious': False, 'volume_ratio': 1.0, 'recommendation': 'PROCEED'}
    
    def get_execution_recommendation(
        self,
        symbol: str,
        amount_usd: float,
        intended_price: float = None
    ) -> Dict:
        """
        Get comprehensive execution recommendation.
        
        Combines all MEV protection strategies into a single recommendation.
        
        Args:
            symbol: Asset to trade
            amount_usd: Trade size in USD
            intended_price: Price when order was generated (optional)
            
        Returns:
            Dict with execution recommendations
        """
        recommendation = {
            'proceed': True,
            'delay': self.randomize_timing(),
            'split': amount_usd > self.LARGE_ORDER_USD,
            'slices': None,
            'max_slice': self.MAX_SLICE_USD,
            'whale_warning': False,
            'slippage_ok': True,
            'notes': []
        }
        
        # 1. Check for iceberg splitting
        if recommendation['split']:
            recommendation['slices'] = self.split_large_order(amount_usd)
            recommendation['notes'].append(
                f"Large order (${amount_usd:.0f}) split into {len(recommendation['slices'])} slices"
            )
        
        # 2. Check for whale activity
        whale_check = self.detect_whale_activity(symbol)
        if whale_check['suspicious']:
            recommendation['whale_warning'] = True
            recommendation['delay'] *= 2  # Double delay on whale activity
            recommendation['notes'].append(
                f"Whale activity detected ({whale_check['volume_ratio']:.1f}x volume)"
            )
        
        # 3. Check slippage guard (if price provided)
        if intended_price:
            is_safe, current_price = self.check_slippage_guard(symbol, intended_price)
            recommendation['slippage_ok'] = is_safe
            if not is_safe:
                recommendation['proceed'] = False
                recommendation['notes'].append("BLOCKED: Price moved beyond tolerance")
        
        # 4. Add random execution jitter
        recommendation['delay'] += random.uniform(0, 0.5)  # Extra jitter
        
        return recommendation
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from Redis cache."""
        if not self.r:
            return None
        try:
            price = self.r.get(f"price:{symbol}")
            return float(price) if price else None
        except (redis.RedisError, ValueError):
            return None


# Singleton instance
_protection = None

def get_mev_protection(redis_client=None) -> MEVProtection:
    """Get or create the singleton MEVProtection."""
    global _protection
    if _protection is None:
        _protection = MEVProtection(redis_client)
    return _protection


# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("MEV PROTECTION - Self Test")
    print("=" * 60)
    
    mev = get_mev_protection()
    
    # Test timing randomization
    print("\n1. Timing Randomization:")
    for _ in range(3):
        delay = mev.randomize_timing()
        print(f"   Random delay: {delay:.3f}s")
    
    # Test order splitting
    print("\n2. Order Splitting (Iceberg):")
    slices = mev.split_large_order(1500)
    print(f"   $1500 → {len(slices)} slices: {slices}")
    
    small_slices = mev.split_large_order(150)
    print(f"   $150 → {len(small_slices)} slices: {small_slices}")
    
    # Test execution recommendation
    print("\n3. Execution Recommendation:")
    rec = mev.get_execution_recommendation("BTC", 1000, 95000)
    print(f"   Symbol: BTC, Amount: $1000")
    print(f"   Proceed: {rec['proceed']}")
    print(f"   Delay: {rec['delay']:.2f}s")
    print(f"   Split: {rec['split']}")
    if rec['slices']:
        print(f"   Slices: {rec['slices']}")
    print(f"   Notes: {rec['notes']}")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")
