
import pandas as pd
import os

path = "fulcrum/arena/numerai/validation.parquet"
if os.path.exists(path):
    df = pd.read_parquet(path)
    print("Columns:", df.columns.tolist()[:10])
    print("Targets:", [c for c in df.columns if "target" in c])
    print("Shape:", df.shape)
else:
    print("File not found.")
