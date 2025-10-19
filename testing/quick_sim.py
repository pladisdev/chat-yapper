#!/usr/bin/env python3
"""
Quick Chat Simulator - A simpler version for quick testing

Usage:
  python quick_sim.py                    # Default 30 second simulation with random users
  python quick_sim.py --duration 60      # 60 second simulation with random users
  python quick_sim.py --messages 50      # Send exactly 50 messages with random users
  python quick_sim.py --rapid            # Rapid fire mode (lots of messages quickly)
  python quick_sim.py --single-user TestUser  # All messages from single user "TestUser"
  python quick_sim.py --single-user TestUser --messages 20  # 20 messages from "TestUser"
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
            
            if response.status == 200:
                print(f"{timestamp} {username}: {message}")
                return True
            else:
                print(f"{timestamp} Failed to send message from {username}")
                return False
    except Exception as e:
        print(f"Error: {e}")
        return False

async def run_time_based_simulation(duration: int, single_user: str = None):
    """Run simulation for a specific duration"""
    if single_user:
        print(f"Running {duration}-second simulation with single user '{single_user}'...")
    else:
        print(f"Running {duration}-second simulation with randomized users...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration:
            # Random delay between messages (realistic chat pacing)
            delay = random.uniform(0.5, 3.0)  # 0.5 to 3 seconds between messages
            await asyncio.sleep(delay)
            
            # Pick user and message (single user or random)
            username = single_user if single_user else random.choice(USERNAMES)
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
        
        user_info = f" from user '{single_user}'" if single_user else " from random users"
        print(f"Sent {message_count} messages{user_info} in {duration} seconds")
        print(f"Average: {message_count / duration:.2f} messages per second")

async def run_message_count_simulation(target_messages: int, single_user: str = None):
    """Run simulation until we send a specific number of messages"""
    if single_user:
        print(f"Sending exactly {target_messages} messages from user '{single_user}'...")
    else:
        print(f"Sending exactly {target_messages} messages from randomized users...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        sent_count = 0
        
        while sent_count < target_messages:
            # Pick user and message (single user or random)
            username = single_user if single_user else random.choice(USERNAMES)
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
        user_info = f" from user '{single_user}'" if single_user else " from random users"
        print(f"Sent {sent_count} messages{user_info} in {elapsed:.1f} seconds")
        print(f"Average: {sent_count / elapsed:.2f} messages per second")

async def run_rapid_simulation(single_user: str = None):
    """Run rapid-fire simulation for testing high load"""
    if single_user:
        print(f"Running RAPID simulation (high message frequency) with single user '{single_user}'...")
    else:
        print("Running RAPID simulation (high message frequency) with randomized users...")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        message_count = 0
        duration = 30  # 30 seconds of rapid fire
        
        while time.time() - start_time < duration:
            # Send multiple messages in quick succession
            burst_size = random.randint(2, 5)
            for _ in range(burst_size):
                username = single_user if single_user else random.choice(USERNAMES)
                message = random.choice(QUICK_MESSAGES)
                
                success = await send_message(session, username, message, "chat")
                if success:
                    message_count += 1
                
                # Very short delay between burst messages
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Longer pause between bursts
            await asyncio.sleep(random.uniform(1, 4))
        
        user_info = f" from user '{single_user}'" if single_user else " from random users"
        print(f"Rapid simulation complete!")
        print(f"Sent {message_count} messages{user_info} in {duration} seconds")
        print(f"Average: {message_count / duration:.2f} messages per second")

async def main():
    parser = argparse.ArgumentParser(description="Quick Chat Simulator for Chat Yapper")
    parser.add_argument("--duration", type=int, default=30, help="Simulation duration in seconds (default: 30)")
    parser.add_argument("--messages", type=int, help="Send exactly this many messages (overrides duration)")
    parser.add_argument("--rapid", action="store_true", help="Rapid fire mode for high load testing")
    parser.add_argument("--single-user", type=str, help="Send all messages from a single user instead of randomizing names")
    
    args = parser.parse_args()
    
    print("Quick Chat Simulator for Chat Yapper")
    print("Make sure your Chat Yapper backend is running on http://localhost:8000")
    
    if args.single_user:
        print(f"Single user mode: All messages will be from '{args.single_user}'")
    else:
        print("Random user mode: Each message will be from a different random user")
    print()
    
    try:
        if args.rapid:
            await run_rapid_simulation(args.single_user)
        elif args.messages:
            await run_message_count_simulation(args.messages, args.single_user)
        else:
            await run_time_based_simulation(args.duration, args.single_user)
    except KeyboardInterrupt:
        print("\nSimulation stopped by user")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(main())
