
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # Try finding it in config
    import json
    try:
        with open('republic/config/config.json') as f:
            c = json.load(f)
            api_key = c.get('gemini', {}).get('api_key')
    except Exception:
        pass

if api_key and api_key.startswith("ENV:"):
    print("API Key is ENV var reference")
    exit()

if api_key:
    genai.configure(api_key=api_key)
    print("Listing Models...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No API Key found to check models.")
