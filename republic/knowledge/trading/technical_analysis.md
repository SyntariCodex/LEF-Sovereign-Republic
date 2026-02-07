# Module 2: Technical Analysis — The Meaning

*What the signals actually represent, not just what the numbers are*

---

## 2.1 RSI — Relative Strength Index

### What RSI Actually Measures

RSI measures **momentum over a period** (typically 14 periods). It compares the magnitude of recent gains to recent losses.

```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss
```

### What RSI < 30 Actually Means

"Oversold" doesn't mean "cheap" or "undervalued." It means:

- Sellers have been dominant recently
- Selling pressure may be exhausting
- A bounce is *possible*, not guaranteed

**Critical Insight**: RSI is about momentum, not value. RSI 25 on a coin dropping from $1 to $0.10 doesn't mean it won't go to $0.01.

### What RSI > 70 Actually Means

"Overbought" doesn't mean "too expensive." It means:

- Buyers have been dominant recently
- Buying pressure may be exhausting
- A pullback is *possible*

**But**: Strong trends can stay overbought for weeks. Selling just because RSI > 70 can mean missing the best part of a rally.

### Divergence — The Real Signal

**Bullish Divergence**: Price makes lower lows, but RSI makes higher lows

- Meaning: Selling is losing momentum even as price falls
- Signal: Potential reversal coming

**Bearish Divergence**: Price makes higher highs, but RSI makes lower highs

- Meaning: Buying is losing momentum even as price rises
- Signal: Rally may be ending

**LEF Principle**: Divergence is more reliable than absolute RSI values. Don't buy just because RSI < 30; wait for divergence confirmation.

---

## 2.2 Moving Averages — Trend Memory

### What a Moving Average Is

A moving average is the average price over N periods. It smooths out noise and shows trend direction.

**Simple Moving Average (SMA)**: All periods weighted equally

```
SMA(20) = (Price_1 + Price_2 + ... + Price_20) / 20
```

**Exponential Moving Average (EMA)**: Recent prices weighted more heavily

- Reacts faster to price changes
- More useful for short-term trading

### What "Price Above SMA" Actually Means

When price is above the 20-day SMA:

- Recent price > 20-day average price
- More recent buyers than average
- Trend has been up

**Key Insight**: This is backward-looking. It tells you where price *has been*, not where it's going.

### Moving Average Crossovers

**Golden Cross**: Short MA (50) crosses above Long MA (200)

- Meaning: Recent momentum is stronger than long-term momentum
- Often cited as bullish

**Death Cross**: Short MA (50) crosses below Long MA (200)

- Meaning: Recent momentum is weaker than long-term momentum
- Often cited as bearish

**The Truth About Crossovers**: They are **lagging indicators**. By the time a golden cross happens, the move is often 10-20% underway. They confirm trends, they don't predict them.

### LEF Application

Use MAs for:

- Trend confirmation (price above 20 SMA = uptrend)
- Support/resistance levels (price often bounces off long MAs)
- Context for other indicators

Don't use MAs for:

- Entry timing (too slow)
- Exact price targets

---

## 2.3 MACD — Momentum of Momentum

### What MACD Actually Is

MACD (Moving Average Convergence Divergence) shows the relationship between two EMAs:

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

### What the Histogram Really Means

**Histogram > 0**: MACD is above signal line — momentum is accelerating
**Histogram < 0**: MACD is below signal line — momentum is decelerating

**Critical Insight**: The histogram shows **acceleration**, not direction. A shrinking positive histogram means the uptrend is slowing, even if price is still rising.

### Zero Line Crossings

**MACD crosses above zero**: Short-term trend is now faster than long-term trend

- This is an **entry signal**, not a hold signal

**MACD crosses below zero**: Short-term trend is now slower than long-term trend

- This is an **exit signal**, not a short signal

### MACD Divergence

Just like RSI, MACD divergence is more powerful than the raw numbers:

- Price making higher highs, MACD making lower highs = bearish divergence
- Price making lower lows, MACD making higher lows = bullish divergence

**LEF Principle**: Treat MACD histogram as a speedometer. Positive histogram = accelerating up. The size of the histogram bars matters more than whether they're positive or negative.

---

## 2.4 Volume — The Conviction Indicator

### What Volume Represents

Volume is the number of tokens traded in a period. High volume = high participation.

```
Price × Volume = Energy spent moving the price
```

### Volume Confirms Price Movement

**High volume + price increase**: Many buyers, strong conviction
**High volume + price decrease**: Many sellers, strong conviction
**Low volume + price increase**: Few buyers, weak rally
**Low volume + price decrease**: Few sellers, weak decline

### Capitulation — The Holy Grail

**Capitulation** is when volume spikes massively during a price crash. It means:

- Panic selling is reaching exhaustion
- Everyone who wanted to sell has sold
- Bottom might be forming

**LEF Principle**: The best buys often come on capitulation candles — huge volume, big red candle, then stabilization.

### Volume Divergence

**Price rising on declining volume**: Rally is weak, running out of buyers
**Price falling on declining volume**: Selling pressure exhausting

---

## 2.5 Combining Indicators

### No Single Indicator Is Enough

Each indicator tells you one thing:

- RSI: Momentum extreme
- MA: Trend direction
- MACD: Momentum acceleration
- Volume: Conviction

### LEF's Confirmation Framework

**Strong Buy Signal** (all must align):

1. RSI < 35 with bullish divergence
2. Price above 20 SMA (uptrend intact)
3. MACD histogram turning positive
4. Above-average volume

**Strong Sell Signal**:

1. RSI > 70 with bearish divergence
2. Price below 20 SMA
3. MACD histogram turning negative
4. High volume selling

### The Trap of Over-Optimization

If you require too many confirmations, you'll never trade. If you require too few, you'll trade noise.

**LEF Balance**: Require 3 of 4 indicators to align. Accept that some trades will fail.

---

## Summary: Technical Analysis Laws

1. **RSI is momentum, not value** — oversold doesn't mean cheap
2. **Divergence > absolute values** — price/indicator disagreement is the signal
3. **Moving averages lag** — they confirm, not predict
4. **MACD is acceleration** — histogram size matters more than sign
5. **Volume is conviction** — low volume moves are lies
6. **Combine indicators** — no single indicator is reliable alone

---

*Next Module: Trading Psychology — The Enemy Is Inside*
