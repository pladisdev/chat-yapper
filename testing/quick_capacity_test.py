"""
Quick test to verify avatar capacity queuing works with the race condition fix.
Send 3 messages rapidly to a system configured for 2 avatars.
Expected: 2 process immediately, 1 gets queued.
"""

import requests
import time

API_URL = "http://localhost:8000"

def send_message(username, text):
    response = requests.post(
        f"{API_URL}/api/simulate",
        data={"user": username, "text": text, "eventType": "chat"}
    )
    return response.json()

def get_debug_info():
    response = requests.get(f"{API_URL}/api/debug/per-user-queuing")
    return response.json()

print("=" * 70)
print("Quick Avatar Capacity Test")
print("=" * 70)

# Get initial state
debug = get_debug_info()
print(f"\nInitial State:")
print(f"   Max positions: {debug['avatarCapacity']['maxPositions']}")
print(f"   Active: {debug['avatarCapacity']['activePositions']}")
print(f"   Queue: {debug['avatarCapacity']['queueSize']}")

# Send 3 messages rapidly (should queue the 3rd one if max is 2)
print(f"\nSending 3 messages rapidly...")
for i in range(3):
    print(f"   Sending message {i+1}...")
    result = send_message(f"User{i+1}", f"Test message {i+1}")
    time.sleep(0.05)  # Very small delay

# Check state immediately after
time.sleep(0.3)  # Small delay for processing
debug = get_debug_info()
print(f"\nAfter sending messages:")
print(f"   Active: {debug['avatarCapacity']['activePositions']}")
print(f"   Queue: {debug['avatarCapacity']['queueSize']}")
print(f"   Active jobs: {debug['activeJobs']}")

if debug['avatarCapacity']['maxPositions'] == 2:
    if debug['avatarCapacity']['activePositions'] <= 2:
        print(f"\nSUCCESS: Capacity respected! (≤2 active)")
    else:
        print(f"\nFAIL: Too many active ({debug['avatarCapacity']['activePositions']}) - race condition not fixed")
    
    if debug['avatarCapacity']['queueSize'] > 0:
        print(f"SUCCESS: Messages queued when at capacity!")
    elif debug['avatarCapacity']['activePositions'] < 2:
        print(f"Messages already completed")
else:
    print(f"Testing with {debug['avatarCapacity']['maxPositions']} positions")

print("\n" + "=" * 70)
