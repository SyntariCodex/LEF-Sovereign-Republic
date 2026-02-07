# Coinbase Advanced Trade Compliance

## ✅ Fulcrum Adherence to Coinbase Rules

### 1. Trading Types
- **✅ Spot Trading Only**: Fulcrum uses spot trading exclusively
- **❌ No Futures/Derivatives**: Derivatives engine disabled (Coinbase Advanced Trade doesn't support futures)
- **✅ Limit Orders Only**: All trades use limit orders (safer than market orders, prevents slippage)

### 2. Rate Limiting
- **Coinbase Limit**: 10,000 requests/hour per API key
- **Fulcrum Implementation**: 
  - Tracks API call timestamps
  - Enforces 9,000 requests/hour (safety margin)
  - Automatically waits when approaching limit
  - Applies to both Coinbase API and CoinGecko API calls

### 3. Order Types
- **Limit Buy Orders**: Buy at or below current price (0.1% below market)
- **Limit Sell Orders**: Sell at or above current price (0.1% above market)
- **No Market Orders**: Market orders are disabled (too risky, can cause slippage)

### 4. Human Gate (Sovereignty)
- **Only APPROVED trades execute**: Coinbase agent checks `status='APPROVED'` in database
- **PENDING trades wait**: No trade executes without human approval
- **Human sovereignty preserved**: Even if Master Controller creates trades, they wait for approval

### 5. Account Limits
- **Balance Checks**: Before executing trades, checks available balance
- **Insufficient Funds**: Trades fail gracefully if balance insufficient
- **Account Verification**: Respects Coinbase account verification levels

### 6. Error Handling
- **Network Errors**: Catches and handles API errors gracefully
- **Rate Limit Errors**: Detects 429 errors and waits appropriately
- **Failed Orders**: Marks orders as 'FAILED' in database for review

## 📋 Coinbase Advanced Trade Features Used

### Supported Features:
- ✅ Spot trading (buy/sell)
- ✅ Limit orders
- ✅ Balance queries
- ✅ Price tickers
- ✅ Order status tracking

### Not Used (Not Supported):
- ❌ Futures trading
- ❌ Perpetual swaps
- ❌ Options trading
- ❌ Margin trading
- ❌ Market orders (intentionally disabled)

## 🔒 Safety Features

1. **Sandbox Mode**: Can run in sandbox mode for testing (though Coinbase Advanced may not fully support it)
2. **Human Gate**: All trades require human approval
3. **Rate Limiting**: Prevents API abuse
4. **Limit Orders**: Prevents slippage and unexpected prices
5. **Balance Checks**: Prevents insufficient fund errors

## 📊 Implementation Details

### Coinbase Agent (`agents/agent_coinbase.py`)
- Uses `ccxt.coinbaseadvanced` for API access
- Implements rate limiting in `_check_rate_limit()`
- Only executes `status='APPROVED'` trades
- Uses limit orders exclusively

### Backtest System (`advanced_backtest.py`)
- Uses real CoinGecko historical data
- Respects CoinGecko rate limits (30 calls/minute)
- Simulates Coinbase-compliant trading behavior
- No futures/derivatives in backtest

## 🚀 Launch Readiness

Fulcrum is configured to launch on Coinbase Advanced Trade with:
- ✅ Spot trading only
- ✅ Rate limit compliance
- ✅ Human gate active
- ✅ Limit orders only
- ✅ Error handling
- ✅ Balance checks

## ⚠️ Important Notes

1. **Sandbox Mode**: Coinbase Advanced Trade may not fully support sandbox mode in ccxt. Test carefully before going live.

2. **API Keys**: Ensure API keys have appropriate permissions:
   - View balances
   - Place limit orders
   - View order status

3. **Account Limits**: Coinbase account limits vary by verification level. Fulcrum respects these limits.

4. **Rate Limits**: If you hit rate limits, Fulcrum will automatically wait. However, for high-frequency trading, consider upgrading to Coinbase Pro API with higher limits.
