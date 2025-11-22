#!/usr/bin/env python3
"""
Simple test script to verify automatic token refresh functionality
"""

import asyncio
import requests
from datetime import datetime

async def test_auto_refresh():
    """Test the automatic refresh functionality"""
    base_url = "http://localhost:8000"
    
    print("Testing Automatic Token Refresh Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Check if backend is running
        print("1. Checking backend connection...")
        response = requests.get(f"{base_url}/api/twitch/status")
        if response.status_code != 200:
            print("Backend not running or Twitch not configured")
            return
        print("Backend connected")
        
        # Test 2: Test the auto-refresh endpoint
        print("\n2. Testing auto-refresh endpoint...")
        response = requests.post(f"{base_url}/api/twitch/test-auto-refresh")
        result = response.json()
        
        if result.get("success"):
            print("Auto-refresh test completed successfully")
            print(f"   Message: {result.get('message')}")
            print(f"   Refresh attempted: {result.get('refresh_attempted')}")
        else:
            print("Auto-refresh test completed with warnings")
            print(f"   Error: {result.get('error')}")
        
        # Test 3: Check current Twitch status
        print("\n3. Checking final Twitch status...")
        response = requests.get(f"{base_url}/api/twitch/status")
        status = response.json()
        
        if status.get("connected"):
            print("Twitch connection active")
            print(f"   User: {status.get('display_name')} (@{status.get('username')})")
        else:
            print("Twitch not connected")
        
        print("\nTest completed! Check backend logs for detailed refresh process.")
        
    except requests.exceptions.ConnectionError:
        print("Cannot connect to backend. Make sure it's running on port 8000")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auto_refresh())