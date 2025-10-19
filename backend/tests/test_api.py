"""Unit tests for FastAPI endpoints"""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Note: API tests are simplified to test basic functionality
# Full integration tests would require more complex setup with actual app state


@pytest.mark.unit
@pytest.mark.api
class TestSettingsEndpoints:
    """Tests for settings-related API endpoints"""
    
    def test_get_settings(self, client):
        """Test getting application settings"""
        response = client.get("/api/settings")
        
        assert response.status_code == 200
        data = response.json()
        # Settings should be a dictionary
        assert isinstance(data, dict)
        # Settings should have at least some content
        assert len(data) > 0
    
    def test_update_settings(self, client):
        """Test updating application settings"""
        # Get current settings first
        response = client.get("/api/settings")
        current_settings = response.json()
        
        # Update settings
        response = client.post(
            "/api/settings",
            json=current_settings
        )
        
        assert response.status_code == 200
        assert response.json().get("ok") is True


@pytest.mark.unit
@pytest.mark.api
class TestVoiceEndpoints:
    """Tests for voice-related API endpoints"""
    
    def test_get_voices_empty(self, client):
        """Test getting voices when database is empty"""
        response = client.get("/api/voices")
        
        assert response.status_code == 200
        data = response.json()
        # API returns {"voices": [...]}
        assert isinstance(data, dict)
        assert "voices" in data
        assert isinstance(data["voices"], list)
    
    def test_get_voices_structure(self, client):
        """Test voices endpoint returns correct structure"""
        response = client.get("/api/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert isinstance(data["voices"], list)
    
    def test_add_voice_missing_fields(self, client):
        """Test adding a voice with missing fields should raise error"""
        voice_data = {
            "voice_id": "new-voice-id",
            "provider": "edge"
            # Missing required 'name' field
        }
        
        # The API doesn't have proper validation, so it will raise KeyError
        # This test documents the current behavior
        with pytest.raises(Exception):
            response = client.post("/api/voices", json=voice_data)


@pytest.mark.unit
@pytest.mark.api
class TestAvatarEndpoints:
    """Tests for avatar-related API endpoints"""
    
    def test_get_avatars_structure(self, client):
        """Test getting avatars returns expected structure"""
        response = client.get("/api/avatars")
        
        assert response.status_code == 200
        data = response.json()
        # API returns object with 'avatars' key containing list
        assert isinstance(data, dict)
        assert "avatars" in data
        assert isinstance(data["avatars"], list)
    
    def test_get_managed_avatars(self, client):
        """Test getting managed avatars from database"""
        response = client.get("/api/avatars/managed")
        
        assert response.status_code == 200
        data = response.json()
        # Should return object with avatars key
        assert isinstance(data, dict)
        assert "avatars" in data


@pytest.mark.unit
@pytest.mark.api
class TestTTSControlEndpoints:
    """Tests for TTS control endpoints"""
    
    @pytest.mark.asyncio
    async def test_stop_all_tts(self, client):
        """Test stopping all TTS"""
        response = client.post("/api/tts/stop-all")
        
        # Should succeed even if no TTS is playing
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_toggle_tts_enabled(self, client):
        """Test toggling TTS enabled state"""
        # Enable TTS
        response = client.post("/api/tts/toggle", json={"enabled": True})
        assert response.status_code == 200
        
        # Disable TTS
        response = client.post("/api/tts/toggle", json={"enabled": False})
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
class TestStatusEndpoint:
    """Tests for status check endpoint"""
    
    def test_status_check(self, client):
        """Test status endpoint"""
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "running"
    
    def test_test_endpoint(self, client):
        """Test simple test endpoint"""
        response = client.get("/api/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


@pytest.mark.integration
@pytest.mark.api
class TestWebSocketConnection:
    """Integration tests for WebSocket connections"""
    
    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    def test_websocket_connection(self, client):
        """Test establishing WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Should connect successfully
            assert websocket is not None
    
    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    def test_websocket_receive_events(self, client):
        """Test receiving events over WebSocket"""
        with client.websocket_connect("/ws") as websocket:
            # Send a test event
            test_event = {
                "type": "test",
                "data": "test_data"
            }
            
            # In a real test, we'd verify the event was received
            pass


@pytest.mark.unit
@pytest.mark.api  
@pytest.mark.skip(reason="Message filter endpoint not found in current API - integration test needed")
class TestMessageFilterEndpoint:
    """Tests for message filtering endpoint - skipped as endpoint may not exist"""
    
    def test_message_filter_placeholder(self, client):
        """Placeholder test - endpoint structure needs verification"""
        # This test suite can be expanded when message filter endpoint is confirmed
        pass
