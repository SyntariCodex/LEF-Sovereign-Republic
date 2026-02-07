# Fulcrum Advanced Backtest Guide

## Overview

The Advanced Backtest system runs Fulcrum for extended periods (1+ year) with full multi-wallet, multi-asset functionality, learning mechanisms, and capital injections.

## Features

### Multiple Wallets
- **Dynasty_Core** (60%): HODL strategy, targets BTC/ETH/PAXG (high teleonomy)
- **Hunter_Tactical** (20%): Alpha strategy, targets SOL/BTC/ETH (volatile opportunities)
- **Builder_Ecosystem** (10%): Growth strategy, targets SOL/ETH (ecosystem development)
- **Yield_Vault** (5%): Stable strategy, holds USDC (stablecoin)
- **Experimental** (5%): High-risk strategy, targets SOL/ETH (experimental plays)

### Multiple Assets
- BTC (Bitcoin)
- ETH (Ethereum)
- SOL (Solana)
- PAXG (Pax Gold - gold-backed token)
- USDC (USD Coin - stablecoin)

### Learning & Evolution
- Tracks successful trading patterns
- Adapts strategy based on market conditions
- Evolves confidence levels over time
- Learns from profitable vs. unprofitable trades

### Capital Management
- Initial capital: $10,000 (configurable)
- Bi-weekly injections: $250 every 14 days (configurable)
- Automatic distribution to wallets based on allocation percentages

### Real-Time Dashboard
- Live progress tracking
- Wallet breakdown updates
- Recent trades display
- Portfolio value tracking
- Updates every 5 seconds during backtest

## Usage

### Basic Run (1 Year)
```bash
cd fulcrum
python3 advanced_backtest.py
```

### Custom Parameters
```bash
python3 advanced_backtest.py \
  --days 730 \
  --capital 10000.0 \
  --injection 250.0 \
  --start-date 2023-01-01
```

### Options
- `--days`: Number of days to simulate (default: 365)
- `--capital`: Initial capital (default: 10000.0)
- `--injection`: Bi-weekly injection amount (default: 250.0)
- `--start-date`: Start date in YYYY-MM-DD format (default: days ago)
- `--no-dashboard`: Disable live dashboard updates

### Generate Visualizations
After the backtest completes:
```bash
python3 visualize_advanced_results.py
```

This creates:
- `fulcrum_performance.png` - Performance over time
- `fulcrum_wallets.png` - Wallet breakdown charts
- `fulcrum_assets.png` - Asset distribution
- `fulcrum_trades.png` - Trade analysis
- `fulcrum_dashboard.html` - Comprehensive HTML dashboard

## Output Files

### During Backtest
- `fulcrum_backtest_live.html` - Live updating dashboard (refreshes every 5 seconds)
- `backtest_progress.json` - Progress data (updated during run)

### After Completion
- `backtest_results.json` - Complete results data
- `backtest_report.txt` - Text summary report
- `fulcrum_dashboard.html` - Final comprehensive dashboard
- Chart PNG files (performance, wallets, assets, trades)

## Understanding Results

### Portfolio Metrics
- **Initial Capital**: Starting amount
- **Capital Injected**: Total bi-weekly injections
- **Final Value**: Total portfolio value at end
- **Total Return**: Final value - (initial + injections)
- **Return %**: Percentage return

### Trading Metrics
- **Total Trades**: All buy/sell transactions
- **Winning Trades**: Profitable trades
- **Losing Trades**: Unprofitable trades
- **Win Rate**: Percentage of profitable trades
- **Total Profit**: Sum of all trade profits

### Wallet Breakdown
Each wallet shows:
- Total value (cash + holdings)
- Cash balance
- Holdings value
- Individual asset holdings with quantities and values

### Learning Data
- Successful patterns identified
- Market adaptations made
- Confidence evolution over time

## How It Works

1. **Market Simulation**: Simulates realistic market conditions with fear/euphoria cycles
2. **Syntax Arbitrage Detection**: Identifies gaps between perceived sentiment and teleonomic alignment
3. **Regime Detection**: Determines market regime (Bull, Bear, Accumulation, Distribution)
4. **Wallet Selection**: Each wallet trades based on its strategy and target assets
5. **Trade Execution**: Executes trades when signals are strong enough
6. **Learning**: Adapts strategy based on successful patterns
7. **Capital Injection**: Adds bi-weekly capital and distributes to wallets

## Notes

- Uses CoinGecko API for historical prices (with caching to avoid rate limits)
- Falls back to approximate prices if API unavailable
- Price cache speeds up repeated lookups
- Dashboard updates may slow down very long runs (can disable with `--no-dashboard`)
- Learning mechanism improves over time as more data accumulates

## Next Steps

After reviewing backtest results:
1. Analyze which wallets performed best
2. Identify which assets were most profitable
3. Review learning patterns and adaptations
4. Adjust strategies if needed
5. Run longer backtests (2+ years) to see evolution
6. Test different capital injection schedules

---

**Ready to run when you are!** 🚀
