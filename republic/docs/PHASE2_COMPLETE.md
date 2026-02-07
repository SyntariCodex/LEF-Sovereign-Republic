# Phase 2 Complete: Dynamic Coin Discovery & Evaluation

## What Was Built

### 1. Coin Scanner Agent (`agents/coin_scanner.py`)
- Scans CoinGecko API for top 100-200 coins
- Evaluates each coin with Teleonomy scoring (4 axes: Survival, Development, Purpose, Self-Sufficiency)
- Assigns coins to wallets based on coin-type definitions
- Enforces exclusivity (no coin in multiple wallets)

### 2. Coin-Type Definitions (Enforced)
- **Dynasty_Core**: >90 teleonomy, >$10B market cap, >5 years, <20% volatility
- **Hunter_Tactical**: 60-80 teleonomy, >50% volatility, narrative-driven
- **Builder_Ecosystem**: 70-90 teleonomy, <40% volatility, infrastructure
- **Yield_Vault**: >80 teleonomy, <5% volatility, stablecoins/RWAs
- **Experimental**: <70 teleonomy, >60% volatility, <$1B market cap

### 3. Integration with Backtest
- Backtest now uses dynamic coin list from database
- Falls back to hardcoded list if database empty
- Coin selection based on wallet assignments, not hardcoded lists

## How to Use

### Step 1: Scan Coins
```bash
cd fulcrum
python3 scan_coins.py
```

This will:
- Scan top 100 coins from CoinGecko
- Evaluate each with Teleonomy scoring
- Assign to appropriate wallets
- Store in database

### Step 2: Run Backtest
```bash
python3 advanced_backtest.py --days 300
```

The backtest will now use the dynamically discovered coins instead of the hardcoded 5.

## What This Achieves

✅ **No More Hardcoded Lists**: Fulcrum discovers coins, doesn't use fixed lists
✅ **Teleonomy-Based Assignment**: Coins assigned based on actual metrics, not assumptions
✅ **Exclusivity Enforced**: No coin exists in multiple wallets
✅ **LEF Intelligence**: System actively reads markets, evaluates opportunities

## Next: Phase 1 (Stablecoin Buckets)

Now that we have dynamic coin discovery, we need to route profits properly:
- USDT bucket for IRS payments
- USDC bucket for SNW/LLC operations (with interest)
- DAI bucket for capital injections
