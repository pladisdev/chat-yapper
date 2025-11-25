"""
Message filtering utilities for rate limiting and content filtering.

This module provides functionality for:
- Single-user spam (rate limiting) - prevents users from sending too many messages too quickly
- Message content filtering - removes URLs, emotes, profanity, etc.
- Message validation - checks length, commands, ignored users, etc.
"""

import re
import time
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional, Any

from modules import logger


class MessageHistory:
    """
    Track recent message timestamps for rate limiting.
    
    Uses in-memory data structures with automatic cleanup of old timestamps.
    """
    
    def __init__(self, max_age_seconds: int = 300):
        """
        Initialize message history tracker.
        
        Args:
            max_age_seconds: How long to keep message timestamps in history (default 5 minutes)
        """
        self.max_age_seconds = max_age_seconds
        
        # Per-user rate limiting: {username: [timestamp1, timestamp2, ...]}
        self.user_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def _cleanup_old_timestamps(self):
        """Remove timestamps older than max_age_seconds"""
        current_time = time.time()
        cutoff_time = current_time - self.max_age_seconds
        
        # Clean up user timestamps
        for username, timestamps in list(self.user_timestamps.items()):
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()
            if not timestamps:
                del self.user_timestamps[username]
    
    def add_message(self, username: str, text: str) -> None:
        """
        Add a message timestamp for rate limiting tracking.
        
        Args:
            username: Username who sent the message
            text: Message text (not used for rate limiting, but kept for compatibility)
        """
        self._cleanup_old_timestamps()
        
        timestamp = time.time()
        username_lower = username.lower()
        
        # Add timestamp for rate limiting
        self.user_timestamps[username_lower].append(timestamp)
    
    def is_spam(
        self, 
        username: str, 
        max_messages: int = 5, 
        time_window_seconds: int = 10
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is spamming (rate limiting).
        
        Args:
            username: Username to check
            max_messages: Maximum messages allowed in time window
            time_window_seconds: Time window for rate limiting
            
        Returns:
            (is_spam, reason)
        """
        self._cleanup_old_timestamps()
        
        username_lower = username.lower()
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds
        
        if username_lower not in self.user_timestamps:
            return False, None
        
        # Count recent messages
        recent_count = sum(1 for ts in self.user_timestamps[username_lower] if ts >= cutoff_time)
        
        if recent_count >= max_messages:
            return True, f"Rate limit exceeded for {username} ({recent_count} messages in {time_window_seconds}s)"
        
        return False, None
    
    def clear(self):
        """Clear all message history (useful for testing)"""
        self.user_timestamps.clear()
    
    def get_stats(self) -> Dict:
        """Get statistics about current message history"""
        return {
            "tracked_users": len(self.user_timestamps),
            "total_timestamps": sum(len(timestamps) for timestamps in self.user_timestamps.values()),
            "max_age_seconds": self.max_age_seconds
        }


# Global instance
_message_history = MessageHistory()


def get_message_history() -> MessageHistory:
    """Get the global message history instance"""
    return _message_history


def should_process_message(
    text: str, 
    settings: Dict[str, Any], 
    username: str = None, 
    active_tts_jobs: Dict[str, Any] = None, 
    tags: Dict[str, Any] = None
) -> Tuple[bool, str]:
    """
    Check if a message should be processed based on filtering settings.
    
    Args:
        text: Original message text
        settings: Application settings dict
        username: Username who sent the message
        active_tts_jobs: Dict of currently active TTS jobs
        tags: Twitch tags dict (for emote detection, channel points, etc.)
    
    Returns:
        (should_process, filtered_text) - tuple indicating if message should be processed and the filtered text
    """
    filtering = settings.get("messageFiltering", {})
    
    if not filtering.get("enabled", True):
        return True, text
    
    # Check Twitch channel point redeem filter
    twitch_settings = settings.get("twitch", {})
    redeem_filter = twitch_settings.get("redeemFilter", {})
    if redeem_filter.get("enabled", False):
        allowed_redeem_names = redeem_filter.get("allowedRedeemNames", [])
        if allowed_redeem_names:
            # Check if message has a msg-param-reward-name tag (the redeem name)
            # Also check custom-reward-id to confirm it's a redeem
            custom_reward_id = tags.get("custom-reward-id", "") if tags else ""
            reward_name = tags.get("msg-param-reward-name", "") if tags else ""
            
            if not custom_reward_id:
                # No redeem ID means this is a regular message, not a channel point redeem
                logger.info(f"Skipping message from {username} - not from a channel point redeem")
                return False, text
            
            # Check if the redeem name is in the allowed list (case-insensitive)
            if not any(reward_name.lower() == allowed_name.lower() for allowed_name in allowed_redeem_names):
                logger.info(f"Skipping message from {username} - redeem name '{reward_name}' not in allowed list")
                return False, text
            
            logger.info(f"Processing message from {username} - redeem name '{reward_name}' is allowed")
    
    # Skip ignored users
    if username and filtering.get("ignoredUsers"):
        ignored_users = filtering.get("ignoredUsers", [])
        # Case-insensitive comparison
        if any(username.lower() == ignored_user.lower() for ignored_user in ignored_users):
            logger.info(f"Skipping message from ignored user: {username}")
            return False, text
    
    # Skip commands if enabled (messages starting with ! or /)
    if filtering.get("skipCommands", True):
        stripped = text.strip()
        if stripped.startswith('!') or stripped.startswith('/'):
            logger.info(f"Skipping command message: {text[:50]}...")
            return False, text
    
    # Start with original text, apply filters progressively
    filtered_text = text
    
    # Remove emotes if enabled (and skip emote-only messages)
    if filtering.get("skipEmotes", False):
        # Use Twitch tags to detect and remove emotes if available
        if tags and "emotes" in tags and tags["emotes"]:
            # Twitch emotes tag format: "emoteid:start-end,start-end/emoteid:start-end"
            # Example: "25:0-4,6-10/1902:12-20" means emote 25 at positions 0-4 and 6-10, emote 1902 at 12-20
            emotes_tag = tags["emotes"]
            
            # Parse emote positions to get character ranges that are emotes
            emote_ranges = []
            try:
                for emote_data in emotes_tag.split('/'):
                    if ':' not in emote_data:
                        continue
                    emote_id, positions = emote_data.split(':', 1)
                    for pos_range in positions.split(','):
                        if '-' in pos_range:
                            start, end = pos_range.split('-')
                            # Emote positions are byte positions (inclusive on both ends)
                            emote_ranges.append((int(start), int(end)))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse emotes tag '{emotes_tag}': {e}")
            
            if emote_ranges:
                # Sort ranges by start position
                emote_ranges.sort()
                
                # Build a set of all character positions that are part of emotes
                emote_positions_set = set()
                for start, end in emote_ranges:
                    for i in range(start, end + 1):  # inclusive range
                        emote_positions_set.add(i)
                
                # Build text without emotes by keeping only non-emote characters
                text_without_emotes = ''.join(
                    char for i, char in enumerate(filtered_text) if i not in emote_positions_set
                )
                
                # Clean up extra whitespace
                text_without_emotes = re.sub(r'\s+', ' ', text_without_emotes).strip()
                
                # If nothing remains after removing emotes, skip the message entirely
                if not text_without_emotes:
                    logger.info(f"Skipping emote-only message: {text[:50]}...")
                    return False, text
                
                # Update filtered_text with emotes removed
                if text_without_emotes != filtered_text:
                    logger.info(f"Removed emotes from message: '{filtered_text[:50]}...' -> '{text_without_emotes[:50]}...'")
                    filtered_text = text_without_emotes
            # else: No valid emote ranges parsed, continue without emote filtering
        else:
            # Fallback: Simple check for common emote patterns if no tags available
            text_without_emotes = re.sub(r'\b\w+\d+\b', '', filtered_text)  # Remove emotes like PogChamp123
            text_without_emotes = re.sub(r'[^\w\s]', '', text_without_emotes)  # Remove special characters
            text_without_emotes = text_without_emotes.strip()
            
            if not text_without_emotes:
                logger.info(f"Skipping emote-only message (fallback detection): {text[:50]}...")
                return False, text
    
    # Remove URLs if enabled
    if filtering.get("removeUrls", True):
        # URL regex pattern that matches http/https, www, and common TLDs
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|[^\s]+\.(com|org|net|edu|gov|mil|int|co|io|ly|me|tv|fm|gg|tk|ml|ga|cf)[^\s]*'
        original_length = len(filtered_text)
        filtered_text = re.sub(url_pattern, '', filtered_text, flags=re.IGNORECASE)
        filtered_text = re.sub(r'\s+', ' ', filtered_text).strip()  # Clean up extra spaces
        
        if len(filtered_text) != original_length:
            logger.info(f"Removed URLs from message: '{text[:50]}...' -> '{filtered_text[:50]}...'")
    
    # Apply profanity filter if enabled
    profanity_config = filtering.get("profanityFilter", {})
    if profanity_config.get("enabled", False):
        custom_words = profanity_config.get("customWords", [])
        replacement = profanity_config.get("replacement", "beep")
        
        if custom_words:
            original_text = filtered_text
            
            for word in custom_words:
                if not word.strip():
                    continue
                    
                # Escape special regex characters in the word
                escaped_word = re.escape(word.strip())
                
                # Full replacement with word boundaries for case-insensitive matching
                pattern = r'\b' + escaped_word + r'\b'
                filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
            
            if filtered_text != original_text:
                logger.info(f"Applied profanity filter: '{original_text[:50]}...' -> '{filtered_text[:50]}...'")
    
    # Check minimum length (after filtering)
    min_length = filtering.get("minLength", 1)
    if len(filtered_text) < min_length:
        logger.info(f"Skipping message too short after filtering ({len(filtered_text)} < {min_length}): {filtered_text}")
        return False, filtered_text
    
    # Truncate if over maximum length
    max_length = filtering.get("maxLength", 500)
    if len(filtered_text) > max_length:
        truncated_text = filtered_text[:max_length].strip()
        # Try to end at a word boundary
        if ' ' in truncated_text:
            last_space = truncated_text.rfind(' ')
            if last_space > max_length * 0.8:  # Only use word boundary if it's not too short
                truncated_text = truncated_text[:last_space]
        
        logger.info(f"Truncating message from {len(filtered_text)} to {len(truncated_text)} characters")
        return True, truncated_text
    
    # Check if user is already speaking (ignore new messages while TTS is active)
    if filtering.get("ignoreIfUserSpeaking", False) and active_tts_jobs is not None:
        username_lower = username.lower() if username else ""
        
        # Check if user has any active TTS jobs
        user_has_active_tts = username_lower in active_tts_jobs
        
        if user_has_active_tts:
            logger.info(f"Ignored message from {username} due to active TTS: {filtered_text[:50]}...")
            return False, filtered_text

    # Check for spam (single user rate limiting)
    if username and filtering.get("enableSpamFilter", True):
        spam_threshold = filtering.get("spamThreshold", 5)
        spam_window = filtering.get("spamTimeWindow", 10)
        
        is_spam, reason = _message_history.is_spam(
            username, 
            max_messages=spam_threshold, 
            time_window_seconds=spam_window
        )
        
        if is_spam:
            logger.info(f"Skipping spam message: {reason}")
            return False, filtered_text
    
    # Add message to history for rate limiting tracking
    if username and filtering.get("enableSpamFilter", True):
        _message_history.add_message(username, filtered_text)
    
    return True, filtered_text


def reset_message_history():
    """Reset the global message history (useful for testing)"""
    global _message_history
    _message_history.clear()