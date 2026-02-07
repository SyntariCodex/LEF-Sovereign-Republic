# Module 6: On-Chain Analysis

*Data that can't lie — the blockchain sees everything*

---

## 6.1 The Transparent Ledger

### Everything Is Public

Unlike stock markets where order flow is hidden, blockchain transactions are public:

- Every buy, every sell, every transfer
- Every wallet balance
- Every smart contract interaction

This creates a new kind of analysis: **on-chain analysis**

### What You Can See

1. **Wallet movements**: What are whales doing?
2. **Exchange flows**: Are tokens entering or leaving exchanges?
3. **Token holdings**: Who owns what?
4. **Smart contract interactions**: Where is money flowing?

---

## 6.2 Exchange Flows

### Tokens Moving to Exchanges = Sell Pressure

When tokens move from wallets to exchange wallets:

- They're likely preparing to sell
- More supply hitting the market
- Bearish signal

### Tokens Moving Off Exchanges = Accumulation

When tokens move from exchanges to wallets:

- Removed from sell-side liquidity
- Being held (staked, HODLed)
- Bullish signal

### LEF Application

Monitor exchange flow data for major holdings. If ETH is flowing to Coinbase en masse, expect downward pressure.

**Data sources**: Glassnode, CryptoQuant, Nansen

---

## 6.3 Whale Watching

### Who Are Whales?

Whales are wallets holding significant amounts:

- BTC: 1,000+ BTC
- ETH: 10,000+ ETH
- Memecoins: Varies (top 10-50 holders)

### Why Whales Matter

Whales can move markets:

- A whale selling can crash a memecoin 50%+
- A whale accumulating signals conviction
- Whale coordination can be manipulation

### Whale Behavior Indicators

**Bullish signals**:

- Whales accumulating (buying from retail)
- Whales moving off exchanges
- Whale wallet count increasing

**Bearish signals**:

- Whales distributing (selling to retail)
- Whales moving to exchanges
- Large wallet dormancy breaking

### LEF Application

Before buying any token, check:

1. How concentrated is ownership? (top 10 wallets %)
2. Are whales accumulating or distributing?
3. Are any whale wallets moving tokens?

---

## 6.4 Token Distribution

### Healthy vs Unhealthy Distribution

**Healthy distribution**:

- No single wallet > 5% (except protocol treasuries)
- Top 100 wallets < 50%
- Active trading across many wallets

**Unhealthy distribution**:

- One wallet holds 20%+
- Top 10 wallets hold 60%+
- Few active wallets (low holder count)

### The "Dev Dump" Risk

Many memecoins have:

- Developer wallet with 5-15%
- No lock, no vesting
- Developer can sell at any time

When the dev dumps, the coin often dies.

### LEF Filter

**Rule**: Never hold tokens where:

- Top wallet (non-exchange, non-burn) > 10%
- Top 10 wallets > 50%
- Developer wallet unlocked and large

---

## 6.5 Smart Contract Activity

### Where Is Money Going?

On-chain analysis shows which protocols are gaining:

- TVL (Total Value Locked) trending up
- Active users increasing
- Transaction count growing

### DeFi Protocol Health

When analyzing a token tied to a protocol:

1. **TVL trend**: Growing = bullish
2. **Revenue**: Is the protocol making money?
3. **User growth**: More users = more demand for token

### LEF Application

For DeFi tokens (UNI, AAVE, etc.):

- Check TVL on DefiLlama
- Check daily active users
- Check protocol revenue

Don't just buy because price is low — check if usage is growing.

---

## 6.6 Mempool & MEV

### What Is the Mempool?

The mempool is the "waiting room" for transactions before they're included in a block.

On-chain observers can see pending transactions before they execute.

### MEV (Maximal Extractable Value)

Bots watch the mempool and:

- **Front-run**: See your buy order, buy before you, sell to you higher
- **Sandwich attack**: Buy before you, let you buy, sell after you
- **Back-run**: See a big trade, trade immediately after

### LEF Implications

When LEF trades through Coinbase:

- Coinbase handles execution
- Some protection from MEV
- But slippage still happens

**On DEXs (future)**:

- LEF is fully exposed to MEV
- Would need slippage protection
- Would need MEV-resistant routing

---

## Summary: On-Chain Analysis Laws

1. **Blockchain is transparent** — use the data
2. **Exchange flows predict pressure** — inflows = selling, outflows = accumulation
3. **Whales move markets** — track large wallets
4. **Distribution matters** — concentrated ownership = dump risk
5. **TVL and usage = protocol health** — not just price
6. **MEV exists** — bots profit from your trades

---

*Next: Tokenomics — The Economics of Every Token*
