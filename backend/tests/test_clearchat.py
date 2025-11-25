"""
Test Twitch CLEARCHAT event handling (bans/timeouts)
Tests that TTS is properly cancelled when users are banned or timed out
"""
import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch
from modules.twitch_listener import TwitchBot


class TestClearChatEvents:
    """Test CLEARCHAT event parsing and handling"""
    
    @pytest.fixture(autouse=True)
    def mock_twitch_credentials(self, monkeypatch):
        """Mock Twitch credentials for all tests in this class"""
        monkeypatch.setenv("TWITCH_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("TWITCH_CLIENT_SECRET", "test_client_secret")
    
    def test_normalize_tags_dict(self):
        """Test tag normalization with dict input"""
        from modules.twitch_listener import _normalize_tags
        
        tags = {"login": "testuser", "ban-duration": "600"}
        result = _normalize_tags(tags)
        
        assert isinstance(result, dict)
        assert result["login"] == "testuser"
        assert result["ban-duration"] == "600"
    
    def test_normalize_tags_none(self):
        """Test tag normalization with None input"""
        from modules.twitch_listener import _normalize_tags
        
        result = _normalize_tags(None)
        assert result == {}
    
    def test_normalize_tags_list(self):
        """Test tag normalization with list input"""
        from modules.twitch_listener import _normalize_tags
        
        tags = [{"login": "testuser"}, {"ban-duration": "600"}]
        result = _normalize_tags(tags)
        
        assert isinstance(result, dict)
        assert result["login"] == "testuser"
        assert result["ban-duration"] == "600"
    
    @pytest.mark.asyncio
    async def test_clearchat_ban_event(self):
        """Test ban event (no duration)"""
        events_received = []
        
        def on_event(event):
            events_received.append(event)
        
        # Create a mock bot instance
        bot = TwitchBot(
            token="oauth:test_token",
            nick="test_bot",
            channel="test_channel",
            on_event=on_event
        )
        
        # Simulate CLEARCHAT ban event
        tags = {
            "login": "banneduser",
            "target-user-id": "12345",
            "display-name": "BannedUser"
        }
        
        # Call the internal method
        bot._emit_clearchat("test_channel", tags)
        
        # Verify event was emitted
        assert len(events_received) == 1
        event = events_received[0]
        
        assert event["type"] == "moderation"
        assert event["eventType"] == "ban"
        assert event["target_user"] == "banneduser"
        assert event["duration"] is None
        assert "tags" in event
    
    @pytest.mark.asyncio
    async def test_clearchat_timeout_event(self):
        """Test timeout event (with duration)"""
        events_received = []
        
        def on_event(event):
            events_received.append(event)
        
        bot = TwitchBot(
            token="oauth:test_token",
            nick="test_bot",
            channel="test_channel",
            on_event=on_event
        )
        
        # Simulate CLEARCHAT timeout event
        tags = {
            "login": "timedoutuser",
            "target-user-id": "67890",
            "display-name": "TimedOutUser",
            "ban-duration": "600"  # 10 minutes
        }
        
        bot._emit_clearchat("test_channel", tags)
        
        # Verify event was emitted
        assert len(events_received) == 1
        event = events_received[0]
        
        assert event["type"] == "moderation"
        assert event["eventType"] == "timeout"
        assert event["target_user"] == "timedoutuser"
        assert event["duration"] == 600
        assert "tags" in event
    
    @pytest.mark.asyncio
    async def test_clearchat_chat_clear(self):
        """Test general chat clear (no target user)"""
        events_received = []
        
        def on_event(event):
            events_received.append(event)
        
        bot = TwitchBot(
            token="oauth:test_token",
            nick="test_bot",
            channel="test_channel",
            on_event=on_event
        )
        
        # Simulate CLEARCHAT without target user (general clear)
        tags = {}  # No target user
        
        bot._emit_clearchat("test_channel", tags)
        
        # Verify event was emitted
        assert len(events_received) == 1
        event = events_received[0]
        
        assert event["type"] == "moderation"
        assert event["eventType"] == "clear_chat"
        assert "target_user" not in event or event.get("target_user") is None
    
    @pytest.mark.asyncio
    async def test_clearchat_with_display_name_fallback(self):
        """Test CLEARCHAT using display-name when login not available"""
        events_received = []
        
        def on_event(event):
            events_received.append(event)
        
        bot = TwitchBot(
            token="oauth:test_token",
            nick="test_bot",
            channel="test_channel",
            on_event=on_event
        )
        
        # Tags with only display-name
        tags = {
            "display-name": "DisplayNameUser",
            "ban-duration": "300"
        }
        
        bot._emit_clearchat("test_channel", tags)
        
        # Verify event uses display-name
        assert len(events_received) == 1
        event = events_received[0]
        
        assert event["target_user"] == "DisplayNameUser"
        assert event["eventType"] == "timeout"
        assert event["duration"] == 300


class TestClearChatIntegration:
    """Integration tests for CLEARCHAT with TTS cancellation"""
    
    @pytest.mark.asyncio
    async def test_ban_cancels_active_tts(self):
        """Test that banning a user cancels their active TTS"""
        # This would require mocking the app's handle_event and TTS system
        # For now, this is a placeholder for integration testing
        pass
    
    @pytest.mark.asyncio
    async def test_timeout_cancels_active_tts(self):
        """Test that timing out a user cancels their active TTS"""
        # Placeholder for integration testing
        pass
    
    @pytest.mark.asyncio
    async def test_ban_removes_queued_messages(self):
        """Test that banning a user removes their queued messages"""
        # Placeholder for integration testing
        pass


if __name__ == "__main__":
    # Run tests with: python -m pytest backend/tests/test_clearchat.py -v
    pytest.main([__file__, "-v", "-s"])
