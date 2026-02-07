
import sys
import os
import requests
import json

def test_voice(url):
    print(f"🎤 Testing Voice Connection to: {url[:30]}...")
    
    payload = {
        "username": "LEF Technician",
        "embeds": [{
            "title": "Mic Check 1, 2",
            "description": "System Voice Active. Connection Verified.",
            "color": 0x2ecc71, # Green
            "footer": {"text": "Phase 23 Complete"}
        }]
    }
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code in [200, 204]:
            print("✅ SUCCESS: Message sent. Check your Discord Channel.")
        else:
            print(f"❌ FAILURE: API returned {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Webhook URL: ").strip()
        
    if url:
        test_voice(url)
    else:
        print("No URL provided.")
