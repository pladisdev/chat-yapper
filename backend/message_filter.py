"""
Message filtering utilities for duplicate and spam detection.

This module provides functionality to detect:
- Exact duplicate messages from the same user
- Similar messages within a time window (spam)
- Single-user spam (rate limiting)
- Multi-user coordinated spam (similar messages from different users)
"""

import time
import hashlib
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re


class MessageHistory:
    """
    Track recent messages for duplicate and spam detection.
    
    Uses in-memory data structures with automatic cleanup of old messages.
    """
    
    def __init__(self, max_age_seconds: int = 300):
        """
        Initialize message history tracker.
        
        Args:
            max_age_seconds: How long to keep messages in history (default 5 minutes)
        """
        self.max_age_seconds = max_age_seconds
        
        # Per-user message history: {username: [(timestamp, message, hash)]}
        self.user_messages: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        
        # Global message history for multi-user spam detection: [(timestamp, message, hash, username)]
        self.global_messages: deque = deque(maxlen=200)
        
        # Per-user rate limiting: {username: [timestamp1, timestamp2, ...]}
        self.user_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def _cleanup_old_messages(self):
        """Remove messages older than max_age_seconds"""
        current_time = time.time()
        cutoff_time = current_time - self.max_age_seconds
        
        # Clean up user messages
        for username, messages in list(self.user_messages.items()):
            while messages and messages[0][0] < cutoff_time:
                messages.popleft()
            if not messages:
                del self.user_messages[username]
        
        # Clean up global messages
        while self.global_messages and self.global_messages[0][0] < cutoff_time:
            self.global_messages.popleft()
        
        # Clean up user timestamps
        for username, timestamps in list(self.user_timestamps.items()):
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()
            if not timestamps:
                del self.user_timestamps[username]
    
    def _normalize_message(self, text: str) -> str:
        """
        Normalize message for comparison.
        
        - Convert to lowercase
        - Remove extra whitespace
        - Remove common punctuation variations
        """
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove trailing punctuation variations (!!!, ???, etc.)
        normalized = re.sub(r'[!?.]+$', '', normalized)
        
        return normalized
    
    def _hash_message(self, text: str) -> str:
        """Create a hash of the normalized message"""
        normalized = self._normalize_message(text)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two messages.
        
        Returns:
            Float between 0.0 (completely different) and 1.0 (identical)
        """
        norm1 = self._normalize_message(text1)
        norm2 = self._normalize_message(text2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def add_message(self, username: str, text: str) -> None:
        """
        Add a message to history.
        
        Args:
            username: Username who sent the message
            text: Message text
        """
        self._cleanup_old_messages()
        
        timestamp = time.time()
        message_hash = self._hash_message(text)
        
        # Add to user history
        username_lower = username.lower()
        self.user_messages[username_lower].append((timestamp, text, message_hash))
        
        # Add to global history
        self.global_messages.append((timestamp, text, message_hash, username_lower))
        
        # Add timestamp for rate limiting
        self.user_timestamps[username_lower].append(timestamp)
    
    def is_duplicate(
        self, 
        username: str, 
        text: str, 
        time_window_seconds: int = 60
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if message is an exact duplicate within time window.
        
        Args:
            username: Username sending the message
            text: Message text
            time_window_seconds: Time window to check for duplicates
            
        Returns:
            (is_duplicate, reason)
        """
        self._cleanup_old_messages()
        
        username_lower = username.lower()
        message_hash = self._hash_message(text)
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds
        
        # Check user's recent messages
        if username_lower in self.user_messages:
            for timestamp, msg, msg_hash in self.user_messages[username_lower]:
                if timestamp < cutoff_time:
                    continue
                    
                if msg_hash == message_hash:
                    time_ago = int(current_time - timestamp)
                    return True, f"Duplicate message from {username} (sent {time_ago}s ago)"
        
        return False, None
    
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
        self._cleanup_old_messages()
        
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
    
    def is_similar_spam(
        self, 
        username: str, 
        text: str,
        similarity_threshold: float = 0.8,
        time_window_seconds: int = 60
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is sending very similar messages (variation spam).
        
        Args:
            username: Username to check
            text: Message text
            similarity_threshold: Minimum similarity to consider spam (0.0-1.0)
            time_window_seconds: Time window to check
            
        Returns:
            (is_spam, reason)
        """
        self._cleanup_old_messages()
        
        username_lower = username.lower()
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds
        
        if username_lower not in self.user_messages:
            return False, None
        
        # Check for similar messages
        for timestamp, msg, _ in self.user_messages[username_lower]:
            if timestamp < cutoff_time:
                continue
            
            similarity = self._calculate_similarity(text, msg)
            
            if similarity >= similarity_threshold and msg != text:
                return True, f"Similar message detected from {username} (similarity: {similarity:.2f})"
        
        return False, None
    
    def is_multi_user_spam(
        self,
        text: str,
        min_users: int = 3,
        similarity_threshold: float = 0.85,
        time_window_seconds: int = 30
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if multiple users are sending similar messages (coordinated spam).
        
        Args:
            text: Message text to check
            min_users: Minimum number of users for coordinated spam
            similarity_threshold: Minimum similarity to consider coordinated
            time_window_seconds: Time window to check
            
        Returns:
            (is_spam, reason)
        """
        self._cleanup_old_messages()
        
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds
        
        # Track unique users with similar messages
        similar_users = set()
        
        for timestamp, msg, _, msg_username in self.global_messages:
            if timestamp < cutoff_time:
                continue
            
            similarity = self._calculate_similarity(text, msg)
            
            if similarity >= similarity_threshold:
                similar_users.add(msg_username)
        
        if len(similar_users) >= min_users:
            return True, f"Coordinated spam detected ({len(similar_users)} users with similar messages)"
        
        return False, None
    
    def clear(self):
        """Clear all message history (useful for testing)"""
        self.user_messages.clear()
        self.global_messages.clear()
        self.user_timestamps.clear()
    
    def get_stats(self) -> Dict:
        """Get statistics about current message history"""
        return {
            "tracked_users": len(self.user_messages),
            "total_user_messages": sum(len(msgs) for msgs in self.user_messages.values()),
            "total_global_messages": len(self.global_messages),
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
