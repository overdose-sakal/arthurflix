#!/usr/bin/env python3
"""
Test script to verify ShrinkEarn API is working correctly
Run this to debug the API integration
"""

import requests
import json

# Your API key
API_KEY = '1c444b32ebb82524c41ea5b89ad3b90a52df0a5f'

# Test URL to shorten
TEST_URL = 'https://www.google.com'

# API endpoint
API_ENDPOINT = 'https://shrinkearn.com/api'

print("=" * 60)
print("SHRINKEARN API TEST")
print("=" * 60)

# Test 1: Basic API call without alias
print("\n🧪 Test 1: Basic API call (no alias)")
print(f"API Key: {API_KEY[:10]}...")
print(f"Test URL: {TEST_URL}")

params1 = {
    'api': API_KEY,
    'url': TEST_URL,
}

try:
    print(f"\n📡 Making request to: {API_ENDPOINT}")
    response1 = requests.get(API_ENDPOINT, params=params1, timeout=10)
    
    print(f"✅ Status Code: {response1.status_code}")
    print(f"📄 Response Headers: {dict(response1.headers)}")
    print(f"📄 Raw Response Text:\n{response1.text}\n")
    
    if response1.status_code == 200:
        try:
            data = response1.json()
            print(f"📊 Parsed JSON:")
            print(json.dumps(data, indent=2))
            
            if data.get('status') == 'success':
                print(f"\n✅ SUCCESS! Shortened URL: {data.get('shortenedUrl')}")
            elif 'shortenedUrl' in data:
                print(f"\n✅ SUCCESS! Shortened URL: {data.get('shortenedUrl')}")
            else:
                print(f"\n❌ FAILED: Unexpected response format")
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
    else:
        print(f"❌ HTTP Error: {response1.status_code}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: API call with custom alias
print("\n" + "=" * 60)
print("🧪 Test 2: API call with custom alias")

params2 = {
    'api': API_KEY,
    'url': TEST_URL,
    'alias': 'testlink123'
}

try:
    print(f"\n📡 Making request with alias: testlink123")
    response2 = requests.get(API_ENDPOINT, params=params2, timeout=10)
    
    print(f"✅ Status Code: {response2.status_code}")
    print(f"📄 Raw Response Text:\n{response2.text}\n")
    
    if response2.status_code == 200:
        try:
            data = response2.json()
            print(f"📊 Parsed JSON:")
            print(json.dumps(data, indent=2))
            
            if data.get('status') == 'success':
                print(f"\n✅ SUCCESS! Shortened URL: {data.get('shortenedUrl')}")
            elif 'shortenedUrl' in data:
                print(f"\n✅ SUCCESS! Shortened URL: {data.get('shortenedUrl')}")
            else:
                print(f"\n❌ FAILED: {data.get('error', 'Unknown error')}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)