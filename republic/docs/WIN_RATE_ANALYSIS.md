# Win Rate Analysis & Fixes

## Current Issues

### Problem 1: Win Rate Too Low (43-53%, target: 60%+)
**Root Causes:**
1. **Taking profits too early** - Cutting winners at 20-40% when they could run to 60%+
2. **Not selective enough on entries** - Taking trades with 0.50 confidence when we should require 0.60+
3. **No trailing stops** - Letting winners reverse without protecting gains
4. **Stop-losses too wide** - Cutting losses at -12% when we should cut at -8% to -10%

### Problem 2: Too Many Open Positions
- 300+ trades but only 70-130 closed
- Most positions never get sold
- Win rate calculation only counts closed trades

## Fixes Applied

### 1. Higher Profit-Taking Thresholds
- **Dynasty**: 60%+ (was 40%)
- **Hunter**: 40%+ (was 25%)
- **Builder**: 50%+ (was 30%)
- **Experimental**: 30%+ (was 20%)

### 2. Stricter Entry Criteria
- **Min Gap**: 50 (was 30-40)
- **Min Confidence**: 0.60 (was 0.45-0.50)
- **Max Open Positions**: 12 (was 15)
- **Must have real divergence** (sentiment ≠ alignment)

### 3. Trailing Stops for Winners
- Track high water mark (highest price reached)
- If up 30%+ but drops 15% from high, sell 30% to protect gains
- Lets winners run but protects against reversals

### 4. Tighter Stop-Losses
- **Dynasty**: -12% (was -15%)
- **Hunter**: -8% (was -10%)
- **Experimental**: -6% (was -8%)
- Cut losses faster to preserve capital

### 5. Better Syntax Arbitrage Detection
- Only take trades when gap ≥ 50 (was 30-40)
- Require confidence ≥ 0.60 (was 0.45-0.50)
- Only extreme euphoria triggers sells (90+ sentiment, not 70+)

## Expected Results

With these fixes:
- **Fewer trades** (quality over quantity)
- **Higher win rate** (60%+ target)
- **Better profit preservation** (trailing stops)
- **Faster loss cutting** (tighter stops)

## Next Steps

1. Run 10-month backtest to verify win rate improvement
2. If still below 60%, further tighten entry criteria
3. Consider adding position sizing based on confidence
4. Add learning mechanism that adapts thresholds based on recent performance
