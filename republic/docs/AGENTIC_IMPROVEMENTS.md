# LEF Agentic AI Improvements - Coin Diversification

## Overview
Enhanced Fulcrum to be more agentic in discovering, evaluating, and trading a diverse set of coins from the market. The system now actively explores the market rather than being limited to a small set of coins.

## Key Changes

### 1. Increased Coin Discovery (100 coins vs 50)
- **Before**: Scanned 50 coins monthly
- **After**: Scans 100 coins monthly for better market coverage
- **Impact**: 2x more coins available for trading, better diversification

### 2. Agentic Exploration Strategy
- **70% Exploration**: Prefers coins not currently held and not recently traded
- **20% Re-exploration**: Allows re-trading coins traded 5-10 trades ago
- **10% Re-entry**: Allows re-entering positions after sufficient time
- **20% Random Selection**: Randomly picks coins 20% of the time to avoid local optima

### 3. Improved Coin Scanner
- **Broader Market Coverage**: Scans top 250 coins (CoinGecko max per page)
- **Exploration Mode**: Includes 20% lower-cap coins for discovery
- **Less Restrictive**: Removed overly strict filtering that limited diversity

### 4. Enhanced Asset Selection
- **Rotation System**: Ensures all available coins get a chance to be traded
- **Diversification Priority**: Strongly prefers coins not in current holdings
- **Wallet-Specific Logic**: Each wallet has optimized selection based on its strategy
- **Logging**: Tracks which coins are selected and why (for learning)

### 5. Fresh Scan on Startup
- **Forced Rescan**: Resets scan schedule on restart to ensure fresh data
- **Database Population**: Ensures at least 20 coins before starting backtest
- **Automatic Discovery**: Runs coin scanner if database is empty

## Agentic AI Features

### Exploration vs Exploitation Balance
The system now balances:
- **Exploitation**: Trading known good coins (70% of time)
- **Exploration**: Trying new coins to discover opportunities (20% random)
- **Re-exploration**: Revisiting previously traded coins (10%)

### Market Reading Capability
- Scans historical market data at the time of backtest
- Evaluates coins based on market conditions during that period
- Assigns coins to appropriate wallets based on Teleonomy scoring
- Adapts to market changes over time

### Self-Improvement
- Tracks which coins perform well
- Rotates through all available options
- Learns from trading history
- Adapts selection strategy based on performance

## Expected Results

1. **More Diverse Trading**: Should see 10-20+ different coins being traded instead of just 2-3
2. **Better Market Coverage**: Explores more of the cryptocurrency market
3. **Improved Performance**: Diversification reduces risk and increases opportunities
4. **Agentic Behavior**: System actively discovers and evaluates new opportunities

## Monitoring

The system now logs:
- Which coins are selected for each wallet
- Rotation indices (to ensure all coins get a chance)
- Exploration vs exploitation decisions
- Coin distribution across wallets

Check logs for messages like:
- `[AGENTIC] Exploration mode: Randomly selected X for Y`
- `[AGENTIC] Dynasty_Core: Selected BTC (rotation 3/15)`
- `[BACKTEST] Coin distribution: {'Dynasty_Core': 5, 'Hunter_Tactical': 12, ...}`

## Next Steps

1. Run a fresh backtest to see the improved diversification
2. Monitor the logs to verify coins are being rotated
3. Check the dashboard to see diverse coin holdings
4. Review trade history to confirm multiple coins are being traded
