"""
Message filtering utilities for rate limiting.

This module provides functionality for:
- Single-user spam (rate limiting) - prevents users from sending too many messages too quickly
"""

import time
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional


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


def reset_message_history():
    """Reset the global message history (useful for testing)"""
    global _message_history
    _message_history.clear()