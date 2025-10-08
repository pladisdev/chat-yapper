#!/usr/bin/env python3
"""
Per-User Queuing Demo Script

This script demonstrates the new "Ignore messages from users who are already speaking" setting.
It shows how the same user's new messages are handled when they already have TTS active.
"""

import asyncio
import aiohttp
import time

API_BASE_URL = "http://localhost:8000"

async def send_message(session, username, message, delay=0):
    """Send a message with optional delay"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    data = aiohttp.FormData()
    data.add_field('user', username)
    data.add_field('text', message)
    data.add_field('eventType', 'chat')
    
    try:
        async with session.post(f"{API_BASE_URL}/api/simulate", data=data) as response:
            result = await response.json()
            timestamp = time.strftime("%H:%M:%S")
            
            if response.status == 200 and result.get("ok", True):
                print(f"{timestamp} ✅ {username}: {message}")
            else:
                reason = result.get("reason", "Unknown")
                print(f"{timestamp} 🚫 {username}: {message} - IGNORED ({reason})")
                
    except Exception as e:
        print(f"❌ Error sending message: {e}")

async def get_setting(session, setting_path):
    """Get current setting value"""
    try:
        async with session.get(f"{API_BASE_URL}/api/settings") as response:
            settings = await response.json()
            # Navigate nested setting path like "messageFiltering.ignoreIfUserSpeaking"
            value = settings
            for key in setting_path.split('.'):
                value = value.get(key, {})
            return value
    except Exception as e:
        print(f"❌ Error getting setting: {e}")
        return None

async def set_setting(session, setting_path, new_value):
    """Update a setting"""
    try:
        # Get current settings
        async with session.get(f"{API_BASE_URL}/api/settings") as response:
            settings = await response.json()
        
        # Update the nested setting
        keys = setting_path.split('.')
        target = settings
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = new_value
        
        # Save updated settings
        async with session.post(f"{API_BASE_URL}/api/settings", 
                               json=settings,
                               headers={'Content-Type': 'application/json'}) as response:
            if response.status == 200:
                print(f"✅ Updated {setting_path} = {new_value}")
                return True
            else:
                print(f"❌ Failed to update setting: {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ Error updating setting: {e}")
        return False

async def demo_with_setting(session, enabled):
    """Run demo with per-user queuing enabled or disabled"""
    setting_name = "messageFiltering.ignoreIfUserSpeaking"
    
    print(f"\n{'='*60}")
    print(f"DEMO: Per-User Queuing {'ENABLED' if enabled else 'DISABLED'}")
    print(f"{'='*60}")
    
    # Update the setting
    await set_setting(session, setting_name, enabled)
    await asyncio.sleep(0.5)  # Let setting take effect
    
    # Test scenario: Same user sends multiple messages quickly
    print(f"\n📝 Scenario: 'TestUser' sends 3 messages rapidly")
    print(f"Expected behavior: {'Only first message should play, others ignored' if enabled else 'All messages should play'}")
    print("-" * 40)
    
    # Send 3 messages from the same user with small delays
    await send_message(session, "TestUser", "This is my first message!", 0)
    await send_message(session, "TestUser", "This is my second message!", 0.5)
    await send_message(session, "TestUser", "This is my third message!", 1.0)
    
    # Wait a bit for TTS to process
    print("\n⏳ Waiting for TTS to process...")
    await asyncio.sleep(3)
    
    # Test with different user to show it doesn't affect other users
    print(f"\n📝 Testing different user (should always work):")
    print("-" * 40)
    await send_message(session, "DifferentUser", "I'm a different user, this should always work!")
    
    await asyncio.sleep(2)

async def main():
    """Run the per-user queuing demonstration"""
    print("🎮 Per-User Queuing Demo for Chat Yapper")
    print("Make sure your Chat Yapper backend is running on http://localhost:8000\n")
    
    async with aiohttp.ClientSession() as session:
        # Check current setting
        current_value = await get_setting(session, "messageFiltering.ignoreIfUserSpeaking")
        print(f"Current 'ignoreIfUserSpeaking' setting: {current_value}")
        
        try:
            # Demo with setting enabled (default behavior)
            await demo_with_setting(session, True)
            
            # Wait between demos
            print(f"\n⏳ Waiting 5 seconds before next demo...")
            await asyncio.sleep(5)
            
            # Demo with setting disabled
            await demo_with_setting(session, False)
            
            # Restore original setting
            print(f"\n🔄 Restoring original setting...")
            await set_setting(session, "messageFiltering.ignoreIfUserSpeaking", current_value)
            
        except KeyboardInterrupt:
            print("\n⏹️ Demo interrupted by user")
            # Still restore original setting
            await set_setting(session, "messageFiltering.ignoreIfUserSpeaking", current_value)
        
        print(f"\n🎉 Demo complete!")
        print("=" * 60)
        print("SUMMARY:")
        print("• When ENABLED: Same user's rapid messages are ignored while speaking")
        print("• When DISABLED: All messages play, potentially interrupting each other")
        print("• Different users are never affected by per-user queuing")
        print("• This setting is found in Settings → Message Filtering")

if __name__ == "__main__":
    asyncio.run(main())
