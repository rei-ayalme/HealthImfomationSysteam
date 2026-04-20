#!/usr/bin/env python3
"""
Mediastack API Connection Test Script
Verify API Key configuration and API connectivity
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_api_key_configured():
    """Test if API Key is configured"""
    api_key = os.getenv("MEDIASTACK_API_KEY", "")
    if not api_key:
        print("[FAIL] MEDIASTACK_API_KEY not set")
        print("       Please check .env file configuration")
        return False

    if api_key == "your_mediastack_api_key_here":
        print("[FAIL] API Key is placeholder value")
        print("       Please set real API Key in .env file")
        return False

    print(f"[PASS] API Key configured: {api_key[:8]}...{api_key[-4:]}")
    return True


def test_api_connection():
    """Test Mediastack API connection"""
    api_key = os.getenv("MEDIASTACK_API_KEY", "")

    if not api_key:
        print("[SKIP] Connection test: API Key not configured")
        return False

    # Build test request URL
    url = f"http://api.mediastack.com/v1/news?access_key={api_key}&keywords=health&countries=cn&limit=1"

    try:
        print("\nTesting API connection...")
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                articles = data.get("data", [])
                print(f"[PASS] API connection successful! Got {len(articles)} news")

                if articles:
                    article = articles[0]
                    print(f"\nSample News:")
                    print(f"  Title: {article.get('title', 'N/A')[:50]}...")
                    print(f"  Source: {article.get('source', 'N/A')}")
                    print(f"  Date: {article.get('published_at', 'N/A')}")
                return True
            else:
                print(f"[WARN] API returned unexpected data: {data}")
                return False
        elif response.status_code == 401:
            print(f"[FAIL] API authentication failed (401): Invalid API Key")
            print(f"       Please check MEDIASTACK_API_KEY in .env file")
            return False
        elif response.status_code == 429:
            print(f"[WARN] API rate limit (429): Too many requests")
            return False
        else:
            print(f"[FAIL] API request failed: HTTP {response.status_code}")
            print(f"       Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"[FAIL] Connection timeout: Cannot connect to Mediastack API")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Connection error: Network issue")
        return False
    except Exception as e:
        print(f"[FAIL] Test exception: {str(e)}")
        return False


def test_backend_integration():
    """Test backend DataLoader integration"""
    print("\n" + "=" * 50)
    print("Testing Backend DataLoader Integration...")
    print("=" * 50)

    try:
        # Add project root to path
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from modules.data.loader import DataLoader

        loader = DataLoader()
        news = loader.fetch_health_news(limit=3)

        print(f"[PASS] DataLoader call successful! Got {len(news)} news")

        for i, item in enumerate(news, 1):
            print(f"\n{i}. {item.get('title', 'N/A')[:40]}...")
            print(f"   Desc: {item.get('description', 'N/A')[:50]}...")
            print(f"   Source: {item.get('source', 'N/A')}")
            print(f"   Date: {item.get('publishedAt', 'N/A')}")
            print(f"   URL: {item.get('url', '#')}")

        return True

    except Exception as e:
        print(f"[FAIL] DataLoader test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("=" * 50)
    print("Mediastack API Connection Test")
    print("=" * 50)

    # Test 1: API Key configuration
    print("\n[Test 1] Check API Key configuration...")
    key_ok = test_api_key_configured()

    # Test 2: API connection
    print("\n[Test 2] Test API connection...")
    connection_ok = test_api_connection()

    # Test 3: Backend integration
    print("\n[Test 3] Test backend integration...")
    integration_ok = test_backend_integration()

    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    print(f"API Key Config: {'PASS' if key_ok else 'FAIL'}")
    print(f"API Connection: {'PASS' if connection_ok else 'FAIL'}")
    print(f"Backend Integration: {'PASS' if integration_ok else 'FAIL'}")

    if key_ok and connection_ok and integration_ok:
        print("\n[SUCCESS] All tests passed! Mediastack API configured correctly")
        return 0
    else:
        print("\n[WARNING] Some tests failed, please check configuration")
        return 1


if __name__ == "__main__":
    sys.exit(main())
