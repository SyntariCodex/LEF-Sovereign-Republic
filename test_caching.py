
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    from google.generativeai import caching
    print("Caching module found.")
except ImportError:
    print("Caching module NOT found.")
    exit()

try:
    # Try to create a dummy cache
    # content = "This is a cached system instruction."
    # cache = caching.CachedContent.create(
    #     model='models/gemini-1.5-flash-001',
    #     display_name='test_cache',
    #     system_instruction=content,
    #     ttl=300
    # )
    # print(f"Cache created: {cache.name}")
    pass
except Exception as e:
    print(f"Cache creation failed: {e}")
