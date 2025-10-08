#!/usr/bin/env python3
"""
Twitch Chat Simulator for Chat Yapper Testing

This script simulates realistic Twitch chat behavior with multiple chatters,
varying message frequencies, and different types of messages (chat, raids, bits, etc.)
Perfect for testing voice distribution and TTS functionality.
"""

import asyncio
import aiohttp
import random
import time
from typing import List, Dict, Any
import json

# Configuration
API_BASE_URL = "http://localhost:8000"
SIMULATION_DURATION = 60  # seconds
NUM_CHATTERS = 10

# Realistic chatter names
CHATTER_NAMES = [
    "StreamFan2024", "GamerGirl99", "NightOwl_", "CoffeeAddict", "PixelMaster",
    "ChatLurker", "MemeLord420", "RetroGamer", "TechNinja", "BookwormReads",
    "MusicLover88", "ArtisticSoul", "CodeWarrior", "NatureLover", "FitnessFreak"
]

# Realistic chat messages with weights (more common messages have higher weights)
CHAT_MESSAGES = [
    # Very common messages (weight 10)
    ("Hello!", 10), ("Hi everyone!", 10), ("Hey there!", 10), ("What's up?", 10),
    ("Good stream!", 10), ("Nice!", 10), ("Wow!", 10), ("LOL", 10), ("LMAO", 10),
    ("gg", 10), ("Nice play!", 10), ("That was awesome!", 10),
    
    # Common messages (weight 5)
    ("How's everyone doing?", 5), ("Great content as always!", 5), ("Love this game!", 5),
    ("Can't wait to see what happens next!", 5), ("This is so entertaining!", 5),
    ("You're doing great!", 5), ("Keep it up!", 5), ("Amazing work!", 5),
    ("This stream is fire!", 5), ("Best streamer ever!", 5),
    
    # Less common but engaging messages (weight 3)
    ("I've been watching for 2 hours straight!", 3), ("Your gameplay is incredible!", 3),
    ("Can you try that trick again?", 3), ("What mouse do you use?", 3),
    ("How long have you been streaming?", 3), ("Do you have any tips for beginners?", 3),
    ("Your setup looks amazing!", 3), ("What's your favorite game to stream?", 3),
    
    # Rare longer messages (weight 1)
    ("I just discovered your channel and I'm already hooked! Keep up the fantastic work!", 1),
    ("This reminds me of when I first played this game years ago. So much nostalgia!", 1),
    ("I'm supposed to be doing homework but this stream is too good to miss!", 1),
    ("My friends recommended your channel and now I see why everyone loves it!", 1),
]

# Special event messages
RAID_MESSAGES = [
    "Raid incoming from SmallStreamer with 15 viewers!",
    "BigStreamer is here with 200 raiders!",
    "Surprise raid from FriendlyStreamer!",
    "RetroGamer42 brought 50 friends!",
]

BITS_MESSAGES = [
    "Thanks for the entertainment! cheer100",
    "Love the stream! cheer50",
    "Keep up the great work! cheer25",
    "Amazing content! cheer200",
    "First time donating bits! cheer10",
]

SUB_MESSAGES = [
    "Just subscribed! Thanks for the great content!",
    "Month 6 of supporting this amazing channel!",
    "Gifted 5 subs to spread the love!",
    "New subscriber here, love what you do!",
]

VIP_MESSAGES = [
    "VIP checking in! Stream looks great today!",
    "As a VIP, I have to say this is your best stream yet!",
    "VIP exclusive: You should try the secret area!",
]

HIGHLIGHT_MESSAGES = [
    "This moment needs to be clipped!",
    "HIGHLIGHT REEL MATERIAL RIGHT HERE!",
    "Someone please clip that!",
    "That was highlight worthy!",
]

class ChatSimulator:
    def __init__(self, single_user: str = None):
        self.session = None
        self.chatters = []
        self.active_chatters = set()
        self.message_history = []
        self.single_user = single_user  # If set, all messages come from this user
        
    async def initialize(self):
        """Initialize the simulator"""
        self.session = aiohttp.ClientSession()
        
        if self.single_user:
            # Single user mode - create one chatter profile
            chatter = {
                "name": self.single_user,
                "activity_level": "high",  # Single user should be active
                "personality": "chatty",   # And chatty to generate variety
                "last_message_time": 0,
                "message_count": 0
            }
            self.chatters.append(chatter)
            print(f"🎯 Single user mode: All messages will be from '{self.single_user}'")
        else:
            # Multi-user mode - create multiple chatter profiles
            for i in range(NUM_CHATTERS):
                chatter = {
                    "name": random.choice(CHATTER_NAMES) + str(random.randint(1, 999)),
                    "activity_level": random.choice(["high", "medium", "low", "lurker"]),
                    "personality": random.choice(["chatty", "supportive", "funny", "technical", "casual"]),
                    "last_message_time": 0,
                    "message_count": 0
                }
                self.chatters.append(chatter)
            
            print(f"🎭 Initialized {len(self.chatters)} virtual chatters")
            for chatter in self.chatters:
                print(f"   {chatter['name']}: {chatter['activity_level']} activity, {chatter['personality']} personality")
    
    async def send_message(self, username: str, message: str, event_type: str = "chat"):
        """Send a message to the Chat Yapper API"""
        try:
            data = aiohttp.FormData()
            data.add_field('user', username)
            data.add_field('text', message)
            data.add_field('eventType', event_type)
            
            async with self.session.post(f"{API_BASE_URL}/api/simulate", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    timestamp = time.strftime("%H:%M:%S")
                    event_emoji = {
                        "chat": "💬",
                        "raid": "⚔️", 
                        "bits": "💎",
                        "sub": "⭐",
                        "vip": "👑",
                        "highlight": "✨"
                    }.get(event_type, "💬")
                    
                    print(f"{timestamp} {event_emoji} {username}: {message}")
                    self.message_history.append({
                        "timestamp": timestamp,
                        "user": username,
                        "message": message,
                        "event_type": event_type
                    })
                    return True
                else:
                    print(f"❌ Failed to send message: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return False
    
    def get_chatter_message_interval(self, chatter: Dict[str, Any]) -> float:
        """Get the next message interval for a chatter based on their activity level"""
        activity_intervals = {
            "high": (1, 5),       # Very active, messages every 1-5 seconds
            "medium": (3, 10),    # Moderate, messages every 3-10 seconds  
            "low": (5, 15),       # Occasional, messages every 5-15 seconds
            "lurker": (10, 30)    # Rare messages, every 10-30 seconds
        }
        
        min_interval, max_interval = activity_intervals[chatter["activity_level"]]
        return random.uniform(min_interval, max_interval)
    
    def select_message_for_chatter(self, chatter: Dict[str, Any]) -> str:
        """Select an appropriate message based on chatter personality"""
        # Weight messages based on personality
        if chatter["personality"] == "chatty":
            # Prefer longer, more engaging messages
            weighted_messages = [(msg, weight * 2 if len(msg) > 20 else weight) for msg, weight in CHAT_MESSAGES]
        elif chatter["personality"] == "supportive":
            # Prefer positive, encouraging messages
            supportive_keywords = ["great", "awesome", "amazing", "love", "best", "keep", "good"]
            weighted_messages = [(msg, weight * 3 if any(word in msg.lower() for word in supportive_keywords) else weight) 
                                for msg, weight in CHAT_MESSAGES]
        elif chatter["personality"] == "funny":
            # Prefer short, reaction messages
            funny_keywords = ["lol", "lmao", "wow", "gg", "nice"]
            weighted_messages = [(msg, weight * 3 if any(word in msg.lower() for word in funny_keywords) else weight) 
                                for msg, weight in CHAT_MESSAGES]
        elif chatter["personality"] == "technical":
            # Prefer question-based messages
            weighted_messages = [(msg, weight * 3 if "?" in msg else weight) for msg, weight in CHAT_MESSAGES]
        else:  # casual
            # Use default weights
            weighted_messages = CHAT_MESSAGES
        
        # Select message based on weights
        messages = [msg for msg, weight in weighted_messages for _ in range(weight)]
        return random.choice(messages)
    
    async def simulate_burst_activity(self):
        """Simulate a burst of activity (like when something exciting happens)"""
        print("\n🔥 BURST ACTIVITY! Something exciting happened on stream!")
        
        # 5-8 chatters react quickly
        num_reactors = random.randint(5, 8)
        reactors = random.sample(self.chatters, num_reactors)
        
        reactions = ["WOW!", "HOLY!", "NO WAY!", "INSANE!", "YOOO!", "POGGERS!", "CLUTCH!"]
        
        # Send reactions with small delays
        for i, chatter in enumerate(reactors):
            await asyncio.sleep(random.uniform(0.1, 2.0))  # Quick reactions
            reaction = random.choice(reactions)
            await self.send_message(chatter["name"], reaction, "chat")
    
    async def simulate_special_event(self):
        """Simulate a special event (raid, bits, sub, etc.)"""
        event_type = random.choice(["raid", "bits", "sub", "vip", "highlight"])
        
        messages_map = {
            "raid": RAID_MESSAGES,
            "bits": BITS_MESSAGES, 
            "sub": SUB_MESSAGES,
            "vip": VIP_MESSAGES,
            "highlight": HIGHLIGHT_MESSAGES
        }
        
        message = random.choice(messages_map[event_type])
        # Use single user if specified, otherwise pick random chatter
        username = self.single_user if self.single_user else random.choice(self.chatters)["name"]
        
        print(f"\n✨ Special Event: {event_type.upper()}")
        await self.send_message(username, message, event_type)
        
        # Some events trigger follow-up reactions
        if event_type in ["raid", "sub"]:
            await asyncio.sleep(1)
            # 2-4 people react to the special event
            num_reactors = random.randint(2, 4)
            reactors = random.sample(self.chatters, num_reactors)
            reactions = ["Welcome!", "Congrats!", "Thanks!", "Awesome!", "Let's go!"]
            
            for chatter in reactors:
                await asyncio.sleep(random.uniform(0.5, 2.0))
                reaction = random.choice(reactions)
                await self.send_message(chatter["name"], reaction, "chat")
    
    async def simulate_quiet_period(self):
        """Simulate a quiet period with minimal chat"""
        print("\n😴 Quiet period... only the most active chatters are messaging")
        duration = random.uniform(3, 8)  # Much shorter quiet periods
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Only high activity chatters message during quiet periods
            active_chatters = [c for c in self.chatters if c["activity_level"] == "high"]
            if active_chatters:
                chatter = random.choice(active_chatters)
                message = self.select_message_for_chatter(chatter)
                await self.send_message(chatter["name"], message, "chat")
            
            await asyncio.sleep(random.uniform(1, 3))  # Much shorter delays
    
    async def run_simulation(self):
        """Run the main chat simulation"""
        print(f"\n🚀 Starting Twitch Chat Simulation for {SIMULATION_DURATION} seconds!")
        print("=" * 60)
        
        start_time = time.time()
        next_special_event = start_time + random.uniform(8, 15)  # More frequent special events
        next_burst = start_time + random.uniform(10, 20)  # More frequent bursts
        next_quiet = start_time + random.uniform(25, 35)  # Less frequent quiet periods
        
        # Schedule initial messages for each chatter
        chatter_next_message = {}
        for chatter in self.chatters:
            chatter_next_message[chatter["name"]] = start_time + random.uniform(0.5, 3)  # Start messaging faster
        
        while time.time() - start_time < SIMULATION_DURATION:
            current_time = time.time()
            
            # Check for special events
            if current_time >= next_special_event:
                await self.simulate_special_event()
                next_special_event = current_time + random.uniform(10, 25)  # More frequent
            
            # Check for burst activity
            if current_time >= next_burst:
                await self.simulate_burst_activity()
                next_burst = current_time + random.uniform(15, 35)  # More frequent
            
            # Check for quiet periods (less frequent)
            if current_time >= next_quiet:
                await self.simulate_quiet_period()
                next_quiet = current_time + random.uniform(40, 80)  # Less frequent quiet periods
            
            # Check for regular chatter messages
            for chatter in self.chatters:
                if current_time >= chatter_next_message[chatter["name"]]:
                    message = self.select_message_for_chatter(chatter)
                    await self.send_message(chatter["name"], message, "chat")
                    chatter["message_count"] += 1
                    
                    # Schedule next message
                    interval = self.get_chatter_message_interval(chatter)
                    chatter_next_message[chatter["name"]] = current_time + interval
            
            # Small delay to prevent overwhelming the API
            await asyncio.sleep(0.1)
        
        print("\n" + "=" * 60)
        print("🏁 Simulation Complete!")
        self.print_statistics()
    
    def print_statistics(self):
        """Print simulation statistics"""
        mode_text = f"Single user '{self.single_user}'" if self.single_user else f"{len(self.chatters)} random chatters"
        print(f"\n📊 Simulation Statistics:")
        print(f"   Mode: {mode_text}")
        print(f"   Total messages sent: {len(self.message_history)}")
        print(f"   Duration: {SIMULATION_DURATION} seconds")
        print(f"   Average messages per second: {len(self.message_history) / SIMULATION_DURATION:.2f}")
        
        # Event type breakdown
        event_counts = {}
        for msg in self.message_history:
            event_type = msg["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        print(f"\n📈 Message Types:")
        for event_type, count in sorted(event_counts.items()):
            percentage = (count / len(self.message_history)) * 100
            emoji = {"chat": "💬", "raid": "⚔️", "bits": "💎", "sub": "⭐", "vip": "👑", "highlight": "✨"}.get(event_type, "📝")
            print(f"   {emoji} {event_type}: {count} ({percentage:.1f}%)")
        
        # Chatter activity
        print(f"\n👥 Chatter Activity:")
        for chatter in sorted(self.chatters, key=lambda c: c["message_count"], reverse=True):
            if chatter["message_count"] > 0:
                if self.single_user:
                    print(f"   {chatter['name']}: {chatter['message_count']} messages (single user mode)")
                else:
                    print(f"   {chatter['name']}: {chatter['message_count']} messages ({chatter['activity_level']} - {chatter['personality']})")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()

async def main():
    """Main function to run the chat simulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Twitch Chat Simulator for Chat Yapper")
    parser.add_argument("--single-user", type=str, help="Send all messages from a single user instead of multiple chatters")
    parser.add_argument("--duration", type=int, default=SIMULATION_DURATION, help=f"Simulation duration in seconds (default: {SIMULATION_DURATION})")
    
    args = parser.parse_args()
    
    # Update global duration if specified
    global SIMULATION_DURATION
    SIMULATION_DURATION = args.duration
    
    simulator = ChatSimulator(single_user=args.single_user)
    
    try:
        await simulator.initialize()
        await simulator.run_simulation()
    except KeyboardInterrupt:
        print("\n⏹️ Simulation interrupted by user")
    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    print("🎮 Twitch Chat Simulator for Chat Yapper")
    print("Make sure your Chat Yapper backend is running on http://localhost:8000")
    print("Usage:")
    print("  python simulate_chat.py                    # Multiple random chatters")
    print("  python simulate_chat.py --single-user TestUser  # All messages from 'TestUser'")
    print("  python simulate_chat.py --duration 120     # Run for 2 minutes")
    print("Press Ctrl+C to stop the simulation early\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
