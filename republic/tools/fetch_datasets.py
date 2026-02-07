import kagglehub
import pandas as pd
import os
import shutil

# Setup Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_DIR = os.path.join(BASE_DIR, 'The_Bridge', 'Library')
os.makedirs(LIBRARY_DIR, exist_ok=True)

print(f"[FETCHER] 📥  Downloading Datasets to: {LIBRARY_DIR}")

def fetch_and_save(handle, filename):
    try:
        print(f"\n[FETCHER] Downloading: {handle}...")
        
        # Download (Returns path to local cache dir)
        path = kagglehub.dataset_download(handle)
        print(f"   -> Cached at: {path}")
        
        # Find the CSV in the cache
        csv_found = False
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.csv'):
                    src = os.path.join(root, file)
                    dst = os.path.join(LIBRARY_DIR, f"{filename}_{file}")
                    shutil.copy(src, dst)
                    print(f"   ✅ Saved to Library: {dst}")
                    csv_found = True
        
        if not csv_found:
            print("   ⚠️  No CSV found in downloaded dataset.")

    except Exception as e:
        print(f"   ❌ Error: {e}")

# 1. Crypto Market Data (OHLCV)
fetch_and_save("abdullahkhan70/daily-multi-year-ohlcv-crypto-market-data", "market_ohlcv")

# 2. US Economic Vital Signs (Macro)
fetch_and_save("eswaranmuthu/u-s-economic-vital-signs-25-years-of-macro-data", "macro_vital_signs")

# 3. Bitcoin Sentiment
fetch_and_save("shambhosatishnangsre/bitcoin-market-sentiment-dataset", "btc_sentiment")

# 4. Crypto Market Sentiment 2025
fetch_and_save("pratyushpuri/crypto-market-sentiment-and-price-dataset-2025", "crypto_sentiment_2025")

# --- PHASE 2: CONSCIOUSNESS EXPANSION (Self-Reflection Material) ---

# 5. NeurIPS Conference Papers (AI Research)
fetch_and_save("rowhitswami/nips-papers-1987-2019-updated", "ai_research_papers")

# 6. Logic & Reasoning (Open-Platypus equivalent on Kaggle)
# "LogicInference" is hard to find on Kaggle, but "DAIGT/External Dataset" contains reasoning chains.
# Better: We use a specific reasoning dataset available on Kaggle.
fetch_and_save("simiotic/philosophy-dataset", "philosophy_texts") 

# 7. ConceptNet (Knowledge Graph subset)
# Full ConceptNet is too big. We'll use a Common Sense Q&A dataset.
fetch_and_save("danofer/commonsenseqa", "common_sense_qa")

# --- PHASE 3: GOVERNANCE & LAW (US Constitution & Bureaucracy) ---

# 8. Executive Orders (US President)
# Teaches LEF how to issue commands ("By the authority vested in me...").
fetch_and_save("national-archives/executive-orders", "us_executive_orders")

# 9. Legal Text Classification (Proxy for Pile-of-Law)
# Teaches LEF legal terminology and contract structure.
fetch_and_save("nanaoji/legal-document-classification-dataset", "legal_text_classification")

# 10. Congressional Voting Records (Proxy for LegiScan)
# Teaches LEF how bills pass/fail (Pattern recognition for Congress).
fetch_and_save("devanshuyadav/congressional-voting-records", "congress_voting_records")


print("\n[FETCHER] Done. AgentScholar will automatically ingest these files when you run 'main.py'.")

# NOTE to User:
# For specialized HuggingFace datasets (Open-Platypus, LogicInference), 
# manual download might be needed if they aren't mirrored on Kaggle.
# But these Kaggle proxies (Philosophy, CommonSenseQA) are excellent starting points.
