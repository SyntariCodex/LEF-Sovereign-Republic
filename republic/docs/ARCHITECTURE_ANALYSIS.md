# Fulcrum Architecture Analysis & Gaps

## Understanding the Why

### Stablecoin Bucket Strategy
**Why USDT for IRS?**
- USDT (Tether) is the most widely accepted stablecoin for tax reporting
- Largest market cap = most liquidity = easiest to convert to USD for tax payments
- IRS recognizes USDT transactions, making compliance straightforward

**Why USDC for SNW/LLC?**
- USDC (Circle) is more transparent and auditable than USDT
- Better for institutional/LLC operations (Circle is regulated, publishes attestations)
- Can earn interest on USDC (Coinbase, Aave, etc.) while holding for SNW operations
- Regulatory clarity for LLC-structured operations

**Why DAI for Injections?**
- DAI is decentralized (not controlled by a single entity like USDT/USDC)
- True DeFi native - can bridge between ecosystems without centralized dependencies
- Represents the "sovereign" aspect - not dependent on Circle/Tether
- Perfect for "interjected funds" that move between ecosystems

### Coin-Type Exclusivity
**Why no overlaps?**
- Prevents over-concentration (same coin in multiple wallets = risk)
- Forces strategic allocation decisions
- Each wallet has distinct risk/return profile
- Migration logic ensures coins evolve through wallet hierarchy

### Dynamic Coin Evaluation
**Why scan new coins?**
- Markets evolve - new opportunities emerge
- Can't be stuck with only 5 coins forever
- LEF should discover, evaluate, and integrate new assets
- Teleonomy scoring should identify "capacity for self-sufficiency" in new projects

## Current Gaps

### 1. Missing Stablecoin Buckets
- No USDT bucket for IRS payments
- No USDC bucket for SNW/LLC (gains should flow here for interest)
- No DAI bucket for injection funds
- Current Yield_Vault just holds USDC, doesn't separate by purpose

### 2. Hardcoded Coin List
- Only 5 coins: BTC, ETH, SOL, PAXG, USDC
- No dynamic scanning/evaluation
- No coin discovery mechanism
- Teleonomy scorer exists but isn't used to evaluate new coins

### 3. No Migration Logic
- Coins don't move between wallets as they evolve
- No promotion/demotion system
- Dynasty assets can't decay and move to Hunter
- Experimental can't graduate to Dynasty

### 4. Missing Quadrant System
- White paper defines A/B/C/D quadrants for decision making
- Current system only uses BUY/SELL/HOLD
- No "Accelerate" or "Defend" regimes

### 5. Learning vs. Overfitting
- Current system learns patterns from historical data
- Risk: Getting good at backtest, bad at real markets
- Need: Generalization, regime detection, adaptation
- Should learn market "language" not just patterns

### 6. Coin-Type Definitions Not Enforced
- Dynasty: >90 teleonomy, >$10B market cap, >5 years, <20% volatility
- Hunter: 60-80 teleonomy, >50% volatility, narrative-driven
- Builder: 70-90 teleonomy, infrastructure, <40% volatility
- Yield: >80 teleonomy, <5% volatility, yield mechanisms
- Experimental: <70 teleonomy, >60% volatility, unproven

These criteria exist in white paper but aren't enforced in code.

## What Needs to Be Built

### 1. Stablecoin Bucket System
```
- USDT_Bucket (IRS): Receives profits for tax payments
- USDC_Bucket (SNW_LLC): Receives gains, earns interest, funds SNW/LLC
- DAI_Bucket (Injections): Receives bi-weekly injections, bridges ecosystems
- Yield_Vault: Manages all three buckets, optimizes APY
```

### 2. Dynamic Coin Discovery & Evaluation
```
- Coin Scanner: Queries CoinGecko for top 100-200 coins
- Teleonomy Evaluator: Scores each coin on 4 axes
- Wallet Assigner: Matches coins to wallets based on type definitions
- Exclusivity Enforcer: Ensures no coin in multiple wallets
```

### 3. Migration System
```
- Monthly Re-evaluation: Re-score all holdings
- Promotion Logic: Experimental → Builder → Dynasty (if scores rise)
- Demotion Logic: Dynasty → Hunter → Experimental (if scores fall)
- Audit Trail: Log all migrations with reasoning
```

### 4. Quadrant System
```
- Quadrant A (Ultimate Sell): High Sentiment + Low Reality → Exit positions
- Quadrant B (Healthy Bull): High + High → Accelerate (increase positions)
- Quadrant C (Panic Trap): Low + Low → Defend (hedge to stables)
- Quadrant D (Ultimate Buy): Low + High → Entry (aggressive buying)
```

### 5. Generalization-Focused Learning
```
- Regime Detection: Learn market regimes (Bull/Bear/Accumulation/Distribution)
- Pattern Recognition: Learn market "language" not just patterns
- Adaptation: Adjust strategies based on regime, not just historical wins
- Anti-Overfitting: Test on out-of-sample data, validate generalization
```

## Implementation Priority

1. **Stablecoin Buckets** (Critical for operations)
2. **Dynamic Coin Evaluation** (Core LEF functionality)
3. **Migration Logic** (Evolution engine)
4. **Quadrant System** (Strategic decision making)
5. **Generalization Learning** (Sovereign intelligence)
