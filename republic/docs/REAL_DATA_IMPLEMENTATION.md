# Real Historical Data & Derivatives Implementation

## ✅ What's Been Implemented

### 1. Real Historical Data (CoinGecko API)
- **Replaced simulated prices** with real CoinGecko historical data
- `get_historical_price()` now fetches actual market prices from CoinGecko
- Uses real price history for the past 10 months (300 days)
- Caches prices to avoid API rate limits
- Falls back to cached prices if API unavailable

### 2. Derivatives & Futures Trading
- **New `DerivativesEngine`** (`agents/derivatives_engine.py`)
- Supports:
  - **Perpetual futures** (long/short positions)
  - **Leveraged trading** (2x, 3x, 5x, 10x leverage)
  - **Position tracking** (entry price, quantity, leverage, margin)
  - **PnL calculation** (realized and unrealized)
  - **Liquidation risk monitoring**
- Database tables:
  - `futures_positions` - tracks open/closed futures positions
  - `derivatives_trades` - history of all derivatives trades

### 3. 10-Month Training Period
- Default duration: **300 days (10 months)**
- Uses actual past dates (10 months ago from today)
- Ensures real historical data is available
- Trains Fulcrum on actual market conditions

## 📊 How It Works

### Real Data Flow:
1. **CoinGecko API** → Fetches historical prices for each date
2. **Price Cache** → Stores prices to avoid repeated API calls
3. **Backtest Loop** → Uses real prices for each day
4. **Trade Execution** → Based on real market conditions

### Derivatives Trading:
1. **Open Position** → `derivatives_engine.open_futures_position()`
   - Specify: wallet, symbol, long/short, quantity, leverage
   - Calculates margin required
   - Records position in database

2. **Close Position** → `derivatives_engine.close_futures_position()`
   - Calculates PnL (profit/loss)
   - Updates position status
   - Records trade history

3. **Monitor Positions** → `derivatives_engine.check_liquidation_risk()`
   - Tracks unrealized PnL
   - Warns if margin threshold exceeded

## 🚀 Next Steps

### To Use Derivatives in Backtest:
1. **Add futures trading logic** to `advanced_backtest.py`:
   ```python
   # In the trading loop, after spot trades:
   if conditions['signal'] == 'BUY' and axes['confidence'] > 0.70:
       # Open leveraged long position
       position_id = self.derivatives_engine.open_futures_position(
           wallet_name='Hunter_Tactical',
           symbol=symbol,
           position_type='long',
           quantity=quantity,
           entry_price=current_price,
           leverage=3  # 3x leverage
       )
   ```

2. **Close positions** when profit targets met:
   ```python
   # Check open futures positions
   open_positions = self.derivatives_engine.get_open_positions()
   for position in open_positions:
       current_price = self.get_historical_price(position['symbol'], date)
       pnl = self.derivatives_engine.calculate_position_pnl(
           position['id'], current_price
       )
       
       # Close if profit target met
       if pnl > profit_target:
           self.derivatives_engine.close_futures_position(
               position['id'], current_price
           )
   ```

## 📝 Notes

- **Real data** is slower (API calls) but more accurate
- **Derivatives** add leverage risk - use carefully
- **10-month period** ensures sufficient training data
- **CoinGecko rate limits** - caching helps but may need delays for large backtests

## 🔧 Configuration

In `advanced_backtest.py`:
- `use_real_data=True` - Uses CoinGecko API
- `duration_days=300` - 10 months
- `start_date=None` - Defaults to 10 months ago

To run:
```bash
cd fulcrum
python3 advanced_backtest.py --days 300 --capital 10000.0 --injection 250.0
```
