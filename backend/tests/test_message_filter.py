"""Unit tests for message filtering (duplicate and spam detection)"""
import pytest
import time
from message_filter import MessageHistory, get_message_history, reset_message_history


@pytest.fixture
def message_history():
    """Create a fresh message history for each test"""
    history = MessageHistory(max_age_seconds=300)
    history.clear()
    yield history
    history.clear()


@pytest.mark.unit
@pytest.mark.filtering
class TestMessageHistory:
    """Tests for MessageHistory data structure"""
    
    def test_create_message_history(self, message_history):
        """Test creating a message history instance"""
        assert message_history is not None
        assert message_history.max_age_seconds == 300
        stats = message_history.get_stats()
        assert stats["tracked_users"] == 0
        assert stats["total_timestamps"] == 0
    
    def test_add_message(self, message_history):
        """Test adding a message to history"""
        message_history.add_message("TestUser", "Hello world")
        
        stats = message_history.get_stats()
        assert stats["tracked_users"] == 1
        assert stats["total_timestamps"] == 1
    
    def test_add_multiple_messages_same_user(self, message_history):
        """Test adding multiple messages from same user"""
        message_history.add_message("TestUser", "Message 1")
        message_history.add_message("TestUser", "Message 2")
        message_history.add_message("TestUser", "Message 3")
        
        stats = message_history.get_stats()
        assert stats["tracked_users"] == 1
        assert stats["total_timestamps"] == 3
    
    def test_add_messages_different_users(self, message_history):
        """Test adding messages from different users"""
        message_history.add_message("User1", "Hello")
        message_history.add_message("User2", "World")
        message_history.add_message("User3", "Test")
        
        stats = message_history.get_stats()
        assert stats["tracked_users"] == 3
        assert stats["total_timestamps"] == 3


@pytest.mark.unit
@pytest.mark.filtering
@pytest.mark.skip(reason="Duplicate detection feature removed for simplification")
class TestDuplicateDetection:
    """Tests for duplicate message detection"""
    
    def test_exact_duplicate_same_case(self, message_history):
        """Test detecting exact duplicate with same case"""
        message_history.add_message("TestUser", "Hello world")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello world", 60)
        
        assert is_dup is True
        assert "Duplicate message" in reason
        assert "TestUser" in reason
    
    def test_exact_duplicate_different_case(self, message_history):
        """Test detecting duplicate with different case"""
        message_history.add_message("TestUser", "Hello World")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "hello world", 60)
        
        assert is_dup is True  # Should normalize case
        assert "Duplicate message" in reason
    
    def test_duplicate_different_user(self, message_history):
        """Test that different users can send same message"""
        message_history.add_message("User1", "Hello world")
        
        is_dup, reason = message_history.is_duplicate("User2", "Hello world", 60)
        
        assert is_dup is False  # Different user, not a duplicate for User2
    
    def test_duplicate_outside_time_window(self, message_history):
        """Test that old duplicates are not detected"""
        message_history.add_message("TestUser", "Hello world")
        
        # Check with very short time window (message is now "old")
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello world", time_window_seconds=0.001)
        
        time.sleep(0.01)  # Wait longer than time window
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello world", time_window_seconds=0.001)
        
        assert is_dup is False  # Outside time window
    
    def test_duplicate_with_extra_punctuation(self, message_history):
        """Test that extra punctuation is normalized"""
        message_history.add_message("TestUser", "Hello world")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello world!!!", 60)
        
        assert is_dup is True  # Punctuation normalized
    
    def test_duplicate_with_extra_whitespace(self, message_history):
        """Test that extra whitespace is normalized"""
        message_history.add_message("TestUser", "Hello   world")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello world", 60)
        
        assert is_dup is True  # Whitespace normalized
    
    def test_not_duplicate_different_message(self, message_history):
        """Test that different messages are not duplicates"""
        message_history.add_message("TestUser", "Hello world")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Goodbye world", 60)
        
        assert is_dup is False


@pytest.mark.unit
@pytest.mark.filtering
class TestSpamDetection:
    """Tests for spam/rate limiting detection"""
    
    def test_no_spam_under_threshold(self, message_history):
        """Test that normal message rate is not spam"""
        for i in range(3):
            message_history.add_message("TestUser", f"Message {i}")
        
        is_spam, reason = message_history.is_spam("TestUser", max_messages=5, time_window_seconds=10)
        
        assert is_spam is False
    
    def test_spam_at_threshold(self, message_history):
        """Test spam detection at exact threshold"""
        for i in range(5):
            message_history.add_message("TestUser", f"Message {i}")
        
        is_spam, reason = message_history.is_spam("TestUser", max_messages=5, time_window_seconds=10)
        
        assert is_spam is True
        assert "Rate limit exceeded" in reason
        assert "TestUser" in reason
        assert "5 messages" in reason
    
    def test_spam_above_threshold(self, message_history):
        """Test spam detection above threshold"""
        for i in range(10):
            message_history.add_message("TestUser", f"Message {i}")
        
        is_spam, reason = message_history.is_spam("TestUser", max_messages=5, time_window_seconds=10)
        
        assert is_spam is True
        assert "10 messages" in reason
    
    def test_spam_different_users_independent(self, message_history):
        """Test that different users have independent rate limits"""
        for i in range(10):
            message_history.add_message("User1", f"Message {i}")
        
        # User2 should not be affected by User1's spam
        is_spam, reason = message_history.is_spam("User2", max_messages=5, time_window_seconds=10)
        
        assert is_spam is False
    
    def test_spam_outside_time_window(self, message_history):
        """Test that old messages don't count toward spam"""
        # This test simulates waiting by using a very short time window
        for i in range(5):
            message_history.add_message("TestUser", f"Message {i}")
        
        time.sleep(0.01)
        
        # Check with time window that excludes all messages
        is_spam, reason = message_history.is_spam("TestUser", max_messages=5, time_window_seconds=0.001)
        
        assert is_spam is False


@pytest.mark.unit
@pytest.mark.filtering
@pytest.mark.skip(reason="Similar spam detection feature removed for simplification")
class TestSimilarSpamDetection:
    """Tests for similar message spam detection"""
    
    def test_similar_messages_detected(self, message_history):
        """Test detecting very similar messages"""
        message_history.add_message("TestUser", "This is a test message")
        
        is_spam, reason = message_history.is_similar_spam(
            "TestUser", 
            "This is a test message!", 
            similarity_threshold=0.8,
            time_window_seconds=60
        )
        
        assert is_spam is True
        assert "Similar message" in reason
    
    def test_similar_spam_different_user(self, message_history):
        """Test that similar messages from different users are not spam"""
        message_history.add_message("User1", "This is a test")
        
        is_spam, reason = message_history.is_similar_spam(
            "User2",
            "This is a test!",
            similarity_threshold=0.8,
            time_window_seconds=60
        )
        
        assert is_spam is False  # Different user
    
    def test_similar_spam_low_similarity(self, message_history):
        """Test that dissimilar messages are not flagged"""
        message_history.add_message("TestUser", "Hello world")
        
        is_spam, reason = message_history.is_similar_spam(
            "TestUser",
            "Goodbye universe",
            similarity_threshold=0.8,
            time_window_seconds=60
        )
        
        assert is_spam is False  # Messages too different
    
    def test_exact_duplicate_not_similar_spam(self, message_history):
        """Test that exact duplicates are not flagged as similar spam"""
        message_history.add_message("TestUser", "Hello world")
        
        # Exact duplicates should be caught by duplicate detection, not similar spam
        is_spam, reason = message_history.is_similar_spam(
            "TestUser",
            "Hello world",
            similarity_threshold=0.8,
            time_window_seconds=60
        )
        
        assert is_spam is False  # Exact match, not similar spam


@pytest.mark.unit
@pytest.mark.filtering
@pytest.mark.skip(reason="Multi-user spam detection feature removed for simplification")
class TestMultiUserSpamDetection:
    """Tests for coordinated multi-user spam detection"""
    
    def test_multi_user_spam_detected(self, message_history):
        """Test detecting coordinated spam from multiple users"""
        # Three users send similar messages
        message_history.add_message("User1", "Check out this cool link!")
        message_history.add_message("User2", "Check out this cool link")
        message_history.add_message("User3", "Check out this cool link!!")
        
        is_spam, reason = message_history.is_multi_user_spam(
            "Check out this cool link",
            min_users=3,
            similarity_threshold=0.85,
            time_window_seconds=60
        )
        
        assert is_spam is True
        assert "Coordinated spam" in reason
        assert "3 users" in reason or "4 users" in reason  # Depends on if test message counts
    
    def test_multi_user_spam_under_threshold(self, message_history):
        """Test that coordinated spam needs minimum users"""
        # Only two users send similar messages
        message_history.add_message("User1", "Check out this cool link")
        message_history.add_message("User2", "Check out this cool link!")
        
        is_spam, reason = message_history.is_multi_user_spam(
            "Check out this cool link",
            min_users=3,
            similarity_threshold=0.85,
            time_window_seconds=60
        )
        
        assert is_spam is False  # Not enough users
    
    def test_multi_user_different_messages(self, message_history):
        """Test that different messages from multiple users are not spam"""
        message_history.add_message("User1", "Hello world")
        message_history.add_message("User2", "Goodbye universe")
        message_history.add_message("User3", "Testing 123")
        
        is_spam, reason = message_history.is_multi_user_spam(
            "Something completely different",
            min_users=3,
            similarity_threshold=0.85,
            time_window_seconds=60
        )
        
        assert is_spam is False  # Messages too different
    
    def test_multi_user_spam_case_insensitive(self, message_history):
        """Test multi-user spam detection is case-insensitive"""
        message_history.add_message("User1", "SPAM MESSAGE")
        message_history.add_message("User2", "spam message")
        message_history.add_message("User3", "Spam Message")
        
        is_spam, reason = message_history.is_multi_user_spam(
            "spam message",
            min_users=3,
            similarity_threshold=0.85,
            time_window_seconds=60
        )
        
        assert is_spam is True


@pytest.mark.unit
@pytest.mark.filtering
class TestMessageHistoryCleanup:
    """Tests for automatic cleanup of old messages"""
    
    def test_old_messages_cleaned(self):
        """Test that old messages are automatically cleaned up"""
        # Create history with very short max age
        history = MessageHistory(max_age_seconds=0.1)
        
        history.add_message("TestUser", "Old message")
        
        # Wait for message to age out
        time.sleep(0.15)
        
        # Add new message to trigger cleanup
        history.add_message("TestUser", "New message")
        
        stats = history.get_stats()
        # Old message should be cleaned up
        assert stats["total_timestamps"] == 1
    
    def test_clear_history(self, message_history):
        """Test clearing message history"""
        message_history.add_message("User1", "Message 1")
        message_history.add_message("User2", "Message 2")
        
        message_history.clear()
        
        stats = message_history.get_stats()
        assert stats["tracked_users"] == 0
        assert stats["total_timestamps"] == 0


@pytest.mark.unit
@pytest.mark.filtering
class TestGlobalMessageHistoryInstance:
    """Tests for the global message history singleton"""
    
    def test_get_global_instance(self):
        """Test getting the global message history instance"""
        history1 = get_message_history()
        history2 = get_message_history()
        
        assert history1 is history2  # Same instance
    
    def test_reset_global_history(self):
        """Test resetting the global history"""
        history = get_message_history()
        history.add_message("TestUser", "Test message")
        
        reset_message_history()
        
        stats = history.get_stats()
        assert stats["total_timestamps"] == 0


@pytest.mark.unit
@pytest.mark.filtering
@pytest.mark.skip(reason="Edge case tests for removed duplicate detection functionality")
class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_empty_message(self, message_history):
        """Test handling empty messages"""
        message_history.add_message("TestUser", "")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "", 60)
        
        # Should handle empty messages without error
        assert is_dup is True
    
    def test_very_long_message(self, message_history):
        """Test handling very long messages"""
        long_message = "A" * 10000
        
        message_history.add_message("TestUser", long_message)
        
        is_dup, reason = message_history.is_duplicate("TestUser", long_message, 60)
        
        assert is_dup is True
    
    def test_special_characters(self, message_history):
        """Test handling special characters"""
        message_history.add_message("TestUser", "Hello 🎉🎊 world! @#$%^&*()")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Hello 🎉🎊 world! @#$%^&*()", 60)
        
        assert is_dup is True
    
    def test_unicode_normalization(self, message_history):
        """Test Unicode message handling"""
        message_history.add_message("TestUser", "Héllo wörld")
        
        is_dup, reason = message_history.is_duplicate("TestUser", "Héllo wörld", 60)
        
        assert is_dup is True
    
    def test_case_sensitive_usernames(self, message_history):
        """Test that usernames are case-insensitive"""
        message_history.add_message("TestUser", "Hello")
        
        # Same user different case
        is_dup, reason = message_history.is_duplicate("testuser", "Hello", 60)
        
        assert is_dup is True  # Should normalize username case
