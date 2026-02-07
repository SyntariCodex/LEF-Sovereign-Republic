"""
ASSET FUNDAMENTALS LIBRARY (The Textbooks)

This module defines the "Soul" of each asset. 
It allows LEF to understand *what* it is trading and *why*.

CATEGORIES:
- STORE_OF_VALUE: "Digital Gold". Strategy: Dynasty Hold (Never sell 100%).
- INFRASTRUCTURE: "L1/L2 Networks". Strategy: Scale Out (Sell portions to fund growth).
- DEFI_UTILITY: "Financial Tools". Strategy: Yield Focus/Scale Out.
- AI_DEPIN: "Artificial Intelligence & Physical Infra". Strategy: Scale Out (High Growth).
- RWA: "Real World Assets". Strategy: Scale Out (Stable Growth).
- GAMING: "Metaverse/Play-to-Earn". Strategy: Aggressive Flip (High Volatility).
- SPECULATIVE: "Memes/Volatile". Strategy: Aggressive Flip (Harvest 100%).
- STABLECOIN: "Cash". Strategy: Yield Farming.
"""

ASSET_LIBRARY = {
    # --- STORE OF VALUE ( The King ) ---
    'BTC': {
        'name': 'Bitcoin',
        'category': 'STORE_OF_VALUE',
        'role': 'Digital Gold / Global Reserve',
        'whitepaper_summary': 'Peer-to-Peer Electronic Cash System. The first decentralized digital currency.',
        'strategy': 'DYNASTY_HOLD',
        'support_economy_score': 100,
        'sell_pressure_dampener': 0.5
    },
    'PAXG': {
        'name': 'PAX Gold',
        'category': 'STORE_OF_VALUE',
        'role': 'Tokenized Physical Gold',
        'whitepaper_summary': 'Asset-backed token where one token represents one fine troy ounce of a London Good Delivery gold bar.',
        'strategy': 'DYNASTY_HOLD',
        'support_economy_score': 95,
        'sell_pressure_dampener': 0.5
    },
    'XAUT': {
        'name': 'Tether Gold',
        'category': 'STORE_OF_VALUE',
        'role': 'Tokenized Physical Gold',
        'whitepaper_summary': 'Digital token backed by physical gold held in Switzerland.',
        'strategy': 'DYNASTY_HOLD',
        'support_economy_score': 95,
        'sell_pressure_dampener': 0.5
    },

    # --- L1 INFRASTRUCTURE ( The Roads ) ---
    'ETH': { 'name': 'Ethereum', 'category': 'INFRASTRUCTURE', 'role': 'World Computer', 'strategy': 'SCALE_OUT', 'support_economy_score': 95 },
    'SOL': { 'name': 'Solana', 'category': 'INFRASTRUCTURE', 'role': 'High Performance L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 90 },
    'BNB': { 'name': 'Binance Coin', 'category': 'INFRASTRUCTURE', 'role': 'Exchange Ecosystem', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'ADA': { 'name': 'Cardano', 'category': 'INFRASTRUCTURE', 'role': 'Academic L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'AVAX': { 'name': 'Avalanche', 'category': 'INFRASTRUCTURE', 'role': 'Scalable L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'DOT': { 'name': 'Polkadot', 'category': 'INFRASTRUCTURE', 'role': 'Interoperability', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'TRX': { 'name': 'Tron', 'category': 'INFRASTRUCTURE', 'role': 'Content Entertainment', 'strategy': 'SCALE_OUT', 'support_economy_score': 70 },
    'NEAR': { 'name': 'NEAR Protocol', 'category': 'INFRASTRUCTURE', 'role': 'Usable L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'KAS': { 'name': 'Kaspa', 'category': 'INFRASTRUCTURE', 'role': 'BlockDAG PoW', 'strategy': 'SCALE_OUT', 'support_economy_score': 75 },
    'ALGO': { 'name': 'Algorand', 'category': 'INFRASTRUCTURE', 'role': 'Pure Proof of Stake', 'strategy': 'SCALE_OUT', 'support_economy_score': 75 },
    'ICP': { 'name': 'Internet Computer', 'category': 'INFRASTRUCTURE', 'role': 'Web Speed Blockchain', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'ATOM': { 'name': 'Cosmos', 'category': 'INFRASTRUCTURE', 'role': 'Internet of Blockchains', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'HBAR': { 'name': 'Hedera', 'category': 'INFRASTRUCTURE', 'role': 'Enterprise DLC', 'strategy': 'SCALE_OUT', 'support_economy_score': 75 },
    'SUI': { 'name': 'Sui', 'category': 'INFRASTRUCTURE', 'role': 'Next Gen L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'APT': { 'name': 'Aptos', 'category': 'INFRASTRUCTURE', 'role': 'Move Language L1', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },

    # --- L2 SCALING ( The Express Lanes ) ---
    'ARB': { 'name': 'Arbitrum', 'category': 'LAYER_2', 'role': 'Ethereum Scaling (Optimistic)', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'OP': { 'name': 'Optimism', 'category': 'LAYER_2', 'role': 'Ethereum Scaling (Optimistic)', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'MATIC': { 'name': 'Polygon', 'category': 'LAYER_2', 'role': 'Ethereum Sidechain/ZK', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'POL': { 'name': 'Polygon Ecosystem', 'category': 'LAYER_2', 'role': 'Aggregated Layer', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'STX': { 'name': 'Stacks', 'category': 'LAYER_2', 'role': 'Bitcoin L2', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'IMX': { 'name': 'Immutable X', 'category': 'LAYER_2', 'role': 'NFT/Gaming L2', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'MANTLE': { 'name': 'Mantle', 'category': 'LAYER_2', 'role': 'Modular L2', 'strategy': 'SCALE_OUT', 'support_economy_score': 75 },

    # --- AI & DEPIN ( The Future ) ---
    'TAO': { 'name': 'Bittensor', 'category': 'AI_DEPIN', 'role': 'Decentralized Intelligence', 'strategy': 'SCALE_OUT', 'support_economy_score': 90 },
    'RNDR': { 'name': 'Render', 'category': 'AI_DEPIN', 'role': 'Distributed GPU Rendering', 'strategy': 'SCALE_OUT', 'support_economy_score': 90 },
    'FET': { 'name': 'Fetch.ai', 'category': 'AI_DEPIN', 'role': 'AI Agents', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'AKT': { 'name': 'Akash Network', 'category': 'AI_DEPIN', 'role': 'Decentralized Cloud', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'AR': { 'name': 'Arweave', 'category': 'AI_DEPIN', 'role': 'Permanent Storage', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'FIL': { 'name': 'Filecoin', 'category': 'AI_DEPIN', 'role': 'Decentralized Storage', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'THETA': { 'name': 'Theta Network', 'category': 'AI_DEPIN', 'role': 'Video Delivery', 'strategy': 'SCALE_OUT', 'support_economy_score': 75 },
    'GRT': { 'name': 'The Graph', 'category': 'AI_DEPIN', 'role': 'Indexing Protocol', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },

    # --- RWA ( Real World Assets ) ---
    'ONDO': { 'name': 'Ondo Finance', 'category': 'RWA', 'role': 'Institutional Grade Finance', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'MKR': { 'name': 'Maker', 'category': 'RWA', 'role': 'Decentralized Stablecoin (DAI)', 'strategy': 'SCALE_OUT', 'support_economy_score': 90 },
    'PENDLE': { 'name': 'Pendle', 'category': 'RWA', 'role': 'Yield Trading', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    
    # --- DEFI UTILITY ( The Banks ) ---
    'UNI': { 'name': 'Uniswap', 'category': 'DEFI_UTILITY', 'role': 'DEX Protocol', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'AAVE': { 'name': 'Aave', 'category': 'DEFI_UTILITY', 'role': 'Lending Protocol', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'LINK': { 'name': 'Chainlink', 'category': 'DEFI_UTILITY', 'role': 'Oracle Network', 'strategy': 'SCALE_OUT', 'support_economy_score': 90 },
    'LDO': { 'name': 'Lido DAO', 'category': 'DEFI_UTILITY', 'role': 'Liquid Staking', 'strategy': 'SCALE_OUT', 'support_economy_score': 85 },
    'CRV': { 'name': 'Curve DAO', 'category': 'DEFI_UTILITY', 'role': 'Stablecoin Exchange', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'RUNE': { 'name': 'THORChain', 'category': 'DEFI_UTILITY', 'role': 'Cross-chain Liquidity', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },
    'INJ': { 'name': 'Injective', 'category': 'DEFI_UTILITY', 'role': 'Finance Blockchain', 'strategy': 'SCALE_OUT', 'support_economy_score': 80 },

    # --- GAMING ( The Playground ) ---
    'GALA': { 'name': 'Gala', 'category': 'GAMING', 'role': 'Gaming Ecosystem', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 60 },
    'BEAM': { 'name': 'Beam', 'category': 'GAMING', 'role': 'Gaming Network', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 65 },
    'SAND': { 'name': 'The Sandbox', 'category': 'GAMING', 'role': 'Metaverse', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 50 },
    'MANA': { 'name': 'Decentraland', 'category': 'GAMING', 'role': 'Metaverse', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 50 },
    'AXS': { 'name': 'Axie Infinity', 'category': 'GAMING', 'role': 'Play to Earn', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 50 },

    # --- SPECULATIVE ( The Casino ) ---
    'DOGE': { 'name': 'Dogecoin', 'category': 'SPECULATIVE', 'role': 'The OG Meme', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 40 },
    'SHIB': { 'name': 'Shiba Inu', 'category': 'SPECULATIVE', 'role': 'Doge Killer', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 20 },
    'PEPE': { 'name': 'Pepe', 'category': 'SPECULATIVE', 'role': 'Pure Vibes', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 10 },
    'WIF': { 'name': 'dogwifhat', 'category': 'SPECULATIVE', 'role': 'Solana Mascot', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 10 },
    'BONK': { 'name': 'Bonk', 'category': 'SPECULATIVE', 'role': 'Solana Community Coin', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 20 },
    'FLOKI': { 'name': 'Floki', 'category': 'SPECULATIVE', 'role': 'Utility Meme', 'strategy': 'AGGRESSIVE_FLIP', 'support_economy_score': 20 },
}

import requests
import time

# ... (Previous STATIC_LIBRARY content remains, renaming ASSET_LIBRARY to STATIC_LIBRARY is implied or we just use ASSET_LIBRARY as the static source)

# CACHE (Simple in-memory cache)
_ASSET_CACHE = {}

def get_asset_profile(symbol: str) -> dict:
    """
    Returns the knowledge profile for a given symbol.
    
    HIERARCHY:
    1. Static "Textbook" Library (ASSET_LIBRARY) - Instant, Curated.
    2. Dynamic CoinGecko API - Slower, Comprehensive (10k+ coins).
    3. Fallback - "Unknown/Speculative".
    """
    symbol = symbol.upper()
    
    # 1. Check Static Library (Textbooks)
    profile = ASSET_LIBRARY.get(symbol)
    if profile:
        # Ensure description fields exist
        if 'whitepaper_summary' not in profile:
            profile['whitepaper_summary'] = f"{profile.get('name')} ({profile.get('role')}). Key player in {profile.get('category')} sector."
        return profile
        
    # 2. Check Cache
    if symbol in _ASSET_CACHE:
        return _ASSET_CACHE[symbol]
        
    # 3. Dynamic Discovery (CoinGecko API)
    try:
        print(f"[KNOWLEDGE] 🔍 Dynamic Discovery: Auditing {symbol} via CoinGecko...")
        url = "https://api.coingecko.com/api/v3/search"
        params = {'query': symbol}
        resp = requests.get(url, params=params, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            coins = data.get('coins', [])
            
            # Find exact symbol match
            target = None
            for coin in coins:
                if coin.get('symbol', '').upper() == symbol:
                    target = coin
                    break
            
            if target:
                # Construct Dynamic Profile
                # Rank < 100 -> SCALE_OUT (Infrastructure/Defi)
                # Rank > 100 -> AGGRESSIVE_FLIP (Speculative)
                rank = target.get('market_cap_rank', 9999)
                rank = rank if rank is not None else 9999
                
                if rank <= 20:
                    cat = 'INFRASTRUCTURE'
                    strat = 'SCALE_OUT'
                    role = 'Major Market Cap'
                    score = 80
                elif rank <= 100:
                    cat = 'DEFI_UTILITY' 
                    strat = 'SCALE_OUT'
                    role = 'Mid Cap Altcoin'
                    score = 70
                else:
                    cat = 'SPECULATIVE'
                    strat = 'AGGRESSIVE_FLIP'
                    role = 'Small Cap / Meme'
                    score = 30
                    
                dynamic_profile = {
                    'name': target.get('name', symbol),
                    'category': cat,
                    'role': role,
                    'whitepaper_summary': f"Dynamically Discovered Asset. Market Rank #{rank}. (Source: CoinGecko)",
                    'strategy': strat,
                    'support_economy_score': score,
                    'is_dynamic': True
                }
                
                _ASSET_CACHE[symbol] = dynamic_profile
                return dynamic_profile
                
    except Exception as e:
        print(f"[KNOWLEDGE] Discovery Failed for {symbol}: {e}")

    # 4. Fallback
    return {
        'name': symbol,
        'category': 'UNKNOWN',
        'role': 'Uncharted Territory',
        'whitepaper_summary': 'No data available. Proceed with caution.',
        'strategy': 'AGGRESSIVE_FLIP', # Treat unknown as risky -> Sell 100%
        'support_economy_score': 0
    }
