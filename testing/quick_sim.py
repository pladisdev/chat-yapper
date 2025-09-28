#!/usr/bin/env python3
"""
Quick Chat Simulator - A simpler version for quick testing

Usage:
  python quick_sim.py                    # Default 30 second simulation
  python quick_sim.py --duration 60      # 60 second simulation
  python quick_sim.py --messages 50      # Send exactly 50 messages
  python quick_sim.py --rapid            # Rapid fire mode (lots of messages quickly)
"""

import asyncio
import aiohttp
import random
import time
import argparse
from typing import List

# Simple configuration
API_BASE_URL = "http://localhost:8000"

# Quick message pools
QUICK_MESSAGES = [
    "Hello!", "Nice!", "Wow!", "LOL", "Great stream!", "Good job!", "Amazing!", 
    "Keep it up!", "Love this!", "So good!", "Awesome!", "gg", "Epic!", "Cool!",
    "Incredible!", "Best streamer!", "This is fun!", "More please!", "So cool!",
    "What's next?", "How do you do that?", "Teach me!", "You're the best!",
    "I love this game!", "Stream more!", "Don't stop!", "This is great!",
    "Amazing gameplay!", "You're so good!", "Keep going!", "I'm hooked!",
]

USERNAMES = [
    "TestUser1", "StreamFan", "ChatBot2024", "Viewer123", "GameLover", 
    "PixelMaster", "RetroGamer", "NightOwl", "CoffeeAddict", "TechNinja",
    "BookWorm", "MusicFan", "ArtLover", "CodeWarrior", "FitnessGuru"
]

EVENT_TYPES = ["chat", "raid", "bits", "sub", "vip", "highlight"]

async def send_message(session: aiohttp.ClientSession, username: str, message: str, event_type: str = "chat"):
    """Send a single message to Chat Yapper"""
    try:
        data = aiohttp.FormData()
        data.add_field('user', username)
        data.add_field('text', message)
        data.add_field('eventType', event_type)
        
        async with session.post(f"{API_BASE_URL}/api/simulate", data=data) as response:
            timestamp = time.strftime("%H:%M:%S")
            event_emoji = {"chat": "💬", "raid": "⚔️", "bits": "💎", "sub": "⭐", "vip": "👑", "highlight": "✨"}.get(event_type, "💬")
            
            if response.status == 200:
                print(f"{timestamp} {event_emoji} {username}: {message}")
                return True
            else:
                print(f"{timestamp} ❌ Failed to send message from {username}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def run_time_based_simulation(duration: int):
    """Run simulation for a specific duration"""
    print(f"🚀 Running {duration}-second simulation...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration:
            # Random delay between messages (realistic chat pacing)
            delay = random.uniform(0.5, 3.0)  # 0.5 to 3 seconds between messages
            await asyncio.sleep(delay)
            
            # Pick random user and message
            username = random.choice(USERNAMES)
            message = random.choice(QUICK_MESSAGES)
            
            # Occasionally send special events (10% chance)
            event_type = "chat"
            if random.random() < 0.1:
                event_type = random.choice(["raid", "bits", "sub", "vip", "highlight"])
                # Adjust message for special events
                if event_type == "raid":
                    message = f"Raid incoming with {random.randint(5, 100)} viewers!"
                elif event_type == "bits":
                    message = f"Thanks for the stream! cheer{random.choice([25, 50, 100, 200])}"
                elif event_type == "sub":
                    message = "Just subscribed! Love the content!"
                elif event_type == "vip":
                    message = "VIP here! Stream is looking great!"
                elif event_type == "highlight":
                    message = "That needs to be clipped!"
            
            success = await send_message(session, username, message, event_type)
            if success:
                message_count += 1
        
        print(f"✅ Sent {message_count} messages in {duration} seconds")
        print(f"📊 Average: {message_count / duration:.2f} messages per second")

async def run_message_count_simulation(target_messages: int):
    """Run simulation until we send a specific number of messages"""
    print(f"🚀 Sending exactly {target_messages} messages...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        sent_count = 0
        
        while sent_count < target_messages:
            # Pick random user and message
            username = random.choice(USERNAMES)
            message = random.choice(QUICK_MESSAGES)
            
            # Occasionally send special events (15% chance for more variety)
            event_type = "chat"
            if random.random() < 0.15:
                event_type = random.choice(["raid", "bits", "sub", "vip", "highlight"])
                
            success = await send_message(session, username, message, event_type)
            if success:
                sent_count += 1
            
            # Small delay to avoid overwhelming the server
            if sent_count < target_messages:
                delay = random.uniform(0.2, 1.5)
                await asyncio.sleep(delay)
        
        elapsed = time.time() - start_time
        print(f"✅ Sent {sent_count} messages in {elapsed:.1f} seconds")
        print(f"📊 Average: {sent_count / elapsed:.2f} messages per second")

async def run_rapid_simulation():
    """Run rapid-fire simulation for testing high load"""
    print("🚀 Running RAPID simulation (high message frequency)...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        message_count = 0
        duration = 30  # 30 seconds of rapid fire
        
        while time.time() - start_time < duration:
            # Send multiple messages in quick succession
            burst_size = random.randint(2, 5)
            for _ in range(burst_size):
                username = random.choice(USERNAMES)
                message = random.choice(QUICK_MESSAGES)
                
                success = await send_message(session, username, message, "chat")
                if success:
                    message_count += 1
                
                # Very short delay between burst messages
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Longer pause between bursts
            await asyncio.sleep(random.uniform(1, 4))
        
        print(f"✅ Rapid simulation complete!")
        print(f"📊 Sent {message_count} messages in {duration} seconds")
        print(f"📊 Average: {message_count / duration:.2f} messages per second")

async def main():
    parser = argparse.ArgumentParser(description="Quick Chat Simulator for Chat Yapper")
    parser.add_argument("--duration", type=int, default=30, help="Simulation duration in seconds (default: 30)")
    parser.add_argument("--messages", type=int, help="Send exactly this many messages (overrides duration)")
    parser.add_argument("--rapid", action="store_true", help="Rapid fire mode for high load testing")
    
    args = parser.parse_args()
    
    print("🎮 Quick Chat Simulator for Chat Yapper")
    print("Make sure your Chat Yapper backend is running on http://localhost:8000\n")
    
    try:
        if args.rapid:
            await run_rapid_simulation()
        elif args.messages:
            await run_message_count_simulation(args.messages)
        else:
            await run_time_based_simulation(args.duration)
    except KeyboardInterrupt:
        print("\n⏹️ Simulation stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
