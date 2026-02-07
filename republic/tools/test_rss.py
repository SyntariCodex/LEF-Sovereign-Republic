import feedparser
import sys

urls = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

import requests

print("Testing Feedparser with Requests...")
for url in urls:
    try:
        print(f"Fetching: {url}")
        # Try standard requests (uses certifi)
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            print(f"Entries: {len(feed.entries)}")
            if feed.entries:
                print(f"Sample: {feed.entries[0].title}")
        else:
             print("Failed to fetch.")
             
    except Exception as e:
        print(f"Requests Exception: {e}")
    print("-" * 20)
