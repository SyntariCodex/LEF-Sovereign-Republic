# Derivatives & Futures Status

## Current Status: **DISABLED**

### Why Derivatives Are Disabled

1. **No Historical Data**
   - We don't have historical futures/derivatives price data
   - Can't backtest futures strategies without historical data
   - Would need to source futures data from exchanges (Binance, Bybit, etc.)

2. **Coinbase Advanced Trade Limitation**
   - Coinbase Advanced Trade **only supports spot trading**
   - No futures, perpetual swaps, or derivatives available
   - Fulcrum is launching on Coinbase first, so must comply

## What Still Exists

### `agents/derivatives_engine.py`
- ✅ **Code is still there** - fully implemented and ready
- ✅ **Database tables** - `futures_positions` and `derivatives_trades`
- ✅ **All functions work** - open/close positions, PnL calculation, liquidation checks
- ❌ **Not imported** - commented out in `advanced_backtest.py`
- ❌ **Not initialized** - disabled in backtest system

## Future Use Cases

### If You Move to Another Exchange
If you later want to use derivatives on an exchange that supports them (Binance, Bybit, etc.):

1. **Enable the derivatives engine:**
   ```python
   # In advanced_backtest.py, uncomment:
   from derivatives_engine import DerivativesEngine
   self.derivatives_engine = DerivativesEngine(db_path=self.db_path)
   ```

2. **Get historical futures data:**
   - Binance API has historical futures data
   - Bybit API has perpetual swap data
   - Can integrate with these exchanges

3. **Add futures trading to backtest:**
   - Open futures positions alongside spot trades
   - Use leverage for enhanced returns
   - Implement hedging strategies

## Current Implementation

The `DerivativesEngine` supports:
- ✅ Perpetual futures (long/short)
- ✅ Leveraged positions (2x, 3x, 5x, 10x)
- ✅ Position tracking and PnL calculation
- ✅ Liquidation risk monitoring
- ✅ Database persistence

**It's ready to use** - just needs:
1. Historical data source
2. Exchange that supports futures
3. Enable it in the code

## Summary

- **Removed from backtest**: Yes (commented out)
- **Code deleted**: No (still exists, just disabled)
- **Reason**: Both lack of historical data AND Coinbase limitation
- **Future use**: Ready to enable when you have data + exchange support
