# Module 1: Market Microstructure

*Why prices move — the physics of markets*

---

## 1.1 Order Books & Liquidity

### What Is an Order Book?

An order book is a ledger of all pending buy and sell orders for an asset. It shows:

- **Bids**: Orders to buy at a specific price (demand)
- **Asks**: Orders to sell at a specific price (supply)

```
ASKS (Sellers)                    BIDS (Buyers)
$101.50 — 500 tokens              $99.50 — 800 tokens
$101.00 — 200 tokens              $99.00 — 1,200 tokens
$100.50 — 150 tokens   ← Spread → $98.50 — 600 tokens
```

### The Spread Is the Cost of Immediacy

The **bid-ask spread** is the gap between the lowest ask and highest bid. If you want to buy *right now*, you pay the ask price. If you want to sell *right now*, you accept the bid price.

**Key Insight**: The spread is what you pay for *immediacy*. Patient traders use limit orders and wait. Impatient traders use market orders and pay the spread.

For LEF: Every market order has an invisible cost — the spread. On low-liquidity memecoins, this spread can be 1-5% of the trade value.

### Thin Order Books = Volatility

When there are few orders at each price level, a single large order can move the price significantly. This is why:

- Memecoins are volatile (thin books)
- BTC is more stable (deep books)
- Late-night trading is choppier (fewer participants)

**LEF Principle**: Trade assets with sufficient liquidity. If the order book is thin, your trade becomes the price movement.

---

## 1.2 Market Impact

### Your Trade Affects the Price

When you buy, you consume the lowest ask orders. If you buy more than what's available at that price, you start consuming higher-priced orders. This is **market impact**.

Example:

```
Before your 1,000 token buy:
Ask $100.50 — 500 tokens
Ask $101.00 — 300 tokens
Ask $101.50 — 800 tokens

After your buy:
You paid: 500 @ $100.50 + 300 @ $101.00 + 200 @ $101.50
Average: $100.80 (not $100.50)
New lowest ask: $101.50
```

You moved the market up $1 just by buying.

### LEF's Size Matters

With $8,000 starting capital, LEF is a small fish. But on micro-cap memecoins, even $500 trades can move the market.

**Rule**: Your trade size should never exceed 1% of daily volume for that asset. If daily volume is $50,000, your max trade is $500.

---

## 1.3 Market Makers

### Who Provides Liquidity?

Market makers are entities (usually bots or firms) that continuously post both bid and ask orders. They profit from the spread:

- Buy at $99.50 (bid)
- Sell at $100.50 (ask)
- Profit: $1.00 per token (minus risk)

### The Game You're Playing

When you trade, you're often trading *against* market makers. They have:

- Better data (order flow, latency)
- Better algorithms (statistical arbitrage)
- More capital (can wait you out)

**Key Insight**: Market makers profit from volatility. They love when you panic sell, because they buy your coins cheap and sell them back higher.

### Memecoins Have No Real Market Makers

Blue-chip assets (BTC, ETH) have institutional market makers providing deep liquidity. Memecoins often have:

- Only retail traders
- Bot-driven manipulation
- "Dev dumps" where creators sell into buyers

**LEF Principle**: The absence of market makers means the absence of a safety net. Treat memecoin positions as high-risk always.

---

## 1.4 Slippage Reality

### Expected vs Executed Price

**Slippage** is the difference between the price you expected and the price you actually got.

Positive slippage (rare): Price moves in your favor
Negative slippage (common): Price moves against you

Causes:

1. Market impact (your order moved the price)
2. Latency (price changed while your order was in transit)
3. Thin liquidity (not enough at your target price)

### Calculating Realistic Slippage

For LEF trades, assume:

- BTC/ETH: 0.1% slippage
- Mid-cap alts: 0.5% slippage
- Memecoins: 1-5% slippage

A $1,000 memecoin buy might actually cost $1,030-$1,050 after slippage.

### Position Sizing Relative to Liquidity

**The Law**: Never trade more than 1% of a token's daily volume.

If BONK has $100,000 daily volume:

- Max trade size: $1,000
- Larger trades = massive slippage + market impact

**LEF Implementation**: Before any trade, check 24h volume. Reject trades that exceed 1% of volume.

---

## Summary: Market Microstructure Laws

1. **The spread is your first loss** — account for it in every trade
2. **Thin books mean your trade IS the price movement** — avoid illiquid assets
3. **Market makers are the house** — you're playing against professionals
4. **Slippage is real cost** — factor 0.5-2% into memecoin trades
5. **Size relative to volume** — never exceed 1% of daily volume

---

*Next Module: Technical Analysis — The Meaning Behind the Numbers*
