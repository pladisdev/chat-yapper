#!/usr/bin/env python3
"""
Simple example showing the difference between single user and random user modes
Run this to see a quick side-by-side comparison
"""

import asyncio
import sys
import os

# Add the testing directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our simulator classes
try:
    from quick_sim import send_message, QUICK_MESSAGES
    import aiohttp
    import random
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the testing directory")
    sys.exit(1)

async def demo_single_user():
    """Demo single user mode"""
    print("SINGLE USER MODE DEMO")
    print("All messages will be from 'DemoUser'")
    print("-" * 40)
    
    async with aiohttp.ClientSession() as session:
        for i in range(5):
            message = random.choice(QUICK_MESSAGES)
            await send_message(session, "DemoUser", message, "chat")
            await asyncio.sleep(1)  # 1 second between messages

async def demo_random_users():
    """Demo random user mode"""
    print("\nRANDOM USER MODE DEMO")
    print("Each message will be from a different user")
    print("-" * 40)
    
    usernames = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    
    async with aiohttp.ClientSession() as session:
        for i in range(5):
            username = random.choice(usernames)
            message = random.choice(QUICK_MESSAGES)
            await send_message(session, username, message, "chat")
            await asyncio.sleep(1)  # 1 second between messages

async def main():
    """Run both demos"""
    print("Chat Yapper User Mode Comparison")
    print("=" * 50)
    print("This demonstrates the difference between single user and random user modes")
    print("Perfect for testing per-user TTS queuing vs parallel audio!")
    print()
    
    try:
        await demo_single_user()
        await asyncio.sleep(2)  # Pause between demos
        await demo_random_users()
        
        print("\nDemo complete!")
        print("\nKey differences:")
        print("• Single user: Great for testing per-user queuing (same user won't interrupt)")
        print("• Random users: Great for testing parallel audio (multiple voices at once)")
    
    except Exception as e:
        print(f"Demo error: {e}")
        print("Make sure Chat Yapper backend is running on http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(main())
