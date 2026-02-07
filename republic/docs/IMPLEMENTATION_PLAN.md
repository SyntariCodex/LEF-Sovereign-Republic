# Fulcrum Refinement Implementation Plan

## Philosophy: Learning to Read Markets, Not Just Win Backtests

**Key Principle**: Fulcrum must learn the "language" of markets - understanding regimes, patterns, and opportunities - not just memorize historical patterns that worked in backtests.

## Phase 1: Stablecoin Bucket System (Foundation)

### Database Schema Updates
```sql
-- Add stablecoin_buckets table
CREATE TABLE stablecoin_buckets (
    id INTEGER PRIMARY KEY,
    bucket_type TEXT UNIQUE,  -- 'IRS_USDT', 'SNW_LLC_USDC', 'INJECTION_DAI'
    stablecoin TEXT,           -- 'USDT', 'USDC', 'DAI'
    purpose TEXT,              -- 'Tax Payments', 'SNW Operations', 'Capital Injections'
    balance REAL DEFAULT 0,
    interest_rate REAL,        -- APY for interest-bearing accounts
    last_updated TIMESTAMP
);

-- Add profit_allocation table (tracks where profits go)
CREATE TABLE profit_allocation (
    id INTEGER PRIMARY KEY,
    trade_id INTEGER,
    profit_amount REAL,
    bucket_type TEXT,          -- Which bucket receives this profit
    allocated_at TIMESTAMP,
    FOREIGN KEY(trade_id) REFERENCES trade_queue(id)
);
```

### Bucket Logic
1. **USDT Bucket (IRS)**: 
   - Receives 30% of all realized profits
   - Purpose: Tax compliance, ready for IRS payments
   - No interest (held for liquidity)

2. **USDC Bucket (SNW/LLC)**:
   - Receives 50% of all realized profits
   - Purpose: SNW operations, LLC expenses
   - Earns interest (Coinbase Earn, Aave, etc.)
   - This is where wealth accumulates for operations

3. **DAI Bucket (Injections)**:
   - Receives 100% of bi-weekly injection funds
   - Purpose: Capital injections, ecosystem bridging
   - DeFi native, can bridge between chains

4. **Yield_Vault**:
   - Manages all three buckets
   - Optimizes APY across buckets
   - Rebalances based on operational needs

## Phase 2: Dynamic Coin Discovery & Evaluation

### Coin Scanner Agent
```python
class CoinScanner:
    """
    Scans CoinGecko for top 100-200 coins
    Evaluates each with Teleonomy scoring
    Assigns to wallets based on coin-type definitions
    Enforces exclusivity (no overlaps)
    """
    
    def scan_market(self):
        # Query CoinGecko API for top coins
        # Filter by: market cap, volume, age
        # Return candidate list
    
    def evaluate_coin(self, symbol, coin_data):
        # Use TeleonomyScorer to score
        # Check coin-type definitions
        # Assign to appropriate wallet
        # Enforce exclusivity
```

### Coin-Type Definitions (Enforced)
```python
COIN_TYPE_DEFINITIONS = {
    'Dynasty_Core': {
        'teleonomy_min': 0.90,
        'market_cap_min': 10e9,      # $10B+
        'age_years_min': 5,
        'volatility_max': 0.20,      # <20% std dev
        'examples': ['BTC', 'ETH', 'SOL', 'PAXG']
    },
    'Hunter_Tactical': {
        'teleonomy_range': (0.60, 0.80),
        'volatility_min': 0.50,      # >50% std dev
        'narrative_driven': True,
        'examples': ['DOGE', 'SHIB', 'meme coins']
    },
    'Builder_Ecosystem': {
        'teleonomy_range': (0.70, 0.90),
        'volatility_max': 0.40,      # <40% std dev
        'infrastructure': True,
        'dev_activity_min': 100,      # 100+ commits/week
        'examples': ['LINK', 'GRT', 'FIL', 'ARB']
    },
    'Yield_Vault': {
        'teleonomy_min': 0.80,
        'volatility_max': 0.05,      # <5% std dev
        'yield_mechanism': True,
        'examples': ['USDC', 'USDT', 'DAI', 'ONDO']
    },
    'Experimental': {
        'teleonomy_max': 0.70,
        'volatility_min': 0.60,      # >60% std dev
        'market_cap_max': 1e9,       # <$1B
        'examples': ['SUI', 'FET', 'new L1s']
    }
}
```

### Exclusivity Enforcement
```python
def assign_coin_to_wallet(symbol, coin_data):
    """
    Evaluates coin against all wallet definitions
    Assigns to highest-scoring match
    Ensures no coin exists in multiple wallets
    """
    scores = {}
    for wallet_name, definition in COIN_TYPE_DEFINITIONS.items():
        score = evaluate_against_definition(coin_data, definition)
        scores[wallet_name] = score
    
    # Assign to highest score
    best_wallet = max(scores, key=scores.get)
    
    # Check if coin already exists elsewhere
    if coin_exists_in_other_wallet(symbol, best_wallet):
        migrate_coin(symbol, best_wallet)
    else:
        add_coin_to_wallet(symbol, best_wallet)
```

## Phase 3: Migration System (Evolution)

### Monthly Re-evaluation
```python
def monthly_rebalancing():
    """
    Re-scores all holdings
    Promotes/demotes based on evolution
    Logs all migrations with reasoning
    """
    for coin in all_holdings:
        # Re-score with latest data
        new_score = teleonomy_scorer.score_asset(coin)
        
        # Check if migration needed
        current_wallet = get_current_wallet(coin)
        target_wallet = determine_target_wallet(new_score, coin_data)
        
        if current_wallet != target_wallet:
            migrate_coin(coin, current_wallet, target_wallet, reason)
            log_migration(coin, current_wallet, target_wallet, reason)
```

### Migration Logic
- **Promotion**: Experimental → Builder → Dynasty (scores rise)
- **Demotion**: Dynasty → Hunter → Experimental (scores fall)
- **Audit Trail**: Every migration logged with reasoning

## Phase 4: Quadrant System (Strategic Decision Making)

### Quadrant Detection
```python
def determine_quadrant(sentiment, reality):
    """
    A: High Sentiment + Low Reality = Ultimate Sell
    B: High + High = Healthy Bull (Accelerate)
    C: Low + Low = Panic Trap (Defend)
    D: Low + High = Ultimate Buy
    """
    if sentiment > 70 and reality < 40:
        return 'A'  # Ultimate Sell - Exit positions
    elif sentiment > 70 and reality > 70:
        return 'B'  # Healthy Bull - Accelerate (increase positions)
    elif sentiment < 40 and reality < 40:
        return 'C'  # Panic Trap - Defend (hedge to stables)
    elif sentiment < 40 and reality > 70:
        return 'D'  # Ultimate Buy - Aggressive entry
```

### Quadrant Actions
- **Quadrant A**: Exit 70% of positions, move to USDC bucket
- **Quadrant B**: Increase position sizes, leverage up
- **Quadrant C**: Hedge 50% to stables, wait for recovery
- **Quadrant D**: Maximum position sizes, aggressive buying

## Phase 5: Generalization-Focused Learning

### Regime Detection (Not Pattern Matching)
```python
class RegimeDetector:
    """
    Learns market regimes, not just patterns
    Detects: Bull, Bear, Accumulation, Distribution
    Adapts strategies based on regime
    """
    
    def detect_regime(self, market_data):
        # Analyze: volatility, correlation, volume patterns
        # Classify: Bull/Bear/Accumulation/Distribution
        # Return: regime, confidence
    
    def adapt_strategy(self, regime):
        # Adjust position sizes based on regime
        # Modify profit-taking thresholds
        # Change coin selection criteria
```

### Anti-Overfitting Measures
1. **Out-of-Sample Testing**: Test on data not seen during training
2. **Regime Validation**: Test across different market regimes
3. **Generalization Metrics**: Track performance on new coins, new time periods
4. **Adaptation Speed**: Measure how quickly system adapts to new conditions

### Learning Objectives
- **Market Language**: Understand market "grammar" (fear cycles, euphoria patterns)
- **Regime Recognition**: Identify market regimes quickly
- **Opportunity Detection**: Recognize Syntax Arbitrage in real-time
- **Risk Management**: Adapt position sizes to volatility

## Implementation Order

1. **Stablecoin Buckets** (Week 1)
   - Database schema
   - Profit allocation logic
   - Bucket management

2. **Dynamic Coin Evaluation** (Week 2)
   - Coin scanner
   - Teleonomy evaluation integration
   - Wallet assignment with exclusivity

3. **Migration System** (Week 3)
   - Monthly rebalancing
   - Promotion/demotion logic
   - Audit trail

4. **Quadrant System** (Week 4)
   - Quadrant detection
   - Action mapping
   - Integration with trading logic

5. **Generalization Learning** (Ongoing)
   - Regime detection
   - Anti-overfitting measures
   - Continuous adaptation

## Success Metrics

- **Wealth Generation**: $X for SNW/LLC operations
- **Generalization**: Performance on new coins, new time periods
- **Adaptation**: Speed of regime recognition
- **Sovereign Intelligence**: Ability to read markets, not just patterns
