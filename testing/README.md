# Chat Yapper Test Simulators

This directory contains test simulators for the Chat Yapper application, perfect for testing TTS functionality, user queuing logic, and overall system performance.

## Available Simulators

### 1. `quick_sim.py` - Quick Testing Simulator

A simple, lightweight simulator for quick testing scenarios.

#### Features:
- **Single User Mode**: All messages from one consistent user
- **Random User Mode**: Each message from different random users
- **Time-based simulation**: Run for specific duration
- **Message-count simulation**: Send exact number of messages  
- **Rapid-fire mode**: High frequency message bursts

#### Usage Examples:
```bash
# Default 30-second simulation with random users
python quick_sim.py

# Single user sending 20 messages
python quick_sim.py --single-user TestUser --messages 20

# Rapid fire mode with single user
python quick_sim.py --single-user SpeedTester --rapid

# 60-second simulation with random users
python quick_sim.py --duration 60

# All available options
python quick_sim.py --help
```

### 2. `simulate_chat.py` - Full Featured Simulator

A comprehensive simulator that mimics realistic Twitch chat behavior with multiple chatters, varying personalities, and special events.

#### Features:
- **Single User Mode**: All messages from one user (great for testing per-user queuing)
- **Multi-User Mode**: Realistic chat with multiple virtual chatters
- **Realistic chat patterns**: Different activity levels and personalities
- **Special events**: Raids, bits, subscriptions, VIP messages, highlights
- **Burst activity**: Simulates excitement during stream highlights
- **Quiet periods**: Natural lulls in chat activity

#### Usage Examples:
```bash
# Default multi-user simulation
python simulate_chat.py

# Single user mode for 2 minutes
python simulate_chat.py --single-user StreamViewer --duration 120

# Custom duration with multiple chatters
python simulate_chat.py --duration 180

# All available options
python simulate_chat.py --help
```

### 3. `demo_user_modes.py` - Interactive Demo

A demonstration script that showcases both user modes with various scenarios.

```bash
python demo_user_modes.py
```

### 4. `demo_per_user_queuing.py` - Per-User Queuing Demo

A demonstration script that shows how the new "Ignore messages from users who are already speaking" setting works.

```bash
python demo_per_user_queuing.py
```

## When to Use Each Mode

### Single User Mode (`--single-user Username`)
**Perfect for testing:**
- ✅ Per-user TTS queuing (same user won't interrupt themselves)
- ✅ Consistent voice/personality testing
- ✅ User-specific moderation features (bans, timeouts)
- ✅ Message rate limiting per user
- ✅ User state management
- ✅ New "Ignore messages from users who are already speaking" setting

**Example scenarios:**
- Testing that "TestUser" can't interrupt their own TTS
- Verifying ban/timeout cancellation works for specific users
- Checking user-specific settings or preferences
- Testing the new per-user queuing setting toggle

### Random User Mode (default behavior)
**Perfect for testing:**
- ✅ Multiple concurrent TTS voices
- ✅ Parallel audio playback
- ✅ Cross-user interactions
- ✅ System load under varied input
- ✅ General chat flow and mixing

**Example scenarios:**
- Testing multiple users speaking simultaneously
- Verifying different TTS voices don't interfere
- Load testing with varied message patterns
- General system stress testing

## Configuration

Both simulators can be customized by editing the configuration variables at the top of each file:

### `quick_sim.py` Configuration:
```python
API_BASE_URL = "http://localhost:8000"  # Chat Yapper backend URL
QUICK_MESSAGES = [...]                  # Pool of test messages
USERNAMES = [...]                       # Pool of random usernames
```

### `simulate_chat.py` Configuration:
```python
API_BASE_URL = "http://localhost:8000"  # Chat Yapper backend URL
SIMULATION_DURATION = 60                # Default duration in seconds
NUM_CHATTERS = 10                       # Number of virtual chatters
CHATTER_NAMES = [...]                   # Pool of realistic chatter names
CHAT_MESSAGES = [...]                   # Weighted message pool
```

## Tips for Testing

1. **TTS Per-User Queuing**: Use single user mode to verify same user doesn't interrupt themselves
2. **Per-User Queuing Setting**: Use `demo_per_user_queuing.py` to test the new toggle setting
3. **Parallel Audio**: Use random user mode to test multiple concurrent voices
4. **Moderation Features**: Use single user mode, then trigger ban/timeout via Twitch chat
5. **Performance Testing**: Use rapid fire mode with multiple users
6. **Realistic Testing**: Use full `simulate_chat.py` with default multi-user mode

## Requirements

- Chat Yapper backend running on `http://localhost:8000`
- Python 3.7+ with `aiohttp` installed
- Active Twitch chat connection (for moderation testing)

## Troubleshooting

- **Connection errors**: Ensure Chat Yapper backend is running
- **No TTS output**: Check TTS provider configuration in Chat Yapper settings
- **Permission errors**: Ensure Python has network access
- **Rate limiting**: Reduce message frequency if API returns 429 errors

---

*These simulators are essential tools for testing the Chat Yapper TTS system, especially the advanced per-user queuing and moderation features.*
