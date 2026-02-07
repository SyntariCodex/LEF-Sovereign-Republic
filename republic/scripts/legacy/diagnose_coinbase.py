import ccxt
import json
import os
import sys

# Load Config
try:
    with open('republic/config/config.json', 'r') as f:
        config = json.load(f)
        api_key = config['coinbase']['api_key']
        api_secret = config['coinbase']['api_secret']
        print(f"Loaded Keys.")
        print(f"API Key: {'*' * 8}...{api_key[-4:]}")
        print(f"Secret: {'*' * 8}...{api_secret[-4:]}")
except Exception as e:
    print(f"Failed to load config: {e}")
    sys.exit(1)

# Init Exchange
try:
    print("\nAttempting Connection to Coinbase Advanced Trade (Real API)...")
    exchange = ccxt.coinbaseadvanced({
        'apiKey': api_key,
        'secret': api_secret,
    })
    
    # 1. Fetch Ticker (Simple)
    print("1. Fetching BTC/USD Ticker...")
    ticker = exchange.fetch_ticker('BTC/USD')
    print(f"✅ Success! BTC Price: {ticker['last']}")
    
    # 2. Fetch OHLCV (Complexity)
    print("2. Fetching BTC/USD Candles...")
    candles = exchange.fetch_ohlcv('BTC/USD', '1h', limit=5)
    print(f"✅ Success! Retrieved {len(candles)} candles.")
    
except Exception as e:
    print(f"\n❌ CONNECTION FAILED:")
    print(e)
