"""
Test script to verify avatar capacity queuing works correctly.

This test sends multiple messages rapidly to see if they queue properly
when all avatar positions are occupied.
"""

import requests
import time

API_URL = "http://localhost:8"

def get_debug_info():
    """Get debug information about queuing state"""
    try:
        response = requests.get(f"{API_URL}/api/debug/per-user-queuing")
        return response.json()
    except Exception as e:
        print(f"Error getting debug info: {e}")
        return None

def send_test_message(username, text, event_type="chat"):
    """Send a test message"""
    try:
        response = requests.post(
            f"{API_URL}/api/simulate",
            data={
                "user": username,
                "text": text,
                "eventType": event_type
            }
        )
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def main():
    print("=" * 70)
    print("Avatar Capacity Queuing Test")
    print("=" * 70)
    
    # Get initial state
    print("\nInitial State:")
    debug_info = get_debug_info()
    if debug_info:
        capacity = debug_info.get("avatarCapacity", {})
        print(f"   Max avatar positions: {capacity.get('maxPositions', 'unknown')}")
        print(f"   Active positions: {capacity.get('activePositions', 0)}")
        print(f"   Available positions: {capacity.get('availablePositions', 'unknown')}")
        print(f"   Queue size: {capacity.get('queueSize', 0)}")
        print(f"   Active jobs: {debug_info.get('activeJobs', [])}")
        max_positions = capacity.get('maxPositions', 12)
    else:
        print("   Could not retrieve debug info")
        max_positions = 12  # Default assumption
    
    # Send messages to fill all avatar positions + queue some
    num_messages = max_positions + 5  # Fill all positions and queue 5 more
    
    print(f"\nSending {num_messages} messages rapidly...")
    print(f"   This should fill all {max_positions} avatar positions and queue {5} messages")
    print()
    
    for i in range(num_messages):
        username = f"TestUser{i+1}"
        text = f"Test message number {i+1}"
        
        print(f"   Sending message {i+1}/{num_messages} from {username}...")
        result = send_test_message(username, text)
        
        if result:
            if result.get("ok"):
                print(f"      Message accepted")
            else:
                print(f"      Message rejected: {result.get('reason', 'unknown')}")
        
        # Small delay to allow messages to be processed
        time.sleep(0.1)
    
    # Check state after sending all messages
    print(f"\nState after sending {num_messages} messages:")
    time.sleep(0.5)  # Give backend time to process
    
    debug_info = get_debug_info()
    if debug_info:
        capacity = debug_info.get("avatarCapacity", {})
        print(f"   Max avatar positions: {capacity.get('maxPositions', 'unknown')}")
        print(f"   Active positions: {capacity.get('activePositions', 0)}")
        print(f"   Available positions: {capacity.get('availablePositions', 'unknown')}")
        print(f"   Queue size: {capacity.get('queueSize', 0)}")
        print(f"   Active jobs: {debug_info.get('activeJobs', [])}")
        
        active = capacity.get('activePositions', 0)
        queued = capacity.get('queueSize', 0)
        
        print(f"\nResults:")
        print(f"   Expected: {max_positions} active, ~5 queued")
        print(f"   Actual: {active} active, {queued} queued")
        
        if active == max_positions:
            print(f"   All avatar positions filled correctly!")
        else:
            print(f"   Avatar positions not fully filled (expected {max_positions}, got {active})")
        
        if queued > 0:
            print(f"   Messages queued when capacity reached!")
        else:
            print(f"   No messages queued (expected some queued messages)")
    else:
        print("   Could not retrieve debug info")
    
    # Wait and check again to see queue processing
    print(f"\nWaiting 5 seconds to observe queue processing...")
    time.sleep(5)
    
    print(f"\nFinal State:")
    debug_info = get_debug_info()
    if debug_info:
        capacity = debug_info.get("avatarCapacity", {})
        print(f"   Active positions: {capacity.get('activePositions', 0)}")
        print(f"   Queue size: {capacity.get('queueSize', 0)}")
        
        if capacity.get('queueSize', 0) < queued:
            print(f"   Queue is being processed (was {queued}, now {capacity.get('queueSize', 0)})")
        else:
            print(f"   Queue size unchanged or still processing")
    
    print("\n" + "=" * 70)
    print("Test Complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()