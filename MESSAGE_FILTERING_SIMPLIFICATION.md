# Message Filtering Simplification

## Overview

The message filtering system has been simplified to focus on the most essential features while maintaining clear functionality and user-friendly settings.

## Removed Features

The following complex features were removed for better user experience:

1. **Duplicate Message Detection** - Previously blocked exact duplicate messages from users
2. **Similar Message Detection** - Previously blocked messages that were very similar (variation spam)  
3. **Multi-User Coordinated Spam Detection** - Previously detected when multiple users sent similar messages

## Current Features

The simplified system now includes:

### 1. **Rate Limiting** 🚫
- **Purpose**: Prevent users from sending too many messages quickly
- **Behavior**: When a user exceeds the limit, their new messages are completely ignored
- **Settings**: 
  - Max Messages (default: 5)
  - Time Window (default: 10 seconds)
- **UI**: Clear blue section in settings with detailed explanation

### 2. **Ignore if User Speaking** 🔊  
- **Purpose**: Prevent message interruptions and overlapping TTS
- **Behavior**: When a user's message is currently playing TTS, ignore new messages from that user until finished
- **Settings**: Simple on/off toggle
- **UI**: Clear green section in settings with detailed explanation

### 3. **Basic Filtering** (unchanged)
- Minimum/Maximum message length
- Skip commands (! or /)
- Skip emote-only messages
- Remove URLs
- Profanity filter
- Ignored users list

## UI Improvements

- **Clear Visual Distinction**: Rate limiting (blue) vs Ignore if Speaking (green)
- **Better Descriptions**: Each feature explains exactly what it does with examples
- **Simplified Layout**: Removed complex configuration options that were confusing
- **Key Differences Box**: Explains the distinction between the two main filtering types

## Technical Changes

### Backend (`message_filter.py`)
- Removed: `is_duplicate()`, `is_similar_spam()`, `is_multi_user_spam()` methods
- Removed: Global message tracking, similarity calculations, hash-based duplicate detection
- Kept: `is_spam()` method for rate limiting, timestamp tracking
- Simplified: Data structures only track user timestamps for rate limiting

### Frontend (`SettingsPage.jsx`)
- Removed: Complex UI for duplicate detection, similar spam, coordinated spam
- Added: Clear visual sections with color coding and detailed examples
- Improved: Explanations distinguish between rate limiting and ignore-if-speaking

### Settings (`settings_defaults.json`)
- Removed: `enableDuplicateFilter`, `duplicateTimeWindow`, `enableSimilarSpamFilter`, `similarityThreshold`, `similarSpamTimeWindow`, `enableMultiUserSpamFilter`, `multiUserSpamMinUsers`, `multiUserSpamSimilarity`, `multiUserSpamTimeWindow`
- Kept: `enableSpamFilter`, `spamThreshold`, `spamTimeWindow`, `ignoreIfUserSpeaking`

### Tests (`test_message_filter.py`)
- Marked as skipped: `TestDuplicateDetection`, `TestSimilarSpamDetection`, `TestMultiUserSpamDetection` 
- Updated: Stats assertions to use `total_timestamps` instead of `total_user_messages` and `total_global_messages`
- Kept: `TestSpamDetection` for rate limiting functionality

## Benefits

1. **Clearer User Experience**: Users understand exactly what each option does
2. **Simpler Configuration**: Fewer settings to configure and maintain
3. **Better Performance**: Reduced memory usage and processing overhead
4. **Easier Maintenance**: Less complex code to debug and extend
5. **Focus on Core Needs**: Rate limiting and speak-queue management cover the main use cases

## Migration

Existing users will see:
- Duplicate detection settings will be ignored (gracefully handled)
- Rate limiting continues to work as before
- No breaking changes to core TTS functionality