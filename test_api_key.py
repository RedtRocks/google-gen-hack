"""
Test script to verify your Gemini API key is valid
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    print("❌ No API key found in environment or .env file")
    exit(1)

print(f"Testing API key: {API_KEY[:20]}...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

payload = {
    "contents": [{"parts": [{"text": "Say hello"}]}],
}

try:
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    
    if response.status_code == 200:
        print("✅ API key is VALID!")
        result = response.json()
        if 'candidates' in result:
            text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"Test response: {text}")
    else:
        print(f"❌ API key is INVALID")
        print(f"Status code: {response.status_code}")
        error_detail = response.json()
        print(f"Error: {error_detail.get('error', {}).get('message', 'Unknown error')}")
        print(f"\nFull error details:")
        import json
        print(json.dumps(error_detail, indent=2))
        
        print("\n🔧 How to fix:")
        print("1. Go to https://aistudio.google.com/app/apikey")
        print("2. Click 'Create API Key' or 'Get API key'")
        print("3. Copy the NEW key (it starts with 'AIza...')")
        print("4. Update your .env file with the new key")
        
except Exception as e:
    print(f"❌ Request failed: {str(e)}")
    print("\n🔧 Check your internet connection")
