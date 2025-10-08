# Message Filtering: Duplicate and Spam Detection

## Overview

Chat Yapper now includes comprehensive message filtering to prevent duplicate messages and spam from disrupting your TTS experience. The system tracks recent messages and applies intelligent filtering rules to maintain a smooth stream.

## Features

### 1. **Duplicate Message Detection** ✅
Prevents the same user from sending identical messages within a time window.

**Use Case**: User accidentally sends "hello" twice
**Result**: Second message is ignored

**Settings**:
- `enableDuplicateFilter` (default: `true`)
- `duplicateTimeWindow` (default: `60` seconds)

### 2. **Rate Limiting (Spam Filter)** ⚡
Prevents a single user from flooding chat with too many messages too quickly.

**Use Case**: User sends 10 messages in 2 seconds
**Result**: Messages beyond threshold are ignored

**Settings**:
- `enableSpamFilter` (default: `true`)
- `spamThreshold` (default: `5` messages)
- `spamTimeWindow` (default: `10` seconds)

### 3. **Similar Message Detection** 🔍
Detects when a user sends nearly identical messages (spam variations).

**Use Case**: User sends "Check this out!", then "Check this out!!", then "Check this out!!!"
**Result**: Similar variations are detected and ignored

**Settings**:
- `enableSimilarSpamFilter` (default: `true`)
- `similarityThreshold` (default: `0.8` - 80% similar)
- `similarSpamTimeWindow` (default: `60` seconds)

### 4. **Multi-User Coordinated Spam** 🚫
Detects when multiple users send similar messages (bot attacks, raid spam).

**Use Case**: 5 different accounts all post "Check out this link!"
**Result**: Coordinated spam detected and blocked

**Settings**:
- `enableMultiUserSpamFilter` (default: `false` - disabled by default)
- `multiUserSpamMinUsers` (default: `3` users)
- `multiUserSpamSimilarity` (default: `0.85` - 85% similar)
- `multiUserSpamTimeWindow` (default: `30` seconds)

---

## Configuration

All settings are found in `settings_defaults.json` under `messageFiltering`:

```json
{
  "messageFiltering": {
    "enabled": true,
    
    // Duplicate Detection
    "enableDuplicateFilter": true,
    "duplicateTimeWindow": 60,
    
    // Single-User Spam (Rate Limiting)
    "enableSpamFilter": true,
    "spamThreshold": 5,
    "spamTimeWindow": 10,
    
    // Similar Message Spam
    "enableSimilarSpamFilter": true,
    "similarityThreshold": 0.8,
    "similarSpamTimeWindow": 60,
    
    // Multi-User Coordinated Spam
    "enableMultiUserSpamFilter": false,
    "multiUserSpamMinUsers": 3,
    "multiUserSpamSimilarity": 0.85,
    "multiUserSpamTimeWindow": 30
  }
}
```

### Recommended Settings

**For Small Streams (< 100 viewers)**:
```json
{
  "enableDuplicateFilter": true,
  "enableSpamFilter": true,
  "spamThreshold": 3,
  "enableSimilarSpamFilter": true,
  "enableMultiUserSpamFilter": false
}
```

**For Medium Streams (100-1000 viewers)**:
```json
{
  "enableDuplicateFilter": true,
  "enableSpamFilter": true,
  "spamThreshold": 5,
  "enableSimilarSpamFilter": true,
  "enableMultiUserSpamFilter": true,
  "multiUserSpamMinUsers": 5
}
```

**For Large Streams (1000+ viewers)**:
```json
{
  "enableDuplicateFilter": true,
  "enableSpamFilter": true,
  "spamThreshold": 3,
  "spamTimeWindow": 5,
  "enableSimilarSpamFilter": true,
  "enableMultiUserSpamFilter": true,
  "multiUserSpamMinUsers": 3,
  "multiUserSpamTimeWindow": 15
}
```

---

## How It Works

### Message Normalization

Messages are normalized before comparison:
- Convert to lowercase
- Remove extra whitespace
- Remove trailing punctuation (`!!!`, `???`)
- Case-insensitive username matching

**Example**:
- `"Hello World"` = `"hello world"` = `"Hello   World!!!"` (all treated as duplicates)

### Similarity Calculation

Uses `SequenceMatcher` to calculate similarity ratio between messages:
- `1.0` = Identical messages
- `0.8` = 80% similar (default threshold)
- `0.0` = Completely different

**Example**:
```python
"Check this out!"  vs  "Check this out!!"  = 0.95 similarity (detected)
"Hello world"      vs  "Goodbye world"     = 0.50 similarity (not detected)
```

### Time Windows

All filtering uses sliding time windows:
- Only recent messages within the time window are checked
- Old messages are automatically cleaned up
- No permanent storage required

---

## Testing

### Unit Tests

Comprehensive test suite in `backend/tests/test_message_filter.py`:

**Test Coverage**:
- ✅ 33 unit tests
- ✅ Duplicate detection (exact, case-insensitive, punctuation)
- ✅ Spam detection (rate limiting)
- ✅ Similar message detection
- ✅ Multi-user coordinated spam
- ✅ Edge cases (empty messages, Unicode, special characters)

**Run Tests**:
```bash
cd backend
pytest tests/test_message_filter.py -v
```

### Manual Testing

Use the Message Filter Tester in the Settings page:
1. Go to Settings → Message Filtering
2. Scroll to "Test Message Filter"
3. Enter a username and message
4. Click "Test Message Filter"
5. See if message would be processed or filtered

---

## API Integration

The filtering is automatically integrated into the message processing pipeline:

```python
from message_filter import get_message_history

# Automatic in should_process_message()
should_process, filtered_text = should_process_message(
    text=message,
    settings=get_settings(),
    username=user,
    active_tts_jobs=active_tts_jobs
)

if should_process:
    # Process message for TTS
    message_history.add_message(username, filtered_text)
else:
    # Message was filtered
    logger.info(f"Message filtered: {reason}")
```

### Message History API

Access the message history programmatically:

```python
from message_filter import get_message_history, reset_message_history

history = get_message_history()

# Check for duplicates
is_dup, reason = history.is_duplicate("Username", "message", time_window_seconds=60)

# Check for spam
is_spam, reason = history.is_spam("Username", max_messages=5, time_window_seconds=10)

# Check for similar spam
is_similar, reason = history.is_similar_spam("Username", "message", similarity_threshold=0.8)

# Check for multi-user spam
is_coordinated, reason = history.is_multi_user_spam("message", min_users=3, similarity_threshold=0.85)

# Get statistics
stats = history.get_stats()
# Returns: {"tracked_users": 10, "total_user_messages": 45, ...}

# Clear history (testing only)
reset_message_history()
```

---

## Performance

### Memory Usage

- **Per-user tracking**: ~50 most recent messages
- **Global tracking**: ~200 most recent messages  
- **Automatic cleanup**: Messages older than 5 minutes are removed
- **Typical usage**: < 1 MB memory for moderate traffic

### Processing Time

- Duplicate check: < 1ms
- Spam check: < 1ms
- Similar message check: < 5ms
- Multi-user spam check: < 10ms
- **Total overhead**: < 20ms per message

### Scalability

The system is designed for real-time stream chat:
- ✅ Handles 100+ messages/minute easily
- ✅ Automatic cleanup prevents memory growth
- ✅ O(n) complexity where n = recent messages (capped at 200)
- ✅ No database queries required

---

## Troubleshooting

### Issue: Legitimate messages are being filtered

**Solution**: Adjust thresholds
```json
{
  "similarityThreshold": 0.9,  // Increase from 0.8
  "spamThreshold": 10,          // Increase from 5
  "duplicateTimeWindow": 30     // Decrease from 60
}
```

### Issue: Too much spam getting through

**Solution**: Tighten filters
```json
{
  "enableMultiUserSpamFilter": true,  // Enable if disabled
  "spamThreshold": 3,                  // Decrease from 5
  "similarityThreshold": 0.7           // Decrease from 0.8
}
```

### Issue: Multi-user spam not detected

**Solution**: Check if enabled and adjust sensitivity
```json
{
  "enableMultiUserSpamFilter": true,
  "multiUserSpamMinUsers": 2,      // Lower threshold
  "multiUserSpamSimilarity": 0.75  // Lower similarity requirement
}
```

### Debugging

Enable detailed logging:
```python
import logging
logging.getLogger('ChatYapper.Backend').setLevel(logging.DEBUG)
```

Check message history stats:
```python
from message_filter import get_message_history
stats = get_message_history().get_stats()
print(f"Tracking {stats['tracked_users']} users with {stats['total_user_messages']} messages")
```

---

## Examples

### Example 1: Duplicate Detection

```python
# User sends same message twice
send_message("Alice", "Hello world")
send_message("Alice", "Hello world")  # ❌ Filtered (duplicate)
send_message("Alice", "Goodbye")      # ✅ Processed (different message)
```

### Example 2: Rate Limiting

```python
# User rapid-fires messages
for i in range(10):
    send_message("Bob", f"Message {i}")

# First 5 processed ✅
# Remaining 5 filtered ❌ (spam threshold: 5)
```

### Example 3: Similar Spam

```python
send_message("Charlie", "Check this out!")   # ✅ Processed
send_message("Charlie", "Check this out!!")  # ❌ Filtered (95% similar)
send_message("Charlie", "Check this out!!!")  # ❌ Filtered (95% similar)
```

### Example 4: Multi-User Spam

```python
# Bot attack - 5 accounts post same link
send_message("Bot1", "Visit example.com now!")  # ✅ Processed
send_message("Bot2", "Visit example.com now!")  # ✅ Processed
send_message("Bot3", "Visit example.com now!")  # ❌ Filtered (3+ users detected)
send_message("Bot4", "Visit example.com now!")  # ❌ Filtered
send_message("Bot5", "Visit example.com now!")  # ❌ Filtered
```

---

## Future Enhancements

Planned features:
- [ ] Whitelist for trusted users (mods, VIPs)
- [ ] Per-user customizable thresholds
- [ ] Machine learning spam detection
- [ ] Persistent message history (optional)
- [ ] Analytics dashboard for filtered messages
- [ ] Auto-adjust thresholds based on stream size

---

## Credits

**Implementation**: message_filter.py  
**Tests**: tests/test_message_filter.py  
**Integration**: app.py (should_process_message function)

For questions or issues, please check the logs or run the unit tests.
