
import os
import numerapi
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(ENV_PATH)

napi = numerapi.NumerAPI(os.getenv("NUMERAI_PUBLIC_ID"), os.getenv("NUMERAI_SECRET_KEY"))
datasets = napi.list_datasets()
print("Available Datasets:")
for d in datasets:
    if "int8" in d:
        print(d)
