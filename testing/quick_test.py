#!/usr/bin/env python3
"""Simple test script to trigger per-user queuing"""

import requests
import time

def send_message(user, text):
    data = {'user': user, 'text': text, 'eventType': 'chat'}
    try:
        response = requests.post('http://localhost:8008/api/simulate', data=data)
        print(f"Sent: {user} - {text} | Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing per-user queuing...")
    
    # Send first message
    send_message("TestUser", "First message should play")
    
    # Wait a tiny bit then send second message
    time.sleep(0.1)
    send_message("TestUser", "Second message should be ignored if queuing enabled")
    
    # Wait longer then send third message
    time.sleep(2)
    send_message("TestUser", "Third message after delay")
