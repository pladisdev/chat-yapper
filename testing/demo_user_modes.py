#!/usr/bin/env python3
"""
Demo script to showcase the different user modes in the simulators

This script demonstrates:
1. Single user mode - all messages from one user
2. Random user mode - each message from different random users
3. Quick comparisons between modes
"""

import asyncio
import subprocess
import sys
import time

async def run_command_demo(description: str, command: list, duration: int = 15):
    """Run a command and show its output"""
    print(f"\n🎯 {description}")
    print("=" * 60)
    print(f"Running: {' '.join(command)}")
    print("-" * 60)
    
    try:
        # Run the command
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        start_time = time.time()
        while process.poll() is None and (time.time() - start_time) < duration:
            output = process.stdout.readline()
            if output:
                print(output.rstrip())
        
        # Terminate if still running
        if process.poll() is None:
            process.terminate()
            process.wait()
            print("\n⏹️ Demo stopped after time limit")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ Error running demo: {e}")

async def main():
    """Run the demo scenarios"""
    print("🎮 Chat Yapper Test Simulator - User Mode Demo")
    print("=" * 60)
    print("This demo shows the difference between single user and random user modes")
    print("Make sure your Chat Yapper backend is running on http://localhost:8000")
    print("\nPress Ctrl+C at any time to skip to the next demo or exit")
    
    demos = [
        {
            "description": "Demo 1: Single User Mode (quick_sim.py)",
            "command": [sys.executable, "quick_sim.py", "--single-user", "DemoUser", "--messages", "10"],
            "duration": 20
        },
        {
            "description": "Demo 2: Random User Mode (quick_sim.py)",
            "command": [sys.executable, "quick_sim.py", "--messages", "10"],
            "duration": 20
        },
        {
            "description": "Demo 3: Single User - Rapid Fire Mode",
            "command": [sys.executable, "quick_sim.py", "--single-user", "SpeedTester", "--rapid"],
            "duration": 35
        },
        {
            "description": "Demo 4: Random Users - Rapid Fire Mode",
            "command": [sys.executable, "quick_sim.py", "--rapid"],
            "duration": 35
        },
        {
            "description": "Demo 5: Full Simulation - Single User",
            "command": [sys.executable, "simulate_chat.py", "--single-user", "StreamViewer", "--duration", "20"],
            "duration": 25
        },
        {
            "description": "Demo 6: Full Simulation - Multiple Random Users",
            "command": [sys.executable, "simulate_chat.py", "--duration", "20"],
            "duration": 25
        }
    ]
    
    try:
        for i, demo in enumerate(demos, 1):
            print(f"\n\n🚀 Starting Demo {i}/{len(demos)}")
            await run_command_demo(demo["description"], demo["command"], demo["duration"])
            
            if i < len(demos):
                print(f"\n⏳ Waiting 3 seconds before next demo...")
                await asyncio.sleep(3)
        
        print("\n\n🎉 All demos completed!")
        print("=" * 60)
        print("Summary of what you just saw:")
        print("• Single user mode: All messages from one consistent user")
        print("• Random user mode: Each message from different random users") 
        print("• Both modes support: time-based, message-count, and rapid-fire simulations")
        print("• Perfect for testing TTS with consistent vs varied voices")
        print("• Great for testing per-user queuing logic (same user won't interrupt themselves)")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo session ended by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")

if __name__ == "__main__":
    print("🎯 Starting Chat Yapper User Mode Demos...")
    print("Tip: Use --single-user for testing per-user TTS queuing")
    print("Tip: Use random mode for testing multiple concurrent voices\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo session ended!")
