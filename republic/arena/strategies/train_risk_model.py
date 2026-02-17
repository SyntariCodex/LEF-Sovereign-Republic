
import os
import json
import pandas as pd
import numpy as np
import sys
from datetime import datetime

# Setup Path
# strategies -> arena -> republic -> LEF Ai (ROOT)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from republic.departments.Dept_Strategy.agent_gladiator import AgentGladiator
from autogluon.tabular import TabularPredictor

def compute_risk_features(df):
    """
    Engineering features to predict liquidation risk.
    """
    print("[RISK] ⚙️  Engineering Features...")
    df = df.copy()
    
    # Ensure datetime
    if 'Timestamp' in df.columns:
        df['datetime'] = pd.to_datetime(df['Timestamp'], unit='s')
    elif 'Date' in df.columns:
        df['datetime'] = pd.to_datetime(df['Date'])
        
    df = df.sort_values('datetime')
    
    # 1. Price Dynamics
    df['returns'] = df['Close'].pct_change()
    df['volatility_24h'] = df['returns'].rolling(window=1440).std()
    
    # 2. Drawdown from 24h High
    df['rolling_max_24h'] = df['Close'].rolling(window=1440).max()
    df['drawdown_24h'] = (df['Close'] - df['rolling_max_24h']) / df['rolling_max_24h']
    
    # 3. Volume Intensity
    df['vol_ma_24h'] = df['Volume'].rolling(window=1440).mean()
    df['vol_shock'] = df['Volume'] / df['vol_ma_24h']
    
    # TARGET: Will we crash > 3% in the next 4 hours (240 mins)?
    # Look ahead 240 rows
    df['future_min_4h'] = df['Close'].rolling(window=240).min().shift(-240)
    df['max_drop_4h'] = (df['future_min_4h'] - df['Close']) / df['Close']
    
    # Label: 1 if drop is worse than -3%, else 0
    df['RISK_CRASH'] = (df['max_drop_4h'] < -0.03).astype(int)
    
    # Clean NaN
    df = df.dropna()
    print(f"[RISK] ✅ Features Ready. risk_crash rate: {df['RISK_CRASH'].mean():.4f}")
    return df

def train_risk_model():
    gladiator = AgentGladiator()
    
    # 1. DOWNLOAD
    # Using the famous 'mczielinski/bitcoin-historical-data'
    dataset_slug = "mczielinski/bitcoin-historical-data"
    data_dir = gladiator.fetch_dataset(dataset_slug, target_subdir="btc_history")
    
    if not data_dir:
        print("Failed to download.")
        return
        
    # Find CSV
    csv_file = None
    for f in os.listdir(data_dir):
        if f.endswith('.csv'):
            csv_file = os.path.join(data_dir, f)
            break
            
    if not csv_file:
        print("No CSV found.")
        return
        
    print(f"[RISK] 📂 Loading Data: {csv_file}")
    # Load last 500k rows to save memory/speed for MVP
    try:
        df = pd.read_csv(csv_file)
        print(f"[RISK] Loaded {len(df)} rows.")
        # Slice recent history (e.g., last 2 years ~ 1M minutes)
        # Assuming 1 min data.
        df = df.tail(1000000) 
    except Exception as e:
        print(f"Error loading: {e}")
        return

    # 2. PREPARE
    train_df = compute_risk_features(df)
    
    # Use a subset of columns for training
    features = ['Close', 'volatility_24h', 'drawdown_24h', 'vol_shock', 'RISK_CRASH']
    train_data = train_df[features]
    
    # Split Time-Series (Audit check)
    cutoff = int(len(train_data) * 0.9)
    train = train_data.iloc[:cutoff]
    test = train_data.iloc[cutoff:]
    
    print(f"[RISK] 🥊 Training AutoGluon on {len(train)} rows...")
    
    # 3. TRAIN
    model_path = os.path.join(BASE_DIR, 'republic', 'models', 'risk_v1')
    predictor = TabularPredictor(label='RISK_CRASH', path=model_path, eval_metric='f1').fit(
        train, 
        time_limit=300, # 5 mins for prototype
        presets='medium_quality' 
    )
    
    # 4. EVALUATE
    print("[RISK] ⚖️  Evaluating on Test Set...")
    performance = predictor.evaluate(test)
    print(f"[RISK] Performance: {performance}")
    
    # 5. INTEGRATION HINT
    print(f"[RISK] Model Saved to: {model_path}")
    print(f"[RISK] To Use: predictor.predict(current_features)")

    # Phase 37: Publish model update notification to Redis (TLS-10)
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        version_info = json.dumps({
            'model_path': model_path,
            'trained_at': datetime.now().isoformat(),
            'performance': str(performance),
        })
        r.publish('risk_model_updated', version_info)
        r.set('risk_model:latest_version', version_info)
        print(f"[RISK] Model update published to Redis")
    except Exception as e:
        print(f"[RISK] Redis notification skipped: {e}")

if __name__ == "__main__":
    train_risk_model()
