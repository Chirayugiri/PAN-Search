#!/usr/bin/env python3
"""
Simple script to test the Transaction Search API
"""
import requests
import json
import sys
from typing import Optional

API_BASE = "http://localhost:8000"


def test_health():
    """Test the health endpoint"""
    print("🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        response.raise_for_status()
        print(f"✅ Health check passed: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
        print("   Start it with: python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_search(pan: Optional[str] = None, seed_name: Optional[str] = None, limit: int = 10):
    """Test the search endpoint"""
    if not pan and not seed_name:
        print("❌ Provide either pan or seed_name")
        return False
    
    print(f"\n🔍 Testing /search endpoint...")
    params = {"limit": limit}
    if pan:
        params["pan"] = pan
        print(f"   Searching by PAN: {pan}")
    if seed_name:
        params["seed_name"] = seed_name
        print(f"   Searching by name: {seed_name}")
    
    try:
        response = requests.get(f"{API_BASE}/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Search successful!")
        print(f"   Found {data['count']} results")
        
        if data['data']:
            print(f"\n   First result (sample):")
            first = data['data'][0]
            # Show key fields
            for key in ['pan_numbers', 'buyer', 'seller', 'score', 'age']:
                if key in first:
                    val = first[key]
                    if val:
                        display_val = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
                        print(f"      {key}: {display_val}")
        else:
            print("   No results found")
        
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Search failed: {e}")
        try:
            error_detail = response.json()
            print(f"   Details: {error_detail}")
        except:
            print(f"   Response: {response.text}")
        return False
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return False


def main():
    """Main test function"""
    print("=" * 60)
    print("Transaction Search API Test Script")
    print("=" * 60)
    
    # Test health first
    if not test_health():
        sys.exit(1)
    
    # Test search - you can modify these examples
    print("\n" + "=" * 60)
    
    # Example 1: Search by PAN (modify with a real PAN from your data)
    if len(sys.argv) > 1:
        # If PAN provided as argument
        pan = sys.argv[1].upper()
        test_search(pan=pan, limit=5)
    elif len(sys.argv) > 2 and sys.argv[1] == "--name":
        # If name provided as argument
        seed_name = sys.argv[2]
        test_search(seed_name=seed_name, limit=5)
    else:
        # Default: test with a sample (you'll need to update this with a real PAN from your data)
        print("ℹ️  No search parameters provided.")
        print("   Usage examples:")
        print("     python test_api.py ABCDE1234F")
        print("     python test_api.py --name 'John Doe'")
        print("     python test_api.py --name 'चिरायु संजय गिरी'")
        print("\n   Or run without arguments to just test health check")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)

