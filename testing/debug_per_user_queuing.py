#!/usr/bin/env python3
"""
Debug script to check per-user queuing setting and test behavior
"""

import asyncio
import aiohttp
import json

API_BASE_URL = "http://localhost:8000"

async def check_setting(session):
    """Check the current per-user queuing setting"""
    try:
        # Check the debug endpoint
        async with session.get(f"{API_BASE_URL}/api/debug/per-user-queuing") as response:
            if response.status == 200:
                data = await response.json()
                print("Current Per-User Queuing Debug Info:")
                print(f"   ignoreIfUserSpeaking: {data.get('ignoreIfUserSpeaking')}")
                print(f"   Active TTS jobs: {data.get('activeJobs', [])}")
                print(f"   Queued TTS jobs: {data.get('queuedJobs', [])}")
                print(f"   Full messageFiltering config: {json.dumps(data.get('messageFiltering', {}), indent=2)}")
                return data.get('ignoreIfUserSpeaking')
            else:
                print(f"Failed to get debug info: {response.status}")
                return None
    except Exception as e:
        print(f"Error checking setting: {e}")
        return None

async def send_test_messages(session, username="TestUser"):
    """Send test messages from the same user"""
    print(f"\nTesting with user: {username}")
    
    messages = [
        "First message - this should always work",
        "Second message - this should be ignored if setting is ON",
        "Third message - this should also be ignored if setting is ON"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"\nSending message {i}: {message}")
        
        data = aiohttp.FormData()
        data.add_field('user', username)
        data.add_field('text', message)
        data.add_field('eventType', 'chat')
        
        try:
            async with session.post(f"{API_BASE_URL}/api/simulate", data=data) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("ok", True):
                    print(f"   Message accepted")
                else:
                    reason = result.get("reason", "Unknown")
                    print(f"   Message rejected: {reason}")
                    
        except Exception as e:
            print(f"   Error: {e}")
        
        # Small delay between messages
        await asyncio.sleep(0.5)

async def toggle_setting(session, new_value):
    """Toggle the per-user queuing setting"""
    try:
        # Get current settings
        async with session.get(f"{API_BASE_URL}/api/settings") as response:
            settings = await response.json()
        
        # Update the setting
        if "messageFiltering" not in settings:
            settings["messageFiltering"] = {}
        settings["messageFiltering"]["ignoreIfUserSpeaking"] = new_value
        
        # Save updated settings
        async with session.post(f"{API_BASE_URL}/api/settings", 
                               json=settings,
                               headers={'Content-Type': 'application/json'}) as response:
            if response.status == 200:
                print(f"Set ignoreIfUserSpeaking = {new_value}")
                return True
            else:
                print(f"Failed to update setting: {response.status}")
                return False
                
    except Exception as e:
        print(f"Error updating setting: {e}")
        return False

async def main():
    """Run the debug test"""
    print("Per-User Queuing Debug Tool")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Check current setting
        print("1. Checking current setting...")
        current_setting = await check_setting(session)
        
        if current_setting is None:
            print("Could not determine current setting. Is the backend running?")
            return
        
        print(f"\n2. Current setting: ignoreIfUserSpeaking = {current_setting}")
        
        # Test with current setting
        print(f"\n3. Testing with current setting ({current_setting})...")
        await send_test_messages(session, "DebugUser")
        
        # Wait for TTS to clear
        print(f"\nWaiting 3 seconds for TTS to clear...")
        await asyncio.sleep(3)
        
        # Toggle setting and test again
        new_setting = not current_setting
        print(f"\n4. Toggling setting to {new_setting}...")
        if await toggle_setting(session, new_setting):
            await asyncio.sleep(1)  # Let setting take effect
            
            print(f"\n5. Testing with new setting ({new_setting})...")
            await send_test_messages(session, "DebugUser2")
            
            # Restore original setting
            print(f"\n6. Restoring original setting ({current_setting})...")
            await toggle_setting(session, current_setting)
        
        # Final check
        print(f"\n7. Final setting check...")
        await check_setting(session)

if __name__ == "__main__":
    asyncio.run(main())
