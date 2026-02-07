"""
History Fetcher (The Librarian)
Downloads historical candle data from Coinbase Public API for training simulations.
"""
import requests
import json
import time
import os
import argparse
from datetime import datetime, timedelta

SCENARIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios')

# Coinbase Granularity (seconds): 3600 = 1 hour, 86400 = 1 day, 900 = 15 mins
GRANULARITY = 3600 

def fetch_candles(product_id, start_str, end_str):
    """
    Fetches candles in chunks (Coinbase limit is 300 candles per request).
    """
    url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
    
    # Parse dates
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    
    all_candles = []
    current_end = end_dt
    
    print(f"📥 Fetching {product_id} from {start_str} to {end_str}...")
    
    while current_end > start_dt:
        # Calculate chunk start (300 hours max per call * 3600s)
        # We step back 200 hours to be safe
        chunk_seconds = 200 * GRANULARITY
        current_start = current_end - timedelta(seconds=chunk_seconds)
        
        if current_start < start_dt:
            current_start = start_dt
            
        params = {
            'start': current_start.isoformat(),
            'end': current_end.isoformat(),
            'granularity': GRANULARITY
        }
        
        try:
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                # data is [time, low, high, open, close, volume]
                if data:
                    all_candles.extend(data)
                    print(f"   ✅ Got {len(data)} candles ({current_start.date()} -> {current_end.date()})")
                else:
                    print(f"   ⚠️ No data for this chunk.")
            else:
                print(f"   ❌ Error {resp.status_code}: {resp.text}")
                
            # Rate limit respect
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
        # Move window back
        current_end = current_start
        
        if current_end <= start_dt:
            break

    # Sort by timestamp ascending (Oldest first)
    all_candles.sort(key=lambda x: x[0])
    
    # Remove duplicates
    seen = set()
    unique_candles = []
    for c in all_candles:
        if c[0] not in seen:
            seen.add(c[0])
            unique_candles.append(c)
            
    print(f"📦 Total Unique Candles: {len(unique_candles)}")
    return unique_candles

def save_scenario(name, product_id, candles):
    filename = f"{name}_{product_id}.json"
    path = os.path.join(SCENARIO_DIR, filename)
    
    scenario_data = {
        "name": name,
        "asset": product_id,
        "granularity": GRANULARITY,
        "count": len(candles),
        "data": candles # [time, low, high, open, close, volume]
    }
    
    with open(path, 'w') as f:
        json.dump(scenario_data, f)
    
    print(f"💾 Saved Scenario: {path}")

if __name__ == "__main__":
    # Expanded Scenario Library (The Curriculum)
    scenarios = {
        # --- CRASHES (Survival Training) ---
        "CRASH_FTX_2022":      {"asset": "SOL-USD", "start": "2022-09-01", "end": "2023-01-01"}, # The Falling Knife
        "CRASH_LUNA_2022":     {"asset": "BTC-USD", "start": "2022-04-01", "end": "2022-08-01"}, # Structural Failure
        "CRASH_COVID_2020":    {"asset": "BTC-USD", "start": "2020-02-01", "end": "2020-06-01"}, # Flash Crash
        
        # --- BULL RUNS (Profit Maximization) ---
        "BULL_SOL_2023":       {"asset": "SOL-USD", "start": "2023-09-01", "end": "2024-01-01"}, # The Rocket Ship
        "BULL_DEFI_SUMMER":    {"asset": "ETH-USD", "start": "2020-06-01", "end": "2020-10-01"}, # Alt Season
        "BULL_ETF_2024":       {"asset": "BTC-USD", "start": "2023-10-01", "end": "2024-02-01"}, # Institutional Flow
        
        # --- CHOP / SIDEWAYS (Patience Training) ---
        "CHOP_BEAR_2018":      {"asset": "BTC-USD", "start": "2018-06-01", "end": "2018-10-01"}, # The Long Winter
        "CHOP_DESERT_2023":    {"asset": "SOL-USD", "start": "2023-04-01", "end": "2023-08-01"}, # The Desert
        "CHOP_ETH_2019":       {"asset": "ETH-USD", "start": "2019-06-01", "end": "2019-10-01"}, # Choppy Accumulation
        
        # --- VOLATILITY (Scalper's Paradise) ---
        "VOL_DOGE_SNL_2021":   {"asset": "DOGE-USD", "start": "2021-03-01", "end": "2021-07-01"}, # Meme Mania
        "VOL_SHIB_2021":       {"asset": "SHIB-USD", "start": "2021-08-01", "end": "2021-12-01"}, # Retail Frenzy
    }
    
    # Verify Dir
    if not os.path.exists(SCENARIO_DIR):
        os.makedirs(SCENARIO_DIR)
        
    for name, cfg in scenarios.items():
        print(f"\n--- Processing {name} ---")
        candles = fetch_candles(cfg['asset'], cfg['start'], cfg['end'])
        save_scenario(name, cfg['asset'], candles)
        
    print("\n✨ All Scenarios Downloaded.")
